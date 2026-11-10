import threading
import time

from qtw import stream, worker


def test_kick_noop_when_worker_not_running(monkeypatch):
    monkeypatch.setattr(worker, "_thread", None)
    assert worker.kick("x") is False


def test_wait_next_returns_early_on_kick(monkeypatch):
    monkeypatch.setattr(worker, "_stop", threading.Event())
    monkeypatch.setattr(worker, "_kick", threading.Event())
    threading.Timer(0.2, worker._kick.set).start()
    t0 = time.time()
    worker._wait_next(30)
    assert time.time() - t0 < 2.0
    assert not worker._kick.is_set()


def test_host_freeze_runs_callbacks(monkeypatch):
    seen = []
    monkeypatch.setattr(stream, "_on_host_freeze", [seen.append])
    monkeypatch.setattr(stream, "_host_freeze_count", 0)
    assert stream._note_watchdog_gap(100.0, 200.0) is True
    assert seen == [100.0]
