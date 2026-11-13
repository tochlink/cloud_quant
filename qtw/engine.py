"""系统化信号 → 进出场时机 → 纸面执行（默认）/ 实盘（三重闸门）。"""
from __future__ import annotations

import csv
import logging
import math
import threading

import pandas as pd

from . import settings as S
from .live import guard
from .market import MarketDataError, get_client
from .market import cache as mcache
from .market.base import INTERVAL_MS
from . import db
from . import signal_log
from .paper import ORDER_COLS, PaperBook
from .paths import OUTPUT_DIR
from .backtest import short_breaker
from .risk import cap_at_entry, scale_to_room, size
from .strategy import bar_close_equity, btc_regime_blocks_long, combine, indicators, last_cross, market_of, name_vol_mult, port_vol_factor, side_of, trend_ok, chop_ok, elder_short_ok
from .timeutil import iso, la, sh, utcnow

log = logging.getLogger(__name__)
ADVICE = {1: "做多", -1: "做空", 0: "空仓"}
MARKET_CN = {"spot": "现货", "perp": "USDT 永续", "-": "—"}
_BOOK: PaperBook | None = None
_BOOK_LOCK = threading.Lock()
CYCLE_LOCK = threading.Lock()


def book(cfg: dict | None = None) -> PaperBook:
    global _BOOK
    with _BOOK_LOCK:
        if _BOOK is None:
            cfg = cfg or S.load()
            _BOOK = PaperBook(cfg["risk"]["starting_equity_usdt"], cfg["fees"].get("taker_bps", 4.0),
                              fee_by_market={m: S.taker_rate(cfg, m) for m in ("spot", "perp")})
        elif cfg:
            _BOOK.set_fees(float(cfg["fees"].get("taker_bps", 4.0)) / 10_000, {m: S.taker_rate(cfg, m) for m in ("spot", "perp")})
        if cfg:
            _MARK["venue"] = cfg["venue"]
        return _BOOK


_MARK = {"venue": None, "dirty": False}


def mark_from_stream(q) -> None:
    """WS/REST 实时报价回调：只给“同交易所 + 同市场”的纸面持仓计价（现货多用现货价，永续空用永续标记价）。"""
    if _BOOK is None or q.venue.lower() != _MARK["venue"]:
        return
    p = _BOOK.positions.get(q.symbol)
    if p and p.market == q.market:
        _BOOK.mark(q.symbol, q.price, iso(q.ts), q.data_source)
        _MARK["dirty"] = True


def persist_marks() -> bool:
    if _BOOK is not None and _MARK["dirty"]:
        _MARK["dirty"] = False
        _BOOK.save()
        return True
    return False


def _init_stop(p) -> float:
    v = float(getattr(p, "init_stop", 0) or 0)
    return v if v > 0 else float(p.stop_price)


def take_profit_hit(p, px: float, st: dict) -> bool:
    """固定止盈（与回测同一公式）：目标价 = 入场价 ± tp_r × |入场价 − 初始止损|；tp_r = 0 关闭。"""
    k = float(st.get("tp_r", 0) or 0)
    R = abs(p.entry_price - _init_stop(p))
    if k <= 0 or R <= 0:
        return False
    return p.direction * (px - (p.entry_price + p.direction * k * R)) >= 0


def partial_tp_price(p, st: dict) -> float:
    """分批止盈价（与回测 backtest.partial_tp_target 同一公式）：入场价 ± tp_partial_r × R0。未持仓 / R0 = 0 返回 NaN。"""
    from .backtest import partial_tp_target
    return partial_tp_target(p.side, p.entry_price, _init_stop(p), float(st.get("tp_partial_r", 2.0) or 2.0))


def breakeven_price(p, st: dict, fee_rate: float) -> float:
    from .backtest import breakeven_stop
    return breakeven_stop(p.side, p.entry_price, fee_rate, bool(st.get("tp_be_fees", True)))


def exit_rule_cn(side: str, st: dict) -> str:
    """信号离场条件（白话）。"""
    k = int(st.get("confirm_bars", 1) or 1)
    iv = st.get("interval", "4h")
    if side == "long":
        return f"{iv} 收盘快线下穿慢线即平多（下一根开盘）"
    if side == "short":
        return f"{iv} 收盘快线上穿慢线即平空（下一根开盘）"
    return f"快慢线同向 {k} 根收盘确认后入场" if k > 1 else "快慢线交叉确认后入场"


def lot_floor(cfg: dict, sym: str, market: str, qty: float, px: float | None = None) -> float:
    """按交易所官方下单精度向下取整（qtw/lots.py）。精度拿不到时不下单（返回 0），绝不猜。"""
    from . import lots
    try:
        return lots.floor_qty(qty, lots.spec(cfg["venue"], sym, market), px)
    except Exception as e:  # noqa: BLE001
        log.warning("下单精度不可用 %s %s：%s", sym, market, e)
        return 0.0


def _exit_checks(cfg: dict, bk, s: str, p, px: float, kind: str, q, events: list, tag: str = "") -> bool:
    """CYCLE_LOCK 已持有。止损（ATR止损 / 保本止损）→ 固定止盈 → 分批止盈；与回测第 3 步同一顺序。
    返回 True 表示整仓已平。分批止盈按官方精度取整数量、吃单费率记账；剩余低于最小下单量时整仓止盈。"""
    st = cfg.get("strategy") or {}
    venue = cfg["venue"]
    side, mkt = p.side, p.market
    hit = (side == "long" and px <= p.stop_price) or (side == "short" and px >= p.stop_price)
    if hit or take_profit_hit(p, px, st):
        why = ("保本止损" if p.be_moved else "ATR止损") if hit else "止盈"
        if hit or not st.get("tp_reentry", False):
            bk.blocks[s] = p.direction
        qty = p.qty
        pnl = bk.close(s, px, kind, why, venue, data_source=q.data_source, price_time=iso(q.ts))
        _route(cfg, s, mkt, "close_long" if side == "long" else "close_short", qty, px)
        events.append(f"{s} 平{('多' if side == 'long' else '空')} {qty:.6g} @ {px:g}（{why}{tag}，盈亏 {pnl:+.2f}）")
        return True
    if st.get("tp_partial") and not p.tp_done:
        pt = partial_tp_price(p, st)
        if pt == pt and p.direction * (px - pt) >= 0:
            frac = float(st.get("tp_frac", 0.5) or 0.5)
            dq = lot_floor(cfg, s, mkt, p.qty * frac, px)
            rest = lot_floor(cfg, s, mkt, p.qty - dq, px)
            label = f"止盈（{float(st.get('tp_partial_r', 2.0)):g}R 平 {frac:.0%}）"
            if dq <= 0 or rest <= 0:  # 拆不开（低于最小下单量）：整仓止盈
                qty = p.qty
                pnl = bk.close(s, px, kind, "止盈", venue, data_source=q.data_source, price_time=iso(q.ts))
                _route(cfg, s, mkt, "close_long" if side == "long" else "close_short", qty, px)
                bk.blocks[s] = p.direction
                events.append(f"{s} 平{('多' if side == 'long' else '空')} {qty:.6g} @ {px:g}（止盈·仓位太小无法分批{tag}，盈亏 {pnl:+.2f}）")
                return True
            res = bk.resize(s, p.qty - dq, px, kind, label, venue, data_source=q.data_source, price_time=iso(q.ts))
            _route(cfg, s, mkt, "close_long" if side == "long" else "close_short", res["qty"], px)
            p.tp_done = 1
            msg = f"{s} 止盈{('多' if side == 'long' else '空')} {res['qty']:.6g} @ {px:g}（{label}{tag}，已实现 {res['pnl']:+.2f}）"
            if st.get("tp_breakeven"):
                be = breakeven_price(p, st, bk.fee_for(mkt))
                if p.direction * (be - p.stop_price) > 0:
                    p.stop_price, p.be_moved = be, 1
                    msg += f"；剩余止损移到保本 {be:.6g}"
            bk.save()
            events.append(msg)
    return False


