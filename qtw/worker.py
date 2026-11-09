"""后台自动交易线程。默认关闭；开启后每 interval_sec 运行一次 run_cycle。"""
from __future__ import annotations

import logging
import threading
import time

from . import settings as S
from .timeutil import iso, la, utcnow

log = logging.getLogger(__name__)
_state = {"running": False, "last_run": "", "last_run_la": "", "last_result": None, "last_error": "", "next_run": 0.0}
_stop = threading.Event()
_thread: threading.Thread | None = None
_lock = threading.Lock()


def _loop():
    from .engine import run_cycle
    while not _stop.is_set():
        cfg = S.load()
        try:
            res = run_cycle(cfg, note="")
            _state.update(last_result=res, last_error="")
        except Exception as e:  # noqa: BLE001
            log.exception("cycle failed")
            _state["last_error"] = str(e)[:300]
        _state.update(last_run=iso(utcnow()), last_run_la=la(utcnow()))
        _state["next_run"] = time.time() + cfg["worker"]["interval_sec"]
        _stop.wait(cfg["worker"]["interval_sec"])
    _state["running"] = False


def start():
    global _thread
    with _lock:
        if _thread and _thread.is_alive():
            return
        _stop.clear()
        _state["running"] = True
        _thread = threading.Thread(target=_loop, name="qtw-worker", daemon=True)
        _thread.start()


def stop():
    _stop.set()
    _state["running"] = False


def status() -> dict:
    s = dict(_state)
    s["running"] = bool(_thread and _thread.is_alive() and not _stop.is_set())
    s["next_run_in_sec"] = max(0, int(s.pop("next_run") - time.time())) if s["running"] else None
    return s
