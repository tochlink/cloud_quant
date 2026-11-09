"""Quote callbacks must not run on the caller thread (keeps asyncio recv free)."""
import threading

from qtw import stream
from qtw.market.base import Quote
from qtw.timeutil import utcnow


def test_put_dispatches_callbacks_off_caller_thread():
    seen = {"tid": None, "n": 0}
    ready = threading.Event()

    def cb(q):
        seen["tid"] = threading.get_ident()
        seen["n"] += 1
        ready.set()

    stream._on_quote.clear()
    stream.on_quote(cb)
    caller = threading.get_ident()
    q = Quote(
        symbol="BTCUSDT", market="perp", price=1.0, kind="mark", ts=utcnow(),
        venue="okx", data_source="okx_public_ws",
    )
    stream._put(q)
    assert ready.wait(2.0), "callback was not dispatched"
    assert seen["n"] == 1
    assert seen["tid"] != caller
    stream._on_quote.clear()