def poll_stops(cfg: dict | None = None) -> list[str]:
    """Worker 周期之间用最新公共价检查 ATR 止损，避免最多等 interval_sec 才离场。

    只平仓已触及止损的纸面持仓；信号反转仍由 run_cycle 处理。拿不到报价就跳过该币。
    """
    events: list[str] = []
    if not CYCLE_LOCK.acquire(blocking=False):
        return events  # 正在跑完整周期，让 run_cycle 自己处理
    try:
        cfg = cfg or S.load()
        bk = book(cfg)
        venue = cfg["venue"]
        if not bk.positions:
            return events
        touched = False
        for s, p in list(bk.positions.items()):
            try:
                px, kind, q = _quote(venue, s, p.market)
            except MarketDataError:
                continue
            bk.mark(s, px, iso(q.ts), q.data_source)
            touched = True
            _exit_checks(cfg, bk, s, p, px, kind, q, events, "·实时")
        if events:
            bk.snapshot("；".join(events)[:240])
            export_paper_csv(cfg)
        elif touched:
            bk.save()
        return events
    finally:
        CYCLE_LOCK.release()



def _quote(venue: str, sym: str, market: str):
    """真实公共报价：现货最新价 / 永续标记价。

    优先用官方公共 WebSocket 推送的最新值（≤ 30 秒内），否则走官方公共 REST。
    失败抛 MarketDataError，绝不回退到虚构价格。
    """
    from . import stream
    q = stream.latest(venue, sym, market, max_age_sec=30)
    if q is None:
        q = get_client(venue).quote(sym, market)
    return q.price, q.kind, q




_SB_CACHE: dict = {}


def _short_breaker_state(frames: dict, cfg: dict) -> dict:
    """空头熔断当前状态（影子只做空账本，按最新已收盘 K 线缓存）。失败时不熔断并给出原因。"""
    st = cfg["strategy"]
    if not st.get("short_breaker_bars") or not cfg["risk"].get("allow_perp_short"):
        return {"blocked_now": False, "trailing_pnl": 0.0, "bars": 0, "error": ""}
    try:
        last = max(str(df["open_time"].iloc[-1]) for m in frames.values() for df in m.values())
        key = (cfg["venue"], last, repr(sorted(st.items())), repr(sorted(cfg["risk"].items())), tuple(cfg["symbols"]), repr(sorted(cfg["fees"].items())))
        if key not in _SB_CACHE:
            _SB_CACHE.clear()
            r = short_breaker({"spot": frames.get("spot", {}), "perp": frames.get("perp", {})}, cfg)
            _SB_CACHE[key] = {"blocked_now": r["blocked_now"], "trailing_pnl": r["trailing_pnl"], "bars": r["bars"], "error": ""}
        return _SB_CACHE[key]
    except Exception as e:  # noqa: BLE001 — 熔断只是附加过滤，数据不足时不阻断主流程
        log.warning("空头熔断计算失败：%s", e)
        return {"blocked_now": False, "trailing_pnl": 0.0, "bars": int(st.get("short_breaker_bars") or 0), "error": str(e)}




def _held_row_without_signal(pos, eq: float, error: str, *, in_universe: bool, halted: bool) -> dict:
    """K 线不可用时仍展示持仓的真实止损与状态，避免持仓从信号列表消失。"""
    notional = abs(pos.qty * pos.mark_price)
    if halted:
        state = "halted"
    elif not in_universe:
        state = "held_outside"
    else:
        state = "holding"
    return {
        "symbol": pos.symbol, "market": pos.market, "market_cn": MARKET_CN.get(pos.market, pos.market),
        "side": pos.side, "signal": 0, "advice": ADVICE[pos.direction], "signal_market": pos.market,
        "ref_price": pos.mark_price, "ref_price_kind": "mark" if pos.market == "perp" else "last",
        "ref_price_time": pos.mark_time, "ref_price_source": pos.mark_source,
        "stop_price": pos.stop_price, "stop_source": "position", "stop_side": pos.side,
        "position_entry": pos.entry_price, "position_side": pos.side,
        "target_notional_usdt": notional, "target_qty": pos.qty,
        "target_weight": (notional / eq) if eq else 0,
        "risk_usdt": abs(pos.qty * (pos.stop_price - pos.mark_price)) if pos.direction * (pos.mark_price - pos.stop_price) > 0 else 0.0,
        "state": state, "in_universe": in_universe, "halted": halted,
        "error": "", "warning": error, "entry_timing": f"持有中：{pos.entry_time} 以 {pos.entry_price:g} 入场",
        "exit_timing": f"价格触及持仓止损 {pos.stop_price:g}（按入场价）时离场；信号因 K 线不可用暂无法判断",
    }


def _btc_regime_state(cfg: dict) -> dict:
    """BTC 熊市体制过滤（与回测同口径）：最新已收盘 BTC 现货收盘 < SMA_N 时不新开多单。
    BTC K 线取不到时不拦（并返回错误文本），历史不足 N 根时同样不拦。"""
    st = cfg["strategy"]
    n = int(st.get("btc_regime_ma", 0) or 0)
    if not n:
        return {"n": 0, "blocked": False, "error": ""}
    try:
        df = mcache.candles(cfg["venue"], "BTCUSDT", st["interval"], n + 5, "spot")
        b = btc_regime_blocks_long(df["close"], n)
        return {"n": n, "blocked": bool(b.iloc[-1]) if len(b) else False, "error": ""}
    except Exception as e:  # noqa: BLE001 —— 真实错误原样上报
        return {"n": n, "blocked": False, "error": str(e)}


BARS_PER_YEAR_MS = 365 * 24 * 3600 * 1000


