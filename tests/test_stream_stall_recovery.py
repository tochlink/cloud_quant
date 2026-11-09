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
    filled = {"n": 0}
    monkeypatch.setattr(stream, "_rest_fill_stale_sync",
                        lambda *_a, **_k: filled.__setitem__("n", filled["n"] + 1) or 2)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog",
                        lambda: (_ for _ in ()).throw(AssertionError("async fill on stall")))
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(35),  # > STALL_ZOMBIE (30), < ZOMBIE (70)
            "connected_at": _iso_ago(200),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {"okx_public": ws})
    monkeypatch.setattr(stream, "_watch_symbols", ["BTCUSDT"])
    stream._loop_heartbeat = time.time() - 20  # stalled
    stream._rest_fill_depth = 0
    stream._rest_fill_started_at = 0.0
    before = stream._stall_suspect_count
    n = stream._watchdog_tick()
    assert n == 1
    assert ws.aborted is True
    assert filled["n"] == 1
    assert stream._stall_suspect_count == before + 1


def test_watchdog_stall_schedules_rest_fill_before_zombies(monkeypatch):
    filled = {"n": 0}
    monkeypatch.setattr(stream, "_rest_fill_stale_sync",
                        lambda *_a, **_k: filled.__setitem__("n", filled["n"] + 1) or 1)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog",
                        lambda: (_ for _ in ()).throw(AssertionError("async fill on stall")))
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(5),  # still fresh — not a zombie yet
            "connected_at": _iso_ago(20),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {})
    monkeypatch.setattr(stream, "_watch_symbols", ["BTCUSDT"])
    stream._loop_heartbeat = time.time() - 30
    stream._rest_fill_depth = 0
    assert stream._watchdog_tick() == 0
    assert filled["n"] == 1


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
    monkeypatch.setattr(stream, "_rest_fill_stale_sync", lambda *_a, **_k: 0)
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
    monkeypatch.setattr(stream, "_watch_symbols", ["BTCUSDT"])
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


def test_watchdog_stall_uses_sync_rest_fill(monkeypatch):
    """Frozen loop must REST-fill from the watchdog thread, not the dead asyncio loop."""
    called = {"sync": 0, "async": 0}

    def _sync(*_a, **_k):
        called["sync"] += 1
        return 3

    def _async():
        called["async"] += 1

    monkeypatch.setattr(stream, "_rest_fill_stale_sync", _sync)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", _async)
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(5),
            "connected_at": _iso_ago(20),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {})
    monkeypatch.setattr(stream, "_watch_symbols", ["BTCUSDT"])
    monkeypatch.setattr(stream, "_watch_venue", "okx")
    stream._loop_heartbeat = time.time() - 30
    stream._rest_fill_depth = 0
    before = stream._early_stall_fill_count
    assert stream._watchdog_tick() == 0
    assert called["sync"] == 1
    assert called["async"] == 0
    assert stream._early_stall_fill_count == before + 1
    assert stream._last_early_stall_fill_n == 3


def test_watchdog_healthy_zombie_still_schedules_async_fill(monkeypatch):
    class _WS:
        def __init__(self):
            self.aborted = False
            self.transport = self
        def is_closing(self):
            return self.aborted
        def abort(self):
            self.aborted = True

    ws = _WS()
    called = {"sync": 0, "async": 0}
    monkeypatch.setattr(stream, "_rest_fill_stale_sync", lambda *_a, **_k: called.__setitem__("sync", called["sync"] + 1) or 0)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", lambda: called.__setitem__("async", called["async"] + 1))
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(stream.ZOMBIE_SEC + stream.WATCHDOG_GRACE_SEC + 5),
            "connected_at": _iso_ago(200),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {"okx_public": ws})
    stream._loop_heartbeat = time.time()  # healthy loop
    stream._rest_fill_depth = 0
    n = stream._watchdog_tick()
    assert n == 1
    assert ws.aborted is True
    assert called["async"] == 1
    assert called["sync"] == 0


def test_status_exposes_ws_conn_max_age_and_early_fill():
    st = stream.status()
    assert "ws_conn_max_age_sec" in st
    assert "early_stall_fill_count" in st
    assert "last_early_stall_fill_age_sec" in st
