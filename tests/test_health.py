""" /api/health is the ensure_up / polish smoke probe — keep it secret-free. """
from fastapi.testclient import TestClient

from qtw.app import app


def test_health_reports_paper_gate_and_stream_without_secrets():
    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["mode"] == "paper"
    assert body["venue"] in ("okx", "gate")
    assert body["live_enabled"] is False
    assert body["live_gate_open"] is False
    assert isinstance(body["stream"], dict)
    assert "mode" in body["stream"]
    assert "running" in body["stream"]
    assert "quotes_ws_fresh" in body["stream"]
    assert "quotes_rest_fresh" in body["stream"]
    assert "watchdog_running" in body["stream"]
    assert "loop_heartbeat_age_sec" in body["stream"]
    assert "rest_fill_inflight" in body["stream"]
    assert "stall_suspect_count" in body["stream"]
    assert body["quotes_ws_fresh"] == body["stream"]["quotes_ws_fresh"]
    assert isinstance(body["worker"]["running"], bool)
    assert "persist_running" in body
    assert isinstance(body["persist_running"], bool)
    assert "time" in body and "time_sh" in body
    assert "paper" in body
    if body["paper"] is not None:
        assert "equity" in body["paper"] and "positions" in body["paper"]
        assert "starting_equity" in body["paper"]
    assert "btc_perp" in body  # may be null when stream not started in TestClient
    assert "last_zombie_kick_age_sec" in body["stream"]
    assert "last_zombie_max_age_sec" in body["stream"]
    # Must never leak vault / keys / full settings
    blob = r.text.lower()
    for forbidden in ("api_key", "secret", "passphrase", "vault", "fernet", "settings"):
        assert forbidden not in blob, forbidden