def vol_scaled_cfg(cfg: dict, bk) -> dict:
    """可选组合波动率目标（strategy.port_vol_target > 0 才生效，默认关闭）：
    用账本按 K 线周期分桶后的收盘权益，取最近 port_vol_lookback 根算 k = min(1, 目标/年化σ)，
    返回单笔风险上限、单币权重上限都 × k 的配置副本（总敞口上限不变；只缩不放）；
    历史不足 lookback+1 根时 k = 1，与回测一致。已缩放过的配置原样返回。"""
    if "_pv_k" in cfg:
        return cfg
    st, rk = cfg["strategy"], cfg["risk"]
    t = float(st.get("port_vol_target", 0) or 0)
    k = 1.0
    if t > 0:
        ms = INTERVAL_MS[st["interval"]]
        k = port_vol_factor(bar_close_equity(bk.ledger(), ms), t, int(st.get("port_vol_lookback", 180) or 180), BARS_PER_YEAR_MS / ms)
    out = {**cfg, "_pv_k": k, "_pv_base_risk": rk}
    if k < 1.0:
        out["risk"] = {**rk, "max_risk_per_trade": float(rk["max_risk_per_trade"]) * k,
                       "max_weight_per_name": float(rk["max_weight_per_name"]) * k}
    return out


def listed_symbols(cfg: dict, bk=None) -> list[str]:
    """标的池 ∪ 当前持仓：已移出池但仍持有的标的也要出现在信号列表里，并继续接受止损 / 信号离场。"""
    out = []
    for s in list(cfg.get("symbols") or []) + list((bk or book(cfg)).positions):
        if s and s not in out:
            out.append(s)
    return out


