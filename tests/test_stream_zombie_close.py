"""Zombie WS force-close must abort without hanging the supervisor."""
import asyncio
import time

import pytest

from qtw import stream


class _HangCloseWS:
    """Simulates a half-open socket: close() never finishes; abort() works."""

    def __init__(self):
        self.aborted = False
        self.close_calls = 0
        self.transport = self

    def is_closing(self):
        return self.aborted

    def abort(self):
        self.aborted = True

    async def close(self):
        self.close_calls += 1
        await asyncio.sleep(30)


class _NoTransportHangWS:
    """No transport attribute — close hangs; fallback path must time out fast."""

    def __init__(self):
        self.close_calls = 0

    async def close(self):
        self.close_calls += 1
        await asyncio.sleep(30)


def test_force_close_aborts_transport_without_waiting_on_close(monkeypatch):
    monkeypatch.setattr(stream, "_conn_state", lambda name, **kw: None)
    stream._ws_refs.clear()
    ws = _HangCloseWS()
    stream._ws_refs["okx_public"] = ws

    async def run():
        t0 = time.monotonic()
        await stream._force_close_ws(ws, "okx_public")
        elapsed = time.monotonic() - t0
        assert ws.aborted is True
        assert ws.close_calls == 0  # abort path returns before close()
        assert "okx_public" not in stream._ws_refs
        assert elapsed < 1.0  # must not sit on the 3s close handshake

    asyncio.run(run())


def test_force_close_short_timeout_when_no_transport(monkeypatch):
    monkeypatch.setattr(stream, "_conn_state", lambda name, **kw: None)
    stream._ws_refs.clear()
    ws = _NoTransportHangWS()
    stream._ws_refs["gate_spot"] = ws

    async def run():
        t0 = time.monotonic()
        await stream._force_close_ws(ws, "gate_spot")
        elapsed = time.monotonic() - t0
        assert ws.close_calls == 1
        assert "gate_spot" not in stream._ws_refs
        assert elapsed < 2.0  # 0.5s wait_for, not 3s

    asyncio.run(run())


def test_kick_zombies_marks_reconnecting_and_parallel_abort(monkeypatch):
    # Four zombies: abort must finish quickly and flip status.
    states = {}

    def fake_state(name, **kw):
        st = states.setdefault(name, {"name": name, "status": "connected", "last_msg": "", "reconnects": 0})
        st.update(kw)

    monkeypatch.setattr(stream, "_conn_state", fake_state)
    monkeypatch.setattr(stream, "ZOMBIE_SEC", 70)
    stream._ws_refs.clear()
    with stream._lock:
        stream._conns.clear()
        old = time.time() - 400
        from datetime import datetime, timezone
        lm = datetime.fromtimestamp(old, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for name in ("okx_public", "okx_business", "gate_spot", "gate_futures"):
            stream._conns[name] = {
                "name": name, "status": "connected", "last_msg": lm,
                "reconnects": 0, "url": "", "connected_at": "", "last_error": "", "channels": [],
            }
            stream._ws_refs[name] = _HangCloseWS()

    async def run():
        t0 = time.monotonic()
        await stream._kick_zombies()
        elapsed = time.monotonic() - t0
        assert elapsed < 1.5  # parallel abort, not 4×3s
        for name in ("okx_public", "okx_business", "gate_spot", "gate_futures"):
            assert states[name]["status"] == "reconnecting"
            assert stream._ws_refs.get(name) is None
            assert stream._ws_refs == {} or name not in stream._ws_refs

    asyncio.run(run())
    # cleanup module globals used by other tests
    with stream._lock:
        stream._conns.clear()
    stream._ws_refs.clear()


def test_activity_age_falls_back_to_connected_at():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 10, 4, 20, tzinfo=timezone.utc).timestamp()
    connected = datetime(2026, 11, 10, 4, 18, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    age = stream._activity_age_sec({"last_msg": "", "connected_at": connected}, now)
    assert age is not None and 119 <= age <= 121

    fresh_msg = datetime(2026, 11, 10, 4, 19, 50, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    age2 = stream._activity_age_sec({"last_msg": fresh_msg, "connected_at": connected}, now)
    assert age2 is not None and 9 <= age2 <= 11


def test_kick_zombies_triggers_rest_fill(monkeypatch):
    states = {}
    filled = {"n": 0}

    def fake_state(name, **kw):
        st = states.setdefault(name, {"name": name, "status": "connected", "last_msg": "", "reconnects": 0})
        st.update(kw)

    async def fake_rest(symbols, venues=("okx", "gate")):
        filled["n"] += 1
        assert symbols == ["BTCUSDT"]
        return 2

    monkeypatch.setattr(stream, "_conn_state", fake_state)
    monkeypatch.setattr(stream, "ZOMBIE_SEC", 70)
    monkeypatch.setattr(stream, "_rest_fill_stale", fake_rest)
    stream._ws_refs.clear()
    with stream._lock:
        stream._conns.clear()
        old = time.time() - 400
        from datetime import datetime, timezone
        lm = datetime.fromtimestamp(old, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        stream._conns["okx_public"] = {
            "name": "okx_public", "status": "connected", "last_msg": lm,
            "reconnects": 0, "url": "", "connected_at": lm, "last_error": "", "channels": [],
        }
        stream._ws_refs["okx_public"] = _HangCloseWS()

    async def run():
        n = await stream._kick_zombies(["BTCUSDT"])
        assert n == 1
        assert filled["n"] == 1
        assert states["okx_public"]["status"] == "reconnecting"

    asyncio.run(run())
    with stream._lock:
        stream._conns.clear()
    stream._ws_refs.clear()


def test_load_settings_does_not_block_event_loop(monkeypatch):
    """S.load() can wait on db._LOCK; supervisor must await it in an executor."""
    ticks = {"n": 0}

    def slow_load():
        time.sleep(0.35)
        return {
            "symbols": ["BTCUSDT"],
            "strategy": {"interval": "4h"},
        }

    async def ticker():
        # While _load_settings awaits the executor, this must keep advancing.
        for _ in range(6):
            await asyncio.sleep(0.05)
            ticks["n"] += 1

    monkeypatch.setattr(stream.S, "load", slow_load)

    async def run():
        t0 = time.monotonic()
        cfg_task = asyncio.create_task(stream._load_settings())
        tick_task = asyncio.create_task(ticker())
        cfg = await cfg_task
        await tick_task
        elapsed = time.monotonic() - t0
        assert cfg["symbols"] == ["BTCUSDT"]
        assert ticks["n"] >= 4  # would stay ~0 if load blocked the loop
        assert elapsed >= 0.30

    asyncio.run(run())
