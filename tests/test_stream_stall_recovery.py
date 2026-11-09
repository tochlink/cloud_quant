"""Faster stall recovery: activity heartbeat, short zombie floor, wedged fill shield."""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from qtw import stream


def _iso_ago(sec: float) -> str:
    return datetime.fromtimestamp(time.time() - sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reset_stall_fill_state():
    stream._early_fill_inflight = False
    stream._last_early_stall_fill_at = 0.0
    stream._last_early_stall_fill_n = 0
    stream._rest_fill_depth = 0
    stream._rest_fill_started_at = 0.0


def _wait_until(pred, timeout=1.0, msg="condition not met"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pred():
            return
        time.sleep(0.01)
    raise AssertionError(msg)


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
    _reset_stall_fill_state()
    before = stream._stall_suspect_count
    n = stream._watchdog_tick()
    assert n == 1
    assert ws.aborted is True
    _wait_until(lambda: filled["n"] == 1, msg="background stall fill did not run")
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
    _reset_stall_fill_state()
    assert stream._watchdog_tick() == 0
    _wait_until(lambda: filled["n"] == 1, msg="background stall fill did not run")


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
    stream._early_fill_inflight = False
    stream._last_early_stall_fill_at = 0.0
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
    _reset_stall_fill_state()
    before = stream._early_stall_fill_count
    assert stream._watchdog_tick() == 0
    _wait_until(lambda: called["sync"] == 1, msg="background stall fill did not run")
    _wait_until(lambda: stream._early_stall_fill_count == before + 1)
    assert called["async"] == 0
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
    assert "early_fill_inflight" in st
    assert "last_early_stall_fill_age_sec" in st


def test_watchdog_tick_does_not_block_on_slow_sync_fill(monkeypatch):
    """Stall REST fill must not pin the watchdog thread (it has to keep aborting)."""
    started = threading.Event()
    release = threading.Event()

    def _sync(*_a, **_k):
        started.set()
        assert release.wait(1.0), "test failed to release stall fill"
        return 2

    monkeypatch.setattr(stream, "_rest_fill_stale_sync", _sync)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog",
                        lambda: (_ for _ in ()).throw(AssertionError("async fill on stall")))
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
    stream._loop_heartbeat = time.time() - 30
    stream._rest_fill_depth = 0
    _reset_stall_fill_state()
    t0 = time.monotonic()
    assert stream._watchdog_tick() == 0
    assert time.monotonic() - t0 < 0.2
    assert started.wait(0.5)
    assert stream._early_fill_inflight is True
    release.set()
    _wait_until(lambda: not stream._early_fill_inflight, msg="stall fill worker did not finish")


def test_watchdog_stall_fill_coalesces_while_inflight(monkeypatch):
    calls = {"n": 0}
    started = threading.Event()
    release = threading.Event()

    def _sync(*_a, **_k):
        calls["n"] += 1
        started.set()
        assert release.wait(1.0)
        return 1

    monkeypatch.setattr(stream, "_rest_fill_stale_sync", _sync)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", lambda: None)
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
    stream._loop_heartbeat = time.time() - 30
    stream._rest_fill_depth = 0
    _reset_stall_fill_state()
    assert stream._watchdog_tick() == 0
    assert started.wait(0.5)
    assert stream._watchdog_tick() == 0  # still inflight — do not start a second fill
    release.set()
    _wait_until(lambda: not stream._early_fill_inflight)
    assert calls["n"] == 1


def test_watchdog_stall_fill_respects_cooldown(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(stream, "_rest_fill_stale_sync",
                        lambda *_a, **_k: calls.__setitem__("n", calls["n"] + 1) or 0)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", lambda: None)
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
    stream._loop_heartbeat = time.time() - 30
    stream._rest_fill_depth = 0
    _reset_stall_fill_state()
    stream._last_early_stall_fill_at = time.time()  # just filled
    assert stream._spawn_stall_fill() is False
    time.sleep(0.05)
    assert calls["n"] == 0


def test_connect_ws_disables_proxy_and_prefers_ipv4(monkeypatch):
    """Official public WS must not inherit proxy autodetect or IPv6 delays."""
    import socket

    seen = {}

    async def fake_connect(url, **kw):
        seen.update(kw)
        seen["url"] = url
        return object()

    monkeypatch.setattr("websockets.connect", fake_connect)

    async def run():
        ws = await stream._connect_ws("wss://ws.okx.com/ws/v5/public")
        assert ws is not None

    import asyncio
    asyncio.run(run())
    assert seen.get("proxy") is None
    assert seen.get("family") == socket.AF_INET
    assert seen.get("url") == "wss://ws.okx.com/ws/v5/public"