def compute_signals(cfg: dict, with_quotes: bool = True) -> dict:
    cfg = vol_scaled_cfg(cfg, book(cfg))
    st, rk = cfg["strategy"], cfg["risk"]
    venue = cfg["venue"]
    need = max(st["lookback_bars"], st["slow_ma"] + st["atr_period"] + 5, int(st.get("trend_ma", 0) or 0) + 5,
               int(st.get("chop_n", 0) or 0) + 5)
    cn, cmax = int(st.get("chop_n", 0) or 0), float(st.get("chop_max", 50) or 50)
    en, ex = int(st.get("elder_short_gate_n", 0) or 0), float(st.get("elder_short_gate_x", 0) or 0)
    if en:
        need = max(need, 4 * en + 120)  # EMA / Wilder ATR 需要足够历史收敛，与长历史回测一致
    nv_t, nv_l = float(st.get("name_vol_target", 0) or 0), int(st.get("name_vol_lookback", 120) or 120)
    if nv_t > 0:
        need = max(need, nv_l + 5)  # 单币波动率封顶需要 lookback+1 根收盘
    if st.get("short_breaker_bars"):
        need = max(need, 400)  # 影子账本需要足够历史
    bk = book(cfg)
    syms = listed_symbols(cfg, bk)
    frames, errs = mcache.many(venue, syms, st["interval"], need)
    sb = _short_breaker_state(frames, cfg)
    rg = _btc_regime_state(cfg)
    eq = bk.equity()
    step = pd.Timedelta(milliseconds=INTERVAL_MS[st["interval"]])
    rows = []
    universe = set(cfg.get("symbols") or [])
    for sym in syms:
        ind = {}
        for m in ("spot", "perp"):
            df = frames.get(m, {}).get(sym)
            if df is not None and len(df) >= st["slow_ma"] + 1:
                ind[m] = indicators(df, st["fast_ma"], st["slow_ma"], st["atr_period"], st.get("confirm_bars", 1), st.get("trend_ma", 0), cn, en)
                ind[m].attrs.update(df.attrs)
        if not ind:
            pos = bk.positions.get(sym)
            err = "；".join(v for k, v in errs.items() if k.startswith(sym + ":")) or "K 线不足"
            if pos:
                rows.append(_held_row_without_signal(pos, eq, err, in_universe=sym in universe, halted=sym in bk.halts))
            else:
                rows.append({"symbol": sym, "error": err, "in_universe": sym in universe})
            continue
        ssig = int(ind["spot"]["signal"].iloc[-1]) if "spot" in ind else 0
        psig = int(ind["perp"]["signal"].iloc[-1]) if "perp" in ind else 0
        sig = int(combine([ssig], [psig])[0])
        side, mkt = side_of(sig), market_of(sig)
        use = mkt if mkt in ind else ("spot" if "spot" in ind else "perp")
        src = ind[use]
        last = src.iloc[-1]
        # 合成信号序列（两市场按开盘时间对齐）→ 信号起始时间
        if "spot" in ind and "perp" in ind:
            j = ind["spot"][["open_time", "close_time", "signal"]].merge(
                ind["perp"][["open_time", "signal"]], on="open_time", suffixes=("_s", "_p"))
            j["signal"] = combine(j["signal_s"], j["signal_p"])
        else:
            j = src[["open_time", "close_time", "signal"]].copy()
            if "perp" not in ind:
                j["signal"] = combine(j["signal"], [0] * len(j))
            else:
                j["signal"] = combine([0] * len(j), j["signal"])
        cross = last_cross(j)
        prev_sig = None  # 上一段信号（当前信号段开始前的方向），供信号变化日志使用
        if cross is not None:
            hit = j.index[j["close_time"].eq(cross)]
            if len(hit):
                at = j.index.get_loc(hit[-1])
                prev_sig = int(j["signal"].iloc[at - 1]) if at > 0 else None
        as_of = last["close_time"]
        warn = [f"{m} 数据不可用：{errs.get(f'{sym}:{m}', 'K 线不足')}" for m in ("spot", "perp") if m not in ind]
        if "spot" in ind and "perp" in ind and ind["spot"]["close_time"].iloc[-1] != ind["perp"]["close_time"].iloc[-1]:
            warn.append("现货与永续最新收盘 K 线时间不一致")
        row = {
            "symbol": sym, "rule_id": st["rule_id"], "signal": sig, "advice": ADVICE[sig], "side": side,
            "market": mkt, "market_cn": MARKET_CN[mkt], "signal_market": use,
            "spot_signal": ssig, "perp_signal": psig, "conflict": bool(ssig == 1 and psig == -1),
            "bar_close": float(last["close"]),
            "sma_fast": float(last["sma_fast"]), "sma_slow": float(last["sma_slow"]), "atr": float(last["atr"]),
            "spot_close": float(ind["spot"]["close"].iloc[-1]) if "spot" in ind else None,
            "perp_close": float(ind["perp"]["close"].iloc[-1]) if "perp" in ind else None,
            "as_of": iso(as_of.to_pydatetime()), "as_of_la": la(as_of.to_pydatetime()),
            "as_of_sh": sh(as_of.to_pydatetime()),
            "signal_since": iso(cross.to_pydatetime()) if cross is not None else "",
            "prev_run_close": iso((cross - step).to_pydatetime()) if cross is not None else "",
            "next_check": iso((as_of + step).to_pydatetime()), "next_check_la": la((as_of + step).to_pydatetime()),
            "next_check_sh": sh((as_of + step).to_pydatetime()),
            "venue": venue, "data_source": src.attrs.get("data_source", ""), "source_host": src.attrs.get("source_host", ""),
            "fetched_at": src.attrs.get("fetched_at", ""), "candle_cache": src.attrs.get("cache", ""),
            "error": "", "warning": "；".join(warn), "prev_signal": prev_sig,
        }
        px, kind = float(last["close"]), "bar_close"
        if with_quotes and mkt != "-":
            try:
                px, kind, q = _quote(venue, sym, mkt)
                row.update(ref_price_time=iso(q.ts), ref_price_source=q.data_source, ref_price_host=q.source_host)
            except MarketDataError as e:
                row["error"] = f"报价失败：{e}"
        row["ref_price"], row["ref_price_kind"] = px, kind
        pos = bk.positions.get(sym)
        # 单币波动率封顶：用信号所在市场（多=现货、空=永续）最近已收盘 K 线算 m，与回测第 i 根用 m_{i-1} 一致
        nvm = float(name_vol_mult(src["close"].to_numpy(), nv_t, nv_l, BARS_PER_YEAR_MS / INTERVAL_MS[st["interval"]])[-1]) if nv_t > 0 else 1.0
        row["name_vol_mult"] = nvm
        z = size(side=side, equity=eq, price=px, atr=row["atr"], max_risk=rk["max_risk_per_trade"] * nvm,
                 max_weight=rk["max_weight_per_name"] * nvm, atr_mult=st["atr_stop_mult"])
        row.update({"target_notional_usdt": z.notional, "target_qty": z.qty, "target_weight": z.weight,
                    "stop_price": z.stop_price, "stop_pct": z.stop_pct, "risk_usdt": z.risk_usdt, "capped_by": z.capped_by})
        blocked = block_active(bk, sym, row)
        tl = int(st.get("trend_ma", 0) or 0)
        tma = float(last["trend_ma"]) if tl else float("nan")
        tok = trend_ok(sig, float(last["close"]), tma, tl)
        row.update({"trend_ma": tma if tl else None, "trend_ok": bool(tok)})
        if cn:
            cv = float(last["chop"])
            row["chop"] = cv if cv == cv else None
            if sig != 0 and not chop_ok(cv, cn, cmax):
                row["chop_ok"] = False
        if en:
            ev = float(ind["spot"]["elder_bull"].iloc[-1]) if "spot" in ind else float("nan")
            row["elder_bull"] = ev if ev == ev else None
            if sig < 0 and not elder_short_ok(ev, en, ex):
                row["elder_ok"] = False
        if rg["n"]:
            row["btc_regime_block_long"] = bool(rg["blocked"])
            if sig > 0 and rg["blocked"]:
                row["regime_ok"] = False
        row["suggested_stop_price"] = z.stop_price
        row["in_universe"] = sym in universe
        row["halted"] = sym in bk.halts
        if pos:
            # 已有持仓：始终展示账本里按入场价计算的真实止损（不是按现价重算的建议止损）
            entry = f"持有中：{pos.entry_time} 以 {pos.entry_price:g} 入场"
            exit_ = f"出现反向/归零信号（下次收盘检查 {row['next_check_sh']}）或价格触及止损 {pos.stop_price:g} 时离场"
            row["stop_price"] = pos.stop_price
            row["stop_source"] = "position"
            row["position_entry"] = pos.entry_price
            row["stop_side"] = pos.side
            if pos.side != side:
                state = "exit_pending"
                exit_ = f"信号已转为{ADVICE[sig]}，等待离场；持仓止损仍为 {pos.stop_price:g}（按入场价）"
            elif row["halted"]:
                state = "halted"
            elif not row["in_universe"]:
                state = "held_outside"
            else:
                state = "holding"
        elif sig == 0:
            entry, exit_, state = "无信号，保持空仓", "—", "flat"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        elif blocked:
            entry = "已止损，观望中：等待信号方向改变后再入场"
            exit_, state = "—", "blocked"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        elif sig < 0 and sb["blocked_now"]:
            entry = f"空头熔断中：最近 {sb['bars']} 根 K 线影子空单合计 {sb['trailing_pnl']:+.2f} USDT，暂不新开空单（转正后恢复）"
            exit_, state = "—", "short_paused"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        elif sig > 0 and row.get("regime_ok") is False:
            entry = f"BTC 熊市过滤中：BTC 现货收盘低于 SMA{rg['n']}，暂不新开多单（BTC 站回均线后恢复；已有持仓不受影响）"
            exit_, state = "—", "regime_wait"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        elif row.get("chop_ok") is False:
            cv = row.get("chop")
            entry = f"震荡指数闸门：CHOP{cn} = {cv:.1f} > {cmax:g}（震荡市），暂不新开 / 反手开仓（CHOP 回落后恢复；已有持仓不受影响）" if cv is not None else f"震荡指数 CHOP{cn} 尚未形成，暂不新开仓"
            exit_, state = "—", "chop_wait"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        elif row.get("elder_ok") is False:
            entry = f"Elder-Ray 空头闸门：现货牛力 {row['elder_bull']:.2f} < −{ex:g} ATR（整根 K 线低于 EMA{en}，空头过度延伸），暂不新开 / 反手开空（回到阈值内后恢复；已有持仓不受影响）"
            exit_, state = "—", "elder_wait"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        elif not tok:
            where = "下方" if sig > 0 else "上方"
            entry = f"信号有效，但收盘价在 SMA{tl} 趋势线{where}（趋势线 {tma:.6g}）：暂不开新仓"
            exit_, state = "—", "trend_wait"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        else:
            entry = f"信号自 {row['signal_since'] or '数据起点'} 生效 → 下一个执行周期按最新{('现货价' if mkt == 'spot' else '标记价')}入场"
            exit_ = f"止损 {z.stop_price:.6g}（{st['atr_stop_mult']}×ATR）；或收盘出现反向交叉时离场"
            state = "entry_pending"
            row["stop_source"] = "suggested"
            row["stop_side"] = side
        row.update({"entry_timing": entry, "exit_timing": exit_, "state": state,
                    "position_side": pos.side if pos else "flat"})
        rows.append(row)
    # 待入场标的：按剩余总敞口等比缩放后的建议仓位
    pend = {r["symbol"]: r for r in rows if r.get("state") == "entry_pending"}
    alloc = scale_to_room({s: r["target_notional_usdt"] for s, r in pend.items()},
                          eq * rk["max_gross_exposure"] - bk.gross(), bk.fee)
    for s, r in pend.items():
        if alloc[s] < r["target_notional_usdt"] - 1e-9:
            r["capped_by"] = "gross"
        r["target_notional_usdt"] = alloc[s]
        r["target_qty"] = alloc[s] / r["ref_price"] if r["ref_price"] else 0
        r["target_weight"] = alloc[s] / eq if eq else 0
        r["risk_usdt"] = alloc[s] * r["stop_pct"]
    led = bk.ledger()
    for r in rows:  # 已持仓的显示实际仓位，并用开仓数据回填真正收紧仓位的约束
        p = bk.positions.get(r["symbol"])
        if p and r.get("state") in ("holding", "exit_pending", "held_outside", "halted"):
            r["target_notional_usdt"] = abs(p.qty * p.mark_price)
            r["target_qty"] = p.qty
            r["target_weight"] = r["target_notional_usdt"] / eq if eq else 0
            r["risk_usdt"] = abs(p.qty * (p.stop_price - p.mark_price)) if p.direction * (p.mark_price - p.stop_price) > 0 else 0.0
            r["capped_by"] = cap_at_entry(
                entry_notional=p.notional_entry, entry_price=p.entry_price, stop_price=p.stop_price,
                entry_equity=_equity_near(led, p.entry_time, bk.starting),
                max_risk=cfg["_pv_base_risk"]["max_risk_per_trade"], max_weight=cfg["_pv_base_risk"]["max_weight_per_name"])
    _annotate_qty_tp(cfg, bk, rows)
    return {"generated_at": iso(utcnow()), "generated_at_la": la(utcnow()), "generated_at_sh": sh(utcnow()),
            "venue": venue, "equity": eq, "short_breaker": sb, "btc_regime": rg, "port_vol_k": cfg["_pv_k"],
            "rows": rows, "errors": errs}


