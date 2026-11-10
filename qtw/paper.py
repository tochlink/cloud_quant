"""持久化纸面账本 —— SQLite 为唯一数据源（data/qtw.sqlite），CSV 只是导出物。

记账模型（1 倍保证金）：
  realized = 起始资金 + 已实现盈亏 − 手续费
  equity   = realized + Σ 未实现盈亏
  可用现金 = equity − Σ |持仓名义|（现货占用资金，永续空头占用等额保证金）
成交价必须来自交易所公共行情（现货最新价 / 永续标记价），本模块不产生任何价格。
"""
from __future__ import annotations

import csv
import math
import threading
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import db
from .paths import PAPER_DIR
from .timeutil import iso, utcnow

_LOCK = threading.RLock()


@dataclass
class Position:
    symbol: str
    market: str
    side: str
    qty: float
    entry_price: float
    entry_time: str
    stop_price: float
    mark_price: float
    mark_time: str
    notional_entry: float
    fees_paid: float
    signal_bar: str
    venue: str = ""
    mark_source: str = ""

    @property
    def direction(self) -> int:
        return 1 if self.side == "long" else -1

    def upnl(self, px: float | None = None) -> float:
        return self.direction * self.qty * ((px or self.mark_price) - self.entry_price)

    def upnl_pct(self, px: float | None = None) -> float | None:
        """Unrealized return on entry price, or None if entry/mark is missing or not a real price."""
        try:
            entry = float(self.entry_price)
            mark = float(self.mark_price if px is None else px)
        except (TypeError, ValueError):
            return None
        if entry <= 0 or mark <= 0 or not math.isfinite(entry) or not math.isfinite(mark):
            return None
        return self.direction * (mark / entry - 1)


FILL_COLS = ["fill_id", "time", "symbol", "market", "side", "action", "qty", "price", "price_kind",
             "notional_usdt", "fee_usdt", "realized_pnl_usdt", "reason", "mode", "venue", "data_source", "price_time"]
LEDGER_COLS = ["time", "equity_usdt", "realized_usdt", "unrealized_usdt", "cash_free_usdt", "gross_exposure_usdt",
               "net_exposure_usdt", "positions", "note"]
POS_COLS = [f.name for f in fields(Position)]
ORDER_COLS = ["time", "mode", "venue", "symbol", "market", "action", "qty", "ref_price", "status", "detail"]


def _ins(conn, table: str, row: dict):
    cols = list(row)
    conn.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join('?' * len(cols))})", tuple(row[c] for c in cols))


def migrate_csv(conn, src: Path = PAPER_DIR) -> dict:
    """首次启动：把旧版 data/paper/*.csv 纸面账本导入 SQLite（只做一次），然后把目录改名备份。"""
    if db.meta_get("migrated_paper_csv", conn) or not (src / "state.csv").exists():
        return {}
    n = {}

    def rd(name):
        p = src / name
        if not p.exists():
            return []
        with p.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    with db.tx(conn) as c:
        if c.execute("SELECT COUNT(*) FROM paper_state").fetchone()[0]:
            db.meta_set("migrated_paper_csv", "skipped: sqlite already had a book", c)
            return {}
        for r in rd("state.csv"):
            c.execute("INSERT OR REPLACE INTO paper_state(key,value) VALUES(?,?)", (r["key"], r["value"]))
        pos = rd("positions.csv")
        for r in pos:
            _ins(c, "paper_positions", {k: r.get(k, "") for k in POS_COLS if k in r})
        fills = rd("fills.csv")
        for r in fills:
            _ins(c, "paper_fills", {k: r[k] for k in FILL_COLS if k in r})
        led = rd("ledger.csv")
        for r in led:
            _ins(c, "paper_ledger", {k: r[k] for k in LEDGER_COLS if k in r})
        for r in rd("stop_blocks.csv"):
            c.execute("INSERT OR REPLACE INTO paper_blocks VALUES(?,?)", (r["symbol"], int(r["blocked_signal"])))
        orders = rd("orders.csv")
        for r in orders:
            _ins(c, "orders", {k: r[k] for k in ORDER_COLS if k in r})
        n = {"positions": len(pos), "fills": len(fills), "ledger": len(led), "orders": len(orders)}
        db.meta_set("migrated_paper_csv", f"{iso(utcnow())} {n}", c)
    src.rename(src.with_name(src.name + ".migrated-to-sqlite"))
    return n


