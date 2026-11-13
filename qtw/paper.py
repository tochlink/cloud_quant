"""持久化纸面账本 —— SQLite 为唯一数据源（data/qtw.sqlite），CSV 只是导出物。

记账模型（逐仓保证金，2026-11-13 起永续可设杠杆）：
  realized = 起始资金 + 已实现盈亏 − 手续费
  equity   = realized + Σ 未实现盈亏
  可用资金 = equity − Σ 占用（现货 = 买入名义；永续 = 名义 / 杠杆 的逐仓保证金）
  资金费在结算点计入 realized（apply_funding）；被强平时损失该仓全部逐仓保证金（liquidate）
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
    init_stop: float = 0.0  # 初始止损（R0 = |入场价 − 初始止损|）；旧持仓加载时用当前止损回填
    tp_done: int = 0  # 已分批止盈
    be_moved: int = 0  # 剩余仓位止损已移到保本价
    leverage: float = 1.0  # 永续逐仓杠杆（现货 1）
    margin_usdt: float = 0.0  # 占用保证金 = 名义 / 杠杆（现货 = 名义）
    liq_price: float = 0.0  # 逐仓强平价（0 = 不会强平 / 现货）
    lev_reason: str = ""  # 杠杆被下调的原因
    funding_usdt: float = 0.0  # 本仓累计资金费（+ 收取 / − 支付），已计入 realized
    funding_ms: int = 0  # 已结算到的最后一个资金费时间（ms）

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
    def __init__(self, starting_equity: float = 1000.0, fee_bps: float = 4.0, conn=None, fee_by_market: dict | None = None):
        self.conn = conn or db.connect()
        self.set_fees(fee_bps / 10_000, fee_by_market)
        self.migrated = migrate_csv(self.conn) if conn is None else {}
        self.load(starting_equity)

    def set_fees(self, default: float, by_market: dict | None = None):
        """default：小数费率；by_market：{"spot": 小数, "perp": 小数}（taker）。self.fee = 最大值，用于敞口预留。"""
        self.fee_by_market = dict(by_market or {})
        self.default_fee = float(default)
        self.fee = max([self.default_fee, *self.fee_by_market.values()]) if self.fee_by_market else self.default_fee

    def fee_for(self, market: str) -> float:
        return float(self.fee_by_market.get(market, self.default_fee))

    # ---------- 持久化 ----------
    def _q(self, sql, args=()):
        return db.query(sql, args, self.conn)

    def load(self, starting_equity: float):
        with _LOCK:
            st = {r["key"]: r["value"] for r in self._q("SELECT key, value FROM paper_state")}
            self.starting = float(st.get("starting_equity_usdt", starting_equity))
            self.realized = float(st.get("realized_usdt", self.starting))
            self.created = st.get("created_at", iso(utcnow()))
            self.funding_total = float(st.get("funding_total_usdt", 0.0) or 0.0)
            self.positions = {r["symbol"]: Position(**{k: r[k] for k in POS_COLS}) for r in
                              self._q("SELECT * FROM paper_positions")}
            for p in self.positions.values():
                p.venue, p.mark_source = p.venue or "", p.mark_source or ""
                p.tp_done, p.be_moved = int(p.tp_done or 0), int(p.be_moved or 0)
                if not (p.init_stop and float(p.init_stop) > 0):
                    p.init_stop = float(p.stop_price)  # 旧持仓：尚未移动过的止损即初始止损
                p.leverage = float(p.leverage or 1) or 1.0
                p.liq_price, p.funding_usdt = float(p.liq_price or 0), float(p.funding_usdt or 0)
                p.funding_ms, p.lev_reason = int(p.funding_ms or 0), p.lev_reason or ""
                if not p.funding_ms:  # 旧持仓：从入场时间起算资金费（不能追溯入场前的结算点）
                    try:
                        from datetime import datetime
                        p.funding_ms = int(datetime.fromisoformat(str(p.entry_time).replace("Z", "+00:00")).timestamp() * 1000)
                    except (TypeError, ValueError):
                        p.funding_ms = int(utcnow().timestamp() * 1000)
                if not (p.margin_usdt and float(p.margin_usdt) > 0):
                    p.margin_usdt = float(p.qty) * float(p.entry_price) / p.leverage  # 旧持仓：1 倍
            healed = self._heal_venues()
            self.blocks = {r["symbol"]: int(r["blocked_signal"]) for r in self._q("SELECT * FROM paper_blocks")}
            self.halts = {r["symbol"] for r in self._q("SELECT symbol FROM paper_halts")}
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
                     ("created_at", self.created), ("updated_at", iso(utcnow())),
                     ("funding_total_usdt", float(getattr(self, "funding_total", 0.0)))):
            c.execute("INSERT OR REPLACE INTO paper_state(key,value) VALUES(?,?)", (k, str(v)))
        c.execute("DELETE FROM paper_positions")
        for p in self.positions.values():
            _ins(c, "paper_positions", asdict(p))
        c.execute("DELETE FROM paper_blocks")
        for k, v in self.blocks.items():
            c.execute("INSERT INTO paper_blocks VALUES(?,?)", (k, int(v)))
        c.execute("DELETE FROM paper_halts")
        for s in self.halts:
            c.execute("INSERT INTO paper_halts VALUES(?)", (s,))

    def save(self):
        with _LOCK, db.tx(self.conn) as c:
            self._save(c)

    def reset(self, starting_equity: float):
        with _LOCK, db.tx(self.conn) as c:
            for t in ("paper_state", "paper_positions", "paper_blocks", "paper_halts", "paper_fills", "paper_ledger"):
                c.execute(f"DELETE FROM {t}")
            self.created = iso(utcnow())
            self.starting = self.realized = float(starting_equity)
            self.funding_total = 0.0
            self.positions, self.blocks, self.halts = {}, {}, set()
            self._save(c)

    # ---------- 记账 ----------
    def equity(self) -> float:
        return self.realized + sum(p.upnl() for p in self.positions.values())

    def gross(self) -> float:
        return sum(abs(p.qty * p.mark_price) for p in self.positions.values())

    def margin_used(self) -> float:
        """占用资金：永续 = 逐仓保证金（名义 / 杠杆），现货 = 买入名义。"""
        return sum(float(p.margin_usdt or 0) or abs(p.qty * p.entry_price) for p in self.positions.values())

    def set_leverage(self, symbol: str, lev: float, liq: float, reason: str = "") -> None:
        """开仓 / 调仓 / 移动止损后更新杠杆、保证金（= 数量 × 均价 / 杠杆）与强平价。"""
        with _LOCK:
            p = self.positions.get(symbol)
            if not p:
                return
            p.leverage = float(max(1.0, lev))
            p.liq_price = float(liq if liq == liq else 0.0)
            p.margin_usdt = p.qty * p.entry_price / (p.leverage if p.market == "perp" else 1.0)
            if reason:
                p.lev_reason = reason

    def apply_funding(self, symbol: str, rate: float, price: float, t_ms: int) -> float:
        """资金费结算：金额 = −方向 × 费率 × 数量 × 价格（正费率多付空收）。计入 realized，不产生成交记录。"""
        with _LOCK:
            p = self.positions.get(symbol)
            if not p or p.market != "perp" or int(t_ms) <= int(p.funding_ms or 0):
                return 0.0
            amt = -p.direction * float(rate) * p.qty * float(price)
            self.realized += amt
            p.funding_usdt = float(p.funding_usdt or 0) + amt
            p.funding_ms = int(t_ms)
            self.funding_total = float(getattr(self, "funding_total", 0.0)) + amt
            return amt

    def liquidate(self, symbol: str, price: float, price_kind: str, venue: str, mode="paper",
                  data_source="", price_time="") -> float:
        """逐仓强平：该仓保证金全部损失（剩余维持保证金作为强平费用），记一条 reason=强制平仓 的平仓成交。"""
        with _LOCK, db.tx(self.conn) as c:
            p = self.positions.pop(symbol)
            lost = float(p.margin_usdt or p.qty * p.entry_price / max(1.0, p.leverage))
            g = p.upnl(price)
            pen = max(0.0, lost + g)
            self.realized -= lost
            _ins(c, "paper_fills", dict(time=iso(utcnow()), symbol=symbol, market=p.market,
                                        side="sell" if p.side == "long" else "buy", action="close", qty=p.qty, price=price,
                                        price_kind=price_kind, notional_usdt=p.qty * price, fee_usdt=pen,
                                        realized_pnl_usdt=-lost, reason="强制平仓", mode=mode, venue=venue,
                                        data_source=data_source, price_time=price_time))
            self._save(c)
            return -lost

    def net(self) -> float:
        return sum(p.direction * p.qty * p.mark_price for p in self.positions.values())

    def mark(self, symbol: str, price: float, when: str, source: str = ""):
        # Serialize with save/open/close so WS mark ticks cannot race asdict(_save).
        with _LOCK:
            if symbol in self.positions:
                p = self.positions[symbol]
                p.mark_price, p.mark_time, p.mark_source = price, when, source or p.mark_source

    def open(self, *, symbol, market, side, qty, price, price_kind, stop, signal_bar, reason, venue, mode="paper",
             data_source="", price_time="", leverage: float = 1.0, liq_price: float = 0.0, lev_reason: str = ""):
        with _LOCK, db.tx(self.conn) as c:
            notional = qty * price
            fee = notional * self.fee_for(market)
            self.realized -= fee
            now = iso(utcnow())
            self.positions[symbol] = Position(symbol, market, side, qty, price, now, stop, price, now, notional, fee,
                                              signal_bar, venue, data_source, init_stop=float(stop))
            p = self.positions[symbol]
            p.leverage = float(max(1.0, leverage)) if market == "perp" else 1.0
            p.margin_usdt = notional / p.leverage
            p.liq_price = float(liq_price or 0.0) if market == "perp" else 0.0
            p.lev_reason = lev_reason or ""
            p.funding_ms = int(utcnow().timestamp() * 1000)  # 开仓之后的结算点才计资金费
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
            fee = notional * self.fee_for(p.market)
            pnl = p.upnl(price)
            self.realized += pnl - fee
            _ins(c, "paper_fills", dict(time=iso(utcnow()), symbol=symbol, market=p.market,
                                        side="sell" if p.side == "long" else "buy", action="close", qty=p.qty, price=price,
                                        price_kind=price_kind, notional_usdt=notional, fee_usdt=fee,
                                        realized_pnl_usdt=pnl - fee, reason=reason, mode=mode, venue=venue,
                                        data_source=data_source, price_time=price_time))
            self._save(c)
            return pnl - fee

    def resize(self, symbol: str, new_qty: float, price: float, price_kind: str, reason: str, venue: str, mode="paper",
               data_source="", price_time="") -> dict:
        """调仓（部分减仓 / 加仓）。减仓按加权入场价结算该部分盈亏；加仓更新加权入场价；止损不变。
        每条市价腿按该市场 taker 费率记账。返回 {action, qty, fee, pnl}。"""
        with _LOCK, db.tx(self.conn) as c:
            p = self.positions[symbol]
            dq = float(new_qty) - p.qty
            if abs(dq) <= 0 or new_qty <= 0:
                return {"action": "none", "qty": 0.0, "fee": 0.0, "pnl": 0.0}
            notional = abs(dq) * price
            fee = notional * self.fee_for(p.market)
            if dq < 0:
                action, g = "reduce", p.direction * (-dq) * (price - p.entry_price)
                side = "sell" if p.side == "long" else "buy"
            else:
                action, g = "add", 0.0
                side = "buy" if p.side == "long" else "sell"
                p.entry_price = (p.qty * p.entry_price + dq * price) / (p.qty + dq)
                p.notional_entry += notional
            self.realized += g - fee
            p.qty = float(new_qty)
            p.fees_paid += fee
            p.margin_usdt = p.qty * p.entry_price / (max(1.0, float(p.leverage or 1)) if p.market == "perp" else 1.0)
            _ins(c, "paper_fills", dict(time=iso(utcnow()), symbol=symbol, market=p.market, side=side, action=action,
                                        qty=abs(dq), price=price, price_kind=price_kind, notional_usdt=notional,
                                        fee_usdt=fee, realized_pnl_usdt=g - fee, reason=reason, mode=mode, venue=venue,
                                        data_source=data_source, price_time=price_time))
            self._save(c)
            return {"action": action, "qty": abs(dq), "fee": fee, "pnl": g - fee}

    def snapshot(self, note: str = "") -> dict:
        with _LOCK, db.tx(self.conn) as c:
            eq = self.equity()
            row = {"time": iso(utcnow()), "equity_usdt": eq, "realized_usdt": self.realized,
                   "unrealized_usdt": eq - self.realized, "cash_free_usdt": eq - self.margin_used(),
                   "gross_exposure_usdt": self.gross(), "net_exposure_usdt": self.net(),
                   "positions": len(self.positions), "note": note}
            _ins(c, "paper_ledger", row)
            self._save(c)  # 同时持久化最新标记价
            return row

    def last_stop_time(self, symbol: str) -> str:
        """该标的最近一次会锁定同向再入场的平仓（ATR / 保本止损、止盈、手动平仓 / 一键清仓 / 紧急停止）的成交时间（UTC ISO）；没有则返回空串。"""
        r = self._q("SELECT time FROM paper_fills WHERE symbol=? AND action='close' AND reason IN "
                    "('ATR止损','止盈','保本止损','快速离场','手动平仓','一键清仓','紧急停止(Kill Switch)') "
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

        def rec(op, cl, pos=None, adj=()):
            src = op or cl
            if op:
                side = "long" if op["side"] == "buy" else "short"
            else:
                side = "long" if cl["side"] == "sell" else "short"
            qty = float((op or cl)["qty"])
            entry_px = float(op["price"]) if op and px_ok(op.get("price")) else None
            exit_px = float(cl["price"]) if cl and px_ok(cl.get("price")) else None
            fee = float((op or {}).get("fee_usdt") or 0) + float((cl or {}).get("fee_usdt") or 0)
            fee += sum(float(a.get("fee_usdt") or 0) for a in adj)
            adj_real = sum(float(a.get("realized_pnl_usdt") or 0) for a in adj)  # 调仓腿：减仓盈亏 − 手续费 / 加仓 − 手续费
            pnl = pct = mark = None
            mark_src = mark_time = ""
            if cl is not None:
                pnl = float((op or {}).get("realized_pnl_usdt") or 0) + float(cl.get("realized_pnl_usdt") or 0) + adj_real
                if entry_px and qty:
                    pct = pnl / (entry_px * qty)
            elif pos is not None and entry_px and px_ok(pos.mark_price):
                mark = float(pos.mark_price)
                mark_src = pos.mark_source or ""
                mark_time = pos.mark_time or ""
                pnl = pos.upnl(mark) + float((op or {}).get("realized_pnl_usdt") or 0) + adj_real
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
                "resizes": len([a for a in adj if not str(a.get("reason") or "").startswith("止盈")]),
                "exit_qty": float(cl["qty"]) if cl else None,
                "partial_tp_qty": sum(float(a.get("qty") or 0) for a in adj if str(a.get("reason") or "").startswith("止盈")),
                "partial_tp_pnl_usdt": sum(float(a.get("realized_pnl_usdt") or 0) for a in adj if str(a.get("reason") or "").startswith("止盈")),
                "partial_tp": any(str(a.get("reason") or "").startswith("止盈") for a in adj),
            }

        pending: dict[str, list] = {}
        adjs: dict[int, list] = {}  # 开仓 fill_id → 该笔的调仓腿
        out: list[dict] = []
        for f in self.fills():
            if f["action"] == "open":
                pending.setdefault(f["symbol"], []).append(f)
            elif f["action"] in ("add", "reduce"):
                stack = pending.get(f["symbol"]) or []
                if stack:
                    adjs.setdefault(int(stack[-1]["fill_id"]), []).append(f)
            elif f["action"] == "close":
                stack = pending.setdefault(f["symbol"], [])
                op = stack.pop(0) if stack else None
                out.append(rec(op, f, adj=adjs.pop(int(op["fill_id"]), []) if op else ()))
        for sym, stack in pending.items():
            pos = self.positions.get(sym)
            for op in stack:
                out.append(rec(op, None, pos=pos, adj=adjs.pop(int(op["fill_id"]), [])))
        label_actions(out)
        return out

    def ledger(self) -> list[dict]:
        return self._q(f"SELECT {','.join(LEDGER_COLS)} FROM paper_ledger ORDER BY id")

    def log_order(self, **kw):
        row = {"time": iso(utcnow()), **{k: kw.get(k) for k in ORDER_COLS if k != "time"}}
        db.execute(f"INSERT INTO orders({','.join(row)}) VALUES({','.join('?' * len(row))})", tuple(row.values()), self.conn)

    def orders(self, limit: int = 300) -> list[dict]:
        return self._q(f"SELECT {','.join(ORDER_COLS)} FROM orders ORDER BY id DESC LIMIT ?", (limit,))


def _ts(x):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


EXIT_ACTION = {"ATR止损": "止损", "保本止损": "止损", "止盈": "止盈", "信号转空仓": "平仓", "快速离场": "平仓",
               "手动平仓": "手动平仓", "一键清仓": "清仓"}


def label_actions(trades: list[dict], window_sec: float = 300.0) -> list[dict]:
    """给开平配对记录加上动作标签（页面展示用）：
    entry_action：开多 / 开空 / 反手开多 / 反手开空（同币在 window_sec 内刚因「信号反转」平掉反方向）；
    exit_action：反手（信号反转且随即开了反方向）/ 平仓 / 止损 / 止盈 / 手动平仓 / 清仓；
    exit_note：信号反转但新方向没有开仓时说明原因（被入场过滤拦截，如 BTC 熊市过滤 / 趋势过滤 / 止损锁定）。"""
    for t in trades:
        t["entry_action"] = ("开多" if t.get("side") == "long" else "开空") if t.get("entry_time") else ""
        t["exit_action"], t["exit_note"] = "", ""
    by_sym: dict[str, list] = {}
    for t in trades:
        by_sym.setdefault(t["symbol"], []).append(t)
    for rows in by_sym.values():
        for t in rows:
            if t.get("status") != "closed":
                continue
            r = str(t.get("exit_reason") or "")
            base = r.split("（", 1)[0]
            if base == "信号反转":
                xt = _ts(t.get("exit_time"))
                nxt = [u for u in rows if u is not t and u.get("side") != t.get("side") and xt is not None
                       and _ts(u.get("entry_time")) is not None and 0 <= _ts(u.get("entry_time")) - xt <= window_sec]
                if nxt:
                    t["exit_action"] = "反手"
                    for u in nxt[:1]:
                        u["entry_action"] = "反手开多" if u.get("side") == "long" else "反手开空"
                else:
                    t["exit_action"] = "平仓"
                    t["exit_note"] = "信号已反转，但新方向被入场过滤拦截（如 BTC 熊市过滤 / 趋势过滤 / 止损锁定），只平仓未反手"
            else:
                t["exit_action"] = EXIT_ACTION.get(base, "止盈" if base.startswith("止盈") else "平仓")
    return trades

