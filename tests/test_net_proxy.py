"""Proxy resolution, reconnect backoff / log throttle, OKX-down hints."""
from __future__ import annotations

import asyncio
import logging
import socket

import pytest
import requests

from qtw import stream
from qtw.net import (
    RECONNECT_BACKOFF_CAP_SEC,
    RECONNECT_BACKOFF_START_SEC,
    apply_proxy_to_session,
    classify_ws_error,
    env_flag,
    reconnect_backoff,
    reconnect_summary,
    redact_proxy,
    resolve_proxy,
    should_log_reconnect,
    venue_unreachable_hint,
)

PROXY_KEYS = [
    "QTW_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY",
    "https_proxy", "http_proxy", "all_proxy",
]


def _clear_proxy(monkeypatch):
    for k in PROXY_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_resolve_proxy_priority_and_none(monkeypatch):
    _clear_proxy(monkeypatch)
    assert resolve_proxy() is None
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    assert resolve_proxy() == "http://127.0.0.1:7890"
    monkeypatch.setenv("QTW_PROXY", "http://127.0.0.1:10809")
    assert resolve_proxy() == "http://127.0.0.1:10809"
    monkeypatch.setenv("QTW_PROXY", "none")
    assert resolve_proxy() is None


def test_redact_proxy_strips_userinfo():
    assert redact_proxy("http://user:secret@127.0.0.1:7890") == "http://***@127.0.0.1:7890"
    assert redact_proxy("http://127.0.0.1:7890") == "http://127.0.0.1:7890"


def test_apply_proxy_to_session_qtw_none_disables_trust_env(monkeypatch):
    _clear_proxy(monkeypatch)
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("QTW_PROXY", "none")
    s = requests.Session()
    assert apply_proxy_to_session(s) is None
    assert s.trust_env is False


def test_apply_proxy_sets_session_proxies(monkeypatch):
    _clear_proxy(monkeypatch)
    monkeypatch.setenv("QTW_PROXY", "http://127.0.0.1:7890")
    s = requests.Session()
    assert apply_proxy_to_session(s) == "http://127.0.0.1:7890"
    assert s.proxies["https"] == "http://127.0.0.1:7890"


def test_reconnect_backoff_is_5_10_20_capped_at_300():
    seq = [reconnect_backoff(i) for i in range(1, 10)]
    assert seq[0] == RECONNECT_BACKOFF_START_SEC == 5
    assert seq[1] == 10
    assert seq[2] == 20
    assert seq[3] == 40
    assert seq[-1] == RECONNECT_BACKOFF_CAP_SEC == 300
    assert reconnect_backoff(0) == 5


def test_classify_ws_error_dns_and_reset():
    assert classify_ws_error(socket.gaierror(-2, "Name or service not known"))[1] == "DNS 解析失败"
    assert classify_ws_error(ConnectionResetError("Connection reset by peer"))[1] == "连接被重置"
    # last_error strings stored on the connection row
    assert classify_ws_error(RuntimeError("gaierror: [Errno -2] Name or service not known"))[1] == "DNS 解析失败"
    assert classify_ws_error(RuntimeError("ConnectionResetError: Connection reset by peer"))[1] == "连接被重置"


def test_should_log_reconnect_first_few_then_every_tenth_or_10_min():
    assert should_log_reconnect(1, 0, 100) is True
    assert should_log_reconnect(3, 100, 101) is True
    assert should_log_reconnect(4, 100, 101) is True  # first summary
    assert should_log_reconnect(5, 101, 102) is False
    assert should_log_reconnect(10, 101, 102) is True
    assert should_log_reconnect(5, 100, 100 + 600) is True


def test_reconnect_logs_are_throttled(caplog, monkeypatch):
    stream._reconnect_log_at.clear()
    monkeypatch.setattr(stream, "_reconnect_log_at", {})
    with caplog.at_level(logging.INFO, logger="qtw.stream"):
        stream._log_ws_disconnect("okx_public", ConnectionResetError("x"), 1, 5)
        stream._log_ws_disconnect("okx_public", ConnectionResetError("x"), 2, 10)
        stream._log_ws_disconnect("okx_public", socket.gaierror(-2, "Name or service not known"), 3, 20)
        stream._log_ws_disconnect("okx_public", ConnectionResetError("x"), 4, 40)
        stream._log_ws_disconnect("okx_public", ConnectionResetError("x"), 5, 80)
        stream._log_ws_disconnect("okx_public", ConnectionResetError("x"), 10, 300)
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(infos) == 3
    assert any("断开" in r.getMessage() for r in infos)
    assert any("持续失败" in r.getMessage() and "HTTPS_PROXY" in r.getMessage() for r in warns)
    # fail 5 is silent; fail 4 (first beyond first-3) and fail 10 are warnings
    assert len(warns) == 2
    assert "REST 轮询" in reconnect_summary("okx_public", 4, "连接被重置", 40)


def test_hint_when_okx_ws_and_rest_down():
    hint = venue_unreachable_hint(
        venue="okx", mode="down", quotes_ws_fresh=0, quotes_rest_fresh=0,
        rest_errors={"okx:BTCUSDT:perp": "gaierror: Name or service not known"},
        last_errors=["ConnectionResetError: Connection reset by peer"],
    )
    assert "OKX" in hint and "不可达" in hint and "不会编造价格" in hint
    assert "HTTPS_PROXY" in hint
    assert "Gate" in hint


def test_hint_when_rest_fallback_works():
    hint = venue_unreachable_hint(
        venue="okx", mode="rest", quotes_ws_fresh=0, quotes_rest_fresh=8,
        rest_errors={}, last_errors=["ConnectionResetError: x"],
    )
    assert "REST 轮询" in hint and "HTTPS_PROXY" in hint
    assert venue_unreachable_hint(
        venue="okx", mode="ws", quotes_ws_fresh=8, quotes_rest_fresh=0, rest_errors={},
    ) == ""


def test_disable_okx_ws_skips_okx_tasks(monkeypatch):
    monkeypatch.setenv("QTW_DISABLE_OKX_WS", "1")
    assert env_flag("QTW_DISABLE_OKX_WS") is True
    called = {"okx": 0, "gate": 0}

    def fake_okx(*_a, **_k):
        called["okx"] += 1
        return []

    def fake_gate(*_a, **_k):
        called["gate"] += 1
        return []

    async def fake_rest(*_a, **_k):
        return None

    monkeypatch.setattr(stream, "_okx_tasks", fake_okx)
    monkeypatch.setattr(stream, "_gate_tasks", fake_gate)
    monkeypatch.setattr(stream, "_rest_fallback", fake_rest)
    try:
        coros = stream._market_ws_coros(["BTCUSDT"], "4h")
        assert called["okx"] == 0
        assert called["gate"] == 1
        assert len(coros) == 1
        assert stream._okx_ws_disabled_current is True
        coros[0].close()
    finally:
        stream._okx_ws_disabled_current = False


def test_connect_ws_passes_explicit_proxy_or_none(monkeypatch):
    _clear_proxy(monkeypatch)
    seen = {}

    async def fake_connect(url, **kw):
        seen.clear()
        seen.update(kw)
        return object()

    monkeypatch.setattr("websockets.connect", fake_connect)
    asyncio.run(stream._connect_ws("wss://ws.okx.com/ws/v5/public"))
    assert seen.get("proxy") is None
    assert seen.get("family") == socket.AF_INET

    monkeypatch.setenv("QTW_PROXY", "http://127.0.0.1:7890")
    asyncio.run(stream._connect_ws("wss://ws.okx.com/ws/v5/public"))
    assert seen.get("proxy") == "http://127.0.0.1:7890"
