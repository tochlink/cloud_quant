"""多策略注册表（v7）。

每套策略 = id、中文名、说明、参数、信号函数（只用已收盘 K 线，第 t 根收盘信号 → 第 t+1 根开盘成交，无前视），
执行 / ATR 止损 / 仓位 / 分市场费率全部复用 backtest.run_backtest（多单现货、空单 USDT 永续）。
策略 #1（ma_trend）就是现有默认双均线，不传 signals，结果与原回测逐字节相同。

参数一律事先按文献常用值选定（见 docs/STRATEGY_FORMULAS.md「多策略」一节），不在 2026-03-05 之后的数据上调参。
状态（采用 / 观察 / 淘汰）由 output/research_multi_strategy_*.csv 的事先声明规则得出，写在 VERDICTS 里；
只有「采用 / 观察」的策略可以进影子纸面子账本（qtw.shadow），绝不影响默认 1000U 账本与实盘闸门。
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from . import backtest as B


# ---------- 通用小工具（只用已收盘数据） ----------
def _c(df):
    return df["close"].astype(float)


def _day_close_mask(df) -> np.ndarray:
    """该根 K 线收盘时刻是否为 UTC 00:00（日线收盘）。"""
    ct = pd.to_datetime(df["close_time"], utc=True)
    return ((ct.dt.hour == 0) & (ct.dt.minute == 0)).to_numpy()


def _hold_between(raw: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """只在 mask 为 True 的根更新信号，其余根沿用上一次的值（如每日 / 每周换仓）。"""
    out = np.zeros(len(raw), dtype=int)
    cur = 0
    for i in range(len(raw)):
        if mask[i]:
            cur = int(raw[i])
        out[i] = cur
    return out


def rsi(close: pd.Series, n: int) -> pd.Series:
    """Wilder RSI。"""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


# ---------- 信号函数：f(ind, idx, syms, p) -> {sym: np.ndarray[int]} ----------
def sig_donchian(ind, idx, syms, p):
    """唐奇安通道突破（海龟系统思路）：收盘 > 前 N 根最高价 → 多；收盘 < 前 N 根最低价 → 空；
    多单在收盘 < 前 M 根最低价时离场，空单在收盘 > 前 M 根最高价时离场（M < N，有状态）。"""
    N, M = int(p["entry_n"]), int(p["exit_n"])
    out = {}
    for s in syms:
        d = ind["spot"][s]
        c, h, lo = _c(d).to_numpy(), d["high"].astype(float), d["low"].astype(float)
        hn, ln = h.rolling(N).max().shift(1).to_numpy(), lo.rolling(N).min().shift(1).to_numpy()
        hm, lm = h.rolling(M).max().shift(1).to_numpy(), lo.rolling(M).min().shift(1).to_numpy()
        st = np.zeros(len(c), dtype=int)
        cur = 0
        for i in range(len(c)):
            if not (hn[i] == hn[i]):
                cur = 0
            elif cur == 1 and c[i] < lm[i]:
                cur = -1 if c[i] < ln[i] else 0
            elif cur == -1 and c[i] > hm[i]:
                cur = 1 if c[i] > hn[i] else 0
            elif cur == 0:
                cur = 1 if c[i] > hn[i] else (-1 if c[i] < ln[i] else 0)
            st[i] = cur
        out[s] = st
    return out


def sig_tsmom(ind, idx, syms, p):
    """时序动量（Moskowitz-Ooi-Pedersen 2012；加密货币 1–8 周动量见 Liu-Tsyvinski 2021）：
    多个回看期收益的符号投票，>0 做多、<0 做空；只在日线收盘时更新（日频换仓）。仓位按单币波动率封顶缩放。"""
    lbs = [int(x) for x in p["lookbacks"]]
    out = {}
    for s in syms:
        d = ind["spot"][s]
        c = _c(d)
        votes = sum(np.sign(c / c.shift(n) - 1).fillna(0).to_numpy() for n in lbs)
        ready = ~c.shift(max(lbs)).isna().to_numpy()
        raw = np.where(ready, np.sign(votes), 0).astype(int)
        out[s] = _hold_between(raw, _day_close_mask(d))
    return out


def sig_xsmom(ind, idx, syms, p):
    """横截面动量轮动：每 rebalance_days 天（日线收盘）按过去 lookback 根收益给 8 个币排序，
    做多前 top 名（现货），做空后 top 名（永续），其余空仓。"""
    lb, top, every = int(p["lookback"]), int(p["top"]), int(p["rebalance_days"])
    C = pd.DataFrame({s: _c(ind["spot"][s]).to_numpy() for s in syms})
    R = C / C.shift(lb) - 1
    dm = _day_close_mask(ind["spot"][syms[0]])
    ct = pd.to_datetime(ind["spot"][syms[0]]["close_time"], utc=True)
    day_no = (ct.astype("int64") // 86_400_000_000_000 if ct.dt.unit == "ns" else ct.dt.as_unit("ns").astype("int64") // 86_400_000_000_000).to_numpy()
    reb = dm & (day_no % every == 0)  # 按 UTC 纪元日编号对齐，任何数据起点都在同一天换仓
    raw = {s: np.zeros(len(C), dtype=int) for s in syms}
    for i in np.where(reb)[0]:
        r = R.iloc[i].dropna()
        if len(r) < 2 * top:
            continue
        o = r.sort_values()
        for s in o.index[-top:]:
            raw[s][i] = 1
        for s in o.index[:top]:
            raw[s][i] = -1
    return {s: _hold_between(raw[s], reb) for s in syms}


def sig_meanrev(ind, idx, syms, p):
    """短线均值回归（布林带 + RSI）：收盘跌破下轨且 RSI < lo → 多，回到中轨离场；
    收盘升破上轨且 RSI > hi → 空，回到中轨离场；最多持有 max_hold 根。"""
    n, k, rn, lo_, hi_, mh = int(p["bb_n"]), float(p["bb_k"]), int(p["rsi_n"]), float(p["rsi_lo"]), float(p["rsi_hi"]), int(p["max_hold"])
    out = {}
    for s in syms:
        d = ind["spot"][s]
        c = _c(d)
        m, sd = c.rolling(n).mean(), c.rolling(n).std()
        up, dn = (m + k * sd).to_numpy(), (m - k * sd).to_numpy()
        mid, r, cv = m.to_numpy(), rsi(c, rn).to_numpy(), c.to_numpy()
        st = np.zeros(len(cv), dtype=int)
        cur, held = 0, 0
        for i in range(len(cv)):
            if not (mid[i] == mid[i]):
                cur = 0
            elif cur == 1 and (cv[i] >= mid[i] or held >= mh):
                cur = 0
            elif cur == -1 and (cv[i] <= mid[i] or held >= mh):
                cur = 0
            elif cur == 0:
                cur = 1 if (cv[i] < dn[i] and r[i] < lo_) else (-1 if (cv[i] > up[i] and r[i] > hi_) else 0)
                held = 0
            held = held + 1 if cur else 0
            st[i] = cur
        out[s] = st
    return out


def sig_daily_4h(ind, idx, syms, p):
    """日线定方向 + 4h 择时：日线（UTC 收盘）SMA(fast_d) > SMA(slow_d) 为多头环境、反之空头环境；
    多头环境里 4h RSI 从 rsi_lo 下方回升穿越时入场做多（回调买入），空头环境里 RSI 从 rsi_hi 上方回落时做空；
    日线方向改变即离场（有状态）。"""
    fd, sd_, rn, lo_, hi_ = int(p["fast_d"]), int(p["slow_d"]), int(p["rsi_n"]), float(p["rsi_lo"]), float(p["rsi_hi"])
    out = {}
    for s in syms:
        d = ind["spot"][s]
        c = _c(d)
        dm = _day_close_mask(d)
        dc = c[dm]
        dirn = pd.Series(np.where(dc.rolling(fd).mean() > dc.rolling(sd_).mean(), 1, -1), index=dc.index)
        dirn[dc.rolling(sd_).mean().isna()] = 0
        dirv = dirn.reindex(c.index).ffill().fillna(0).astype(int).to_numpy()
        r = rsi(c, rn).to_numpy()
        st = np.zeros(len(c), dtype=int)
        cur = 0
        for i in range(1, len(c)):
            if dirv[i] == 0 or (cur and cur != dirv[i]):
                cur = 0
            if cur == 0:
                if dirv[i] == 1 and r[i - 1] < lo_ <= r[i]:
                    cur = 1
                elif dirv[i] == -1 and r[i - 1] > hi_ >= r[i]:
                    cur = -1
            st[i] = cur
        out[s] = st
    return out


# 每套策略对执行层（cfg.strategy）的覆盖：候选策略一律关闭 #1 专用的趋势过滤 / BTC 体制 / 确认根数（信号自带逻辑）
_NEUTRAL = {"trend_ma": 0, "btc_regime_ma": 0, "confirm_bars": 1, "short_breaker_bars": 0, "chop_n": 0, "elder_short_gate_n": 0}

STRATEGIES: list[dict] = [
    {"id": "ma_trend", "no": 1, "name": "双均线趋势（默认）", "interval": "4h", "kind": "趋势",
     "desc": "SMA50/150 交叉定方向，趋势线 MA100 过滤入场，2×ATR14 止损，确认 2 根，BTC 低于 MA1200 不开多。多单现货、空单永续。",
     "params": {"fast_ma": 50, "slow_ma": 150, "trend_ma": 100, "atr_stop_mult": 2.0, "confirm_bars": 2, "btc_regime_ma": 1200},
     "signal": None, "overrides": {}},
    {"id": "donchian", "no": 2, "name": "唐奇安通道突破", "interval": "4h", "kind": "突破",
     "desc": "收盘突破前 55 天（330 根 4h）最高价做多、跌破最低价做空；反向突破前 20 天（120 根）通道离场。2×ATR 止损。参数为海龟系统 2 的 55/20 天（只用 2026-03-05 前数据在 5 组里选出；事先的 20/10 天整段亏损）。",
     "params": {"entry_n": 330, "exit_n": 120, "atr_stop_mult": 2.0}, "signal": sig_donchian,
     "overrides": {"atr_stop_mult": 2.0}},
    {"id": "tsmom", "no": 3, "name": "时序动量（多周期投票）", "interval": "4h", "kind": "动量",
     "desc": "7 / 30 / 60 天收益符号投票定多空，每天 UTC 收盘换一次方向，始终在场；单币年化波动目标 60% 缩仓，4×ATR 灾难止损。",
     "params": {"lookbacks": [42, 180, 360], "atr_stop_mult": 4.0, "name_vol_target": 0.6}, "signal": sig_tsmom,
     "overrides": {"atr_stop_mult": 4.0, "name_vol_target": 0.6, "name_vol_lookback": 180}},
    {"id": "xsmom", "no": 4, "name": "横截面动量轮动", "interval": "4h", "kind": "轮动",
     "desc": "每 7 天按过去 30 天收益给 8 个币排名：做多前 2 名（现货）、做空后 2 名（永续），其余空仓；单币波动目标 60%，4×ATR 灾难止损。",
     "params": {"lookback": 180, "top": 2, "rebalance_days": 7, "atr_stop_mult": 4.0, "name_vol_target": 0.6}, "signal": sig_xsmom,
     "overrides": {"atr_stop_mult": 4.0, "name_vol_target": 0.6, "name_vol_lookback": 180}},
    {"id": "meanrev_1h", "no": 5, "name": "短线均值回归（1h 布林+RSI）", "interval": "1h", "kind": "均值回归",
     "desc": "1 小时 K 线：收盘跌破布林下轨(20,2)且 RSI14<30 做多、升破上轨且 RSI>70 做空，回到中轨或持有 24 根离场；2×ATR 止损。",
     "params": {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_lo": 30, "rsi_hi": 70, "max_hold": 24, "atr_stop_mult": 2.0},
     "signal": sig_meanrev, "overrides": {"atr_stop_mult": 2.0, "interval": "1h", "slow_ma": 150}},
    {"id": "daily_4h", "no": 6, "name": "日线定向 + 4h 回调入场", "interval": "4h", "kind": "多周期",
     "desc": "日线 SMA10>SMA50 只做多、反之只做空；4h RSI14 从 40 下方回升（空头从 60 上方回落）时入场，日线方向改变离场；2×ATR 止损。日线 10/50 只用 2026-03-05 前数据在 4 组里选出（事先为 20/50）。",
     "params": {"fast_d": 10, "slow_d": 50, "rsi_n": 14, "rsi_lo": 40, "rsi_hi": 60, "atr_stop_mult": 2.0},
     "signal": sig_daily_4h, "overrides": {"atr_stop_mult": 2.0}},
    {"id": "funding_carry", "no": 7, "name": "资金费率套利（期现对冲）", "interval": "8h", "kind": "套利",
     "desc": "同币现货多 + 永续空等额对冲（方向中性），最近 9 次（3 天）平均资金费率 > 0.01%/8h 时持有、< 0 时撤出，赚资金费。用 Gate 官方资金费率历史（OKX 公共接口只给约 3 个月）。",
     "params": {"window": 9, "enter_rate": 0.0001, "exit_rate": 0.0}, "signal": None, "overrides": {}, "separate_sim": True},
    {"id": "ma_trend_lsp", "no": 8, "name": "双均线 + 多空平价 + 风险预算（候选）", "interval": "4h", "kind": "趋势·仓位构建",
     "desc": "信号、止损、过滤与 #1 完全相同；只改仓位：较小一侧信号书的单币风险 / 权重上限放大到与较大一侧相同（最多 3 倍，ls_parity_cap 3），"
             "单笔风险 3%、组合波动目标 50%。多空永续 10× 下 walk-forward 12 格全胜 #1，180 天滚动窗口约八成更好、回撤九成不更差；"
             "2026-03-05 后 5/8 个月更好，尚未改默认（docs/STRATEGY_FORMULAS.md「C3+RB30」）。",
     "params": {"ls_parity_cap": 3.0, "max_risk_per_trade": 0.03, "port_vol_target": 0.5}, "signal": None,
     "overrides": {"ls_parity_cap": 3.0, "port_vol_target": 0.5}, "risk_overrides": {"max_risk_per_trade": 0.03}},
    {"id": "ma_trend_lsp_hp", "no": 9, "name": "#8 + 多空对冲对乘数（候选）", "interval": "4h", "kind": "趋势·仓位构建",
     "desc": "在 #8 之上再改仓位：某币持仓方向与另一币相反、且两币最近 180 根永续收益相关 ≥ 0.5 时（多空对冲对），"
             "该币单币风险 / 权重乘数 × 1.5（hedge_pair_w 180 / c 0.5 / h 1.5）；信号、止损、过滤与 #1 相同，总敞口上限不变。"
             "4 个 4h 相位收益与 2026-03 后都优于 #8，尚未改默认（docs/STRATEGY_FORMULAS.md「对冲对乘数」）。",
     "params": {"ls_parity_cap": 3.0, "max_risk_per_trade": 0.03, "port_vol_target": 0.5, "hedge_pair_w": 180, "hedge_pair_c": 0.5,
                "hedge_pair_h": 1.5}, "signal": None,
     "overrides": {"ls_parity_cap": 3.0, "port_vol_target": 0.5, "hedge_pair_w": 180, "hedge_pair_c": 0.5, "hedge_pair_h": 1.5},
     "risk_overrides": {"max_risk_per_trade": 0.03}},
]
BY_ID = {s["id"]: s for s in STRATEGIES}

# 研究结论（output/research_multi_strategy_*.csv，2026-11-13 PT），按事先声明规则得出；页面与影子子账本读取这里
RESEARCH_PATH = __import__("pathlib").Path(__file__).with_name("multi_strategy_research.json")


def load_research() -> dict:
    try:
        import json
        return json.loads(RESEARCH_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


VERDICTS: dict[str, dict] = load_research().get("verdicts", {})
# 仓位构建变体的结论来自单独研究（多空永续 10× 口径，与上面 JSON 的多策略对比口径不同），不写进 JSON
VERDICTS.setdefault("ma_trend_lsp", {"status": "观察", "reason": (
    "2026-11-13 研究（多空永续 10× + 官方资金费）：整段 Gate +214.9% / OKX +218.8%（#1 同口径 +163.3% / +165.4%），夏普 2.02 / 2.05，"
    "回撤 −15.1% / −15.2%，2026-03-05 后 +73.4% / +72.5%；按训练期 Sharpe 二选一的 walk-forward 12 格全胜 #1；2026-03 后逐月 5/8 更好，"
    "未达改默认余量。信号与 #1 相同，只改仓位，不进影子子账本。CSV：output/research_c3_rb30_walkforward_rolling_perp_both_10x.csv")})

VERDICTS.setdefault("ma_trend_lsp_hp", {"status": "观察", "reason": (
    "2026-11-13 研究（多空永续 10× + 官方资金费）：叠加在 ls_parity_cap 3 上整段 Gate +296.1% / OKX +323.4%（仅 C3 +230.6% / +237.7%），"
    "Sharpe 2.21 / 2.28，回撤约 −15%，12/12 安慰剂胜出，3 / 6 / 12 个月 walk-forward 真实费率全赢；4h 相位检验叠加 C3+RB30 后 4/4 相位收益与 "
    "2026-03 后都更高、Sharpe 不输。2026-03 后逐月 5/8 更好，未达改默认门槛。CSV：output/research_hedged_pair_phase_offset_perp_both_10x.csv")})


def strategy_cfg(cfg: dict, sid: str) -> dict:
    """在默认 cfg 上套该策略的执行层覆盖。#1 原样返回（深拷贝）；沿用 #1 信号的变体只覆盖仓位参数。"""
    c = copy.deepcopy(cfg)
    spec = BY_ID[sid]
    if spec["signal"] is None:
        # 沿用 #1 信号的仓位构建变体（如 ma_trend_lsp）：不套 _NEUTRAL，只覆盖仓位参数
        c["strategy"].update(spec.get("overrides") or {})
        c["risk"].update(spec.get("risk_overrides") or {})
        return c
    c["strategy"].update(_NEUTRAL)
    c["strategy"].update(spec["overrides"])
    return c


