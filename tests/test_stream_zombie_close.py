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
