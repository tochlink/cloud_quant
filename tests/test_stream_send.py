"""WebSocket send watchdog: a hung send must not freeze the recv loop."""
import asyncio

import pytest

from qtw import stream


def test_send_timeout_becomes_connection_error(monkeypatch):
    monkeypatch.setattr(stream, "SEND_WAIT_SEC", 0.05)

    class FakeWS:
        async def send(self, payload):
            await asyncio.sleep(1)

    async def run():
        with pytest.raises(ConnectionError, match="未能发出"):
            await stream._send(FakeWS(), "ping")

    asyncio.run(run())


def test_send_forwards_payload():
    seen = []

    class FakeWS:
        async def send(self, payload):
            seen.append(payload)

    asyncio.run(stream._send(FakeWS(), "ping"))
    assert seen == ["ping"]
