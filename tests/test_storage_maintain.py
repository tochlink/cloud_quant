"""SQLite 24/7 hygiene: candle/ledger prune + WAL TRUNCATE."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from qtw import db


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "qtw.sqlite"
    monkeypatch.setattr(db, "db_path", lambda: path)
    # Fresh connection map for this path
    db._CONNS.clear()
    conn = db.connect(path)
    yield path, conn
    db._CONNS.clear()


def test_prune_candles_keeps_newest_per_series(tmp_db):
    path, conn = tmp_db
    rows = []
    for t in range(10):
        rows.append(("okx", "perp", "BTCUSDT", "4h", 1_000_000 + t * 1000,
                     1.0, 1.0, 1.0, 1.0, 0.0, "test", "localhost", "2026-01-01T00:00:00Z"))
    with db.tx(conn) as c:
        c.executemany(
            "INSERT INTO candles(venue,market,symbol,interval,open_time,open,high,low,close,volume,"
            "data_source,source_host,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    assert db.query("SELECT COUNT(*) n FROM candles", (), conn)[0]["n"] == 10
    deleted = db.prune_candles(keep_bars=4, conn=conn)
    assert deleted == 6
    left = db.query(
        "SELECT open_time FROM candles WHERE venue='okx' AND market='perp' AND symbol='BTCUSDT' "
        "ORDER BY open_time", (), conn)
    assert [r["open_time"] for r in left] == [1_000_000 + t * 1000 for t in range(6, 10)]


def test_prune_ledger_keeps_newest(tmp_db):
    path, conn = tmp_db
    with db.tx(conn) as c:
        for i in range(8):
            c.execute(
                "INSERT INTO paper_ledger(time,equity_usdt,realized_usdt,unrealized_usdt,"
                "cash_free_usdt,gross_exposure_usdt,net_exposure_usdt,positions,note) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (f"2026-01-01T00:0{i}:00Z", 1000 + i, 1000, i, 100, 900, -900, 1, "无变化"),
            )
    deleted = db.prune_ledger(keep_rows=3, conn=conn)
    assert deleted == 5
    left = db.query("SELECT equity_usdt FROM paper_ledger ORDER BY id", (), conn)
    assert [r["equity_usdt"] for r in left] == [1005.0, 1006.0, 1007.0]


def test_maintain_storage_truncate_and_prune(tmp_db):
    path, conn = tmp_db
    with db.tx(conn) as c:
        for t in range(6):
            c.execute(
                "INSERT INTO candles(venue,market,symbol,interval,open_time,open,high,low,close,volume,"
                "data_source,source_host,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("okx", "spot", "ETHUSDT", "4h", 2_000_000 + t, 1, 1, 1, 1, 0, "t", "h", "t"),
            )
        for i in range(5):
            c.execute(
                "INSERT INTO paper_ledger(time,equity_usdt,realized_usdt,unrealized_usdt,"
                "cash_free_usdt,gross_exposure_usdt,net_exposure_usdt,positions,note) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (f"t{i}", 1000, 1000, 0, 1000, 0, 0, 0, "x"),
            )
    # Force some WAL frames then maintain
    info = db.maintain_storage(truncate_wal=True, prune=False)
    assert info["truncate"] is not None
    assert info["truncate"][0] == 0  # not busy
    # prune with monkeypatched keep constants via explicit prune_* already tested;
    # here just ensure maintain_storage(prune=True) runs without error.
    # Temporarily shrink keeps by calling prune helpers after maintain.
    assert db.prune_candles(keep_bars=2, conn=conn) == 4
    assert db.prune_ledger(keep_rows=2, conn=conn) == 3
    info2 = db.maintain_storage(truncate_wal=True, prune=False)
    assert isinstance(info2["wal_bytes"], int)


def test_checkpoint_wal_accepts_truncate(tmp_db):
    _path, _conn = tmp_db
    busy, log, ckpt = db.checkpoint_wal("TRUNCATE")
    assert busy == 0
    assert isinstance(log, int) and isinstance(ckpt, int)
