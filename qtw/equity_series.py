"""Paper equity series with trade events attached to real ledger points.

Only official book data is used: paper_ledger equity snapshots plus the book's
current official equity(). Events come from paper_fills, orders, and signal_log.
No interpolated or mock mid-point equity is invented.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .timeutil import iso, sh, utcnow

# Display kinds requested on the hero tooltip (plus 一键清仓, which is a close).
_KIND_OPEN = "开仓"
_KIND_CLOSE = "平仓"
_KIND_RESIZE = "调仓"
_KIND_STOP = "止损"
_KIND_TP = "止盈"
_KIND_MANUAL = "手动平仓"
_KIND_FLAT = "一键清仓"

_TRADE_KINDS = (_KIND_OPEN, _KIND_CLOSE, _KIND_RESIZE, _KIND_STOP, _KIND_TP, _KIND_MANUAL, _KIND_FLAT)

MAX_POINTS = 3000


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def _iso(ts: datetime | str | None) -> str:
    if ts is None:
        return ""
    if isinstance(ts, datetime):
        return iso(ts)
    return str(ts)


def classify(action: str | None, reason: str | None) -> str | None:
    """Map a fill/order/signal action + reason to a tooltip kind, or None to skip."""
    a = (action or "").strip().lower()
    r = reason or ""
    if a in ("add", "reduce", "resize") or "调仓" in r:
        return _KIND_RESIZE
    if a == "open" or r.startswith("开仓") or "开仓" == r:
        return _KIND_OPEN
    if a in ("close", "flatten") or "平仓" in r or "清仓" in r or "止损" in r or "止盈" in r:
        if "止盈" in r:
            return _KIND_TP
        if "ATR止损" in r or "止损" in r:
            return _KIND_STOP
        if "手动平仓" in r:
            return _KIND_MANUAL
        if "一键清仓" in r:
            return _KIND_FLAT
        return _KIND_CLOSE
    return None


def _pos_side(action: str | None, fill_side: str | None) -> str:
    a = (action or "").strip().lower()
    s = (fill_side or "").strip().lower()
    if s in ("long", "short"):
        return s
    if a in ("open", "add"):
        return "long" if s == "buy" else "short" if s == "sell" else ""
    if a in ("close", "reduce", "flatten"):
        return "long" if s == "sell" else "short" if s == "buy" else ""
    return "long" if s == "buy" else "short" if s == "sell" else ""


def _event(*, time: str, kind: str, symbol: str, market: str = "", side: str = "",
           action: str = "", price: float | None = None, qty: float | None = None,
           realized_pnl: float | None = None, reason: str = "", source: str = "") -> dict[str, Any]:
    return {
        "time": time,
        "time_sh": sh(_parse(time)),
        "kind": kind,
        "symbol": symbol or "",
        "market": market or "",
        "side": side or "",
        "side_cn": "多" if side == "long" else "空" if side == "short" else "",
        "action": action or "",
        "price": None if price is None else float(price),
        "qty": None if qty is None else float(qty),
        "realized_pnl": None if realized_pnl is None else float(realized_pnl),
        "reason": reason or "",
        "source": source or "",
    }


def _num(x, default=None):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def _events_from_fills(fills: list[dict]) -> list[dict]:
    out = []
    for f in fills or []:
        kind = classify(f.get("action"), f.get("reason"))
        if not kind:
            continue
        out.append(_event(
            time=str(f.get("time") or ""),
            kind=kind,
            symbol=str(f.get("symbol") or ""),
            market=str(f.get("market") or ""),
            side=_pos_side(f.get("action"), f.get("side")),
            action=str(f.get("action") or ""),
            price=_num(f.get("price")),
            qty=_num(f.get("qty")),
            realized_pnl=_num(f.get("realized_pnl_usdt")),
            reason=str(f.get("reason") or ""),
            source="fill",
        ))
    return out


def _events_from_orders(orders: list[dict], have: set[tuple]) -> list[dict]:
    """Orders that are not already represented by a fill (same symbol+kind+second)."""
    out = []
    for o in orders or []:
        kind = classify(o.get("action"), o.get("detail") or o.get("reason"))
        if not kind:
            continue
        ts = _parse(o.get("time"))
        key = (kind, str(o.get("symbol") or ""), ts.replace(microsecond=0) if ts else None)
        if key in have:
            continue
        out.append(_event(
            time=str(o.get("time") or ""),
            kind=kind,
            symbol=str(o.get("symbol") or ""),
            market=str(o.get("market") or ""),
            side=_pos_side(o.get("action"), o.get("side")),
            action=str(o.get("action") or ""),
            price=_num(o.get("ref_price") or o.get("price")),
            qty=_num(o.get("qty")),
            realized_pnl=None,
            reason=str(o.get("detail") or o.get("reason") or ""),
            source="order",
        ))
    return out


def _events_from_signals(rows: list[dict], have: set[tuple]) -> list[dict]:
    """signal_log rows that name a trade-like action and are not already covered by a fill."""
    out = []
    for r in rows or []:
        action = str(r.get("action") or "")
        kind = None
        if "调仓" in action:
            kind = _KIND_RESIZE
        elif "止盈" in action:
            kind = _KIND_TP
        elif "止损" in action:
            kind = _KIND_STOP
        elif "手动平仓" in action:
            kind = _KIND_MANUAL
        elif "一键清仓" in action:
            kind = _KIND_FLAT
        elif "平仓" in action:
            kind = _KIND_CLOSE
        elif "开仓" in action:
            kind = _KIND_OPEN
        if not kind:
            continue
        ts = _parse(r.get("time"))
        key = (kind, str(r.get("symbol") or ""), ts.replace(microsecond=0) if ts else None)
        if key in have:
            continue
        new_sig = r.get("new_signal")
        side = "long" if new_sig == 1 else "short" if new_sig == -1 else ""
        out.append(_event(
            time=str(r.get("time") or ""),
            kind=kind,
            symbol=str(r.get("symbol") or ""),
            side=side,
            action=action,
            reason=action,
            source="signal_log",
        ))
    return out


def _dedupe_key(ev: dict) -> tuple:
    ts = _parse(ev.get("time"))
    return (ev.get("kind") or "", ev.get("symbol") or "", ts.replace(microsecond=0) if ts else None)


def collect_events(bk, signal_rows: list[dict] | None = None) -> list[dict]:
    fills = _events_from_fills(bk.fills())
    have = {_dedupe_key(e) for e in fills}
    extra = _events_from_orders(bk.orders(limit=2000), have)
    have |= {_dedupe_key(e) for e in extra}
    if signal_rows is None:
        try:
            from . import signal_log
            signal_rows = signal_log.recent(limit=2000, conn=getattr(bk, "conn", None))
        except Exception:  # noqa: BLE001
            signal_rows = []
    sigs = _events_from_signals(signal_rows, have)
    evs = fills + extra + sigs
    evs.sort(key=lambda e: _parse(e["time"]) or datetime.min.replace(tzinfo=timezone.utc))
    return evs


def _ledger_points(bk) -> list[dict]:
    rows = list(bk.ledger() or [])
    if len(rows) > MAX_POINTS:
        rows = rows[-MAX_POINTS:]
    out: list[dict] = []
    for r in rows:
        t = str(r.get("time") or "")
        eq = _num(r.get("equity_usdt"), None)
        if not t or eq is None:
            continue
        # Drop only an exact duplicate (same time and same equity). Keep same-second
        # snapshots that record a different official equity so the curve is not flattened.
        if out and out[-1]["time"] == t and abs(out[-1]["equity"] - float(eq)) < 1e-9:
            out[-1]["gross"] = _num(r.get("gross_exposure_usdt"), 0.0) or 0.0
            out[-1]["net"] = _num(r.get("net_exposure_usdt"), 0.0) or 0.0
            continue
        out.append({
            "time": t,
            "time_sh": sh(_parse(t)),
            "equity": float(eq),
            "gross": _num(r.get("gross_exposure_usdt"), 0.0) or 0.0,
            "net": _num(r.get("net_exposure_usdt"), 0.0) or 0.0,
            "events": [],
        })
    return out


def _append_current(points: list[dict], bk) -> None:
    """Append the book's current official equity if it is newer than the last ledger row.

    This is a live official computation (book.equity()), not a mock mid-point.
    """
    try:
        cur = float(bk.equity())
    except Exception:  # noqa: BLE001
        return
    now = utcnow()
    last_t = _parse(points[-1]["time"]) if points else None
    # Skip if last ledger is already this equity at the same second (no new info).
    if points and last_t and abs(points[-1]["equity"] - cur) < 1e-9 and (now - last_t).total_seconds() < 2:
        return
    # If last row is very recent with a different equity, still add a current mark.
    if last_t and (now - last_t).total_seconds() < 0.5 and abs(points[-1]["equity"] - cur) < 1e-9:
        return
    t = iso(now)
    try:
        gross = float(bk.gross())
        net = float(bk.net())
    except Exception:  # noqa: BLE001
        gross = net = 0.0
    points.append({
        "time": t,
        "time_sh": sh(now),
        "equity": cur,
        "gross": gross,
        "net": net,
        "events": [],
    })


def attach_events(points: list[dict], events: list[dict]) -> None:
    """Assign each event to the first ledger point whose time is >= the event (causal).

    Events after the last point attach to the last point; events before the first
    attach to the first. Equity values are never changed.
    """
    if not points or not events:
        return
    parsed = [(_parse(p["time"]), p) for p in points]

    def _sec(ts: datetime | None):
        return ts.replace(microsecond=0) if ts else None

    for ev in events:
        et = _parse(ev.get("time"))
        if et is None:
            continue
        # Prefer the last snapshot in the same second (usually the post-fill mark).
        same = [p for ts, p in parsed if ts and _sec(ts) == _sec(et)]
        if same:
            same[-1]["events"].append(ev)
            continue
        chosen = parsed[-1][1]
        for ts, p in parsed:
            if ts and ts > et:
                chosen = p
                break
        chosen["events"].append(ev)


def for_book(bk, signal_rows: list[dict] | None = None) -> dict[str, Any]:
    """Build the hover series for a PaperBook. All equity values are real book data."""
    points = _ledger_points(bk)
    _append_current(points, bk)
    evs = collect_events(bk, signal_rows)
    attach_events(points, evs)
    try:
        starting = float(bk.starting)
    except Exception:  # noqa: BLE001
        starting = float(points[0]["equity"]) if points else 0.0
    try:
        current = float(bk.equity())
    except Exception:  # noqa: BLE001
        current = float(points[-1]["equity"]) if points else starting
    now = utcnow()
    return {
        "starting_equity": starting,
        "current_equity": current,
        "time": iso(now),
        "time_sh": sh(now),
        "points": points,
        "event_count": sum(len(p["events"]) for p in points),
    }
