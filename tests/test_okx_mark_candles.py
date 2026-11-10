"""OKX mark-price candles are parsed and stored separately from trade-price perp bars."""
from contextlib import contextmanager

from qtw import stream


@contextmanager
def _isolated_forming():
    with stream._lock:
        saved = dict(stream._forming)
        stream._forming.clear()
    try:
        yield
    finally:
        with stream._lock:
            stream._forming.clear()
            stream._forming.update(saved)


def test_parse_okx_mark_price_candle_row():
    row = ["1597026383085", "3.721", "3.743", "3.677", "3.708", "1"]
    p = stream.parse_okx_ws_candle("mark-price-candle4H", row)
    assert p is not None
    assert p["kind"] == "mark"
    assert p["closed"] is True
    assert p["volume"] == 0.0
    assert p["close"] == 3.708
    assert p["open"] == 3.721
    assert p["high"] == 3.743
    assert p["low"] == 3.677
    assert p["open_ms"] == 1597026383085
    open_row = ["1597026383085", "3.721", "3.743", "3.677", "3.708", "0"]
    assert stream.parse_okx_ws_candle("mark-price-candle4H", open_row)["closed"] is False
    assert stream.parse_okx_ws_candle("mark-price-candle4H", ["1", "2"]) is None


def test_parse_okx_trade_candle_confirm_is_index_8():
    row = ["1597026383085", "1", "2", "0.5", "1.5", "100", "200", "300", "1"]
    p = stream.parse_okx_ws_candle("candle4H", row)
    assert p["kind"] == "trade"
    assert p["closed"] is True
    assert p["volume"] == 100.0
    assert p["close"] == 1.5
    short = ["1597026383085", "1", "2", "0.5", "1.5", "100"]
    assert stream.parse_okx_ws_candle("candle4H", short)["closed"] is False


def test_mark_price_candle_does_not_overwrite_perp_trade_forming(monkeypatch):
    stored = []
    monkeypatch.setattr(stream, "_store_closed", lambda *a, **k: stored.append(a))
    inst_map = {"BTC-USDT-SWAP": ("BTCUSDT", "perp")}
    trade_msg = {
        "arg": {"channel": "candle4H", "instId": "BTC-USDT-SWAP"},
        "data": [["1597026383085", "100", "110", "90", "105", "12", "0", "0", "1"]],
    }
    mark_msg = {
        "arg": {"channel": "mark-price-candle4H", "instId": "BTC-USDT-SWAP"},
        "data": [["1597026383085", "101", "111", "91", "106", "1"]],
    }
    with _isolated_forming():
        assert stream.apply_okx_candle_message(trade_msg, "wss://ws.okx.com/ws/v5/business", "4h", inst_map) == 1
        assert stream.apply_okx_candle_message(mark_msg, "wss://ws.okx.com/ws/v5/business", "4h", inst_map) == 1
        with stream._lock:
            trade = stream._forming[("okx", "4h", "BTCUSDT", "perp")]
            mark = stream._forming[("okx", "4h", "BTCUSDT", "perp_mark")]
        assert trade["close"] == 105.0
        assert trade["source"] == "okx_public_ws"
        assert mark["close"] == 106.0
        assert mark["source"] == "okx_mark_price_ws"
        assert mark["closed"] is True
    assert stored[0][1] == "perp"
    assert stored[0][10] == "okx_public_ws"
    assert stored[1][1] == "perp_mark"
    assert stored[1][9] == 0.0  # volume
    assert stored[1][10] == "okx_mark_price_ws"


def test_snapshot_exposes_mark_candles_separately():
    with _isolated_forming():
        stream._forming_put("okx", "perp", "BTCUSDT", "4h", 1597026383085, 100, 110, 90, 105, True, "okx_public_ws")
        stream._forming_put("okx", "perp_mark", "BTCUSDT", "4h", 1597026383085, 101, 111, 91, 106, False, "okx_mark_price_ws")
        snap = stream.snapshot("okx")
        assert "4h:BTCUSDT:perp" in snap["forming"]
        assert "4h:BTCUSDT:perp_mark" in snap["forming"]
        assert snap["mark_candles"]["BTCUSDT"]["close"] == 106.0
        assert snap["mark_candles"]["BTCUSDT"]["source"] == "okx_mark_price_ws"
        assert snap["mark_candles"]["BTCUSDT"]["closed"] is False
