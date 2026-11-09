"""FastAPI lifespan replaces deprecated on_event startup."""
from pathlib import Path

from fastapi.testclient import TestClient

from qtw import app as app_mod
from qtw.app import app


def test_app_uses_lifespan_not_on_event():
    assert app.router.lifespan_context is not None
    src = Path(app_mod.__file__).read_text(encoding="utf-8")
    assert "async def lifespan" in src
    assert "@app.on_event(" not in src
    assert "on_event(\"startup\")" not in src


def test_lifespan_starts_healthy_paper_mode():
    with TestClient(app) as client:
        h = client.get("/api/health")
        assert h.status_code == 200
        body = h.json()
        assert body["ok"] is True
        assert body["mode"] == "paper"
        st = client.get("/api/status").json()
        assert st["live_gate_open"] is False
        assert st["settings"]["live"]["live_enabled"] is False
