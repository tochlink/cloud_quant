"""组合回测：真实公共历史 K 线 + dual_ma 信号 + 风控仓位。

时间约定（无前视）：
  * 第 i-1 根收盘后的信号/ATR/权益 → 第 i 根开盘价成交；
  * 止损在第 i 根盘中按最高/最低价检查（跳空则按开盘价成交）；
  * 权益在第 i 根收盘按收盘价计价。
做空用现货 K 线近似永续价格，未计资金费率（见 README 局限性）。
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .risk import scale_to_room, size
from .strategy import indicators, market_of, side_of

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
    exit_time: str = ""
    exit_price: float = float("nan")
    exit_reason: str = ""
    pnl_usdt: float = 0.0
    fees_usdt: float = 0.0
    return_pct: float = 0.0
    bars_held: int = 0
    status: str = "open"


def run_backtest(data: dict[str, pd.DataFrame], cfg: dict) -> dict:
    st, rk, fee_bps = cfg["strategy"], cfg["risk"], float(cfg["fees"]["taker_bps"])
    fee = fee_bps / 10_000
    start_eq = float(rk["starting_equity_usdt"])
    ind = {s: indicators(df, st["fast_ma"], st["slow_ma"], st["atr_period"]).set_index("open_time")
           for s, df in data.items() if len(df) > st["slow_ma"] + 2}
    if not ind:
        raise ValueError("历史 K 线不足以计算慢均线")
    idx = None
    for d in ind.values():
        idx = d.index if idx is None else idx.intersection(d.index)
    idx = idx.sort_values()
    syms = sorted(ind)
    O = {s: ind[s].loc[idx, "open"].to_numpy() for s in syms}
    H = {s: ind[s].loc[idx, "high"].to_numpy() for s in syms}
    L = {s: ind[s].loc[idx, "low"].to_numpy() for s in syms}
    C = {s: ind[s].loc[idx, "close"].to_numpy() for s in syms}
    SIG = {s: ind[s].loc[idx, "signal"].to_numpy() for s in syms}
    ATR = {s: ind[s].loc[idx, "atr"].to_numpy() for s in syms}
    close_t = {s: ind[s].loc[idx, "close_time"] for s in syms}
    times = list(idx)
    ct = list(close_t[syms[0]])

    warm = max(st["slow_ma"], st["atr_period"] + 1)
    realized = start_eq
    pos: dict[str, Trade] = {}
    entry_i: dict[str, int] = {}
    blocked: dict[str, int] = {}
    trades: list[Trade] = []
    curve = []
    prev_eq = start_eq

    def upnl(t: Trade, px: float) -> float:
        d = 1 if t.side == "long" else -1
        return d * t.qty * (px - t.entry_price)

    def close(s: str, px: float, when: str, reason: str, i: int):
        nonlocal realized
        t = pos.pop(s)
        f = abs(t.qty * px) * fee
        g = upnl(t, px)
        realized += g - f
        t.exit_time, t.exit_price, t.exit_reason = when, float(px), reason
        t.fees_usdt += f
        t.pnl_usdt = g - t.fees_usdt
        t.return_pct = t.pnl_usdt / t.notional_usdt if t.notional_usdt else 0.0
        t.bars_held, t.status = i - entry_i.pop(s), "closed"
        trades.append(t)

    for i in range(warm + 1, len(times)):
        when = pd.Timestamp(times[i]).isoformat()
        # 1) 信号离场（用 i-1 收盘信号，在 i 开盘执行）
        for s in list(pos):
            want = side_of(SIG[s][i - 1])
            if want != pos[s].side:
                close(s, O[s][i], when, "信号反转" if want != "flat" else "信号转空仓", i)
        # 解除止损锁定
        for s in list(blocked):
            if SIG[s][i - 1] != blocked[s]:
                blocked.pop(s)
        # 2) 入场（同一根 K 线的多个新仓按剩余总敞口额度等比缩放）
        eq_prev = prev_eq
        gross = sum(abs(t.qty) * O[s][i] for s, t in pos.items())
        want: dict = {}
        for s in syms:
            sg = int(SIG[s][i - 1])
            if s in pos or sg == 0 or s in blocked:
                continue
            if sg > 0 and not rk["allow_spot_long"] or sg < 0 and not rk["allow_perp_short"]:
                continue
            z = size(side=side_of(sg), equity=eq_prev, price=O[s][i], atr=ATR[s][i - 1],
                     max_risk=rk["max_risk_per_trade"], max_weight=rk["max_weight_per_name"],
                     atr_mult=st["atr_stop_mult"])
            if z.notional > 0:
                want[s] = (sg, z)
        room = eq_prev * float(rk["max_gross_exposure"]) - gross
        alloc = scale_to_room({s: z.notional for s, (_, z) in want.items()}, room, fee)
        for s, (sg, z) in want.items():
            notional = alloc[s]
            if notional < 1.0:
                continue
            qty = notional / O[s][i]
            f = notional * fee
            realized -= f
            pos[s] = Trade(s, market_of(sg), side_of(sg), when, float(O[s][i]), qty, notional, z.stop_price, fees_usdt=f)
            entry_i[s] = i
        # 3) 盘中止损
        for s in list(pos):
            t = pos[s]
            if t.side == "long" and L[s][i] <= t.stop_price:
                close(s, min(O[s][i], t.stop_price), when, "ATR止损", i)
                blocked[s] = 1
            elif t.side == "short" and H[s][i] >= t.stop_price:
                close(s, max(O[s][i], t.stop_price), when, "ATR止损", i)
                blocked[s] = -1
        # 4) 收盘计价
        eq = realized + sum(upnl(t, C[s][i]) for s, t in pos.items())
        g = sum(abs(t.qty) * C[s][i] for s, t in pos.items())
        n = sum((1 if t.side == "long" else -1) * t.qty * C[s][i] for s, t in pos.items())
        curve.append({"time": pd.Timestamp(ct[i]).isoformat(), "equity": eq, "gross_exposure": g,
                      "net_exposure": n, "positions": len(pos)})
        prev_eq = eq

    last_t = pd.Timestamp(ct[-1]).isoformat()
    open_trades = []
    for s, t in pos.items():
        t.exit_price = float(C[s][-1])
        t.pnl_usdt = upnl(t, t.exit_price) - t.fees_usdt
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
    bh = float(C[btc][-1] / O[btc][warm + 1] - 1)
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
        "avg_gross_exposure_pct": float((ec["gross_exposure"] / ec["equity"]).mean()),
        "benchmark": f"{btc} 买入持有", "benchmark_return": bh,
        "fee_bps": fee_bps, "fast_ma": st["fast_ma"], "slow_ma": st["slow_ma"],
        "atr_stop_mult": st["atr_stop_mult"], "max_risk_per_trade": rk["max_risk_per_trade"],
        "max_weight_per_name": rk["max_weight_per_name"],
    }
    return {"summary": summary, "equity": ec.drop(columns=["peak"]),
            "trades": pd.DataFrame([asdict(t) for t in closed + open_trades])}
