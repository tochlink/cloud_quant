"""短线层（intraday layer，默认关闭）：与长线 4h 核心分开的独立进出场系统，只在 4h / 1D 方向一致时顺势做。

* 方向闸门：长线 4h 合成信号（现货 +1 且永续 ≠ −1 → 多；永续 −1 且现货 ≠ +1 → 空）与 1D 上下文
  （日收盘相对 EMA(daily_ema) 同侧）一致，并且 1h 收盘在 EMA(h1_ema) 同侧；三者都只用已收盘 K 线。
* 入场（基础周期 5m / 10m / 1m）：收盘突破此前 N 根的最高价（多）/ 最低价（空），下一根开盘按吃单价成交。
* 离场：入场价 ∓ k × ATR14(基础周期) 止损（盘中触及；跳空按开盘价）；收盘逆向穿 EMA(exit_ema) → 下一根开盘平；
  持仓满 max_bars 根平；4h 方向改变 → 下一根开盘平。
* 仓位：单笔风险 = 短线预算 × risk_per_trade，单币名义 ≤ 短线预算 × max_weight；短线预算与长线分开（risk.short_budget_frac）。
* 手续费：开平各一次吃单（现货 / 永续各自费率）。
研究结论与启用条件见 docs/STRATEGY_FORMULAS.md「短线层」；未通过「未见数据上两家交易所扣费后期望为正」前，模拟盘不得开启。
"""
from __future__ import annotations

import numpy as np

DEFAULTS = {"enabled": False, "base_tf": "5m", "breakout_n": 24, "atr_n": 14, "stop_atr": 2.0, "exit_ema": 20,
            "max_bars": 96, "h1_ema": 50, "daily_ema": 20, "risk_per_trade": 0.005, "max_weight": 0.10, "budget_frac": 0.3}


def _ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1)
    out = np.empty(len(x))
    m = np.nan
    for i, v in enumerate(x):
        m = v if m != m else a * v + (1 - a) * m
        out[i] = m
    out[: n - 1] = np.nan
    return out


def _atr(h, l, c, n):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return np.convolve(tr, np.ones(n) / n, "full")[: len(tr)] * np.where(np.arange(len(tr)) >= n - 1, 1, np.nan)


def align_last_closed(t_ms: np.ndarray, src_close_ms: np.ndarray, src_val: np.ndarray, step_ms: int) -> np.ndarray:
    """把较慢周期的值对齐到快周期：快周期第 k 根收盘时（t + step）只能看到收盘时间 ≤ 该时刻的慢周期 K 线。"""
    idx = np.searchsorted(src_close_ms, t_ms + step_ms, "right") - 1
    out = np.full(len(t_ms), np.nan)
    ok = idx >= 0
    out[ok] = src_val[idx[ok]]
    return out


