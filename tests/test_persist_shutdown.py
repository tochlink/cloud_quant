"""Mark-persist / stop-poll thread must join on shutdown before the book is cleared."""
import threading

from qtw import app as app_mod
from qtw import engine


def test_stop_persist_joins_alive_thread():
    finished = threading.Event()

    def fake_main():
        # Mimic _mark_persister: block on the stop event, then exit.
        while not app_mod._persist_stop.wait(0.05):
            pass
        finished.set()

    app_mod._persist_stop.clear()
    t = threading.Thread(target=fake_main, name="qtw-mark-persist-test", daemon=True)
    app_mod._persist_thread = t
    t.start()
    app_mod._stop_persist(timeout=2.0)
    assert not t.is_alive()
    assert finished.is_set()
    assert app_mod._persist_stop.is_set()


def test_stop_persist_noop_when_not_started():
    app_mod._persist_thread = None
    app_mod._persist_stop.clear()
    app_mod._stop_persist(timeout=0.2)
    assert app_mod._persist_stop.is_set()


def test_mark_persister_final_flush_on_stop(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(engine, "persist_marks", lambda: calls.append("final") or False)
    monkeypatch.setattr(app_mod, "_persist_tick", lambda: calls.append("tick"))
    app_mod._persist_stop.set()  # wait() returns True immediately → no tick, only final flush
    app_mod._mark_persister()
    assert calls == ["final"]
