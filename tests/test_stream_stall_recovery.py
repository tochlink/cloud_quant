"""Faster stall recovery: activity heartbeat, short zombie floor, wedged fill shield."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from qtw import stream


def _iso_ago(sec: float) -> str:
    return datetime.fromtimestamp(time.time() - sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_note_activity_bumps_loop_heartbeat(monkeypatch):
    stream._loop_heartbeat = time.time() - 60
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {"name": "okx_public", "status": "connected", "last_msg": "", "reconnects": 0},
    })
    stream._note_activity("okx_public")
    assert time.time() - stream._loop_heartbeat < 1.0
    assert stream._conns["okx_public"]["last_msg"]


def test_watchdog_stall_uses_short_zombie_floor(monkeypatch):
    """Frozen loop: abort at STALL_ZOMBIE_SEC (~30), not full ZOMBIE_SEC (70)."""
    class _WS:
        def __init__(self):
            self.aborted = False
            self.transport = self
        def is_closing(self):
            return self.aborted
        def abort(self):
            self.aborted = True

    ws = _WS()
    scheduled = {"n": 0}
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog",
                        lambda: scheduled.__setitem__("n", scheduled["n"] + 1))
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(35),  # > STALL_ZOMBIE (30), < ZOMBIE (70)
            "connected_at": _iso_ago(200),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {"okx_public": ws})
    stream._loop_heartbeat = time.time() - 20  # stalled
    stream._rest_fill_depth = 0
    stream._rest_fill_started_at = 0.0
    before = stream._stall_suspect_count
    n = stream._watchdog_tick()
    assert n == 1
    assert ws.aborted is True
    assert scheduled["n"] == 1
    assert stream._stall_suspect_count == before + 1


def test_watchdog_stall_schedules_rest_fill_before_zombies(monkeypatch):
    scheduled = {"n": 0}
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog",
                        lambda: scheduled.__setitem__("n", scheduled["n"] + 1))
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(5),  # still fresh — not a zombie yet
            "connected_at": _iso_ago(20),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {})
    stream._loop_heartbeat = time.time() - 30
    stream._rest_fill_depth = 0
    assert stream._watchdog_tick() == 0
    assert scheduled["n"] == 1


def test_wedged_rest_fill_drops_shield(monkeypatch):
    class _WS:
        def __init__(self):
            self.aborted = False
            self.transport = self
        def is_closing(self):
            return self.aborted
        def abort(self):
            self.aborted = True

    ws = _WS()
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", lambda: None)
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(40),  # past STALL_ZOMBIE once shield drops
            "connected_at": _iso_ago(200),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {"okx_public": ws})
    stream._loop_heartbeat = time.time() - 60
    stream._rest_fill_depth = 1
    stream._rest_fill_started_at = time.time() - (stream.FILLING_STALL_SEC + 5)
    n = stream._watchdog_tick()
    assert n == 1
    assert ws.aborted is True
    stream._rest_fill_depth = 0
    stream._rest_fill_started_at = 0.0


def test_status_exposes_stall_suspect_count():
    st = stream.status()
    assert "stall_suspect_count" in st
    assert isinstance(st["stall_suspect_count"], int)
