"""Stream mode classification: ws / recovering / rest hysteresis."""
from qtw.stream import classify_mode


def test_fresh_ws_quotes_are_ws_even_if_rest_also_present():
    assert classify_mode(live=8, rest=4, up=4, trying=4, recent_ws=True) == "ws"
    assert classify_mode(live=1, rest=0, up=0, trying=0, recent_ws=False) == "ws"


def test_reconnect_gap_with_rest_fill_is_recovering_not_rest():
    # Connected sockets, no fresh WS ticks yet, REST filled marks — classic storm gap.
    assert classify_mode(live=0, rest=16, up=4, trying=4, recent_ws=True) == "recovering"
    assert classify_mode(live=0, rest=16, up=2, trying=4, recent_ws=False) == "recovering"
    # All flapping reconnecting but we recently had WS quotes.
    assert classify_mode(live=0, rest=8, up=0, trying=4, recent_ws=True) == "recovering"


def test_pure_rest_only_when_ws_path_gone():
    assert classify_mode(live=0, rest=16, up=0, trying=0, recent_ws=False) == "rest"


def test_cold_start_and_down():
    assert classify_mode(live=0, rest=0, up=0, trying=2, recent_ws=False) == "recovering"
    assert classify_mode(live=0, rest=0, up=0, trying=0, recent_ws=False) == "down"

from datetime import datetime, timezone
from contextlib import contextmanager

from qtw import stream
from qtw.market.base import Quote
from qtw.timeutil import iso


@contextmanager
def _isolated_stream_state():
    """Swap stream module globals, then put them back (shared with other tests)."""
    with stream._lock:
        saved_quotes = dict(stream._quotes)
        saved_conns = {k: dict(v) for k, v in stream._conns.items()}
        saved_last = dict(stream._last_ws_at)
        stream._quotes.clear()
        stream._conns.clear()
        stream._last_ws_at.clear()
    try:
        yield
    finally:
        with stream._lock:
            stream._quotes.clear()
            stream._quotes.update(saved_quotes)
            stream._conns.clear()
            stream._conns.update(saved_conns)
            stream._last_ws_at.clear()
            stream._last_ws_at.update(saved_last)


def _q(symbol, venue, source, market="perp"):
    now = datetime.now(timezone.utc)
    return Quote(symbol, market, 1.0, "mark", now, venue, "example", source, iso(now))


def test_status_mode_is_venue_aware_when_other_venue_ws_is_live():
    """OKX marks on REST must not report mode=ws just because Gate WS is healthy."""
    now_iso = iso(datetime.now(timezone.utc))
    with _isolated_stream_state():
        with stream._lock:
            stream._quotes[("okx", "BTCUSDT", "perp")] = _q("BTCUSDT", "OKX", "okx_public_rest")
            stream._quotes[("okx", "ETHUSDT", "perp")] = _q("ETHUSDT", "OKX", "okx_public_rest")
            stream._quotes[("gate", "BTCUSDT", "perp")] = _q("BTCUSDT", "Gate", "gate_public_ws")
            stream._quotes[("gate", "ETHUSDT", "perp")] = _q("ETHUSDT", "Gate", "gate_public_ws")
            stream._last_ws_at["gate"] = __import__("time").time()
        stream._conn_state("okx_public", status="connecting", last_msg=now_iso)
        stream._conn_state("okx_business", status="connected", last_msg=now_iso)
        stream._conn_state("gate_spot", status="connected", last_msg=now_iso)
        stream._conn_state("gate_futures", status="connected", last_msg=now_iso)

        okx = stream.status("okx")
        assert okx["venue"] == "okx"
        assert okx["quotes_ws_fresh"] == 0
        assert okx["quotes_rest_fresh"] == 2
        assert okx["mode"] != "ws"
        assert okx["mode"] == "recovering"  # business still connected, public connecting

        gate = stream.status("gate")
        assert gate["mode"] == "ws"
        assert gate["quotes_ws_fresh"] == 2
        assert gate["quotes_rest_fresh"] == 0

        # Unscoped view still sees Gate WS and would look "ws" — callers must pass venue.
        raw = stream.status()
        assert raw["mode"] == "ws"
        assert raw["quotes_ws_fresh"] == 2


def test_recent_ws_hold_does_not_leak_across_venues():
    """Gate's recent WS activity must not keep OKX in recovering after its WS path is gone."""
    with _isolated_stream_state():
        with stream._lock:
            stream._quotes[("okx", "BTCUSDT", "perp")] = _q("BTCUSDT", "OKX", "okx_public_rest")
            stream._quotes[("gate", "BTCUSDT", "perp")] = _q("BTCUSDT", "Gate", "gate_public_ws")
            stream._last_ws_at["gate"] = __import__("time").time()
        stream._conn_state("okx_public", status="reconnecting")
        stream._conn_state("okx_business", status="reconnecting")
        stream._conn_state("gate_spot", status="connected", last_msg=iso(datetime.now(timezone.utc)))

        okx = stream.status("okx")
        assert okx["quotes_ws_fresh"] == 0
        assert okx["quotes_rest_fresh"] == 1
        # trying>0 but up=0 and no per-venue recent_ws → rest, not recovering
        assert okx["mode"] == "rest"
