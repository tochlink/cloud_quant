"""REST gap-fill must not look like an asyncio loop stall to the watchdog."""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from qtw import stream
from qtw.market.okx import OkxPublic
from qtw.market.gate import GatePublic


def _iso_ago(sec: float) -> str:
    return datetime.fromtimestamp(time.time() - sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_gap_fill_clients_use_short_timeout():
    okx = OkxPublic(timeout=stream.GAP_FILL_TIMEOUT_SEC, max_retries=stream.GAP_FILL_RETRIES,
                    backoff=stream.GAP_FILL_BACKOFF_SEC)
    gate = GatePublic(timeout=stream.GAP_FILL_TIMEOUT_SEC, max_retries=stream.GAP_FILL_RETRIES,
                      backoff=stream.GAP_FILL_BACKOFF_SEC)
    assert okx.http.timeout == stream.GAP_FILL_TIMEOUT_SEC
    assert okx.http.max_retries == stream.GAP_FILL_RETRIES
    assert gate.http.timeout == stream.GAP_FILL_TIMEOUT_SEC
    assert stream.GAP_FILL_TIMEOUT_SEC <= 5.0
    assert stream.GAP_FILL_RETRIES <= 2


def test_quote_for_gap_fill_builds_short_timeout_client(monkeypatch):
    seen = {}

    class Fake:
        def __init__(self, **kw):
            seen.update(kw)

        def quote(self, symbol, market):
            from qtw.market.base import Quote
            return Quote(symbol, market, 1.0, "mark", datetime.now(timezone.utc), "OKX")

    monkeypatch.setattr("qtw.market.okx.OkxPublic", Fake)
    q = stream._quote_for_gap_fill("okx", "BTCUSDT", "perp")
    assert q.price == 1.0
    assert seen["timeout"] == stream.GAP_FILL_TIMEOUT_SEC
    assert seen["max_retries"] == stream.GAP_FILL_RETRIES


def test_rest_fill_bumps_heartbeat_and_clears_depth(monkeypatch):
    class Q:
        def __init__(self, venue, symbol, market):
            self.venue = venue
            self.symbol = symbol
            self.market = market
            self.price = 1.0
            self.kind = "mark" if market == "perp" else "last"
            self.ts = datetime.now(timezone.utc)
            self.data_source = f"{venue}_public_rest"
            self.source_host = "example.test"

    def fake_quote(venue, sym, mkt):
        time.sleep(0.02)
        return Q(venue, sym, mkt)

    monkeypatch.setattr(stream, "latest", lambda *a, **k: None)
    monkeypatch.setattr(stream, "_quote_for_gap_fill", fake_quote)
    monkeypatch.setattr(stream, "_put", lambda q: None)
    stream._rest_errors.clear()
    stream._rest_fill_depth = 0
    stream._loop_heartbeat = time.time() - 30  # stale before fill

    async def run():
        n = await stream._rest_fill_stale(["BTCUSDT"], preferred_venue="okx")
        assert n == 4
        assert stream._rest_fill_depth == 0
        assert time.time() - stream._loop_heartbeat < 1.0

    asyncio.run(run())


def test_watchdog_ignores_stall_while_rest_fill_inflight(monkeypatch):
    """During gap-fill, heartbeat may age past LOOP_STALL — do not mass-abort mid-reconnect."""
    states = {}
    scheduled = {"n": 0}

    def fake_state(name, **kw):
        st = states.setdefault(name, {"name": name, "status": "connected", "last_msg": "", "reconnects": 0})
        st.update(kw)

    class _WS:
        def __init__(self):
            self.aborted = False
            self.transport = self

        def is_closing(self):
            return self.aborted

        def abort(self):
            self.aborted = True

    ws = _WS()
    monkeypatch.setattr(stream, "_conn_state", fake_state)
    monkeypatch.setattr(stream, "LOOP_STALL_SEC", 12)
    monkeypatch.setattr(stream, "WATCHDOG_GRACE_SEC", 12)
    monkeypatch.setattr(stream, "ZOMBIE_SEC", 70)
    monkeypatch.setattr(stream, "_schedule_rest_fill_from_watchdog", lambda: scheduled.__setitem__("n", scheduled["n"] + 1))
    monkeypatch.setattr(stream, "_conns", {
        "okx_public": {
            "name": "okx_public",
            "status": "connected",
            "last_msg": _iso_ago(75),  # past ZOMBIE, inside ZOMBIE+grace
            "connected_at": _iso_ago(200),
        },
    })
    monkeypatch.setattr(stream, "_ws_refs", {"okx_public": ws})
    stream._loop_heartbeat = time.time() - 60  # would be "stalled"
    stream._rest_fill_depth = 1
    assert stream._watchdog_tick() == 0
    assert ws.aborted is False
    assert scheduled["n"] == 0

    # Past grace → still abort even while filling (true zombie)
    stream._conns["okx_public"]["last_msg"] = _iso_ago(95)
    assert stream._watchdog_tick() == 1
    assert ws.aborted is True
    stream._rest_fill_depth = 0


def test_status_exposes_rest_fill_inflight():
    stream._rest_fill_depth = 2
    st = stream.status()
    assert st["rest_fill_inflight"] is True
    stream._rest_fill_depth = 0
    st2 = stream.status()
    assert st2["rest_fill_inflight"] is False
