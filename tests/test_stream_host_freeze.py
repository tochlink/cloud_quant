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


def test_recent_freeze_reports_recovering_not_rest(monkeypatch):
    from types import SimpleNamespace
    from datetime import datetime, timezone
    now = 10_000.0
    # last WS quote right before a 500s freeze; freeze ended 3s ago
    monkeypatch.setattr(stream, "_last_host_freeze_at", now - 3)
    monkeypatch.setattr(stream, "_last_host_freeze_gap_sec", 500.0)
    last_ws = now - 3 - 500 - 1
    q = [SimpleNamespace(data_source="okx_public_rest", ts=datetime.fromtimestamp(now - 1, timezone.utc))]
    conns = [{"status": "connecting"}]
    mode, live, rest = stream._freshness(q, conns, last_ws, now)
    assert (mode, live, rest) == ("recovering", 0, 1)
    # long after the freeze, plain REST fallback is reported honestly
    monkeypatch.setattr(stream, "_last_host_freeze_at", now - 1000)
    assert stream._freshness(q, conns, last_ws, now)[0] == "rest"
