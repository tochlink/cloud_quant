from qtw import stream


def test_watchdog_gap_counts_host_freeze(monkeypatch):
    monkeypatch.setattr(stream, "_host_freeze_count", 0)
    monkeypatch.setattr(stream, "_last_host_freeze_at", 0.0)
    monkeypatch.setattr(stream, "_last_host_freeze_gap_sec", None)
    assert stream._note_watchdog_gap(0.0, 100.0) is False
    assert stream._note_watchdog_gap(100.0, 102.0) is False
    assert stream._note_watchdog_gap(100.0, 268.0) is True
    st = stream.status()
    assert st["host_freeze_count"] == 1
    assert st["last_host_freeze_gap_sec"] == 168.0
    assert st["last_host_freeze_age_sec"] is not None
