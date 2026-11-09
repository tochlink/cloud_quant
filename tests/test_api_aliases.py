"""Thin monitoring aliases should reuse dashboard / stream data instead of 404."""
from fastapi.testclient import TestClient

from qtw.app import app


def test_monitoring_aliases_return_existing_data():
    client = TestClient(app)
    dash = client.get("/api/dashboard")
    assert dash.status_code == 200
    d = dash.json()
    assert "equity" in d and "positions" in d
    assert d.get("mode") == "paper"

    paper = client.get("/api/paper")
    assert paper.status_code == 200
    p = paper.json()
    assert p["mode"] == "paper"
    assert p["starting_equity"] == d["starting_equity"]
    assert p["equity"] == d["equity"]
    assert p["gross"] == d["gross"]
    assert p["positions"] == d["positions"]
    assert p["recent_fills"] == d["recent_fills"]
    assert "time_sh" in p and "CST+8" in p["time_sh"]
    assert "worker" in p

    pos = client.get("/api/positions")
    assert pos.status_code == 200
    pj = pos.json()
    assert pj["positions"] == d["positions"]
    assert pj["equity"] == d["equity"]
    assert pj["venue"] == d["venue"]

    risk = client.get("/api/risk")
    assert risk.status_code == 200
    r = risk.json()
    assert r["mode"] == "paper"
    assert r["rules"]["max_risk_per_trade"] <= 0.05 + 1e-12
    assert r["rules"]["max_weight_per_name"] <= 0.2 + 1e-12
    assert r["equity"] == d["equity"]
    assert r["gross"] == d["gross"]
    assert isinstance(r["positions"], list)
    assert r["name_cap_ok"] is True or r["name_cap_breaches"]
    assert "gross_cap_ok" in r
    assert "gross_usage" in r

    quotes = client.get("/api/quotes")
    assert quotes.status_code == 200
    q = quotes.json()
    assert q["venue"] == d["venue"]
    assert "prices" in q and isinstance(q["prices"], dict)
    assert "quotes" in q and isinstance(q["quotes"], list)
    assert "stream_mode" in q
    assert "quotes_ws_fresh" in q
    assert "time_sh" in q
    for row in q["quotes"]:
        assert "symbol" in row and "market" in row and "price" in row
        nested = q["prices"][row["symbol"]][row["market"]]
        assert nested["price"] == row["price"]
