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
    assert body["quotes_ws_fresh"] == body["stream"]["quotes_ws_fresh"]
    assert isinstance(body["worker"]["running"], bool)
    assert "time" in body and "time_sh" in body
    # Must never leak vault / keys / full settings
    blob = r.text.lower()
    for forbidden in ("api_key", "secret", "passphrase", "vault", "fernet", "settings"):
        assert forbidden not in blob, forbidden