def _annotate_qty_tp(cfg: dict, bk, rows: list[dict]) -> None:
    """每行补充：按官方精度取整后的下单数量（币 / 张）、分批止盈价、保本状态与信号离场条件（白话）。"""
    from . import lots
    from .backtest import partial_tp_target
    st = cfg["strategy"]
    k, frac = float(st.get("tp_partial_r", 2.0) or 2.0), float(st.get("tp_frac", 0.5) or 0.5)
    eq = bk.equity()
    for r in rows:
        if r.get("error"):
            continue
        p = bk.positions.get(r["symbol"])
        side = p.side if p else r.get("side")
        mkt = p.market if p else (r.get("market") if r.get("market") not in (None, "-") else None)
        r["exit_rule_cn"] = exit_rule_cn(side or "flat", st)
        r.update(tp_enabled=bool(st.get("tp_partial")), tp_r=k, tp_frac=frac, tp_breakeven=bool(st.get("tp_breakeven")),
                 tp_done=bool(p.tp_done) if p else False, be_moved=bool(p.be_moved) if p else False, tp_price=None)
        if side not in ("long", "short") or not mkt:
            continue
        if p:
            tp = partial_tp_target(side, p.entry_price, _init_stop(p), k)
            r["init_stop"] = _init_stop(p)
        else:
            tp = partial_tp_target(side, float(r.get("ref_price") or 0), float(r.get("stop_price") or 0), k)
        r["tp_price"] = tp if tp == tp else None
        try:
            lot = lots.spec(cfg["venue"], r["symbol"], mkt)
            r.update(lots.describe(lot))
            if p:
                q = float(p.qty)
            else:
                px = float(r.get("ref_price") or 0)
                q = lots.floor_qty(float(r.get("target_notional_usdt") or 0) / px, lot, px) if px > 0 else 0.0
                if r.get("target_notional_usdt") and q <= 0:
                    r["qty_note"] = "低于最小下单量"
                r["target_qty"] = q
                r["target_notional_usdt"] = q * px
                r["target_weight"] = q * px / eq if eq else 0
                if r.get("stop_pct"):
                    r["risk_usdt"] = q * px * float(r["stop_pct"])
            r["target_contracts"] = lots.contracts(q, lot) if lot.is_contract else None
        except Exception as e:  # noqa: BLE001 —— 精度拿不到：数量按未取整显示并注明
            r["qty_note"] = f"下单精度不可用：{e}"[:120]


def _equity_near(ledger: list[dict], when: str, fallback: float) -> float:
    """Ledger equity at or just before entry; else the first snapshot / starting capital."""
    if not ledger:
        return fallback
    before = [float(r["equity_usdt"]) for r in ledger if r.get("time") and when and r["time"] <= when]
    if before:
        return before[-1]
    return float(ledger[0].get("equity_usdt") or fallback)


def _log_order(**kw):
    book().log_order(**kw)


def _trader(cfg):
    from . import vault
    keys = vault.get_keys(cfg["venue"])
    if not keys:
        return None
    if cfg["venue"] == "okx":
        from .live.okx import OkxTrader
        return OkxTrader(keys, demo=cfg["live"]["okx_demo"])
    from .live.gate import GateTrader
    return GateTrader(keys, testnet=cfg["live"]["gate_testnet"])


def block_active(bk, sym: str, row: dict) -> bool:
    """止损锁是否仍然有效，与回测一致：止损之后只要有任一根已收盘 K 线的信号与被锁方向不同，就解锁。
    引擎可能错过中间的检查（停机/暂停），所以除了看最新信号，还看当前信号段之前那一段的
    最后一根 K 线是否在止损成交之后收盘。"""
    b = bk.blocks.get(sym)
    sig = int(row.get("signal") or 0)
    if not b or sig != b:
        return False
    prev_end, stop_t = row.get("prev_run_close") or "", bk.last_stop_time(sym)
    if prev_end and stop_t:
        try:
            if pd.Timestamp(prev_end) > pd.Timestamp(stop_t):
                return False
        except (ValueError, TypeError):
            pass
    return True


def clamp_spot_sell(tr, venue: str, sym: str, qty: float, price: float) -> tuple[float, str]:
    """现货平多（卖出）数量夹到交易所实际可用余额。

    OKX / Gate 现货市价买入的手续费默认从到手的币里扣（买 Q 实得约 Q × (1 − 0.10%)），账本按 Q 记，
    直接卖 Q 会因余额不足被拒、仓位留在交易所。卖出数量取 min(账本数量, 可用余额)，再按交易所步长向下取整。
    查不到余额时按原数量发（由交易所决定），不猜。返回 (数量, 说明)。"""
    fn = getattr(tr, "spot_available", None)
    if fn is None:
        return qty, ""
    try:
        avail = float(fn(sym[:-4] if sym.endswith("USDT") else sym))
    except Exception as e:  # noqa: BLE001
        return qty, f"可用余额查询失败，按账本数量发单：{e}"
    if avail + 1e-12 >= qty:
        return qty, ""
    from . import lots
    try:
        q = lots.floor_qty(avail, lots.spec(venue, sym, "spot"), price)
    except Exception:  # noqa: BLE001
        q = avail
    return q, f"可用余额 {avail:.12g} 小于账本数量 {qty:.12g}（买入手续费从币里扣），卖出 {q:.12g}"


def _halt_after_live_error(sym: str) -> str:
    """实盘发单失败时，纸面账本已经按成交记账（平仓已平 / 开仓已开），与交易所不再一致。
    自动暂停该币的信号自动开平（与界面「暂停」同一开关，持久化），避免在账本与交易所不一致时继续反手 / 重新开仓；
    ATR 止损仍按账本执行。核对交易所持仓后在界面恢复。返回写进订单日志的说明。"""
    try:
        bk = book()
        bk.halts.add(sym)
        bk.save()
        return "｜已自动暂停该币自动开平，请核对交易所持仓后恢复"
    except Exception as e:  # noqa: BLE001
        return f"｜自动暂停失败：{e}"[:60]


