"""Worker status must be readable over GET without a 405."""
from fastapi.testclient import TestClient

from qtw.app import app


def test_get_worker_status_ok():
    client = TestClient(app)
    r = client.get("/api/worker/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "running" in body
    assert "next_run_in_sec" in body
    assert "last_run_sh" in body


def test_post_worker_status_ok():
    client = TestClient(app)
    r = client.post("/api/worker/status")
    assert r.status_code == 200, r.text
    assert "running" in r.json()
