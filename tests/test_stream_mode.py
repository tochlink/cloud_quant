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
