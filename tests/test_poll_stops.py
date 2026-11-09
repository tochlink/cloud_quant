"""Intrabar ATR stop poll between worker cycles."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from qtw import db, engine
from qtw.market.base import Quote
from qtw.paper import PaperBook


def _q(symbol, market, price, venue="okx"):
    return Quote(
        venue=venue, symbol=symbol, market=market, price=price,
        kind="mark" if market == "perp" else "last",
        ts=datetime.now(timezone.utc), data_source=f"{venue}_public_ws",
        source_host="ws.okx.com",
    )


def test_poll_stops_closes_short_when_mark_hits_stop(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "stops.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.001, price=70000, price_kind="mark",
           stop=72000, signal_bar="x", reason="t", venue="okx", data_source="okx_public_ws",
           price_time="2026-11-09T15:06:00Z")
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "_MARK", {"venue": "okx", "dirty": False})
    routed = []

    def fake_quote(venue, sym, market):
        q = _q(sym, market, 72100)
        return q.price, q.kind, q

    monkeypatch.setattr(engine, "_quote", fake_quote)
    monkeypatch.setattr(engine, "_route", lambda *a, **k: routed.append(a))
    monkeypatch.setattr(engine, "export_paper_csv", lambda cfg: None)
    cfg = {"venue": "okx", "risk": {"starting_equity_usdt": 1000}, "fees": {"taker_bps": 4},
           "live": {"mode": "paper", "live_enabled": False, "okx_demo": True, "gate_testnet": True,
                    "confirm_phrase": ""}}
    ev = engine.poll_stops(cfg)
    assert len(ev) == 1 and "ATR止损·实时" in ev[0]
    assert "BTCUSDT" not in b.positions
    assert b.blocks["BTCUSDT"] == -1
    assert routed and routed[0][3] == "close_short"


def test_poll_stops_skips_when_not_hit(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "nostop.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark",
           stop=2200, signal_bar="x", reason="t", venue="okx")
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "_MARK", {"venue": "okx", "dirty": False})
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (2100, "mark", _q(s, m, 2100)))
    monkeypatch.setattr(engine, "_route", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no route")))
    cfg = {"venue": "okx", "risk": {"starting_equity_usdt": 1000}, "fees": {"taker_bps": 4},
           "live": {"mode": "paper", "live_enabled": False, "okx_demo": True, "gate_testnet": True,
                    "confirm_phrase": ""}}
    assert engine.poll_stops(cfg) == []
    assert "ETHUSDT" in b.positions
    assert b.positions["ETHUSDT"].mark_price == pytest.approx(2100)