def _route(cfg, sym, market, action, qty, price):
    """纸面执行之外，若实盘闸门全部通过才会发单；否则只记录被拦截原因。"""
    mode = "live" if S.live_armed(cfg) else "paper"
    if mode == "paper":
        _log_order(mode="paper", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="paper_filled", detail="纸面成交")
        return "paper_filled"
    ok, reasons = guard.check(cfg, cfg["venue"])
    if not ok:
        _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="blocked", detail="；".join(reasons))
        return "blocked"
    try:
        tr = _trader(cfg)
        spec = get_client(cfg["venue"]).perp_spec(sym) if market == "perp" else None
        if market == "spot" and action == "close_long":
            qty, note = clamp_spot_sell(tr, cfg["venue"], sym, qty, price)
            if qty <= 0:
                _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=0,
                           ref_price=price, status="error", detail=(note[:240] + _halt_after_live_error(sym)))
                return "error"
        else:
            note = ""
        res = tr.place_order(cfg, sym, market, action, qty, price, spec)
        _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="sent", detail=((note + "｜") if note else "") + str(res)[:300])
        return "sent"
    except Exception as e:  # noqa: BLE001
        _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="error", detail=str(e)[:240] + _halt_after_live_error(sym))
        return "error"


def run_cycle(cfg: dict | None = None, note: str = "") -> dict:
    with CYCLE_LOCK:
        cfg = cfg or S.load()
        bk = book(cfg)
        cfg = vol_scaled_cfg(cfg, bk)  # 可选组合波动率目标：入场与调仓的风险/权重上限 × k（默认关闭 k=1）
        venue, st, rk = cfg["venue"], cfg["strategy"], cfg["risk"]
        # 取消勾选但仍有持仓的币（deselect_policy=keep）：照常按信号 / 止损管理到离场，但不再新开（入场只看 cfg["symbols"]）
        extra = [s for s in bk.positions if s not in cfg["symbols"]]
        sig = compute_signals({**cfg, "symbols": list(cfg["symbols"]) + extra} if extra else cfg, with_quotes=False)
        events, errors = [], dict(sig["errors"])
        rows = {r["symbol"]: r for r in sig["rows"] if not r.get("error")}
        # 1) 用最新公共价格给持仓计价
        prices = {}
        for s, p in list(bk.positions.items()):
            try:
                px, kind, q = _quote(venue, s, p.market)
                prices[s] = (px, kind, q)
                bk.mark(s, px, iso(q.ts), q.data_source)
            except MarketDataError as e:
                errors[s] = f"报价失败：{e}"
        # 2) 离场：信号改变 / 触及止损
        for s, p in list(bk.positions.items()):
            if s not in prices:
                continue
            px, kind, q = prices[s]
            reason = None
            row = rows.get(s)
            if row and row.get("side") != p.side and s not in bk.halts:
                reason = "信号反转" if row.get("side") != "flat" else "信号转空仓"
            elif _exit_checks(cfg, bk, s, p, px, kind, q, events):
                continue
            elif s not in bk.halts and fast_exit_now(cfg, s, p):
                reason = "快速离场"
                bk.blocks[s] = p.direction
            if reason:
                pnl = bk.close(s, px, kind, reason, venue, data_source=q.data_source, price_time=iso(q.ts))
                _route(cfg, s, p.market, "close_long" if p.side == "long" else "close_short", p.qty, px)
                events.append(f"{s} 平{('多' if p.side == 'long' else '空')} {p.qty:.6g} @ {px:g}（{reason}，盈亏 {pnl:+.2f}）")
        # 解除止损锁
        for s in list(bk.blocks):
            if s in rows and not block_active(bk, s, rows[s]):
                bk.blocks.pop(s)
        bk.save()
        # 3) 入场（多个新仓按剩余总敞口额度等比缩放，并预留手续费）
        eq = bk.equity()
        want = {}
        for s in cfg["symbols"]:
            r = rows.get(s)
            if not r or s in bk.positions or s in bk.halts or r["signal"] == 0 or block_active(bk, s, r) or r.get("trend_ok") is False or r.get("regime_ok") is False or r.get("chop_ok") is False or r.get("elder_ok") is False or r.get("state") == "short_paused":
                continue
            if r["side"] == "long" and not rk["allow_spot_long"] or r["side"] == "short" and not rk["allow_perp_short"]:
                continue
            try:
                px, kind, q = _quote(venue, s, r["market"])
            except MarketDataError as e:
                errors[s] = f"报价失败：{e}"
                continue
            # 止损所用 ATR 必须来自该市场自己的 K 线（做多=现货，做空=永续）
            if r["signal_market"] != r["market"]:
                errors[s] = f"{r['market']} K 线不可用，跳过入场"
                continue
            nvm = float(r.get("name_vol_mult", 1.0) or 1.0)  # 单币波动率封顶（compute_signals 已算）
            z = size(side=r["side"], equity=eq, price=px, atr=r["atr"], max_risk=rk["max_risk_per_trade"] * nvm,
                     max_weight=rk["max_weight_per_name"] * nvm, atr_mult=st["atr_stop_mult"])
            if z.notional > 0:
                want[s] = (r, px, kind, z, q)
        room = eq * rk["max_gross_exposure"] - bk.gross()
        alloc = scale_to_room({s: w[3].notional for s, w in want.items()}, room, bk.fee)
        for s, (r, px, kind, z, q) in want.items():
            if alloc[s] < 1.0:
                continue
            qty = lot_floor(cfg, s, r["market"], alloc[s] / px, px)  # 按官方精度向下取整（币数量 / 整张）
            if qty <= 0:
                errors[s] = f"建议 {alloc[s]:.2f} U 低于该市场最小下单量，未开仓"
                continue
            bk.open(symbol=s, market=r["market"], side=r["side"], qty=qty, price=px, price_kind=kind,
                    stop=z.stop_price, signal_bar=r["as_of"], reason=f"{r['advice']}信号（{st['rule_id']}）", venue=venue,
                    data_source=q.data_source, price_time=iso(q.ts))
            _route(cfg, s, r["market"], "open_long" if r["side"] == "long" else "open_short", qty, px)
            events.append(f"{s} 开{('多·现货' if r['side'] == 'long' else '空·永续')} {qty:.6g} @ {px:g}，止损 {z.stop_price:.6g}")
        opened = {s for s in want if s in bk.positions and alloc.get(s, 0) >= 1.0}
        # 4) 每根新收盘 K 线调仓一次（rebalance_band；公式与回测第 2c 步相同，见 qtw/rebalance.py）
        events += _rebalance(cfg, bk, {k: v for k, v in rows.items() if k in cfg["symbols"]}, opened, errors)
        # 5) 信号变化日志（旧 → 新 + 本周期对该标的的动作）
        try:
            acts = {}
            for e in events:
                sym_ = e.split(" ", 1)[0]
                acts[sym_] = (acts.get(sym_, "") + "；" if sym_ in acts else "") + e.split(" ", 1)[-1]
            signal_log.record([r for r in sig["rows"] if not r.get("error")], acts, venue, bk.conn)
        except Exception as e:  # noqa: BLE001 — 日志失败不影响交易
            log.warning("信号日志写入失败：%s", e)
        snap = bk.snapshot(note or ("; ".join(events)[:240] if events else "无变化"))
        export_paper_csv(cfg)
        return {"time": snap["time"], "time_la": la(utcnow()), "time_sh": sh(utcnow()), "events": events, "errors": errors, "snapshot": snap}