def simulate(side: int, t, o, h, l, c, step_ms: int, direction: np.ndarray, p: dict, fee: float, budget: float = 1000.0,
             t_from: int = 0) -> list[dict]:
    """单币单方向（side=+1 多 / −1 空）逐根模拟；direction = 对齐到每根快 K 线收盘时可见的方向闸门（+1 / −1 / 0）。"""
    n = len(t)
    N, k = int(p["breakout_n"]), float(p["stop_atr"])
    atr = _atr(h, l, c, int(p["atr_n"]))
    ee = _ema(c, int(p["exit_ema"]))
    hh = np.full(n, np.nan); ll = np.full(n, np.nan)
    from numpy.lib.stride_tricks import sliding_window_view as sw
    if n > N:
        hh[N:] = sw(h, N)[:-1].max(axis=1); ll[N:] = sw(l, N)[:-1].min(axis=1)
    trades, pos = [], None
    risk_u, cap_u = budget * float(p["risk_per_trade"]), budget * float(p["max_weight"])
    pend_entry = pend_exit = None
    for i in range(n):
        if pend_exit is not None and pos is not None:  # 上一根收盘决定的离场 → 本根开盘成交
            pos["exit"], pos["exit_t"], pos["why"] = o[i], t[i], pend_exit
            trades.append(pos); pos = None
        pend_exit = None
        if pend_entry is not None and pos is None:
            stop = o[i] - side * k * pend_entry
            dist = abs(o[i] - stop)
            if dist > 0:
                notional = min(risk_u / (dist / o[i]), cap_u)
                pos = {"side": side, "entry": o[i], "entry_t": t[i], "stop": stop, "qty": notional / o[i], "bars": 0}
        pend_entry = None
        if pos is not None:
            pos["bars"] += 1
            if side > 0 and l[i] <= pos["stop"] or side < 0 and h[i] >= pos["stop"]:
                pos["exit"] = min(o[i], pos["stop"]) if side > 0 else max(o[i], pos["stop"])
                pos["exit_t"], pos["why"] = t[i], "止损"
                trades.append(pos); pos = None
                continue
            if direction[i] != side:
                pend_exit = "方向改变"
            elif ee[i] == ee[i] and side * (c[i] - ee[i]) < 0:
                pend_exit = "逆破EMA"
            elif pos["bars"] >= int(p["max_bars"]):
                pend_exit = "时间离场"
            continue
        if t[i] < t_from or direction[i] != side or not (atr[i] == atr[i]) or hh[i] != hh[i]:
            continue
        if (side > 0 and c[i] > hh[i]) or (side < 0 and c[i] < ll[i]):
            pend_entry = atr[i]
    out = []
    for x in trades:
        gross = x["side"] * (x["exit"] - x["entry"]) * x["qty"]
        fees = (x["entry"] + x["exit"]) * x["qty"] * fee
        out.append({"side": "long" if x["side"] > 0 else "short", "entry_t": int(x["entry_t"]), "exit_t": int(x["exit_t"]),
                    "entry": float(x["entry"]), "exit": float(x["exit"]), "qty": float(x["qty"]), "gross": float(gross),
                    "fees": float(fees), "pnl": float(gross - fees), "why": x["why"], "bars": int(x["bars"]),
                    "risk_u": float(abs(x["entry"] - x["stop"]) * x["qty"])})
    return out


def stats(trades: list[dict], budget: float = 1000.0) -> dict:
    if not trades:
        return {"trades": 0}
    p = np.array([x["pnl"] for x in trades]); g = np.array([x["gross"] for x in trades]); f = np.array([x["fees"] for x in trades])
    r = np.array([x["risk_u"] for x in trades])
    w, lo = p[p > 0], p[p <= 0]
    order = np.argsort([x["exit_t"] for x in trades])
    eq = budget + np.cumsum(p[order])
    dd = float((eq / np.maximum.accumulate(np.r_[budget, eq])[1:] - 1).min() * 100)
    return {"trades": int(len(p)), "win_rate": round(len(w) / len(p) * 100, 1), "avg_win": round(float(w.mean()), 3) if len(w) else 0.0,
            "avg_loss": round(float(lo.mean()), 3) if len(lo) else 0.0,
            "payoff": round(float(w.mean() / -lo.mean()), 2) if len(w) and len(lo) and lo.mean() < 0 else None,
            "profit_factor": round(float(w.sum() / -lo.sum()), 2) if lo.sum() < 0 else None,
            "expectancy_u": round(float(p.mean()), 4), "expectancy_r": round(float((p / np.where(r > 0, r, np.nan)).mean()), 3),
            "gross_u": round(float(g.sum()), 2), "fees_u": round(float(f.sum()), 2), "net_u": round(float(p.sum()), 2),
            "fee_drag_pct": round(float(f.sum() / abs(g.sum()) * 100), 1) if g.sum() else None,
            "ret_pct": round(float(p.sum() / budget * 100), 2), "max_dd_pct": round(dd, 2)}
