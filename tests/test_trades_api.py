"""Round-trip trades API and position pnl fields used by the frontend."""
from fastapi.testclient import TestClient

from qtw.app import EXPORTS, app


def test_trades_endpoint_and_export_registered():
    client = TestClient(app)
    r = client.get("/api/trades")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    for row in r.json():
        for k in ("trade_id", "symbol", "side", "qty", "entry_price", "exit_price",
                  "fee_usdt", "pnl_usdt", "pnl_pct", "status", "entry_reason", "exit_reason"):
            assert k in row
    assert "paper_trades" in EXPORTS
    dash = client.get("/api/dashboard").json()
    for p in dash["positions"]:
        for k in ("entry_price", "mark_price", "upnl", "upnl_pct"):
            assert k in p
