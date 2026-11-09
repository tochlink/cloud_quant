"""Unit tests for OKX/Gate WebSocket application-level keepalive detection."""
import json

from qtw.stream import is_keepalive


def test_okx_text_pong_is_keepalive():
    assert is_keepalive("pong") is True
    assert is_keepalive(b"pong") is True
    assert is_keepalive("  pong\n") is True


def test_okx_json_event_pong_is_keepalive():
    assert is_keepalive(json.dumps({"event": "pong"})) is True
    assert is_keepalive(json.dumps({"event": "pong", "ts": "1710000000000"})) is True


def test_gate_json_pong_is_keepalive():
    assert is_keepalive(json.dumps({"time": 1710000000, "channel": "spot.pong"})) is True
    assert is_keepalive(json.dumps({"time": 1710000000, "channel": "futures.pong"})) is True
    assert is_keepalive('{"channel":"spot.pong","result":null}') is True
    assert is_keepalive(json.dumps({
        "time": 1710000000,
        "channel": "spot.pong",
        "event": "",
        "result": {"status": "success"},
    })) is True


def test_market_payloads_are_not_keepalive():
    assert is_keepalive(json.dumps({
        "arg": {"channel": "tickers", "instId": "BTC-USDT"},
        "data": [{"last": "1", "instId": "BTC-USDT"}],
    })) is False
    assert is_keepalive(json.dumps({
        "channel": "spot.tickers",
        "event": "update",
        "result": [{"currency_pair": "BTC_USDT", "last": "1"}],
    })) is False
    assert is_keepalive(json.dumps({
        "arg": {"channel": "mark-price", "instId": "BTC-USDT-SWAP"},
        "data": [{"markPx": "1"}],
    })) is False
    assert is_keepalive("hello") is False
    assert is_keepalive("{not-json") is False
    assert is_keepalive(None) is False
    assert is_keepalive("") is False
    assert is_keepalive(b"\xff\xfe") is False
