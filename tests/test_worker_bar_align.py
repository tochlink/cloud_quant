from qtw import worker


def test_wakes_just_after_4h_close():
    close = 1_700_006_400.0  # 4h 边界（UTC 整 4 小时）
    assert close % 14400 == 0
    w = worker._next_wait(60, "4h", now=close - 20)
    assert abs(w - (20 + worker.BAR_CLOSE_GRACE_SEC)) < 1e-6


def test_regular_interval_when_close_far():
    assert worker._next_wait(60, "4h", now=1_700_006_400.0 - 3600) == 60


def test_right_after_close_uses_grace_then_regular():
    close = 1_700_006_400.0
    assert abs(worker._next_wait(60, "4h", now=close + 1) - 4.0) < 1e-6
    assert worker._next_wait(60, "4h", now=close + 4.5) == 60  # 剩余 < 1 秒时不做极短等待


def test_unknown_interval_falls_back():
    assert worker._next_wait(60, "", now=123.0) == 60
