"""SSE /api/stream payload must not crash when a connection row is incomplete."""
import json

from qtw import app as qapp


def test_live_payload_survives_missing_last_msg_age_sec(monkeypatch):
    """Regression: KeyError last_msg_age_sec crashed the ASGI SSE generator
    when a socket was reconnecting after gaierror and had no message timestamp.
    """
    def fake_status(venue=None):
        return {
            "mode": "recovering",
            "connections": [
                {
                    "name": "okx_public",
                    "status": "reconnecting",
                    "url": "wss://ws.okx.com:443/ws/v5/public",
                    "last_msg": "",
                    "reconnects": 1,
                    "last_error": "gaierror",
                    # last_msg_age_sec intentionally omitted
                }
            ],
            "quotes_ws_fresh": 0,
        }

    monkeypatch.setattr(qapp.stream, "status", fake_status)
    monkeypatch.setattr(qapp.stream, "snapshot", lambda venue: {"prices": {}, "forming": {}})
    payload = qapp._live_payload()
    row = payload["connections"][0]
    assert row["name"] == "okx_public"
    assert row["status"] == "reconnecting"
    assert row["last_msg_age_sec"] is None
    json.dumps(payload, ensure_ascii=False)
