"""资金费率套利（期现对冲，方向中性）独立模拟：同币现货多 + USDT 永续空等额。

数据：Gate 官方公共 /futures/usdt/funding_rate 的已结算资金费率 + 官方 4h 现货 / 永续 K 线。
规则（第 i 根 4h 收盘决策 → 第 i+1 根开盘成交，无前视）：
  * 截至第 i 根收盘已结算的最近 window 次费率均值 m；空仓且 m > enter_rate → 开对冲；持有且 m < exit_rate → 平对冲；
  * 资金：每币一个槽位 = 当前权益 / 币数，现货腿与永续保证金（1 倍）各占一半，即每腿名义 = 槽位 / 2；
  * 持有期间每次结算：空头收（费率为正）/ 付（为负）名义 × 费率；两条腿按各自收盘价逐根计价（基差盈亏）；
  * 开平各两条腿都按吃单费率（现货 spot_taker、永续 perp_taker）。
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from .settings import taker_rate

GATE_FUNDING = ["https://api.gateio.ws/api/v4"]


def fetch_gate_funding(symbol: str, since_ms: int, http=None) -> pd.DataFrame:
    """Gate 官方历史资金费率（向前翻页）。返回 time_ms / rate，时间升序。"""
    from .market.base import HttpJson
    http = http or HttpJson(GATE_FUNDING)
    to, seen, rows = int(time.time()), set(), []
    base = symbol.replace("USDT", "")
    while True:
        r = http.get("/futures/usdt/funding_rate", {"contract": f"{base}_USDT", "limit": 1000, "to": to})
        new = [x for x in r if x["t"] not in seen]
        if not new:
            break
        for x in new:
            seen.add(x["t"])
            rows.append((int(x["t"]) * 1000, float(x["r"])))
        to = min(x["t"] for x in new) - 1
        if to * 1000 < since_ms:
            break
        time.sleep(0.25)
    df = pd.DataFrame(rows, columns=["time_ms", "rate"]).sort_values("time_ms").reset_index(drop=True)
    return df[df.time_ms >= since_ms]


def simulate(data: dict, funding: dict[str, pd.DataFrame], cfg: dict, window: int = 9, enter_rate: float = 1e-4,
             exit_rate: float = 0.0, start_equity: float | None = None) -> dict:
    spot, perp = data["spot"], data["perp"]
    syms = sorted(s for s in spot if s in perp and s in funding and len(funding[s]))
    fs, fp = taker_rate(cfg, "spot"), taker_rate(cfg, "perp")
    eq0 = float(start_equity or cfg["risk"]["starting_equity_usdt"])
    idx = None
    for s in syms:
        for d in (spot[s], perp[s]):
            ix = pd.Index(d["open_time"])
            idx = ix if idx is None else idx.intersection(ix)
    idx = idx.sort_values()
    O = {m: {s: src[s].set_index("open_time").loc[idx, "open"].to_numpy(float) for s in syms} for m, src in (("s", spot), ("p", perp))}
    C = {m: {s: src[s].set_index("open_time").loc[idx, "close"].to_numpy(float) for s in syms} for m, src in (("s", spot), ("p", perp))}
    close_ms = pd.DatetimeIndex(idx).as_unit("ms").asi8 + 4 * 3_600_000
    # 每根 K 线 (close_{i-1}, close_i] 内结算的费率之和与截至 close_i 的滚动均值
    F_bar, F_mean = {}, {}
    for s in syms:
        f = funding[s]
        t, r = f["time_ms"].to_numpy(np.int64), f["rate"].to_numpy(float)
        k = np.searchsorted(t, close_ms, side="right")  # 截至 close_i 已结算的条数
        cs = np.concatenate([[0.0], np.cumsum(r)])
        F_bar[s] = cs[k] - cs[np.concatenate([[k[0]], k[:-1]])]
        F_bar[s][0] = 0.0
        m = np.full(len(k), np.nan)
        ok = k >= window
        m[ok] = (cs[k[ok]] - cs[k[ok] - window]) / window
        F_mean[s] = m
    pos: dict[str, dict] = {}
    realized = eq0
    curve, trades = [], []
    fees_tot = fund_tot = 0.0
    prev_eq = eq0
    for i in range(1, len(idx)):
        when = pd.Timestamp(idx[i]).isoformat()
        for s in syms:  # 第 i-1 根收盘决策，第 i 根开盘成交
            m = F_mean[s][i - 1]
            if s in pos and not (m >= exit_rate):
                p = pos.pop(s)
                os_, op_ = O["s"][s][i], O["p"][s][i]
                g = p["qs"] * (os_ - p["es"]) - p["qp"] * (op_ - p["ep"])
                f = p["qs"] * os_ * fs + p["qp"] * op_ * fp
                realized += g - f
                fees_tot += f
                p.update(exit_time=when, pnl=g - f + p["fund"] - p["fee_in"], status="closed")
                trades.append(p)
            elif s not in pos and m == m and m > enter_rate:
                h = prev_eq / len(syms) / 2
                os_, op_ = O["s"][s][i], O["p"][s][i]
                f = h * (fs + fp)
                realized -= f
                fees_tot += f
                pos[s] = dict(symbol=s, entry_time=when, es=os_, ep=op_, qs=h / os_, qp=h / op_, notional=h, fund=0.0, fee_in=f)
        for s, p in pos.items():  # 本根内结算的资金费：空头收 +rate
            fr = F_bar[s][i]
            if fr:
                amt = p["qp"] * C["p"][s][i] * fr
                realized += amt
                fund_tot += amt
                p["fund"] += amt
        u = sum(p["qs"] * (C["s"][s][i] - p["es"]) - p["qp"] * (C["p"][s][i] - p["ep"]) for s, p in pos.items())
        g = sum(p["qs"] * C["s"][s][i] + p["qp"] * C["p"][s][i] for s, p in pos.items())
        eq = realized + u
        curve.append({"time": pd.Timestamp(close_ms[i], unit="ms", tz="UTC").isoformat(), "equity": eq, "gross_exposure": g,
                      "net_exposure": sum(p["qs"] * C["s"][s][i] - p["qp"] * C["p"][s][i] for s, p in pos.items()), "positions": len(pos)})
        prev_eq = eq
    for s, p in pos.items():
        g = p["qs"] * (C["s"][s][-1] - p["es"]) - p["qp"] * (C["p"][s][-1] - p["ep"])
        p.update(exit_time="", pnl=g + p["fund"] - p["fee_in"], status="open")
        trades.append(p)
    ec = pd.DataFrame(curve)
    ec["drawdown"] = ec["equity"] / ec["equity"].cummax() - 1
    tr = pd.DataFrame([{"symbol": t["symbol"], "market": "spot+perp", "side": "hedge", "entry_time": t["entry_time"],
                        "exit_time": t["exit_time"], "notional_usdt": t["notional"], "pnl_usdt": t["pnl"],
                        "funding_usdt": t["fund"], "status": t["status"]} for t in trades])
    end = float(ec["equity"].iloc[-1])
    return {"summary": {"rule_id": "funding_carry", "strategy_id": "funding_carry", "total_return": end / eq0 - 1,
                        "max_drawdown": float(ec["drawdown"].min()), "fees_usdt": fees_tot, "funding_usdt": fund_tot,
                        "closed_trades": int((tr.status == "closed").sum()) if len(tr) else 0, "symbols": " ".join(syms)},
            "equity": ec, "trades": tr}