def signal_fn(sid: str):
    spec = BY_ID[sid]
    if spec["signal"] is None:
        return None
    return lambda ind, idx, syms: spec["signal"](ind, idx, syms, spec["params"])


def run(sid: str, data: dict, cfg: dict) -> dict:
    """跑一套策略的组合回测（同一执行引擎）。资金费率套利走独立模拟（qtw.carry），这里不支持。"""
    spec = BY_ID[sid]
    if spec.get("separate_sim"):
        raise ValueError("资金费率套利使用独立的期现对冲模拟")
    c = strategy_cfg(cfg, sid)
    res = B.run_backtest(data, c, signals=signal_fn(sid))
    if spec["signal"] is not None:
        res["summary"]["rule_id"] = sid
        res["summary"]["signal_rule"] = spec["desc"]
    res["summary"]["strategy_id"] = sid
    return res


def latest_signals(sid: str, data: dict, cfg: dict) -> dict:
    """最新一根已收盘 K 线上的目标方向 {sym: -1/0/1}（影子子账本在收盘事件里调用）。"""
    spec = BY_ID[sid]
    fn = signal_fn(sid)
    if fn is None or spec.get("separate_sim"):
        return {}
    syms = sorted(s for s in data.get("spot", {}) if s in data.get("perp", {}))
    ind = {m: {s: data[m][s].set_index("open_time", drop=False) for s in syms} for m in ("spot", "perp")}
    idx = None
    for m in ind.values():
        for d in m.values():
            idx = d.index if idx is None else idx.intersection(d.index)
    idx = idx.sort_values()
    al = {m: {s: ind[m][s].loc[idx] for s in syms} for m in ind}
    sig = fn(al, idx, syms)
    return {s: int(v[-1]) for s, v in sig.items()}


def public_list() -> list[dict]:
    out = []
    for s in STRATEGIES:
        v = VERDICTS.get(s["id"], {})
        out.append({k: s[k] for k in ("id", "no", "name", "interval", "kind", "desc", "params")} | {"verdict": v})
    return out
