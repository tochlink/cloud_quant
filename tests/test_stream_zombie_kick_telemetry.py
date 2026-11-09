"""Zombie kicks expose age telemetry for /api/health polish probes."""
import time
from datetime import datetime, timezone

from qtw import stream


def _iso_ago(sec: float) -> str:
    return datetime.fromtimestamp(time.time() - sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_note_zombie_kick_sets_status_fields(monkeypatch):
    stream._note_zombie_kick([12.5, 80.0])
    st = stream.status()
    assert st["last_zombie_max_age_sec"] == 80.0
    assert st["last_zombie_kick_age_sec"] is not None
    assert st["last_zombie_kick_age_sec"] < 2.0
    # clear for other tests
    monkeypatch.setattr(stream, "_last_zombie_kick_at", 0.0)
    monkeypatch.setattr(stream, "_last_zombie_max_age_sec", None)
    st2 = stream.status()
    assert st2["last_zombie_kick_age_sec"] is None
    assert st2["last_zombie_max_age_sec"] is None


def test_watchdog_tick_records_kick(monkeypatch):
    class _WS:
        def __init__(self):
            self.aborted = False
            self.transport = self
        def is_closing(self):
            return self.aborted
        def abort(self):
            self.aborted = True

    ws = _WS()
    now = time.time()
    monkeypatch.setattr(stream, "_loop_heartbeat", now)  # not stalled → needs age > ZOMBIE+grace
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(95),
            "connected_at": _iso_ago(200),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {"okx_public": ws})
    monkeypatch.setattr(stream, "_watch_symbols", [])
    monkeypatch.setattr(stream, "_loop", None)
    n = stream._watchdog_tick()
    assert n == 1
    assert ws.aborted is True
    st = stream.status()
    assert st["last_zombie_kick_age_sec"] is not None
    assert st["last_zombie_max_age_sec"] >= 90