def rebalance_new_qty(cur: float, want: float, floor) -> float | None:
    """调仓目标数量按官方精度落地：差额向下取整（floor = 按步长 / 最小量 / 最小金额取整，低于最小返回 0）。
    差额取整为 0 → None（不动）；减仓后剩余持仓若低于最小下单量 / 最小金额也返回 None——
    否则会留下交易所无法再单独平掉的尘埃仓（分批止盈已有同样的保护）。"""
    dq = floor(abs(want - cur))
    if dq <= 0:
        return None
    new = cur + (dq if want > cur else -dq)
    if new <= 0:
        return None
    if new < cur and floor(new) <= 0:
        return None
    return new


def _rebalance(cfg, bk, rows: dict, opened: set, errors: dict) -> list[str]:
    """CYCLE_LOCK 已持有。新收盘 K 线后第一次周期：把已有持仓调向目标名义（见 qtw/rebalance.py）。"""
    from . import rebalance as RB
    st = cfg["strategy"]
    if float(st.get("rebalance_band", 0) or 0) <= 0 or not bk.positions:
        return []
    bars = [r["as_of"] for r in rows.values() if r.get("as_of")]
    if not bars:
        return []
    bar = max(bars)
    if RB.last_bar(bk.conn) == bar:
        return []  # 这根 K 线已评估过
    held, prices, kinds, atrs = {}, {}, {}, {}
    for s, p in bk.positions.items():
        r = rows.get(s)
        if s in opened or s in bk.halts or not r or r.get("side") != p.side or p.tp_done:  # 已分批止盈的不再调仓（与回测一致）
            continue
        try:
            px, kind, q = _quote(cfg["venue"], s, p.market)
        except MarketDataError as e:
            errors[s] = f"报价失败，跳过调仓：{e}"
            continue
        if not _px_ok(px):
            continue
        held[s], prices[s], kinds[s], atrs[s] = p, px, (kind, q), r.get("atr")
    new_n = sum(abs(bk.positions[s].qty * bk.positions[s].mark_price) for s in opened if s in bk.positions)
    plan = RB.plan(held, prices, atrs, equity=bk.equity(), new_notional=new_n, cfg=cfg, gross_now=bk.gross(), fee=bk.fee,
                   name_mult={s: float(rows[s].get("name_vol_mult", 1.0) or 1.0) for s in held})
    events = []
    for it in plan:
        s, px = it["symbol"], it["price"]
        p = bk.positions[s]
        kind, q = kinds[s]
        new_qty = rebalance_new_qty(p.qty, max(0.0, p.qty + it["delta_usdt"] / px),
                                    lambda x, _s=s, _m=p.market, _px=px: lot_floor(cfg, _s, _m, x, _px))
        if new_qty is None:
            continue  # 差额低于最小下单量，或减仓后剩余低于最小下单量（尘埃仓）
        side, mkt = p.side, p.market
        res = bk.resize(s, new_qty, px, kind, f"调仓（目标 {it['target_usdt']:.2f} USDT，偏离>{float(st['rebalance_band']):.0%}）",
                        cfg["venue"], data_source=q.data_source, price_time=iso(q.ts))
        if res["action"] == "reduce":
            _route(cfg, s, mkt, "close_long" if side == "long" else "close_short", res["qty"], px)
            events.append(f"{s} 减仓{('多' if side == 'long' else '空')} {res['qty']:.6g} @ {px:g}（调仓，已实现 {res['pnl']:+.2f}）")
        elif res["action"] == "add":
            _route(cfg, s, mkt, "open_long" if side == "long" else "open_short", res["qty"], px)
            events.append(f"{s} 加仓{('多' if side == 'long' else '空')} {res['qty']:.6g} @ {px:g}（调仓，止损不变 {p.stop_price:.6g}）")
    RB.set_last_bar(bk.conn, bar)
    return events


_FAST_CACHE: dict = {}


def fast_frame(cfg: dict, sym: str, market: str, tf: str, n: int):
    """快速层 K 线：5m / 1d 用官方原生 K 线；10m 由官方 1m 聚合（qtw/fastlayer.aggregate）。都走 SQLite 缓存。"""
    from . import fastlayer
    if tf == "10m":
        raw = mcache.candles(cfg["venue"], sym, "1m", min(3000, 10 * n + 20), market)
        return fastlayer.aggregate(raw, 10, 1)
    return mcache.candles(cfg["venue"], sym, tf, n, market)


def fast_exit_now(cfg: dict, sym: str, p) -> bool:
    """快速离场（strategy.fast_exit_tf ≠ off）：最新已收盘快周期 K 线（收盘晚于入场时间）已逆持仓方向破 EMA(n) 连续 confirm 根。
    与回测 FastSeries.walk 的 fast 事件同一判定（fastlayer.ema_break_flags）。数据拿不到时不触发。"""
    from . import fastlayer
    st = cfg.get("strategy") or {}
    tf = str(st.get("fast_exit_tf", "off") or "off")
    if tf == "off":
        return False
    n, k = int(st.get("fast_exit_n", 50) or 50), int(st.get("fast_exit_confirm", 2) or 1)
    try:
        df = fast_frame(cfg, sym, p.market, tf, max(4 * n, 200))
        if len(df) < n + k:
            return False
        if pd.Timestamp(df["close_time"].iloc[-1]) <= pd.Timestamp(p.entry_time):
            return False
        bl, bs = fastlayer.ema_break_flags(df["close"].to_numpy(), n, k)
        return bool((bl if p.side == "long" else bs)[-1])
    except Exception as e:  # noqa: BLE001
        log.warning("快速离场判断失败 %s：%s", sym, e)
        return False


def _px_ok(x) -> bool:
    try:
        v = float(x)
        return math.isfinite(v) and v > 0
    except (TypeError, ValueError):
        return False


def _official_fill_px(cfg, p):
    """官方公共价（优先新报价，否则该持仓最后一次真实标记价）。永不编造价格。"""
    try:
        px, kind, q = _quote(cfg["venue"], p.symbol, p.market)
        if not _px_ok(px):
            raise MarketDataError("报价无效")
        return px, kind, q.data_source, iso(q.ts)
    except MarketDataError:
        if _px_ok(getattr(p, "mark_price", None)) and p.mark_time:
            return p.mark_price, f"last_real_mark@{p.mark_time}", p.mark_source or "", p.mark_time
        raise


