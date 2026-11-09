"""持久化纸面账本（CSV，存于 data/paper/，跨进程/重启保留）。

记账模型（1 倍保证金）：
  realized = 起始资金 + 已实现盈亏 − 手续费
  equity   = realized + Σ 未实现盈亏
  可用现金 = equity − Σ |持仓名义|（现货占用资金，永续空头占用等额保证金）
"""
from __future__ import annotations

import csv
import threading
from dataclasses import asdict, dataclass, fields

from .paths import PAPER_DIR, ensure_dirs
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

    @property
    def direction(self) -> int:
        return 1 if self.side == "long" else -1

    def upnl(self, px: float | None = None) -> float:
        return self.direction * self.qty * ((px or self.mark_price) - self.entry_price)


FILL_COLS = ["fill_id", "time", "symbol", "market", "side", "action", "qty", "price", "price_kind",
             "notional_usdt", "fee_usdt", "realized_pnl_usdt", "reason", "mode", "venue"]
LEDGER_COLS = ["time", "equity_usdt", "realized_usdt", "unrealized_usdt", "cash_free_usdt", "gross_exposure_usdt",
               "net_exposure_usdt", "positions", "note"]
POS_COLS = [f.name for f in fields(Position)]


def _read(path, cols):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _write(path, cols, rows):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def _append(path, cols, row):
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


class PaperBook:
    def __init__(self, starting_equity: float = 1000.0, fee_bps: float = 4.0, directory=None):
        self.dir = directory or PAPER_DIR
        ensure_dirs()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.fee = fee_bps / 10_000
        self.f_state, self.f_pos = self.dir / "state.csv", self.dir / "positions.csv"
        self.f_fills, self.f_ledger = self.dir / "fills.csv", self.dir / "ledger.csv"
        self.f_blocks = self.dir / "stop_blocks.csv"
        self.load(starting_equity)

    # ---------- 持久化 ----------
    def load(self, starting_equity: float):
        with _LOCK:
            st = {r["key"]: r["value"] for r in _read(self.f_state, ["key", "value"])}
            self.starting = float(st.get("starting_equity_usdt", starting_equity))
            self.realized = float(st.get("realized_usdt", self.starting))
            self.created = st.get("created_at", iso(utcnow()))
            self.positions: dict[str, Position] = {}
            for r in _read(self.f_pos, POS_COLS):
                kw = {k: (float(r[k]) if k in ("qty", "entry_price", "stop_price", "mark_price", "notional_entry",
                                                "fees_paid") else r[k]) for k in POS_COLS}
                self.positions[r["symbol"]] = Position(**kw)
            self.blocks = {r["symbol"]: int(r["blocked_signal"]) for r in _read(self.f_blocks, [])}
            if not self.f_state.exists():
                self.save()

    def save(self):
        with _LOCK:
            _write(self.f_state, ["key", "value"], [
                {"key": "starting_equity_usdt", "value": self.starting},
                {"key": "realized_usdt", "value": self.realized},
                {"key": "created_at", "value": self.created},
                {"key": "updated_at", "value": iso(utcnow())},
            ])
            _write(self.f_pos, POS_COLS, [asdict(p) for p in self.positions.values()])
            _write(self.f_blocks, ["symbol", "blocked_signal"],
                   [{"symbol": k, "blocked_signal": v} for k, v in self.blocks.items()])

    def reset(self, starting_equity: float):
        with _LOCK:
            for f in (self.f_state, self.f_pos, self.f_fills, self.f_ledger, self.f_blocks):
                if f.exists():
                    f.unlink()
            self.created = iso(utcnow())
            self.starting = self.realized = float(starting_equity)
            self.positions, self.blocks = {}, {}
            self.save()

    # ---------- 记账 ----------
    def equity(self) -> float:
        return self.realized + sum(p.upnl() for p in self.positions.values())

    def gross(self) -> float:
        return sum(abs(p.qty * p.mark_price) for p in self.positions.values())

    def net(self) -> float:
        return sum(p.direction * p.qty * p.mark_price for p in self.positions.values())

    def mark(self, symbol: str, price: float, when: str):
        if symbol in self.positions:
            self.positions[symbol].mark_price, self.positions[symbol].mark_time = price, when

    def _fill(self, **kw):
        n = len(_read(self.f_fills, FILL_COLS)) + 1
        _append(self.f_fills, FILL_COLS, {"fill_id": n, **kw})

    def open(self, *, symbol, market, side, qty, price, price_kind, stop, signal_bar, reason, venue, mode="paper"):
        with _LOCK:
            notional = qty * price
            fee = notional * self.fee
            self.realized -= fee
            now = iso(utcnow())
            self.positions[symbol] = Position(symbol, market, side, qty, price, now, stop, price, now, notional, fee, signal_bar)
            self._fill(time=now, symbol=symbol, market=market, side="buy" if side == "long" else "sell",
                       action="open", qty=qty, price=price, price_kind=price_kind, notional_usdt=notional,
                       fee_usdt=fee, realized_pnl_usdt=-fee, reason=reason, mode=mode, venue=venue)
            self.save()

    def close(self, symbol: str, price: float, price_kind: str, reason: str, venue: str, mode="paper") -> float:
        with _LOCK:
            p = self.positions.pop(symbol)
            notional = p.qty * price
            fee = notional * self.fee
            pnl = p.upnl(price)
            self.realized += pnl - fee
            self._fill(time=iso(utcnow()), symbol=symbol, market=p.market, side="sell" if p.side == "long" else "buy",
                       action="close", qty=p.qty, price=price, price_kind=price_kind, notional_usdt=notional,
                       fee_usdt=fee, realized_pnl_usdt=pnl - fee, reason=reason, mode=mode, venue=venue)
            self.save()
            return pnl - fee

    def snapshot(self, note: str = "") -> dict:
        with _LOCK:
            eq = self.equity()
            row = {"time": iso(utcnow()), "equity_usdt": eq, "realized_usdt": self.realized,
                   "unrealized_usdt": eq - self.realized, "cash_free_usdt": (0.0 if abs(eq - self.gross()) < 1e-6 else eq - self.gross()),
                   "gross_exposure_usdt": self.gross(), "net_exposure_usdt": self.net(),
                   "positions": len(self.positions), "note": note}
            _append(self.f_ledger, LEDGER_COLS, row)
            return row

    def fills(self) -> list[dict]:
        return _read(self.f_fills, FILL_COLS)

    def ledger(self) -> list[dict]:
        return _read(self.f_ledger, LEDGER_COLS)
