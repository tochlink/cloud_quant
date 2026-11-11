"""纸面账本报告（只读）：python -m qtw.paper_report [--data-dir DIR] [--csv PATH] [--refresh]

打印：权益 vs 起始资金、当前持仓（标的 / 方向 / 交易所 / 数量 / 入场价 / 现价 / 未实现盈亏 / 止损）、
已平仓往返交易（进出场、手续费、盈亏、原因）、自建账以来的订单日志；并把同样内容写成一份 CSV 快照。

* 只读打开 SQLite（mode=ro），不会改动正在运行的服务的账本。
* 现价默认用账本里持久化的最新官方公共标记价（服务每几秒写一次，附时间）；--refresh 时改为当场向
  官方公共 REST 取价（现货最新价 / 永续标记价）。取不到价就显示 “—”，绝不编造价格。
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .paper import PaperBook


def _ro_conn(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _age(ts: str) -> str:
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return f"{(datetime.now(timezone.utc) - t).total_seconds():.0f}s"
    except (TypeError, ValueError, AttributeError):
        return "?"


def _f(x, nd=4) -> str:
    return "—" if x is None else f"{x:.{nd}f}"


def build(db_path: Path, refresh: bool = False) -> dict:
    conn = _ro_conn(db_path)
    bk = PaperBook(conn=conn)
    rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM paper_state")}
    if refresh and bk.positions:
        from .market import MarketDataError, get_client
        for s, p in bk.positions.items():
            try:
                q = get_client(p.venue or "okx").quote(s, p.market)
                p.mark_price, p.mark_time, p.mark_source = q.price, q.ts.strftime("%Y-%m-%dT%H:%M:%SZ"), q.data_source
            except MarketDataError:
                p.mark_price = 0.0  # 取不到 → 显示 —，不计未实现盈亏
    positions = []
    for p in bk.positions.values():
        ok = p.mark_price and p.mark_price > 0
        positions.append({"symbol": p.symbol, "side": p.side, "market": p.market, "venue": p.venue, "qty": p.qty,
                          "entry_time": p.entry_time, "entry_price": p.entry_price,
                          "current_price": p.mark_price if ok else None, "price_time": p.mark_time if ok else "",
                          "price_source": p.mark_source if ok else "", "notional_usdt": p.qty * p.mark_price if ok else None,
                          "unrealized_pnl_usdt": p.upnl() if ok else None, "stop_price": p.stop_price,
                          "open_fee_usdt": p.fees_paid})
    upnl = sum(x["unrealized_pnl_usdt"] or 0 for x in positions)
    unpriced = [x["symbol"] for x in positions if x["current_price"] is None]
    fees = sum(float(f["fee_usdt"]) for f in bk.fills())
    trades = [t for t in bk.trade_records() if t["status"] == "closed"]
    summary = {"created_at": rows.get("created_at", ""), "starting_equity_usdt": bk.starting,
               "realized_usdt": bk.realized, "unrealized_usdt": upnl, "equity_usdt": bk.realized + upnl,
               "pnl_vs_start_usdt": bk.realized + upnl - bk.starting,
               "pnl_vs_start_pct": (bk.realized + upnl) / bk.starting - 1 if bk.starting else None,
               "fees_paid_usdt": fees, "open_positions": len(positions), "closed_trades": len(trades),
               "gross_exposure_usdt": sum(x["notional_usdt"] or 0 for x in positions),
               "unpriced_positions": ",".join(unpriced), "db": str(db_path)}
    orders = bk.orders(1_000_000)[::-1]
    conn.close()
    return {"summary": summary, "positions": positions, "trades": trades, "orders": orders}


def write_csv(rep: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    recs = [{"record": "summary", **rep["summary"]}]
    recs += [{"record": "position", **x} for x in rep["positions"]]
    recs += [{"record": "trade", **{k: t[k] for k in ("symbol", "side", "market", "venue", "qty", "entry_time", "entry_price",
                                                       "exit_time", "exit_price", "fee_usdt", "pnl_usdt", "pnl_pct",
                                                       "entry_reason", "exit_reason", "resizes")}} for t in rep["trades"]]
    recs += [{"record": "order", **o} for o in rep["orders"]]
    cols: list[str] = []
    for r in recs:
        cols += [k for k in r if k not in cols]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(recs)


def render(rep: dict) -> str:
    s = rep["summary"]
    out = [f"纸面账户（建账 {s['created_at']}）  db={s['db']}",
           f"权益 {s['equity_usdt']:.2f} USDT（起始 {s['starting_equity_usdt']:.2f}，{s['pnl_vs_start_usdt']:+.2f} / "
           f"{(s['pnl_vs_start_pct'] or 0) * 100:+.2f}%）  已实现 {s['realized_usdt']:.2f}  未实现 {s['unrealized_usdt']:+.2f}  "
           f"累计手续费 {s['fees_paid_usdt']:.4f}  总敞口 {s['gross_exposure_usdt']:.2f}",
           "", f"持仓 {len(rep['positions'])}："]
    for x in rep["positions"]:
        out.append(f"  {x['symbol']:<9} {x['side']:<5} {x['market']:<4} {x['venue']:<4} qty={x['qty']:.6g} "
                   f"入场={x['entry_price']:g} 现价={_f(x['current_price'], 6) if x['current_price'] is None else format(x['current_price'], 'g')}"
                   f"（{_age(x['price_time']) if x['price_time'] else '—'} 前）未实现={_f(x['unrealized_pnl_usdt'], 2)} 止损={x['stop_price']:.6g}")
    out += ["", f"已平仓往返 {len(rep['trades'])}："]
    for t in rep["trades"]:
        out.append(f"  {t['symbol']:<9} {t['side']:<5} {t['entry_time']} @ {t['entry_price']:g} → {t['exit_time']} @ "
                   f"{t['exit_price']:g}  费 {t['fee_usdt']:.4f}  盈亏 {_f(t['pnl_usdt'], 2)}  原因 {t['exit_reason']}")
    out += ["", f"订单日志 {len(rep['orders'])}："]
    for o in rep["orders"]:
        out.append(f"  {o['time']} {o['mode']:<5} {o['venue']} {o['symbol']:<9} {o['market']:<4} {o['action']:<11} "
                   f"qty={float(o['qty'] or 0):.6g} ref={float(o['ref_price'] or 0):g} {o['status']}")
    return "\n".join(out)


def main(argv=None):
    from .paths import DATA_DIR, OUTPUT_DIR
    ap = argparse.ArgumentParser(prog="python -m qtw.paper_report")
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    ap.add_argument("--csv", default=str(OUTPUT_DIR / "paper_snapshot.csv"))
    ap.add_argument("--refresh", action="store_true", help="当场向官方公共 REST 取价")
    a = ap.parse_args(argv)
    rep = build(Path(a.data_dir) / "qtw.sqlite", refresh=a.refresh)
    print(render(rep))
    write_csv(rep, Path(a.csv))
    print(f"\nCSV 快照：{a.csv}")


if __name__ == "__main__":
    main()
