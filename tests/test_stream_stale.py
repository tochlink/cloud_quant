"""Zombie WS sockets: connected but silent last_msg → status=stale."""
from datetime import datetime, timedelta, timezone

from qtw.stream import ZOMBIE_SEC, annotate_conn, classify_mode


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_annotate_conn_marks_zombie_as_stale():
    now = datetime(2026, 11, 10, 3, 20, tzinfo=timezone.utc).timestamp()
    fresh = annotate_conn(
        {"name": "okx_public", "status": "connected", "last_msg": _iso(datetime(2026, 11, 10, 3, 19, 50, tzinfo=timezone.utc))},
        now=now,
    )
    assert fresh["status"] == "connected"
    assert fresh["last_msg_age_sec"] < ZOMBIE_SEC

    zombie = annotate_conn(
        {"name": "okx_public", "status": "connected",
         "last_msg": _iso(datetime(2026, 11, 10, 3, 20, tzinfo=timezone.utc) - timedelta(seconds=ZOMBIE_SEC + 5))},
        now=now,
    )
    assert zombie["status"] == "stale"
    assert zombie["last_msg_age_sec"] > ZOMBIE_SEC


def test_annotate_conn_connected_without_last_msg_is_stale():
    c = annotate_conn({"name": "gate_spot", "status": "connected", "last_msg": ""}, now=1_700_000_000)
    assert c["status"] == "stale"


def test_stale_sockets_do_not_count_as_up_in_mode():
    # Mimic status() counters after annotate: up excludes stale.
    # All sockets stale + REST serving → honest "rest" (not recovering).
    assert classify_mode(live=0, rest=32, up=0, trying=0, recent_ws=False) == "rest"
    # Actively reconnecting (trying) with recent WS memory → recovering
    assert classify_mode(live=0, rest=32, up=0, trying=2, recent_ws=True) == "recovering"
    # Trying with neither up nor recent_ws, but REST present → rest (not fake recovering)
    assert classify_mode(live=0, rest=32, up=0, trying=2, recent_ws=False) == "rest"


def test_zombie_kick_helper_is_exported():
    # Safety-net close path must stay importable for the supervisor loop.
    from qtw import stream as st
    assert callable(getattr(st, "_kick_zombies", None))
    assert isinstance(getattr(st, "_ws_refs"), dict)
