"""组合回测：交易所真实公共历史 K 线（现货 + USDT 永续）+ dual_ma 信号 + 风控仓位。

数据：data = {"spot": {symbol: df}, "perp": {symbol: df}}，均为官方公共 REST 拉取的已收盘 K 线。
  * 做多仓位的入场 / 止损 / 离场 / 计价全部用**现货** OHLC 与现货 ATR；
  * 做空仓位全部用**永续** OHLC 与永续 ATR；绝不拿现货价格代替永续价格。
  * 信号 = strategy.combine(现货信号, 永续信号)。
时间约定（无前视）：
  * 第 i-1 根收盘后的信号/ATR/权益 → 第 i 根开盘价成交；
  * 止损在第 i 根盘中按最高/最低价检查（跳空则按开盘价成交）；
  * 权益在第 i 根收盘按各自市场的收盘价计价。
未计资金费率与滑点（见 README）。
趋势过滤：入场时用第 i-1 根收盘价与该市场 SMA(trend_ma) 比较，只拦截逆势新开仓，不影响已有持仓离场。
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import rebalance as RB
from .risk import scale_to_room, size
from .settings import taker_rate
from .strategy import btc_regime_blocks_long, combine, name_vol_mult, port_vol_factor, indicators, market_of, side_of, trend_ok, chop_ok, elder_short_ok

BARS_PER_YEAR = {"15m": 35040, "1h": 8760, "4h": 2190, "1d": 365}


@dataclass
class Trade:
    symbol: str
    market: str
    side: str
    entry_time: str
    entry_price: float
    qty: float
    notional_usdt: float
    stop_price: float
    target_price: float = float("nan")  # 止盈价（tp_r = 0 时为 NaN）
    exit_time: str = ""
    exit_price: float = float("nan")
    exit_reason: str = ""
    pnl_usdt: float = 0.0
    fees_usdt: float = 0.0
    return_pct: float = 0.0
    bars_held: int = 0
    status: str = "open"
    adj_pnl_usdt: float = 0.0  # 调仓减仓部分已实现的毛盈亏（不含手续费）
    resizes: int = 0  # 调仓次数（rebalance_band > 0 时）


# 空头熔断影子账本的固定仓位口径（= 默认风控参数）
SHADOW_SIZING = {"starting_equity_usdt": 1000.0, "max_risk_per_trade": 0.05, "max_weight_per_name": 0.20, "max_gross_exposure": 1.0}


def short_breaker(data: dict[str, dict[str, pd.DataFrame]], cfg: dict) -> dict:
    """空头熔断（因果）：用同一套规则跑一本「只做空」的影子账本；
    若最近 N 根 K 线内已平仓的影子空单合计亏损（<0），则暂停新开空单。
    返回 {"mask": {open_time: bool}（第 i 根入场时是否暂停，只用 i 之前已平仓的单），
          "blocked_now": 下一根是否暂停, "trailing_pnl": 最近 N 根影子空单盈亏, "bars": N}。"""
    N = int(cfg["strategy"].get("short_breaker_bars", 0) or 0)
    if not N:
        return {"mask": {}, "blocked_now": False, "trailing_pnl": 0.0, "bars": 0}
    # 影子账本固定用标准仓位口径（与账户实际仓位上限无关）：否则熔断判断依赖 USDT 盈亏的正负号，
    # 改动单笔风险 / 单币权重会让影子盈亏在 0 附近翻号，整段回测结果跳变（2026-11-10 诊断，见 docs）。
    c = {**cfg, "strategy": {**cfg["strategy"], "short_breaker_bars": 0, "sar_hold_bars": 0},
         "risk": {**cfg["risk"], **SHADOW_SIZING, "allow_spot_long": False, "allow_perp_short": True}}
    res = run_backtest(data, c)
    tr, keys = res["trades"], res["bar_open_times"]
    pnl = pd.Series(0.0, index=keys)
    if len(tr):
        tr = tr[tr["status"] == "closed"]
        for t, p in zip(tr["exit_time"], tr["pnl_usdt"]):
            if t in pnl.index:
                pnl[t] += float(p)
    cum = pnl.cumsum()
    before = cum.shift(1).fillna(0.0)  # 第 i 根开盘时可知：截至 i-1 根已平仓
    trail = before - before.shift(N).fillna(0.0)
    now = float(cum.iloc[-1] - (cum.iloc[-1 - N] if len(cum) > N else 0.0))
    return {"mask": {t: bool(v < 0) for t, v in trail.items()}, "blocked_now": now < 0, "trailing_pnl": now, "bars": N}


def run_backtest(data: dict[str, dict[str, pd.DataFrame]], cfg: dict) -> dict:
    st, rk = cfg["strategy"], cfg["risk"]
    # 分市场 taker 费率：多单在现货、空单在永续成交（下一根开盘市价 = taker），每条市价腿各收一次
    FEE = {"spot": taker_rate(cfg, "spot"), "perp": taker_rate(cfg, "perp")}
    fee = max(FEE.values())  # 仅用于总敞口缩放时的保守预留
    start_eq = float(rk["starting_equity_usdt"])
    need = st["slow_ma"] + 2
    spot_d, perp_d = data.get("spot", {}), data.get("perp", {})
    syms = sorted(s for s in spot_d if s in perp_d and len(spot_d[s]) > need and len(perp_d[s]) > need)
    excluded = sorted((set(spot_d) | set(perp_d)) - set(syms))
    if not syms:
        raise ValueError("没有同时具备足够现货与永续历史 K 线的标的")
    ind = {m: {s: indicators(src[s], st["fast_ma"], st["slow_ma"], st["atr_period"], st.get("confirm_bars", 1), st.get("trend_ma", 0), int(st.get("chop_n", 0) or 0), int(st.get("elder_short_gate_n", 0) or 0)).set_index("open_time") for s in syms}
           for m, src in (("spot", spot_d), ("perp", perp_d))}
    idx = None
    for m in ind.values():
        for d in m.values():
            idx = d.index if idx is None else idx.intersection(d.index)
    idx = idx.sort_values()
    if len(idx) <= need:
        raise ValueError("现货与永续 K 线对齐后长度不足")

    def arr(m, col):
        return {s: ind[m][s].loc[idx, col].to_numpy() for s in syms}

    PX = {m: {c: arr(m, c) for c in ("open", "high", "low", "close", "atr", "signal", "trend_ma", "chop", "elder_bull")} for m in ("spot", "perp")}
    # 可选单币波动率封顶（name_vol_target，0 = 关闭）：多头用现货、空头用永续收盘算 m_t，第 i 根入场 / 调仓用 m_{i-1}
    nv_t, nv_l = float(st.get("name_vol_target", 0) or 0), int(st.get("name_vol_lookback", 120) or 120)
    el_n, el_x = int(st.get("elder_short_gate_n", 0) or 0), float(st.get("elder_short_gate_x", 0) or 0)
    NVM = {m: {s: name_vol_mult(PX[m]["close"][s], nv_t, nv_l, BARS_PER_YEAR.get(st["interval"], 2190)) for s in syms} for m in ("spot", "perp")}
    SB = short_breaker(data, cfg)["mask"] if st.get("short_breaker_bars") and rk["allow_perp_short"] else {}
    SIG = {s: combine(PX["spot"]["signal"][s], PX["perp"]["signal"][s]) for s in syms}
    # 可选 BTC 熊市体制过滤：BTC 现货收盘 < SMA_N（上一根）时不新开多单（不平已有仓）。BTCUSDT 不在数据里则不生效
    rg_n = int(st.get("btc_regime_ma", 0) or 0)
    RGL = np.zeros(len(idx), dtype=bool)
    if rg_n and "BTCUSDT" in spot_d:
        b = spot_d["BTCUSDT"].sort_values("open_time").set_index("open_time")
        RGL = btc_regime_blocks_long(b["close"], rg_n).reindex(idx).fillna(False).to_numpy(dtype=bool)
    MK = {"long": "spot", "short": "perp"}
    # 可选组合波动率目标（默认关闭，port_vol_target = 0）：每根开盘前用最近 port_vol_lookback 根收盘权益的年化波动 σ
    # 算 k = min(1, 目标/σ)，新开仓与调仓的单笔风险上限、单币权重上限都 × k（总敞口上限不变）。
    pv_t, pv_l = float(st.get("port_vol_target", 0) or 0), int(st.get("port_vol_lookback", 180) or 180)
    base_risk, base_w = float(rk["max_risk_per_trade"]), float(rk["max_weight_per_name"])
    cfg_eff = cfg

    def P(side, col, s):
        return PX[MK[side]][col][s]

    times = list(idx)
    ct = list(ind["spot"][syms[0]].loc[idx, "close_time"])
    warm = max(st["slow_ma"], st["atr_period"] + 1)
    realized = start_eq
    pos: dict[str, Trade] = {}
    added: set[str] = set()  # 已加过仓的持仓（每笔最多一次）
    pyr_k, pyr_f = float(st.get("pyramid_r", 0) or 0), float(st.get("pyramid_frac", 0) or 0)
    # 可选：固定止盈（默认关闭，tp_r = 0）。目标价 = 入场价 ± tp_r × R，R = |入场价 − 初始止损| = atr_stop_mult × ATR；
    # 触及即全部平仓。tp_reentry = False 时止盈后与止损一样锁定，直到信号改变才允许再开同向仓。
    tp_r, tp_re = float(st.get("tp_r", 0) or 0), bool(st.get("tp_reentry", False))
    rb_band, rb_mode = float(st.get("rebalance_band", 0) or 0), str(st.get("rebalance_mode", "stop") or "stop")
    entry_i: dict[str, int] = {}
    blocked: dict[str, int] = {}
    # 可选止损反手（stop-and-reverse，默认关闭 sar_hold_bars = 0）：第 i 根 ATR 止损后，第 i+1 根开盘开反向仓，
    # 单笔风险 / 单币权重上限 × sar_risk_mult，止损 = sar_atr_mult × ATR，持有 sar_hold_bars 根后按开盘价平仓（「反手时间」）
    # 或被自身止损；期间信号转向反手方向则转为正常持仓。原方向锁定照旧；反手仓止损后不再连环反手；反手多单同样受 btc_regime_ma 约束。
    sar_h, sar_k, sar_m = int(st.get("sar_hold_bars", 0) or 0), float(st.get("sar_risk_mult", 1.0) or 1.0), float(st.get("sar_atr_mult", 2.0) or 2.0)
    sarf: dict[str, int] = {}  # 反手仓 → 原锁定方向
    sarq: dict[str, int] = {}  # 本根止损、下一根待开的反手方向
    trades: list[Trade] = []
    curve = []
    prev_eq = start_eq

    def upnl(t: Trade, px: float) -> float:
        d = 1 if t.side == "long" else -1
        return d * t.qty * (px - t.entry_price)

    def close(s: str, px: float, when: str, reason: str, i: int):
        nonlocal realized
        t = pos.pop(s)
        sarf.pop(s, None)
        added.discard(s)
        f = abs(t.qty * px) * FEE[t.market]
        g = upnl(t, px)
        realized += g - f
        t.exit_time, t.exit_price, t.exit_reason = when, float(px), reason
        t.fees_usdt += f
        t.pnl_usdt = g + t.adj_pnl_usdt - t.fees_usdt
        t.return_pct = t.pnl_usdt / t.notional_usdt if t.notional_usdt else 0.0
        t.bars_held, t.status = i - entry_i.pop(s), "closed"
        trades.append(t)

    for i in range(warm + 1, len(times)):
        when = pd.Timestamp(times[i]).isoformat()
        # 1) 信号离场（用 i-1 收盘信号，在 i 开盘执行）
        for s in list(pos):
            want = side_of(SIG[s][i - 1])
            if s in sarf:
                if want == pos[s].side:
                    sarf.pop(s)
                    continue
                if i - entry_i[s] >= sar_h:
                    close(s, P(pos[s].side, "open", s)[i], when, "反手时间", i)
                continue
            if want != pos[s].side:
                close(s, P(pos[s].side, "open", s)[i], when, "信号反转" if want != "flat" else "信号转空仓", i)
        # 解除止损锁定
        for s in list(blocked):
            if SIG[s][i - 1] != blocked[s]:
                blocked.pop(s)
        # 2) 入场（同一根 K 线的多个新仓按剩余总敞口额度等比缩放）
        eq_prev = prev_eq
        pv_k = port_vol_factor([c["equity"] for c in curve[-(pv_l + 1):]], pv_t, pv_l, BARS_PER_YEAR.get(st["interval"], 2190)) if pv_t > 0 else 1.0
        risk_now, w_now = base_risk * pv_k, base_w * pv_k
        if pv_t > 0:
            cfg_eff = {**cfg, "risk": {**rk, "max_risk_per_trade": risk_now, "max_weight_per_name": w_now}}
        gross = sum(abs(t.qty) * P(t.side, "open", s)[i] for s, t in pos.items())
        want: dict = {}
        for s in syms:
            sg = int(SIG[s][i - 1])
            if s in pos or sg == 0 or s in blocked:
                continue
            if sg > 0 and not rk["allow_spot_long"] or sg < 0 and not rk["allow_perp_short"]:
                continue
            sd = side_of(sg)
            if sg < 0 and SB.get(when, False):
                continue
            if sg > 0 and RGL[i - 1]:
                continue
            if not trend_ok(sg, P(sd, "close", s)[i - 1], P(sd, "trend_ma", s)[i - 1], st.get("trend_ma", 0)):
                continue
            if not chop_ok(P(sd, "chop", s)[i - 1], int(st.get("chop_n", 0) or 0), float(st.get("chop_max", 50) or 50)):
                continue
            # 可选 Elder-Ray 空头闸门：现货上一根牛力 < −X（过度延伸）时不新开 / 反手开空
            if sg < 0 and not elder_short_ok(PX["spot"]["elder_bull"][s][i - 1], el_n, el_x):
                continue
            z = size(side=sd, equity=eq_prev, price=P(sd, "open", s)[i], atr=P(sd, "atr", s)[i - 1],
                     max_risk=risk_now * NVM[MK[sd]][s][i - 1], max_weight=w_now * NVM[MK[sd]][s][i - 1],
                     atr_mult=st["atr_stop_mult"])
            if z.notional > 0:
                want[s] = (sg, z)
        sarnew = set()
        for s, d in list(sarq.items()):
            if s in pos or s in want:
                continue
            if d > 0 and (RGL[i - 1] or not rk["allow_spot_long"]) or d < 0 and not rk["allow_perp_short"]:
                continue
            sd = side_of(d)
            z = size(side=sd, equity=eq_prev, price=P(sd, "open", s)[i], atr=P(sd, "atr", s)[i - 1],
                     max_risk=risk_now * NVM[MK[sd]][s][i - 1] * sar_k, max_weight=w_now * NVM[MK[sd]][s][i - 1] * sar_k,
                     atr_mult=sar_m)
            if z.notional > 0:
                want[s] = (d, z)
                sarnew.add(s)
        sarq.clear()
        room = eq_prev * float(rk["max_gross_exposure"]) - gross
        alloc = scale_to_room({s: z.notional for s, (_, z) in want.items()}, room, fee)
        for s, (sg, z) in want.items():
            notional = alloc[s]
            if notional < 1.0:
                continue
            px = P(side_of(sg), "open", s)[i]
            qty = notional / px
            f = notional * FEE[market_of(sg)]
            realized -= f
            tgt = float(px) + (1 if sg > 0 else -1) * tp_r * abs(float(px) - z.stop_price) if tp_r > 0 else float("nan")
            pos[s] = Trade(s, market_of(sg), side_of(sg), when, float(px), qty, notional, z.stop_price, tgt, fees_usdt=f)
            entry_i[s] = i
            if s in sarnew:
                sarf[s] = -sg
        # 2b) 可选：浮盈加仓（默认关闭，pyramid_r = 0）。前一根收盘浮盈 ≥ k×R（R = |入场价 − 止损|）
        #     时在本根开盘加仓一次：名义 = min(f × 原名义, 单币权重余量, 总敞口余量)；入场价改为加权均价，止损不动。
        if pyr_k > 0 and pyr_f > 0:
            room_add = eq_prev * float(rk["max_gross_exposure"]) - sum(abs(t.qty) * P(t.side, "open", q)[i] for q, t in pos.items())
            for s in list(pos):
                t = pos[s]
                if entry_i[s] == i or s in added:
                    continue
                d = 1 if t.side == "long" else -1
                R = abs(t.entry_price - t.stop_price)
                if R <= 0 or d * (P(t.side, "close", s)[i - 1] - t.entry_price) < pyr_k * R:
                    continue
                px = P(t.side, "open", s)[i]
                add_n = min(pyr_f * t.notional_usdt, eq_prev * w_now - abs(t.qty) * px, room_add)
                if add_n < 1.0:
                    continue
                aq = add_n / px
                realized -= add_n * FEE[t.market]
                t.entry_price = (t.qty * t.entry_price + aq * px) / (t.qty + aq)
                t.qty += aq
                t.notional_usdt += add_n
                t.fees_usdt += add_n * FEE[t.market]
                room_add -= add_n
                added.add(s)
        # 2c) 可选：持仓调仓（默认见 settings.rebalance_band；0 = 关闭）。用 i-1 收盘的权益 / ATR，在第 i 根开盘
        #     把已有持仓（本根新开的除外）调向目标名义：
        #       目标 = min(权益×单笔风险 / 止损距离%, 权益×单币权重)，止损距离按 rebalance_mode：
        #         "stop"：|开盘价 − 该仓现有止损| / 开盘价（保证按现有止损算的单笔风险 ≤ 上限）
        #         "atr" ：max(上式, atr_stop_mult×ATR / 开盘价)（随最新波动缩放，且仍不超过现有止损下的风险上限）
        #       所有已有仓的目标再按「总敞口额度 − 本根新开仓名义」等比缩放；
        #       |当前名义 − 目标| / 目标 > rebalance_band 才调整；先减后加，加仓受剩余总敞口限制；止损价不变。
        if rb_band > 0 and pos:
            held = {q: pos[q] for q in pos if entry_i[q] != i and q not in sarf}
            new_n = sum(abs(pos[q].qty) * P(pos[q].side, "open", q)[i] for q in pos if entry_i[q] == i)
            g_now = sum(abs(x.qty) * P(x.side, "open", y)[i] for y, x in pos.items())
            rb_plan = RB.plan(held, {q: float(P(t.side, "open", q)[i]) for q, t in held.items()},
                              {q: float(P(t.side, "atr", q)[i - 1]) for q, t in held.items()},
                              equity=eq_prev, new_notional=new_n, cfg=cfg_eff, gross_now=g_now, fee=fee,
                              name_mult={q: float(NVM[MK[t.side]][q][i - 1]) for q, t in held.items()})
            for it in rb_plan:  # 与引擎 _rebalance 同一个计划函数（qtw/rebalance.py）
                q, px, delta = it["symbol"], it["price"], it["delta_usdt"]
                t = pos[q]
                d = 1 if t.side == "long" else -1
                if delta < 0:
                    dq = -delta / px
                    f = -delta * FEE[t.market]
                    g = d * dq * (px - t.entry_price)
                    realized += g - f
                    t.adj_pnl_usdt += g
                    t.fees_usdt += f
                    t.notional_usdt -= dq * t.entry_price  # 名义 = 剩余数量 × 加权入场价
                    t.qty -= dq
                else:
                    aq = delta / px
                    f = delta * FEE[t.market]
                    realized -= f
                    t.entry_price = (t.qty * t.entry_price + aq * px) / (t.qty + aq)
                    t.qty += aq
                    t.notional_usdt += delta
                    t.fees_usdt += f
                t.resizes += 1
        # 3) 盘中止损 / 止盈。开盘已越过止盈价 → 按开盘价止盈；否则同一根同时触及时保守地先算止损。
        for s in list(pos):
            t = pos[s]
            ws = sarf.get(s)
            o, h, lo = P(t.side, "open", s)[i], P(t.side, "high", s)[i], P(t.side, "low", s)[i]
            tg = t.target_price
            if tp_r > 0 and ((t.side == "long" and o >= tg) or (t.side == "short" and o <= tg)):
                close(s, o, when, "止盈", i)
                if not tp_re:
                    blocked[s] = 1 if t.side == "long" else -1
            elif t.side == "long" and lo <= t.stop_price:
                close(s, min(o, t.stop_price), when, "ATR止损", i)
                blocked[s] = 1
                if ws is not None:
                    blocked[s] = ws
                elif sar_h > 0:
                    sarq[s] = -1
            elif t.side == "short" and h >= t.stop_price:
                close(s, max(o, t.stop_price), when, "ATR止损", i)
                blocked[s] = -1
                if ws is not None:
                    blocked[s] = ws
                elif sar_h > 0:
                    sarq[s] = 1
            elif tp_r > 0 and ((t.side == "long" and h >= tg) or (t.side == "short" and lo <= tg)):
                close(s, tg, when, "止盈", i)
                if not tp_re:
                    blocked[s] = 1 if t.side == "long" else -1
        # 4) 收盘计价
        eq = realized + sum(upnl(t, P(t.side, "close", s)[i]) for s, t in pos.items())
        g = sum(abs(t.qty) * P(t.side, "close", s)[i] for s, t in pos.items())
        n = sum((1 if t.side == "long" else -1) * t.qty * P(t.side, "close", s)[i] for s, t in pos.items())
        curve.append({"time": pd.Timestamp(ct[i]).isoformat(), "equity": eq, "gross_exposure": g,
                      "net_exposure": n, "positions": len(pos)})
        prev_eq = eq

    last_t = pd.Timestamp(ct[-1]).isoformat()
    open_trades = []
    for s, t in pos.items():
        t.exit_price = float(P(t.side, "close", s)[-1])
        t.pnl_usdt = upnl(t, t.exit_price) + t.adj_pnl_usdt - t.fees_usdt
        t.return_pct = t.pnl_usdt / t.notional_usdt
        t.exit_reason, t.bars_held = "持仓中（按最后收盘价估值）", len(times) - 1 - entry_i[s]
        open_trades.append(t)

    ec = pd.DataFrame(curve)
    ec["peak"] = ec["equity"].cummax()
    ec["drawdown"] = ec["equity"] / ec["peak"] - 1
    rets = ec["equity"].pct_change().dropna()
    bpy = BARS_PER_YEAR.get(st["interval"], 2190)
    sharpe = float(rets.mean() / rets.std() * math.sqrt(bpy)) if len(rets) > 2 and rets.std() > 0 else float("nan")
    closed = [t for t in trades]
    wins = [t for t in closed if t.pnl_usdt > 0]
    gp = sum(t.pnl_usdt for t in wins)
    gl = -sum(t.pnl_usdt for t in closed if t.pnl_usdt <= 0)
    end_eq = float(ec["equity"].iloc[-1])
    years = len(ec) / bpy
    btc = "BTCUSDT" if "BTCUSDT" in syms else syms[0]
    bh = float(PX["spot"]["close"][btc][-1] / PX["spot"]["open"][btc][warm + 1] - 1)
    summary = {
        "rule_id": st["rule_id"], "venue": cfg.get("venue", ""), "interval": st["interval"],
        "symbols": " ".join(syms), "start_time": ec["time"].iloc[0], "end_time": last_t,
        "bars": len(ec), "starting_equity_usdt": start_eq, "ending_equity_usdt": end_eq,
        "total_return": end_eq / start_eq - 1,
        "cagr": (end_eq / start_eq) ** (1 / years) - 1 if years > 0 and end_eq > 0 else float("nan"),
        "max_drawdown": float(ec["drawdown"].min()), "sharpe": sharpe,
        "closed_trades": len(closed), "open_trades": len(open_trades),
        "win_rate": len(wins) / len(closed) if closed else float("nan"),
        "profit_factor": gp / gl if gl > 0 else float("nan"),
        "avg_bars_held": float(np.mean([t.bars_held for t in closed])) if closed else float("nan"),
        "fees_usdt": sum(t.fees_usdt for t in closed + open_trades),
        "stop_exits": sum(1 for t in closed if t.exit_reason == "ATR止损"),
        "take_profit_exits": sum(1 for t in closed if t.exit_reason == "止盈"),
        "avg_gross_exposure_pct": float((ec["gross_exposure"] / ec["equity"]).mean()),
        "benchmark": f"{btc} 现货买入持有", "benchmark_return": bh,
        "signal_rule": "combine(spot_sma, perp_sma): 现货多且永续不空→现货多；永续空且现货不多→永续空；冲突→空仓",
        "long_prices": "spot OHLC", "short_prices": "perp (USDT 永续) OHLC",
        "excluded_symbols": " ".join(excluded),
        "spot_signal_long_bars": int(sum((PX["spot"]["signal"][s][warm:] == 1).sum() for s in syms)),
        "perp_signal_short_bars": int(sum((PX["perp"]["signal"][s][warm:] == -1).sum() for s in syms)),
        "conflict_flat_bars": int(sum(((PX["spot"]["signal"][s][warm:] == 1) & (PX["perp"]["signal"][s][warm:] == -1)).sum() for s in syms)),
        "fee_bps": round(FEE["spot"] * 10_000, 4), "spot_taker_bps": round(FEE["spot"] * 10_000, 4), "perp_taker_bps": round(FEE["perp"] * 10_000, 4), "fast_ma": st["fast_ma"], "slow_ma": st["slow_ma"],
        "atr_stop_mult": st["atr_stop_mult"], "confirm_bars": st.get("confirm_bars", 1), "trend_ma": st.get("trend_ma", 0), "short_breaker_bars": st.get("short_breaker_bars", 0), "tp_r": tp_r, "tp_reentry": tp_re, "rebalance_band": rb_band, "rebalance_band_down": float(st.get("rebalance_band_down", 0) or 0), "rebalance_mode": rb_mode, "port_vol_target": pv_t, "port_vol_lookback": pv_l, "name_vol_target": nv_t, "name_vol_lookback": nv_l, "chop_n": int(st.get("chop_n", 0) or 0), "chop_max": float(st.get("chop_max", 50) or 50), "elder_short_gate_n": el_n, "elder_short_gate_x": el_x, "sar_hold_bars": sar_h, "sar_risk_mult": sar_k, "sar_atr_mult": sar_m,
        "resizes": int(sum(t.resizes for t in closed + open_trades)), "max_risk_per_trade": rk["max_risk_per_trade"],
        "max_weight_per_name": rk["max_weight_per_name"],
    }
    return {"summary": summary, "equity": ec.drop(columns=["peak"]), "bar_open_times": [pd.Timestamp(t).isoformat() for t in times],
            "trades": pd.DataFrame([asdict(t) for t in closed + open_trades])}
