import csv

import pytest

from qtw import db
from qtw.paper import PaperBook, migrate_csv


def test_paper_book_persists_in_sqlite(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last", stop=45000,
           signal_bar="x", reason="t", venue="okx", data_source="okx_public_rest")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark", stop=2200,
           signal_bar="x", reason="t", venue="okx")
    fees = (100 + 100) * 0.0004
    assert b.equity() == pytest.approx(1000 - fees)
    b.mark("BTCUSDT", 55000, "t"); b.mark("ETHUSDT", 1900, "t")
    b.save()
    b2 = PaperBook(1000, 4, conn=conn)
    assert set(b2.positions) == {"BTCUSDT", "ETHUSDT"}
    assert b2.equity() == pytest.approx(1000 - fees + 15)
    pnl = b2.close("ETHUSDT", 1900, "mark", "t", "okx")
    assert pnl == pytest.approx(5 - 0.05 * 1900 * 0.0004)
    assert len(b2.fills()) == 3 and b2.fills()[0]["data_source"] == "okx_public_rest"
    b2.log_order(mode="paper", venue="okx", symbol="X", market="spot", action="open_long", qty=1, ref_price=1, status="paper_filled", detail="")
    assert b2.orders()[0]["status"] == "paper_filled"


def test_migrate_csv_book(tmp_path):
    src = tmp_path / "paper"
    src.mkdir()
    def w(name, rows):
        with (src / name).open("w", newline="", encoding="utf-8") as f:
            cw = csv.DictWriter(f, fieldnames=list(rows[0]))
            cw.writeheader(); cw.writerows(rows)
    w("state.csv", [{"key": "starting_equity_usdt", "value": "1000"}, {"key": "realized_usdt", "value": "999.6"},
                    {"key": "created_at", "value": "2026-11-09T15:06:00Z"}])
    w("positions.csv", [dict(symbol="BTCUSDT", market="perp", side="short", qty="0.001", entry_price="70000",
                             entry_time="t", stop_price="72000", mark_price="70000", mark_time="t", notional_entry="70",
                             fees_paid="0.028", signal_bar="t")])
    w("fills.csv", [dict(fill_id="1", time="t", symbol="BTCUSDT", market="perp", side="sell", action="open", qty="0.001",
                         price="70000", price_kind="mark", notional_usdt="70", fee_usdt="0.028", realized_pnl_usdt="-0.028",
                         reason="r", mode="paper", venue="okx")])
    conn = db.connect(tmp_path / "m.sqlite")
    n = migrate_csv(conn, src)
    assert n["positions"] == 1 and n["fills"] == 1
    b = PaperBook(1000, 4, conn=conn)
    assert b.positions["BTCUSDT"].side == "short" and b.realized == pytest.approx(999.6)
    assert not src.exists()
    assert migrate_csv(conn, src) == {}


def test_heal_empty_position_venue_from_open_fill(tmp_path):
    """Legacy rows may lack venue on positions; load() backfills from open fill."""
    conn = db.connect(tmp_path / "heal.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.001, price=70000, price_kind="mark",
           stop=72000, signal_bar="x", reason="t", venue="okx", data_source="okx_public_ws")
    # Simulate pre-venue schema: wipe position.venue then reload
    with db.tx(conn) as c:
        c.execute("UPDATE paper_positions SET venue='' WHERE symbol='BTCUSDT'")
    b2 = PaperBook(1000, 4, conn=conn)
    assert b2.positions["BTCUSDT"].venue == "okx"
    row = db.query("SELECT venue FROM paper_positions WHERE symbol='BTCUSDT'", (), conn)[0]
    assert row["venue"] == "okx"
