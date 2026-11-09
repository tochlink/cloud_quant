"""有纸面持仓时禁止切换行情源，避免跨所混价。"""
from fastapi.testclient import TestClient

from qtw import db, engine, settings as S
from qtw.app import app
from qtw.paper import PaperBook


def test_put_settings_blocks_venue_switch_with_open_positions(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "lock.sqlite")
    monkeypatch.setattr(engine, "_BOOK", None)
    # Point engine book at temp db via monkeypatch of db.connect default? Use engine.book after seeding.
    # Seed via PaperBook then attach as engine book.
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.001, price=70000, price_kind="mark",
           stop=72000, signal_bar="x", reason="t", venue="okx")
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "_MARK", {"venue": "okx", "dirty": False})

    cfg = S.load()
    cfg["venue"] = "okx"
    # Keep settings on default path; only assert API guard uses engine.book()
    client = TestClient(app)
    r = client.put("/api/settings", json={"venue": "gate"})
    assert r.status_code == 409
    assert "纸面持仓" in r.json()["detail"]
    # same venue is fine
    r2 = client.put("/api/settings", json={"venue": "okx"})
    assert r2.status_code == 200
