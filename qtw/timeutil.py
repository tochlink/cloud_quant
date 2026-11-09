from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LA = ZoneInfo("America/Los_Angeles")
SH = ZoneInfo("Asia/Shanghai")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def la(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LA).strftime("%Y-%m-%d %H:%M:%S %Z")


def sh(dt: datetime | None) -> str:
    """Format in Asia/Shanghai. Label CST+8 so it is not confused with US Central."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(SH).strftime("%Y-%m-%d %H:%M:%S") + " CST+8"


def from_ms(ms: int | float | str) -> datetime:
    return datetime.fromtimestamp(int(float(ms)) / 1000.0, tz=timezone.utc)
