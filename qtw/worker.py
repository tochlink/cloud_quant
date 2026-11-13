"""后台自动交易线程（事件驱动）。

决策周期由实时事件唤醒，而不是定时轮询：长线周期 / 日线 K 线收盘确认（WS）→ kick_bar；
机器暂停恢复 → kick。只有当某根长线 K 线收盘后 BAR_FALLBACK_SEC 内没收到 WS 收盘事件（断线 / 重连中）时，
才用 REST 补跑一轮（_next_wait）。止损 / 止盈由 realtime.on_tick 在每个 tick 判定。
"""
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


BAR_DEBOUNCE_SEC = 1.5  # 同一时刻 8 个币 × 现货/永续的收盘事件会先后到达，合并成一轮
BAR_FALLBACK_SEC = 30.0  # 长线 K 线收盘后这么久仍无 WS 事件 → REST 补跑（仅断线 / 重连兜底）


def kick_bar(ev: dict) -> bool:
    """WS 收盘确认事件唤醒决策周期。同一收盘时刻只触发一次。"""
    if not (_thread and _thread.is_alive() and not _stop.is_set()):
        return False
    key = int(ev.get("close_ms") or 0)  # 4h 与 1d 同一时刻收盘只跑一轮
    with _lock:
        if _state.get("_trig_key") == key:
            return True
        _state["_trig_key"] = key
        _state["pending_trigger"] = {"kind": "ws_bar_close", "tf": ev.get("tf"), "symbol": ev.get("symbol"),
                                     "market": ev.get("market"), "close_ms": key, "recv_at": ev.get("recv_at") or time.time()}
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
    if base <= 0:
        base = float("inf")
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


def fallback_wait(bar_interval: str, now: float | None = None) -> float:
    """距离「下一根长线 K 线收盘 + BAR_FALLBACK_SEC」的秒数：只有 WS 收盘事件没来时这一轮才会真的由它触发。"""
    from .market.base import INTERVAL_MS
    step = (INTERVAL_MS.get(bar_interval) or 3_600_000) / 1000.0
    t = time.time() if now is None else float(now)
    return (int(t // step) + 1) * step + BAR_FALLBACK_SEC - t


def _loop():
    from .engine import run_cycle
    trig = {"kind": "start", "recv_at": time.time()}
    while not _stop.is_set():
        cfg = S.load()
        t0 = time.time()
        try:
            res = run_cycle(cfg, note="")
            _state.update(last_result=res, last_error="")
        except Exception as e:  # noqa: BLE001
            log.exception("cycle failed")
            _state["last_error"] = str(e)[:300]
        done = time.time()
        now = utcnow()
        trig = dict(trig or {})
        trig.update(cycle_ms=round((done - t0) * 1000, 1), decided_at=done,
                    event_to_decision_ms=round((done - float(trig.get("recv_at") or t0)) * 1000, 1))
        if trig.get("close_ms"):
            trig["close_to_decision_ms"] = round(done * 1000 - trig["close_ms"], 1)
        _state.update(last_run=iso(now), last_run_la=la(now), last_run_sh=sh(now), last_trigger=trig)
        # 事件驱动：不按 interval_sec 定时；只在下一根长线 K 线收盘 + BAR_FALLBACK_SEC 兜底（WS 断线时 REST 补跑）
        wait = fallback_wait(cfg.get("strategy", {}).get("interval", ""))
        _state["next_run"] = time.time() + wait
        _wait_next(wait)
        if _stop.is_set():
            break
        with _lock:
            trig = _state.pop("pending_trigger", None)
        if trig:
            time.sleep(BAR_DEBOUNCE_SEC)  # 合并同一时刻其它币的收盘事件
        else:
            trig = {"kind": "rest_fallback_or_kick", "recv_at": time.time()}
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
    s = {k: v for k, v in _state.items() if not k.startswith("_")}
    s["mode"] = "event_driven"
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
