"""Zombie WS force-close must abort without hanging the supervisor."""
import asyncio
import time
from datetime import datetime, timezone

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

    async def fake_rest(symbols, venues=("okx", "gate"), *, preferred_venue=None):
        filled["n"] += 1
        filled["venue"] = preferred_venue
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
        n = await stream._kick_zombies(["BTCUSDT"], preferred_venue="okx")
        assert n == 1
        assert filled["n"] == 1
        assert filled["venue"] == "okx"
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


def test_connect_ws_guard_times_out_hung_handshake(monkeypatch):
    """A handshake that never completes must not leave _run_ws stuck on connecting."""
    async def hanging(*_a, **_k):
        await asyncio.sleep(30)
        raise AssertionError("handshake should have been cancelled")

    monkeypatch.setattr(stream, "CONNECT_GUARD_SEC", 0.2)
    monkeypatch.setattr(stream, "OPEN_TIMEOUT_SEC", 0.1)

    async def run():
        t0 = time.monotonic()
        with pytest.raises(ConnectionError, match="握手"):
            await stream._connect_ws("wss://example.invalid/ws", opener=hanging)
        assert time.monotonic() - t0 < 1.5

    asyncio.run(run())



def test_venue_fill_order_prefers_active():
    assert stream._venue_fill_order("gate") == ["gate", "okx"]
    assert stream._venue_fill_order("okx") == ["okx", "gate"]
    assert stream._venue_fill_order(None) == ["okx", "gate"]
    assert stream._venue_fill_order("nope") == ["okx", "gate"]


def test_rest_fill_stale_runs_preferred_venue_before_secondary(monkeypatch):
    """Paper venue REST fills must complete before the other exchange starts."""
    order = []

    class Q:
        def __init__(self, venue, symbol, market):
            self.venue = venue
            self.symbol = symbol
            self.market = market
            self.price = 1.0
            self.kind = "mark" if market == "perp" else "last"
            from datetime import datetime, timezone
            self.ts = datetime.now(timezone.utc)
            self.data_source = f"{venue}_public_rest"
            self.source_host = "example.test"
            self.exchange = venue.upper()

    def fake_gap_fill(venue, sym, mkt):
        order.append(venue)
        import time as _t
        # Secondary venue is slower; if we awaited it first, preferred would lag.
        if venue == "gate":
            _t.sleep(0.05)
        return Q(venue, sym, mkt)

    monkeypatch.setattr(stream, "latest", lambda *a, **k: None)
    monkeypatch.setattr(stream, "_quote_for_gap_fill", fake_gap_fill)
    monkeypatch.setattr(stream, "_put", lambda q: None)
    stream._rest_errors.clear()

    async def run():
        n = await stream._rest_fill_stale(["BTCUSDT"], preferred_venue="okx")
        assert n == 4  # okx spot+perp + gate spot+perp
        # First two completions must be okx (primary batch finishes before gate starts).
        assert order[:2] == ["okx", "okx"]
        assert set(order[2:]) == {"gate"}

    asyncio.run(run())


def test_abort_ws_transport_sync_from_watchdog_path(monkeypatch):
    states = {}

    def fake_state(name, **kw):
        st = states.setdefault(name, {"name": name, "status": "connected", "last_msg": "", "reconnects": 0})
        st.update(kw)

    monkeypatch.setattr(stream, "_conn_state", fake_state)
    stream._ws_refs.clear()
    ws = _HangCloseWS()
    stream._ws_refs["okx_public"] = ws
    assert stream._abort_ws_transport_sync(ws, "okx_public", reason="zombie: watchdog abort") is True
    assert ws.aborted is True
    assert "okx_public" not in stream._ws_refs
    assert states["okx_public"]["status"] == "reconnecting"
    assert "watchdog" in states["okx_public"]["last_error"]