class PaperBook:
    def __init__(self, starting_equity: float = 1000.0, fee_bps: float = 4.0, conn=None):
        self.conn = conn or db.connect()
        self.fee = fee_bps / 10_000
        self.migrated = migrate_csv(self.conn) if conn is None else {}
        self.load(starting_equity)

    # ---------- 持久化 ----------
    def _q(self, sql, args=()):
        return db.query(sql, args, self.conn)

    def load(self, starting_equity: float):
        with _LOCK:
            st = {r["key"]: r["value"] for r in self._q("SELECT key, value FROM paper_state")}
            self.starting = float(st.get("starting_equity_usdt", starting_equity))
            self.realized = float(st.get("realized_usdt", self.starting))
            self.created = st.get("created_at", iso(utcnow()))
            self.positions = {r["symbol"]: Position(**{k: r[k] for k in POS_COLS}) for r in
                              self._q("SELECT * FROM paper_positions")}
            for p in self.positions.values():
                p.venue, p.mark_source = p.venue or "", p.mark_source or ""
            healed = self._heal_venues()
            self.blocks = {r["symbol"]: int(r["blocked_signal"]) for r in self._q("SELECT * FROM paper_blocks")}
            if not st or healed:
                self.save()

    def _heal_venues(self) -> bool:
        """Backfill empty position.venue from the latest open fill (legacy rows)."""
        changed = False
        for sym, p in self.positions.items():
            if p.venue:
                continue
            rows = self._q(
                "SELECT venue FROM paper_fills WHERE symbol=? AND action='open' AND venue!='' "
                "ORDER BY fill_id DESC LIMIT 1",
                (sym,),
            )
            if rows and rows[0].get("venue"):
                p.venue = str(rows[0]["venue"]).lower()
                changed = True
        return changed

    def _save(self, c):
        for k, v in (("starting_equity_usdt", self.starting), ("realized_usdt", self.realized),
                     ("created_at", self.created), ("updated_at", iso(utcnow()))):
            c.execute("INSERT OR REPLACE INTO paper_state(key,value) VALUES(?,?)", (k, str(v)))
        c.execute("DELETE FROM paper_positions")
        for p in self.positions.values():
            _ins(c, "paper_positions", asdict(p))
        c.execute("DELETE FROM paper_blocks")
        for k, v in self.blocks.items():
            c.execute("INSERT INTO paper_blocks VALUES(?,?)", (k, int(v)))

    def save(self):
        with _LOCK, db.tx(self.conn) as c:
            self._save(c)

    def reset(self, starting_equity: float):
        with _LOCK, db.tx(self.conn) as c:
            for t in ("paper_state", "paper_positions", "paper_blocks", "paper_fills", "paper_ledger"):
                c.execute(f"DELETE FROM {t}")
            self.created = iso(utcnow())
            self.starting = self.realized = float(starting_equity)
            self.positions, self.blocks = {}, {}
            self._save(c)

    # ---------- 记账 ----------
    def equity(self) -> float:
        return self.realized + sum(p.upnl() for p in self.positions.values())

    def gross(self) -> float:
        return sum(abs(p.qty * p.mark_price) for p in self.positions.values())

    def net(self) -> float:
        return sum(p.direction * p.qty * p.mark_price for p in self.positions.values())

    def mark(self, symbol: str, price: float, when: str, source: str = ""):
        # Serialize with save/open/close so WS mark ticks cannot race asdict(_save).
        with _LOCK:
            if symbol in self.positions:
                p = self.positions[symbol]
                p.mark_price, p.mark_time, p.mark_source = price, when, source or p.mark_source

    def open(self, *, symbol, market, side, qty, price, price_kind, stop, signal_bar, reason, venue, mode="paper",
             data_source="", price_time=""):
        with _LOCK, db.tx(self.conn) as c:
            notional = qty * price
            fee = notional * self.fee
            self.realized -= fee
            now = iso(utcnow())
            self.positions[symbol] = Position(symbol, market, side, qty, price, now, stop, price, now, notional, fee,
                                              signal_bar, venue, data_source)
            _ins(c, "paper_fills", dict(time=now, symbol=symbol, market=market, side="buy" if side == "long" else "sell",
                                        action="open", qty=qty, price=price, price_kind=price_kind, notional_usdt=notional,
                                        fee_usdt=fee, realized_pnl_usdt=-fee, reason=reason, mode=mode, venue=venue,
                                        data_source=data_source, price_time=price_time))
            self._save(c)

    def close(self, symbol: str, price: float, price_kind: str, reason: str, venue: str, mode="paper",
              data_source="", price_time="") -> float:
        with _LOCK, db.tx(self.conn) as c:
            p = self.positions.pop(symbol)
            notional = p.qty * price
            fee = notional * self.fee
            pnl = p.upnl(price)
            self.realized += pnl - fee
            _ins(c, "paper_fills", dict(time=iso(utcnow()), symbol=symbol, market=p.market,
                                        side="sell" if p.side == "long" else "buy", action="close", qty=p.qty, price=price,
                                        price_kind=price_kind, notional_usdt=notional, fee_usdt=fee,
                                        realized_pnl_usdt=pnl - fee, reason=reason, mode=mode, venue=venue,
                                        data_source=data_source, price_time=price_time))
            self._save(c)
            return pnl - fee

    def snapshot(self, note: str = "") -> dict:
        with _LOCK, db.tx(self.conn) as c:
            eq = self.equity()
            row = {"time": iso(utcnow()), "equity_usdt": eq, "realized_usdt": self.realized,
                   "unrealized_usdt": eq - self.realized, "cash_free_usdt": eq - self.gross(),
                   "gross_exposure_usdt": self.gross(), "net_exposure_usdt": self.net(),
                   "positions": len(self.positions), "note": note}
            _ins(c, "paper_ledger", row)
            self._save(c)  # 同时持久化最新标记价
            return row

    def last_stop_time(self, symbol: str) -> str:
        """该标的最近一次 ATR 止损平仓的成交时间（UTC ISO）；没有则返回空串。"""
        r = self._q("SELECT time FROM paper_fills WHERE symbol=? AND action='close' AND reason='ATR止损' "
                    "ORDER BY fill_id DESC LIMIT 1", (symbol,))
        return r[0]["time"] if r else ""

    def fills(self) -> list[dict]:
        return self._q(f"SELECT {','.join(FILL_COLS)} FROM paper_fills ORDER BY fill_id")

    def trade_records(self) -> list[dict]:
        """FIFO-pair open/close fills into round-trip records. Open trades stay open until a close.

        pnl_usdt / pnl_pct are net of known fees. For open trades they are unrealized and only
        filled when a real mark price is available; otherwise left None (never invented).
        """
        def px_ok(x) -> bool:
            try:
                v = float(x)
                return math.isfinite(v) and v > 0
            except (TypeError, ValueError):
                return False

        def rec(op, cl, pos=None):
            src = op or cl
            if op:
                side = "long" if op["side"] == "buy" else "short"
            else:
                side = "long" if cl["side"] == "sell" else "short"
            qty = float((op or cl)["qty"])
            entry_px = float(op["price"]) if op and px_ok(op.get("price")) else None
            exit_px = float(cl["price"]) if cl and px_ok(cl.get("price")) else None
            fee = float((op or {}).get("fee_usdt") or 0) + float((cl or {}).get("fee_usdt") or 0)
            pnl = pct = mark = None
            mark_src = mark_time = ""
            if cl is not None:
                pnl = float((op or {}).get("realized_pnl_usdt") or 0) + float(cl.get("realized_pnl_usdt") or 0)
                if entry_px and qty:
                    pct = pnl / (entry_px * qty)
            elif pos is not None and entry_px and px_ok(pos.mark_price):
                mark = float(pos.mark_price)
                mark_src = pos.mark_source or ""
                mark_time = pos.mark_time or ""
                pnl = pos.upnl(mark) - fee
                pct = pnl / (entry_px * qty) if qty else None
            return {
                "trade_id": int(op["fill_id"]) if op else int(cl["fill_id"]),
                "symbol": src["symbol"], "market": src["market"], "side": side, "qty": qty,
                "entry_time": (op or {}).get("time") or "", "entry_price": entry_px,
                "entry_fill_id": (op or {}).get("fill_id"), "entry_reason": (op or {}).get("reason") or "",
                "entry_price_kind": (op or {}).get("price_kind") or "",
                "exit_time": (cl or {}).get("time") or "", "exit_price": exit_px,
                "exit_fill_id": (cl or {}).get("fill_id"), "exit_reason": (cl or {}).get("reason") or "",
                "exit_price_kind": (cl or {}).get("price_kind") or "",
                "fee_usdt": fee, "pnl_usdt": pnl, "pnl_pct": pct,
                "status": "closed" if cl is not None else "open",
                "mode": (cl or op or {}).get("mode") or "paper",
                "venue": (cl or op or {}).get("venue") or "",
                "mark_price": mark, "mark_source": mark_src, "mark_time": mark_time,
            }

        pending: dict[str, list] = {}
        out: list[dict] = []
        for f in self.fills():
            if f["action"] == "open":
                pending.setdefault(f["symbol"], []).append(f)
            elif f["action"] == "close":
                stack = pending.setdefault(f["symbol"], [])
                op = stack.pop(0) if stack else None
                out.append(rec(op, f))
        for sym, stack in pending.items():
            pos = self.positions.get(sym)
            for op in stack:
                out.append(rec(op, None, pos=pos))
        return out

    def ledger(self) -> list[dict]:
        return self._q(f"SELECT {','.join(LEDGER_COLS)} FROM paper_ledger ORDER BY id")

    def log_order(self, **kw):
        row = {"time": iso(utcnow()), **{k: kw.get(k) for k in ORDER_COLS if k != "time"}}
        db.execute(f"INSERT INTO orders({','.join(row)}) VALUES({','.join('?' * len(row))})", tuple(row.values()), self.conn)

    def orders(self, limit: int = 300) -> list[dict]:
        return self._q(f"SELECT {','.join(ORDER_COLS)} FROM orders ORDER BY id DESC LIMIT ?", (limit,))
