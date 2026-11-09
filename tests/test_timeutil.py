"""Display-time helpers: Asia/Shanghai is the UI zone; LA remains available."""
from datetime import datetime, timezone

from qtw.timeutil import la, sh


def test_sh_formats_utc_as_shanghai_next_calendar_day():
    dt = datetime(2026, 11, 9, 16, 0, 0, tzinfo=timezone.utc)
    assert sh(dt) == "2026-11-10 00:00:00 CST+8"


def test_sh_and_la_are_16_hours_apart_in_standard_time():
    dt = datetime(2026, 11, 9, 20, 0, 0, tzinfo=timezone.utc)
    assert sh(dt) == "2026-11-10 04:00:00 CST+8"
    assert la(dt) == "2026-11-09 12:00:00 PST"


def test_sh_none_is_empty():
    assert sh(None) == ""
    assert la(None) == ""
