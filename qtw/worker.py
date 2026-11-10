"""后台自动交易线程。默认关闭；开启后每 interval_sec 运行一次 run_cycle。"""
from __future__ import annotations

import logging
import threading
import time

from . import settings as S
from .timeutil import iso, la, sh, utcnow

log = logging.getLogger(__name__)
_state = {"running": False, "last_run": "", "last_run_la": "", "last_run_sh": "", "last_result": None, "last_error": "", "next_run": 0.0}
_stop = threading.Event()
_thread: threading.Thread | None = None
_lock = threading.Lock()
_kick = threading.Event()  # set after a host/process freeze: re-run the cycle now


def kick(reason: str = "") -> bool:
    """Ask a running worker to run its next cycle immediately (e.g. resume after a machine pause).

    Returns False when the worker is not running (auto-trading off) so nothing happens.
    """
    if not (_thread and _thread.is_alive() and not _stop.is_set()):
        return False
    log.info("worker kick: %s", reason or "requested")
    _kick.set()
    return True


def _wait_next(interval: float) -> None:
    """Sleep until the next cycle, a kick, or stop — in short slices so a kick lands fast."""
    deadline = time.time() + max(0.0, float(interval))
    while not _stop.is_set():
        left = deadline - time.time()
        if left <= 0:
            return
        if _kick.wait(min(1.0, left)):
            _kick.clear()
            return


BAR_CLOSE_GRACE_SEC = 5.0  # 交易所发布刚收盘 K 线需要几秒；拿不到时本周期用上一根，下个周期再试


def _next_wait(interval_sec: float, bar_interval: str, now: float | None = None) -> float:
    """下一次周期的等待秒数：常规 interval_sec，但若 K 线收盘（+宽限）更早就提前醒来。

    研究（docs/STRATEGY_FORMULAS.md 2026-11-10 14:40）表明 4h 信号入场推迟 1 小时整段少约 30 点，
    所以新 K 线收盘后应尽快跑周期，而不是最多再等一个 interval_sec。"""
    from .market.base import INTERVAL_MS
    base = max(0.0, float(interval_sec))
    step = INTERVAL_MS.get(bar_interval)
    if not step:
        return base
    t = time.time() if now is None else float(now)
    step_s = step / 1000.0
    last_close = int(t // step_s) * step_s
    to_close = last_close + BAR_CLOSE_GRACE_SEC - t
    if to_close <= 0:
        to_close += step_s
    return min(base, to_close) if to_close > 1.0 else base


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
        now = utcnow()
        _state.update(last_run=iso(now), last_run_la=la(now), last_run_sh=sh(now))
        wait = _next_wait(cfg["worker"]["interval_sec"], cfg.get("strategy", {}).get("interval", ""))
        _state["next_run"] = time.time() + wait
        _wait_next(wait)
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


def stop(timeout: float = 8.0) -> None:
    """Signal the worker loop to exit and wait for the in-flight cycle to finish."""
    _stop.set()
    t = _thread
    if t and t.is_alive():
        t.join(timeout=timeout)
    _state["running"] = bool(t and t.is_alive() and not _stop.is_set())


def status() -> dict:
    s = dict(_state)
    s["running"] = bool(_thread and _thread.is_alive() and not _stop.is_set())
    next_run = s.pop("next_run", 0.0)
    if not s["running"]:
        s["next_run_in_sec"] = None
    elif not next_run:
        # First cycle has not finished, so the next deadline is still unknown.
        s["next_run_in_sec"] = None
    else:
        remaining = next_run - time.time()
        # A negative remainder means a cycle is in progress; do not report "0 seconds".
        s["next_run_in_sec"] = None if remaining < 0 else int(remaining)
    return s