def test_watchdog_tick_aborts_when_loop_stalled(monkeypatch):
    """If the asyncio heartbeat is stale, side-thread abort must not wait for supervisor."""
    states = {}
    filled = {"n": 0}

    def fake_state(name, **kw):
        st = states.setdefault(name, {"name": name, "status": "connected", "last_msg": "", "reconnects": 0})
        st.update(kw)

    monkeypatch.setattr(stream, "_conn_state", fake_state)
    monkeypatch.setattr(stream, "ZOMBIE_SEC", 70)
    monkeypatch.setattr(stream, "LOOP_STALL_SEC", 12)
    monkeypatch.setattr(stream, "WATCHDOG_GRACE_SEC", 12)
    monkeypatch.setattr(stream, "_rest_fill_stale_sync",
                        lambda *_a, **_k: filled.__setitem__("n", filled["n"] + 1) or 4)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog",
                        lambda: (_ for _ in ()).throw(AssertionError("async fill on stall")))
    monkeypatch.setattr(stream, "_watch_symbols", ["BTCUSDT"])
    stream._ws_refs.clear()
    stream._loop_heartbeat = time.time() - 60  # stalled
    with stream._lock:
        stream._conns.clear()
        lm = datetime.fromtimestamp(time.time() - 95, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for name in ("okx_public", "gate_spot"):
            stream._conns[name] = {
                "name": name, "status": "connected", "last_msg": lm,
                "reconnects": 0, "url": "", "connected_at": lm, "last_error": "", "channels": [],
            }
            stream._ws_refs[name] = _HangCloseWS()

    stream._early_fill_inflight = False
    stream._last_early_stall_fill_at = 0.0
    n = stream._watchdog_tick()
    assert n == 2
    deadline = time.time() + 1.0
    while time.time() < deadline and filled["n"] != 1:
        time.sleep(0.01)
    assert filled["n"] == 1
    for name in ("okx_public", "gate_spot"):
        assert states[name]["status"] == "reconnecting"
        assert stream._ws_refs.get(name) is None
        assert stream._ws_refs.get(name) is None or name not in stream._ws_refs

    with stream._lock:
        stream._conns.clear()
    stream._ws_refs.clear()
    stream._loop_heartbeat = time.time()


def test_watchdog_tick_waits_grace_when_loop_healthy(monkeypatch):
    """Fresh heartbeat + age just past ZOMBIE → leave kick to in-loop supervisor."""
    states = {}
    scheduled = {"n": 0}

    def fake_state(name, **kw):
        st = states.setdefault(name, {"name": name, "status": "connected", "last_msg": "", "reconnects": 0})
        st.update(kw)

    monkeypatch.setattr(stream, "_conn_state", fake_state)
    monkeypatch.setattr(stream, "ZOMBIE_SEC", 70)
    monkeypatch.setattr(stream, "LOOP_STALL_SEC", 12)
    monkeypatch.setattr(stream, "WATCHDOG_GRACE_SEC", 12)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", lambda: scheduled.__setitem__("n", scheduled["n"] + 1))
    stream._ws_refs.clear()
    stream._loop_heartbeat = time.time()  # healthy
    with stream._lock:
        stream._conns.clear()
        # 75s > 70 but within grace (70+12)
        lm = datetime.fromtimestamp(time.time() - 75, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        stream._conns["okx_public"] = {
            "name": "okx_public", "status": "connected", "last_msg": lm,
            "reconnects": 0, "url": "", "connected_at": lm, "last_error": "", "channels": [],
        }
        stream._ws_refs["okx_public"] = _HangCloseWS()

    assert stream._watchdog_tick() == 0
    assert scheduled["n"] == 0
    assert stream._ws_refs.get("okx_public") is not None

    # Past grace → watchdog acts even with healthy heartbeat
    lm2 = datetime.fromtimestamp(time.time() - 95, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stream._conns["okx_public"]["last_msg"] = lm2
    assert stream._watchdog_tick() == 1
    assert scheduled["n"] == 1
    assert "okx_public" not in stream._ws_refs

    with stream._lock:
        stream._conns.clear()
    stream._ws_refs.clear()

