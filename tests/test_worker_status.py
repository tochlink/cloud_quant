"""Worker status should expose Shanghai time and not lie about next_run_in_sec."""
import time

from qtw import worker


class _Alive:
    def is_alive(self):
        return True


def test_next_run_in_sec_none_when_unknown_or_cycle_running(monkeypatch):
    monkeypatch.setattr(worker, "_thread", _Alive())
    worker._stop.clear()
    worker._state.update(
        running=True,
        last_run="2026-11-09T20:00:00Z",
        last_run_la="2026-11-09 12:00:00 PST",
        last_run_sh="2026-11-10 04:00:00 CST+8",
        next_run=0.0,
        last_result=None,
        last_error="",
    )
    s = worker.status()
    assert s["running"] is True
    assert s["next_run_in_sec"] is None
    assert s["last_run_sh"] == "2026-11-10 04:00:00 CST+8"

    worker._state["next_run"] = time.time() + 42.8
    s = worker.status()
    assert s["next_run_in_sec"] in (41, 42)

    worker._state["next_run"] = time.time() - 3
    s = worker.status()
    assert s["next_run_in_sec"] is None


def test_next_run_in_sec_none_when_stopped(monkeypatch):
    monkeypatch.setattr(worker, "_thread", None)
    worker._state.update(running=False, next_run=time.time() + 30)
    s = worker.status()
    assert s["running"] is False
    assert s["next_run_in_sec"] is None
    assert "last_run_sh" in s
