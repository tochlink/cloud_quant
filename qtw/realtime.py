"""事件驱动的模拟盘决策（不靠定时轮询）。

* 每个 tick（官方公共 WS 推送的现货最新价 / 永续标记价）：对该币的纸面持仓按同一价位判定止损 / 保本止损 / 止盈 / 分批止盈
  （engine._exit_checks，与回测同一顺序），触发即按该价吃单记账。
* 每根已收盘确认的 K 线（OKX confirm=1 / Gate w=true；5m / 10m / 1h / 1d 由官方 1m 收盘推导）：
  - 长线周期（strategy.interval，默认 4h）收盘 → 立即唤醒 worker 跑完整决策周期（信号、开平、反手、调仓）；
  - 1d 收盘 → 同样唤醒（日线是长线的上下文 / 过滤）；
  - strategy.fast_exit_tf 对应周期收盘（默认 off）→ 唤醒；
  - 短线层周期（1m / 5m / 10m / 1h）：短线层未通过验证、默认关闭，只记录「已评估 · 短线关闭」。
* REST 只用于断线重连 / 补数据：worker 在长线 K 线收盘后若 WS 收盘事件迟迟不到（BAR_FALLBACK_SEC），才用 REST 跑一轮。
每次决策都记录「事件 → 决策」延迟（本进程收到事件到判定完成），/api/realtime 与页面展示。
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque

from . import settings as S

log = logging.getLogger(__name__)
_CFG = {"at": 0.0, "cfg": None}
_LAT = {"tick": deque(maxlen=5000), "bar": deque(maxlen=2000)}
_LAST: dict = {"tick": None, "bar": {}, "exits": deque(maxlen=50)}
_LOCK = threading.Lock()
CFG_TTL_SEC = 3.0  # 设置缓存（避免每个 tick 读 SQLite）；保存设置后最多 3 秒生效


def _cfg() -> dict:
    now = time.time()
    if _CFG["cfg"] is None or now - _CFG["at"] > CFG_TTL_SEC:
        _CFG.update(cfg=S.load(), at=now)
    return _CFG["cfg"]


def invalidate_cfg() -> None:
    _CFG["cfg"] = None


def _rec(kind: str, ms: float, info: dict) -> None:
    with _LOCK:
        _LAT[kind].append(ms)
        if kind == "tick":
            _LAST["tick"] = info
        else:
            _LAST["bar"][info.get("tf", "?")] = info


def on_tick(q) -> None:
    """quote 回调（在 stream 的回调线程上，不阻塞 WS 事件循环）。"""
    from . import engine
    bk = engine._BOOK
    if bk is None:
        return
    cfg = _cfg()
    if q.venue.lower() != cfg["venue"].lower():
        return
    p = bk.positions.get(q.symbol)
    if not p or p.market != q.market:
        return
    if not engine.CYCLE_LOCK.acquire(blocking=False):
        return  # 正在跑完整周期：由周期自己按最新价处理
    events: list[str] = []
    try:
        p = bk.positions.get(q.symbol)
        if p and p.market == q.market:
            engine._exit_checks(cfg, bk, q.symbol, p, float(q.price), q.kind, q, events, "·实时tick")
            if events:
                bk.snapshot("；".join(events)[:240])
                try:
                    engine.export_paper_csv(cfg)
                except Exception:  # noqa: BLE001
                    log.debug("export after tick exit failed", exc_info=True)
    finally:
        engine.CYCLE_LOCK.release()
    done = time.time()
    recv = float(getattr(q, "recv_at", 0) or done)
    try:
        exch_ms = (done - q.ts.timestamp()) * 1000
    except Exception:  # noqa: BLE001
        exch_ms = None
    info = {"symbol": q.symbol, "market": q.market, "price": float(q.price), "source": q.data_source,
            "event_to_decision_ms": round((done - recv) * 1000, 2),
            "exchange_ts_to_decision_ms": None if exch_ms is None else round(exch_ms, 1), "at": done}
    _rec("tick", (done - recv) * 1000, info)
    if events:
        log.info("实时 tick 离场：%s", "；".join(events))
        _LAST["exits"].append({"at": done, "events": events, **info})


def on_bar_close(ev: dict) -> None:
    from . import worker
    cfg = _cfg()
    if ev.get("venue", "").lower() != cfg["venue"].lower():
        return
    st = cfg.get("strategy") or {}
    tf = ev["tf"]
    core_tf = st.get("interval", "4h")
    if tf in (core_tf, "1d"):
        decision = "长线：唤醒决策周期" if worker.kick_bar(ev) else "长线：自动交易未运行"
    elif tf == st.get("fast_exit_tf"):
        decision = "快速离场周期：唤醒" if worker.kick_bar(ev) else "快速离场周期：自动交易未运行"
    elif tf in ("1m", "5m", "10m", "1h"):
        decision = "短线：已评估（短线层关闭）" if not (cfg.get("short_layer") or {}).get("enabled") else "短线：已评估"
    else:
        decision = "忽略"
    done = time.time()
    ms = (done - float(ev.get("recv_at") or done)) * 1000
    _rec("bar", ms, {**ev, "decision": decision, "event_to_decision_ms": round(ms, 2),
                     "close_to_decision_ms": round(done * 1000 - ev["close_ms"], 1), "at": done})


WS_STALE_SEC = 20.0


def ws_fresh(venue: str) -> bool:
    from . import stream
    with stream._lock:
        t = stream._last_ws_at.get(venue.lower(), 0.0)
    return time.time() - t < WS_STALE_SEC


def _pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(q * (len(s) - 1)))], 2)


def status() -> dict:
    from . import worker
    with _LOCK:
        t, b = list(_LAT["tick"]), list(_LAT["bar"])
        out = {"mode": "event_driven", "tick": {"n": len(t), "p50_ms": _pct(t, .5), "p95_ms": _pct(t, .95), "max_ms": _pct(t, 1.0),
                                                 "last": _LAST["tick"]},
               "bar": {"n": len(b), "p50_ms": _pct(b, .5), "p95_ms": _pct(b, .95), "last_by_tf": dict(_LAST["bar"])},
               "tick_exits": list(_LAST["exits"])[-10:]}
    out["cycle"] = worker.status().get("last_trigger")
    return out
