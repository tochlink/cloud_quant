"""实盘 / 模拟盘成交 与 回测逐笔交易 的对账（只读，不下单、不碰密钥）。

用法：
    .venv/bin/python -m qtw.reconcile --fills 我的成交.csv [--venue okx] [--bars 1500]

输入 CSV 字段见 docs/templates/my_fills_template.csv：
    venue, mode(paper/live), symbol(如 BTCUSDT), market(spot/perp), side(long/short),
    action(open/close), fill_time(ISO 8601，带时区；无时区按 UTC), fill_price, qty, fee_usdt, order_id, reason
同一 symbol + side 的 open / close 按时间顺序配对成一笔往返交易（支持一笔分多次成交，按数量加权均价）。

匹配：用户往返交易的入场时间与回测交易入场时间（第 t+1 根开盘）相差 ≤ tol_bars 根 K 线、且 symbol / side 相同，取最近的一笔。
公式（d = +1 多，−1 空；正数 = 比回测更差）：
    entry_slip_bps = d × (用户入场均价 − 回测入场价) / 回测入场价 × 10000
    exit_slip_bps  = d × (回测离场价 − 用户离场均价) / 回测离场价 × 10000
    entry_delay_min = 用户首笔入场时间 − 回测入场时间（分钟）
    user_return_pct / bt_price_return_pct = 未扣费的价格收益 d×(离场/入场−1)×100（只算已平仓），二者之差 return_gap_pct ≈ 两端滑点之和
输出（output/）：reconcile_trades.csv（逐笔）、reconcile_summary.csv（汇总）、reconcile_missed.csv（回测有、你那边没有的交易）。
"""
from __future__ import annotations

import argparse
import csv
import pathlib

import numpy as np
import pandas as pd

REQUIRED = ["venue", "symbol", "side", "action", "fill_time", "fill_price", "qty"]