def _close_one(cfg, bk, symbol: str, reason: str) -> dict:
    """CYCLE_LOCK 已持有。按市价（taker、分市场）平掉一只纸面持仓；实盘仅在闸门全开时由 _route 发单。"""
    p = bk.positions.get(symbol)
    if not p:
        return {"ok": False, "error": f"当前无 {symbol} 持仓", "symbol": symbol}
    try:
        px, kind, src, pt = _official_fill_px(cfg, p)
    except MarketDataError as e:
        return {"ok": False, "error": f"无官方报价，未平仓：{e}", "symbol": symbol}
    if not _px_ok(px):
        return {"ok": False, "error": "无官方报价，未平仓（不会编造价格）", "symbol": symbol}
    side, mkt, qty = p.side, p.market, p.qty
    fee_rate = bk.fee_for(mkt)
    pnl = bk.close(symbol, px, kind, reason, cfg["venue"], data_source=src, price_time=pt)
    route_status = _route(cfg, symbol, mkt, "close_long" if side == "long" else "close_short", qty, px)
    return {
        "ok": True, "symbol": symbol, "market": mkt, "side": side, "qty": qty,
        "price": px, "price_kind": kind, "pnl": pnl, "fee_rate": fee_rate,
        "fee_bps": fee_rate * 10_000, "reason": reason,
        "live_armed": S.live_armed(cfg), "route_status": route_status,
        "events": [f"{symbol} 已平仓 @ {px:g}（{kind}），盈亏 {pnl:+.2f}"],
    }


def close_position(symbol: str, cfg: dict | None = None, reason: str = "手动平仓") -> dict:
    """按最新官方价手动平掉一只持仓。市价腿按该市场 taker 费率记账。实盘默认关闭。"""
    cfg = cfg or S.load()
    symbol = str(symbol or "").strip().upper()
    with CYCLE_LOCK:
        bk = book(cfg)
        out = _close_one(cfg, bk, symbol, reason)
        if out.get("ok"):
            bk.snapshot(f"{reason} {symbol}")
            export_paper_csv(cfg)
        return out


def flatten_all(cfg: dict | None = None, reason: str = "一键清仓") -> dict:
    """按最新官方价平掉全部纸面持仓。不关闭自动交易、不改变实盘开关（与紧急停止不同）。"""
    cfg = cfg or S.load()
    with CYCLE_LOCK:
        bk = book(cfg)
        events, errors, closed = [], {}, []
        for s in list(bk.positions):
            out = _close_one(cfg, bk, s, reason)
            if out.get("ok"):
                events.extend(out["events"])
                closed.append(out)
            else:
                errors[s] = out.get("error") or "平仓失败"
        if closed:
            bk.snapshot(f"{reason}：平掉 {len(closed)} 个持仓")
            export_paper_csv(cfg)
        return {
            "ok": not errors, "events": events, "errors": errors, "closed": closed,
            "live_armed": S.live_armed(cfg), "remaining": list(bk.positions),
        }


def set_halt(symbol: str, halted: bool, cfg: dict | None = None) -> dict:
    """停止/恢复该标的的信号自动开平。ATR 止损仍然生效。停止在平仓后仍阻止重新开仓，直到恢复。"""
    cfg = cfg or S.load()
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return {"ok": False, "error": "缺少标的", "halted": False}
    with CYCLE_LOCK:
        bk = book(cfg)
        if halted:
            bk.halts.add(symbol)
        else:
            bk.halts.discard(symbol)
        bk.save()
        return {"ok": True, "symbol": symbol, "halted": symbol in bk.halts}

def kill_switch(cfg: dict | None = None) -> dict:
    """紧急停止：关闭自动交易与实盘开关，并按最新公共价平掉全部纸面持仓。"""
    cfg = S.update({"worker": {"enabled": False}, "live": {"mode": "paper", "live_enabled": False, "confirm_phrase": ""}})
    from . import worker
    worker.stop()
    with CYCLE_LOCK:
        bk = book(cfg)
        events = []
        for s, p in list(bk.positions.items()):
            try:
                px, kind, q = _quote(cfg["venue"], s, p.market)
                src, pt = q.data_source, iso(q.ts)
            except MarketDataError:
                # 拿不到新报价时使用该持仓最后一次真实公共标记价（明确标注时间），不编造价格
                px, kind, src, pt = p.mark_price, f"last_real_mark@{p.mark_time}", p.mark_source, p.mark_time
            pnl = bk.close(s, px, kind, "紧急停止(Kill Switch)", cfg["venue"], data_source=src, price_time=pt)
            events.append(f"{s} 已平仓 @ {px:g}（{kind}），盈亏 {pnl:+.2f}")
        bk.snapshot("Kill Switch：全部平仓并停止自动交易")
        export_paper_csv(cfg)
    return {"time": iso(utcnow()), "events": events}


def export_paper_csv(cfg: dict) -> list[str]:
    """把纸面账本导出为 output/ 下的 CSV 交付物。"""
    bk = book(cfg)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    pos_rows = []
    for p in bk.positions.values():
        pos_rows.append({"symbol": p.symbol, "market": p.market, "side": p.side, "qty": p.qty,
                         "entry_price": p.entry_price, "entry_time": p.entry_time, "mark_price": p.mark_price,
                         "mark_time": p.mark_time, "mark_source": p.mark_source, "venue": p.venue, "stop_price": p.stop_price,
                         "notional_usdt": p.qty * p.mark_price,
                         "weight": p.qty * p.mark_price / bk.equity() if bk.equity() else 0,
                         "unrealized_pnl_usdt": p.upnl()})
    for name, rows in (("paper_positions.csv", pos_rows), ("paper_fills.csv", bk.fills()),
                       ("paper_trades.csv", bk.trade_records()), ("paper_ledger.csv", bk.ledger()),
                       ("paper_orders.csv", bk.orders(100000)[::-1])):
        path = OUTPUT_DIR / name
        cols = list(rows[0].keys()) if rows else ["empty"]
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        out.append(str(path))
    return out


def export_signals_csv(sig: dict) -> str:
    path = OUTPUT_DIR / "signals.csv"
    rows = [r for r in sig["rows"] if not r.get("error")]
    cols = ["symbol", "venue", "market", "data_source", "source_host", "fetched_at", "rule_id", "signal", "spot_signal",
            "perp_signal", "conflict", "advice", "signal_market", "ref_price", "ref_price_kind", "ref_price_time",
            "ref_price_source", "spot_close", "perp_close", "bar_close", "sma_fast",
            "sma_slow", "atr", "as_of", "signal_since", "next_check", "target_notional_usdt", "target_qty",
            "target_weight", "stop_price", "risk_usdt", "capped_by", "state", "entry_timing", "exit_timing"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return str(path)