def load_fills(path: str | pathlib.Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise ValueError(f"成交 CSV 缺少字段：{', '.join(miss)}")
    df["symbol"] = df["symbol"].astype(str).str.upper().str.replace("-", "").str.replace("_", "").str.replace("SWAP", "")
    df["side"] = df["side"].astype(str).str.lower().str.strip()
    df["action"] = df["action"].astype(str).str.lower().str.strip()
    bad = df[~df["side"].isin(["long", "short"]) | ~df["action"].isin(["open", "close"])]
    if len(bad):
        raise ValueError("side 只能是 long / short，action 只能是 open / close")
    t = pd.to_datetime(df["fill_time"], utc=True, errors="coerce")
    if t.isna().any():
        raise ValueError("fill_time 无法解析，请用 ISO 8601，例如 2026-11-10T12:00:05+00:00")
    df["fill_time"] = t
    for c in ("fill_price", "qty"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["fee_usdt"] = pd.to_numeric(df.get("fee_usdt", 0.0), errors="coerce").fillna(0.0)
    if df[["fill_price", "qty"]].isna().any().any() or (df["fill_price"] <= 0).any() or (df["qty"] <= 0).any():
        raise ValueError("fill_price / qty 必须是正数")
    return df.sort_values("fill_time").reset_index(drop=True)


def round_trips(fills: pd.DataFrame) -> pd.DataFrame:
    """同 symbol+side 内：从无仓到有仓的 open 开启一笔，数量回到 0 的 close 结束。"""
    out = []
    for (sym, side), g in fills.groupby(["symbol", "side"], sort=False):
        cur, pos = None, 0.0
        for _, r in g.iterrows():
            if r["action"] == "open":
                if cur is None:
                    cur = {"symbol": sym, "side": side, "venue": r["venue"], "mode": r.get("mode", ""),
                           "entry_time": r["fill_time"], "eq": 0.0, "en": 0.0, "xq": 0.0, "xn": 0.0, "fees": 0.0, "exit_time": pd.NaT}
                cur["eq"] += r["qty"]; cur["en"] += r["qty"] * r["fill_price"]; cur["fees"] += r["fee_usdt"]; pos += r["qty"]
            elif cur is not None:
                q = min(r["qty"], pos)
                cur["xq"] += q; cur["xn"] += q * r["fill_price"]; cur["fees"] += r["fee_usdt"]; pos -= q
                cur["exit_time"] = r["fill_time"]
                if pos <= 1e-12 * max(1.0, cur["eq"]):
                    out.append(cur); cur, pos = None, 0.0
        if cur is not None:
            out.append(cur)
    rows = []
    for c in out:
        d = 1 if c["side"] == "long" else -1
        ep = c["en"] / c["eq"]
        xp = c["xn"] / c["xq"] if c["xq"] > 0 else np.nan
        pnl = d * c["xq"] * (xp - ep) - c["fees"] if c["xq"] > 0 else np.nan
        rows.append({"symbol": c["symbol"], "side": c["side"], "venue": c["venue"], "mode": c["mode"],
                     "user_entry_time": c["entry_time"], "user_entry_price": ep, "user_qty": c["eq"],
                     "user_exit_time": c["exit_time"], "user_exit_price": xp, "user_fees_usdt": c["fees"],
                     "user_pnl_usdt": pnl, "user_status": "closed" if c["xq"] >= c["eq"] - 1e-12 * max(1.0, c["eq"]) else "open"})
    return pd.DataFrame(rows)


def reconcile(fills: pd.DataFrame, bt_trades: pd.DataFrame, bar_hours: float = 4.0, tol_bars: float = 1.0):
    """返回 (逐笔对账, 汇总, 回测有但用户没有的交易)。纯函数，便于测试。"""
    ut = round_trips(fills)
    bt = bt_trades.copy()
    bt["entry_time"] = pd.to_datetime(bt["entry_time"], utc=True)
    bt["exit_time"] = pd.to_datetime(bt["exit_time"].replace("", np.nan), utc=True, errors="coerce")
    tol = pd.Timedelta(hours=bar_hours * tol_bars)
    used, rows = set(), []
    for _, u in ut.iterrows():
        cand = bt[(bt["symbol"] == u["symbol"]) & (bt["side"] == u["side"])]
        cand = cand[[k not in used for k in cand.index]]
        gap = (cand["entry_time"] - u["user_entry_time"]).abs()
        r = u.to_dict()
        if len(cand) and gap.min() <= tol:
            k = gap.idxmin(); used.add(k); b = bt.loc[k]; d = 1 if u["side"] == "long" else -1
            r.update(matched=True, bt_entry_time=b["entry_time"], bt_entry_price=float(b["entry_price"]),
                     bt_exit_time=b["exit_time"], bt_exit_price=float(b["exit_price"]), bt_exit_reason=b.get("exit_reason", ""),
                     bt_net_return_pct=float(b.get("return_pct", np.nan)) * 100,
                     bt_price_return_pct=d * (float(b["exit_price"]) / float(b["entry_price"]) - 1) * 100 if u["user_status"] == "closed" else np.nan,
                     entry_slip_bps=d * (u["user_entry_price"] - b["entry_price"]) / b["entry_price"] * 1e4,
                     exit_slip_bps=d * (b["exit_price"] - u["user_exit_price"]) / b["exit_price"] * 1e4 if u["user_status"] == "closed" else np.nan,
                     entry_delay_min=(u["user_entry_time"] - b["entry_time"]).total_seconds() / 60,
                     user_return_pct=d * (u["user_exit_price"] / u["user_entry_price"] - 1) * 100 if u["user_status"] == "closed" else np.nan)
        else:
            r.update(matched=False)
        rows.append(r)
    per = pd.DataFrame(rows)
    if len(ut):
        lo, hi = ut["user_entry_time"].min() - tol, max(ut["user_entry_time"].max(), ut["user_exit_time"].max()) + tol
        missed = bt[(bt["entry_time"] >= lo) & (bt["entry_time"] <= hi) & ~bt.index.isin(list(used))]
        missed = missed[missed["symbol"].isin(set(ut["symbol"]))]
    else:
        missed = bt.iloc[0:0]
    m = per[per["matched"]] if len(per) and "matched" in per else per.iloc[0:0]

    def stat(col, f):
        return round(float(f(m[col].dropna())), 2) if len(m) and col in m and m[col].notna().any() else ""

    summary = [{"user_round_trips": len(per), "matched": int(len(m)), "unmatched_user": int(len(per) - len(m)),
                "missed_backtest": int(len(missed)),
                "entry_slip_bps_mean": stat("entry_slip_bps", np.mean), "entry_slip_bps_median": stat("entry_slip_bps", np.median),
                "exit_slip_bps_mean": stat("exit_slip_bps", np.mean), "exit_slip_bps_median": stat("exit_slip_bps", np.median),
                "entry_delay_min_median": stat("entry_delay_min", np.median),
                "user_return_pct_sum": stat("user_return_pct", np.sum), "bt_price_return_pct_sum": stat("bt_price_return_pct", np.sum),
                "return_gap_pct": round(float((m["user_return_pct"] - m["bt_price_return_pct"]).dropna().sum()), 2) if len(m) and "user_return_pct" in m else "",
                "bar_hours": bar_hours, "tol_bars": tol_bars}]
    return per, pd.DataFrame(summary), missed


def main():
    ap = argparse.ArgumentParser(prog="qtw.reconcile", description="你的模拟盘 / 实盘成交 CSV 与回测逐笔对账")
    ap.add_argument("--fills", required=True)
    ap.add_argument("--venue", choices=["okx", "gate"])
    ap.add_argument("--bars", type=int, default=1500)
    ap.add_argument("--tol-bars", type=float, default=1.0)
    a = ap.parse_args()
    from qtw import db, settings as S
    from qtw.backtest import run_backtest
    from qtw.market import cache as mcache
    from qtw.paths import OUTPUT_DIR as OUTPUT

    db.connect(); cfg = S.load()
    fills = load_fills(a.fills)
    venue = a.venue or str(fills["venue"].iloc[0]).lower()
    fr, _ = mcache.many(venue, cfg["symbols"], cfg["strategy"]["interval"], a.bars)
    n = min(len(df) for m in fr.values() for df in m.values())
    fr = {m: {s: df.iloc[-n:].reset_index(drop=True) for s, df in d.items()} for m, d in fr.items()}
    res = run_backtest(fr, {**cfg, "venue": venue})
    hours = {"15m": 0.25, "1h": 1, "4h": 4, "1d": 24}.get(cfg["strategy"]["interval"], 4)
    per, summ, missed = reconcile(fills[fills["venue"].str.lower() == venue], res["trades"], hours, a.tol_bars)
    out = pathlib.Path(OUTPUT)
    out.mkdir(parents=True, exist_ok=True)
    per.to_csv(out / "reconcile_trades.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    summ.to_csv(out / "reconcile_summary.csv", index=False)
    missed.to_csv(out / "reconcile_missed.csv", index=False)
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
