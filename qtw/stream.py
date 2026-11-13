"""官方公共 WebSocket 实时行情（无需 API Key）+ REST 轮询兜底。

连接（每个交易所现货 / 永续各一条，外加 OKX K 线 business 通道）：
  OKX  public   wss://ws.okx.com/ws/v5/public（443；可用 QTW_OKX_WS_HOST 指定官方域名）
       频道：tickers（现货 BTC-USDT…）、mark-price（永续 BTC-USDT-SWAP…）
  OKX  business wss://ws.okx.com/ws/v5/business  频道：candle4H（现货 + 永续成交价）、mark-price-candle4H（仅永续标记价，不参与信号）
  Gate spot     wss://api.gateio.ws/ws/v4/            频道：spot.tickers、spot.candlesticks
  Gate futures  wss://fx-ws.gateio.ws/v4/ws/usdt       频道：futures.tickers（含 mark_price）、futures.candlesticks
规则：
  * 只保存交易所真实推送的数据；收盘确认的 K 线（OKX confirm=1 / Gate w=true）写入 SQLite candles 表，
    data_source = okx_public_ws / gate_public_ws；未收盘 K 线只推给前端图表，不参与信号。
  * 断线指数退避自动重连（5s→10→20→…→300s）；连续失败时日志节流，并在 status.hint 给出原因与代理建议。
  * 某个价格超过 20 秒没有 WS 更新 → 用官方公共 REST 拉取（data_source=*_public_rest）。
  * QTW_DISABLE_OKX_WS=1 时不连 OKX WebSocket，OKX 价格改走 REST；Gate WS 不受影响。绝不编造价格。
  * 应用层心跳：OKX 文本 ping/pong；Gate JSON 的 channel 以 .pong 结尾（不是字符串 "pong"）。二者都视为连接活跃并刷新 last_msg，不交给行情 handle。
    recv 超时后先再发一次 ping 并多等一轮，仍无消息才重连，避免短暂静默导致连接一起抖动。
    发出订阅 / ping 也有超时：半开 TCP 让 send 挂起时会主动重连，避免状态仍是 connected 但 last_msg 数分钟不刷新。
  * 已收盘 K 线写入 SQLite 放到线程池，避免 db 锁/WAL 卡住 asyncio 事件循环，导致四条连接同时假死（status=connected 但 last_msg 数分钟不刷新）。
  * status() 把「已连接但 last_msg 超过 ZOMBIE_SEC」标为 stale，不计入 up，避免 UI 误报实时。
  * status(venue) 的 mode / quotes_ws_fresh / quotes_rest_fresh 只统计该行情源：OKX 标记价全走 REST 时，不会因为 Gate WS 仍新鲜而显示 mode=ws。
  * WebSocket 握手除库自带 open_timeout 外再包一层 wait_for，避免 DNS / 半开 TCP 让状态一直停在 connecting（此时还没有 _ws_refs，僵尸踢除无法中断）。
  * supervisor 每轮检查僵尸连接：last_msg 过旧仍标 connected 时强制中断套接字（优先 transport.abort，避免 close 握手挂起），并行踢掉并标 reconnecting，迫使 _run_ws 走重连；刚连上时写入 last_msg，空 last_msg 则用 connected_at 计龄；踢掉后立刻 REST 填一次标记价，不等 10 秒轮询。
  * supervisor 读配置走线程池（run_in_executor），避免 S.load()/SQLite 锁被纸面写库或 K 线缓存占用时卡住 asyncio，导致四条 WS 同时假死、zombie age 远超 ZOMBIE_SEC。
  * 侧线程 watchdog：supervisor 的僵尸踢除跑在 asyncio 循环内；若事件循环被卡住，踢除本身也无法执行，last_msg 会拖到 90s+。watchdog 独立扫描；循环心跳过旧或僵尸年龄超过 ZOMBIE+宽限时，先 shutdown 底层 TCP 套接字（线程安全），再经 call_soon_threadsafe 在行情循环上 transport.abort()，由 connection_lost 关闭 recv_messages。不要在 watchdog 线程调用 set_recv_exc / recv_messages.close：那会与 SSLProtocol._do_read → Assembler.put 竞态，触发 Fatal error on SSL protocol，并在踢除后诱发新一轮 loop stall。loop 已冻结时用后台线程 REST 填隙，健康循环仍经 run_coroutine_threadsafe 调度；abort 失败时再 threadsafe 调度 close()。start() 在行情线程已存活时也会补拉 watchdog。
  * 报价回调（纸面 mark）不在 asyncio 线程同步执行：经单线程队列派发，避免 PaperBook._LOCK / SQLite 写锁卡住 recv/ping/zombie kick（曾出现 last_msg 龄到 200s+ 而 watchdog 日志缺失的假死）。
  * supervisor / watchdog 踢僵尸时记录 last_zombie_kick_age_sec / last_zombie_max_age_sec，供 /api/health 与打磨例程一眼看出「上次踢除多久前、当时最大静默龄」。
  * REST 填隙用独立线程池 + 短超时报价客户端，并在填隙期间刷新 loop heartbeat；watchdog 在 rest_fill_inflight 时不把心跳迟滞当成 loop stall（仍会踢超过 ZOMBIE+宽限的真僵尸），避免「填隙拖心跳 → 误杀重连中的套接字 → 再填隙」的正反馈。
  * 若 rest_fill_inflight 持续超过 FILLING_STALL_SEC（填隙协程卡在已冻结的 loop 上、depth 无法清零），取消 filling 护盾，按真 stall 处理。
  * `_note_activity`（recv/pong）也刷新 loop heartbeat：supervisor 卡在 S.load/DB 时，只要事件循环仍在处理帧就不误报 stall。
  * 真 stall 时用更短的 STALL_ZOMBIE_SEC 门槛踢套接字；尚无僵尸前就从 **后台线程** 走官方 REST 填隙（不经冻结的 asyncio loop 的 run_coroutine_threadsafe，也不阻塞 watchdog 自身）。填隙有合并 + EARLY_FILL_COOLDOWN_SEC 冷却，避免每 2s 打一轮 32 路 HTTP 把 watchdog 卡住、错过下一轮僵尸踢除（曾出现 stall 恢复后紧接着 98s 心跳空白、中间没有任何 watchdog 日志）。
  * WebSocket 握手使用 ``QTW_PROXY`` / ``HTTPS_PROXY`` / ``HTTP_PROXY`` / ``ALL_PROXY``（若已设置）；
    未设置时显式 ``proxy=None``（关闭 websockets 15 默认的代理探测），并限制 ``family=AF_INET``，
    避免 get_proxy / IPv6 happy-eyeballs 在事件循环线程上拖死四路同时重连。
  * REST 填隙优先当前纸面行情源（settings.venue），同批内有限并发，避免僵尸踢掉后纸面标记价排在另一所 32 路串行 REST 后面。
  * 状态 mode 带迟滞：WS 断线重连 / 报价短暂被 REST 填隙时标为 recovering，不立刻翻成 rest，避免 UI 误报「REST 兜底」。
  * 拿不到就报错 / 标记过期，绝不编造价格；永续价格只来自永续频道，现货只来自现货频道。
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import queue
import socket
import threading
import time
from datetime import datetime, timezone

from . import db
from . import settings as S
from .market.base import INTERVAL_MS, MarketDataError, Quote, get_client
from .net import (
    classify_ws_error,
    env_flag,
    okx_ws_urls,
    reconnect_backoff,
    reconnect_summary,
    redact_proxy,
    resolve_proxy,
    should_log_reconnect,
    venue_unreachable_hint,
    RECONNECT_BACKOFF_START_SEC,
    RECONNECT_LOG_FIRST,
)
from .timeutil import iso, utcnow

log = logging.getLogger("qtw.stream")

# Defaults (port 443). Task start uses okx_ws_urls() so QTW_OKX_WS_HOST is honored.
# aws.okx.com / wsaws.okx.com ceased 2025-04-28; :8443 public WS discontinued 2026-10-31.
OKX_PUBLIC = ["wss://ws.okx.com/ws/v5/public"]
OKX_BUSINESS = ["wss://ws.okx.com/ws/v5/business"]
GATE_SPOT = ["wss://api.gateio.ws/ws/v4/"]
GATE_FUT = ["wss://fx-ws.gateio.ws/v4/ws/usdt"]
OKX_BAR = {"15m": "15m", "1h": "1H", "4h": "4H", "1d": "1Dutc"}
# 2026-11-13：快速判断层额外订阅官方 1m K 线（OKX candle1m / Gate candlesticks 1m），收盘根写入 SQLite（10m 由 1m 聚合）
FAST_WS_INTERVAL = "1m"
STALE_SEC = 20
# After the last WS quote, keep mode as ws/recovering this long so a reconnect
# storm (sockets flap, REST briefly fills marks) does not flash "rest" in health/UI.
WS_MODE_HOLD_SEC = 90
RECV_WAIT_SEC = 25
PING_EVERY_SEC = 20
SEND_WAIT_SEC = 10
OPEN_TIMEOUT_SEC = 10
# Outer guard around websockets.connect: open_timeout alone can miss DNS/TCP stalls.
CONNECT_GUARD_SEC = OPEN_TIMEOUT_SEC + 2
# connected + last_msg older than this → report as stale (recv/grace should have
# reconnected already; if the event loop was blocked, status must not lie).
ZOMBIE_SEC = RECV_WAIT_SEC * 2 + PING_EVERY_SEC  # 70
# Side-thread watchdog: supervisor zombie kicks live on the asyncio loop, so a
# stalled loop cannot kick itself. Abort from another thread when the heartbeat
# is stale or a zombie survives past ZOMBIE_SEC + grace (supervisor period ~5s).
WATCHDOG_INTERVAL_SEC = 2.0
LOOP_STALL_SEC = 12.0
WATCHDOG_GRACE_SEC = 12.0
# When the asyncio loop is frozen, waiting a full ZOMBIE_SEC (70) before abort
# leaves paper marks blank too long. Stall path uses this shorter age floor.
STALL_ZOMBIE_SEC = 30.0
# rest_fill_inflight shields against false stall; if depth stays >0 this long the
# fill coroutine itself is wedged on a dead loop — drop the shield.
FILLING_STALL_SEC = 45.0
# After a stall-path REST fill, wait this long before starting another from
# the watchdog. Stops a 2s tick from stacking 32-quote HTTP rounds that pin
# the watchdog and leave sockets un-aborted for a full quiet window.
EARLY_FILL_COOLDOWN_SEC = 15.0
# If the watchdog thread itself did not tick for this long (interval is 2s),
# the whole process/host was frozen (VM pause, box suspend, SIGSTOP) — not an
# asyncio-only stall. Logged and counted separately so health telemetry does
# not blame the stream code for time the process never ran.
HOST_FREEZE_GAP_SEC = 15.0

_lock = threading.RLock()
_quotes: dict[tuple, Quote] = {}
_forming: dict[tuple, dict] = {}
_conns: dict[str, dict] = {}
_version = 0
_thread: threading.Thread | None = None
_watchdog_thread: threading.Thread | None = None
_loop: asyncio.AbstractEventLoop | None = None
_loop_heartbeat: float = 0.0  # wall time; supervisor refreshes each tick / sleep slice
_stop = threading.Event()  # set by stop(); supervisor + watchdog exit cleanly
_rest_errors: dict[str, str] = {}
_on_quote = []  # 回调：用于给纸面持仓实时计价（经 _cb_queue 旁路，不阻塞 asyncio）
_cb_queue: queue.SimpleQueue | None = None
_cb_thread: threading.Thread | None = None
_cb_stop = threading.Event()
_last_ws_at: dict[str, float] = {}  # venue -> wall time of last *_ws quote for that venue
_ws_refs: dict[str, object] = {}  # live websocket objects (stream-loop only) for zombie close
_watch_symbols: list[str] = []  # last subscribed symbols (for watchdog REST fill)
_watch_venue: str | None = None
_last_zombie_kick_at: float = 0.0  # wall time of last supervisor/watchdog zombie abort
_last_zombie_max_age_sec: float | None = None  # max last_msg age among sockets in that kick
_io_pool: concurrent.futures.ThreadPoolExecutor | None = None  # dedicated REST/candle/settings IO
_rest_fill_depth = 0  # >0 while _rest_fill_stale runs (watchdog must not false-stall)
_rest_fill_started_at: float = 0.0  # wall time when depth went 0→1 (stuck-fill detector)
_host_freeze_count = 0  # watchdog-thread gaps > HOST_FREEZE_GAP_SEC (process/host frozen)
_last_host_freeze_at: float = 0.0
_last_host_freeze_gap_sec: float | None = None
_on_host_freeze: list = []  # callbacks(gap_sec) run after a detected host/process freeze
_stall_suspect_count = 0  # watchdog mass-abort / stall recoveries (health polish)
_early_stall_fill_count = 0  # sync REST fills while loop heartbeat was stalled
_last_early_stall_fill_at: float = 0.0  # wall time of last sync stall fill
_last_early_stall_fill_n: int = 0  # quotes filled in that sync pass
_early_fill_inflight = False  # background stall-fill worker is running
_fill_state_lock = threading.Lock()  # depth / started_at / inflight
_reconnect_log_at: dict[str, float] = {}  # connection name -> last reconnect log wall time
_okx_ws_disabled_current = False  # last supervisor decision (for status.hint)
GAP_FILL_TIMEOUT_SEC = 5.0
GAP_FILL_RETRIES = 2
GAP_FILL_BACKOFF_SEC = 0.25
_IO_POOL_WORKERS = 8


def _bump():
    global _version
    _version += 1


def _note_zombie_kick(ages: list[float] | None = None) -> None:
    """Record when a zombie abort ran (for /api/health polish probes)."""
    global _last_zombie_kick_at, _last_zombie_max_age_sec
    _last_zombie_kick_at = time.time()
    if ages:
        _last_zombie_max_age_sec = round(max(ages), 1)
    else:
        _last_zombie_max_age_sec = None


def _bump_loop_heartbeat() -> None:
    """Refresh supervisor heartbeat (safe from stream-loop coroutines)."""
    global _loop_heartbeat
    _loop_heartbeat = time.time()


def _rest_fill_begin() -> None:
    """Increment in-flight fill depth; record start time on 0→1 (thread-safe)."""
    global _rest_fill_depth, _rest_fill_started_at
    with _fill_state_lock:
        _rest_fill_depth += 1
        if _rest_fill_depth == 1:
            _rest_fill_started_at = time.time()


def _rest_fill_end() -> None:
    """Decrement fill depth; clear start time on 1→0 (thread-safe)."""
    global _rest_fill_depth, _rest_fill_started_at
    with _fill_state_lock:
        _rest_fill_depth = max(0, _rest_fill_depth - 1)
        if _rest_fill_depth == 0:
            _rest_fill_started_at = 0.0


def _ensure_io_pool() -> concurrent.futures.ThreadPoolExecutor:
    """Lazy dedicated pool so gap-fill / candle writes do not share ad-hoc default workers."""
    global _io_pool
    if _io_pool is None:
        _io_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=_IO_POOL_WORKERS, thread_name_prefix="qtw-stream-io"
        )
    return _io_pool


def _quote_for_gap_fill(venue: str, symbol: str, market: str) -> Quote:
    """Official public REST quote with short timeout for zombie / stale gap-fill.

    Research candle fetches keep the default 15s×3 retries; gap-fill must fail
    fast so a hung host cannot pin every IO worker and starve the supervisor.
    """
    v = (venue or "").strip().lower()
    kw = dict(timeout=GAP_FILL_TIMEOUT_SEC, max_retries=GAP_FILL_RETRIES, backoff=GAP_FILL_BACKOFF_SEC)
    if v == "okx":
        from .market.okx import OkxPublic
        return OkxPublic(**kw).quote(symbol, market)
    if v in ("gate", "gateio", "gate.io"):
        from .market.gate import GatePublic
        return GatePublic(**kw).quote(symbol, market)
    raise ValueError(f"不支持的交易所: {venue}")


def version() -> int:
    return _version


def _ensure_cb_dispatcher() -> None:
    """One worker thread drains quote callbacks so the WS loop never waits on them."""
    global _cb_queue, _cb_thread
    if _cb_queue is None:
        _cb_queue = queue.SimpleQueue()
    if _cb_thread and _cb_thread.is_alive():
        return

    def _run():
        qref = _cb_queue
        while not _cb_stop.is_set():
            try:
                item = qref.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break
            cb, quote = item
            try:
                cb(quote)
            except Exception:  # noqa: BLE001
                log.exception("quote callback failed")

    _cb_stop.clear()
    _cb_thread = threading.Thread(target=_run, name="qtw-quote-cb", daemon=True)
    _cb_thread.start()


def _put(q: Quote):
    with _lock:
        _quotes[(q.venue.lower(), q.symbol, q.market)] = q
        if q.data_source.endswith("_ws"):
            _last_ws_at[q.venue.lower()] = time.time()
        _bump()
    if not _on_quote:
        return
    _ensure_cb_dispatcher()
    qref = _cb_queue
    for cb in list(_on_quote):
        # Bounded soft-drop: if the book lock is stuck for many ticks, prefer
        # shedding callback latency over freezing recv/ping on the stream loop.
        try:
            qref.put_nowait((cb, q))
        except Exception:  # noqa: BLE001
            log.exception("quote callback enqueue failed")


def on_quote(cb):
    _on_quote.append(cb)
    _ensure_cb_dispatcher()


def latest(venue: str, symbol: str, market: str, max_age_sec: float = 30) -> Quote | None:
    with _lock:
        q = _quotes.get((venue.lower(), symbol, market))
    if q is None:
        return None
    if (datetime.now(timezone.utc) - q.ts).total_seconds() > max_age_sec:
        return None
    return q


def _conn_state(name: str, **kw):
    with _lock:
        st = _conns.setdefault(name, {"name": name, "status": "connecting", "url": "", "connected_at": "", "last_msg": "",
                                      "reconnects": 0, "last_error": "", "channels": []})
        st.update(kw)
        _bump()


def classify_mode(*, live: int, rest: int, up: int, trying: int, recent_ws: bool) -> str:
    """Map quote/connection counters to a stable stream mode label.

    Prefer ws / recovering while any socket is still alive or we recently had
    WS quotes, so REST gap-fills during reconnect do not look like a full
    fallback. Pure "rest" only when the WS path is gone and REST is serving.
    """
    if live > 0:
        return "ws"
    if trying > 0 and (up > 0 or recent_ws):
        return "recovering"
    if rest > 0:
        return "rest"
    if trying > 0:
        return "recovering"
    return "down"


def _last_msg_age_sec(conn: dict, now: float | None = None) -> float | None:
    """Seconds since conn['last_msg'], or None if missing/unparseable."""
    lm = conn.get("last_msg") or ""
    if not lm:
        return None
    try:
        ts = datetime.fromisoformat(lm.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None
    return (now if now is not None else time.time()) - ts



def _activity_age_sec(conn: dict, now: float | None = None) -> float | None:
    """Seconds since last_msg, or connected_at if no frame yet.

    Sockets that connect but never deliver a frame used to report age=None and
    were skipped by the zombie kicker forever. Fall back to connected_at so the
    supervisor still aborts them after ZOMBIE_SEC.
    """
    age = _last_msg_age_sec(conn, now)
    if age is not None:
        return age
    return _last_msg_age_sec({"last_msg": conn.get("connected_at") or ""}, now)

def annotate_conn(conn: dict, *, now: float | None = None, zombie_sec: float = ZOMBIE_SEC) -> dict:
    """Copy a connection row and mark zombie sockets as status=stale for API/UI."""
    c = dict(conn)
    age = _activity_age_sec(c, now)
    # Always emit the key: a reconnecting socket with no last_msg / connected_at
    # has age=None. SSE used to KeyError when the field was omitted.
    c["last_msg_age_sec"] = round(age, 1) if age is not None else None
    if c.get("status") == "connected" and (age is None or age > zombie_sec):
        c["status"] = "stale"
    return c


def _conn_belongs(name: str, venue: str) -> bool:
    return (name or "").lower().startswith(venue.lower())


def _freshness(quotes: list, conns: list, last_ws: float, now: float) -> tuple[str, int, int]:
    """Classify mode from the given (already venue-filtered) quotes and sockets."""
    live = sum(1 for x in quotes if x.data_source.endswith("_ws") and (now - x.ts.timestamp()) < STALE_SEC)
    rest = sum(1 for x in quotes if x.data_source.endswith("_rest") and (now - x.ts.timestamp()) < 60)
    # stale sockets must not count as "up" or we keep advertising a live WS path
    up = sum(1 for c in conns if c["status"] == "connected")
    trying = sum(1 for c in conns if c["status"] in ("connected", "reconnecting", "connecting"))
    recent_ws = bool(last_ws) and (now - last_ws) < WS_MODE_HOLD_SEC
    # Time the machine was frozen does not count against the WS hold: right after
    # a host freeze the sockets are reconnecting, so show "recovering", not "rest".
    if not recent_ws and last_ws and _last_host_freeze_at and (now - _last_host_freeze_at) < WS_MODE_HOLD_SEC:
        recent_ws = (_last_host_freeze_at - (_last_host_freeze_gap_sec or 0.0)) - last_ws < WS_MODE_HOLD_SEC
    mode = classify_mode(live=live, rest=rest, up=up, trying=trying, recent_ws=recent_ws)
    return mode, live, rest


def status(venue: str | None = None) -> dict:
    """Stream health. When ``venue`` is set, mode and freshness are scoped to it.

    Paper marks follow settings.venue. A live Gate WebSocket must not make
    stream.mode look like ``ws`` while the active OKX public socket is down
    and every OKX mark is coming from REST.
    """
    with _lock:
        raw = [dict(v) for v in _conns.values()]
        now = time.time()
        q = list(_quotes.values())
        last_ws_map = dict(_last_ws_at)
        rest_err = dict(_rest_errors)
    conns = [annotate_conn(c, now=now) for c in raw]
    v = (venue or "").strip().lower() or None
    if v:
        q_use = [x for x in q if (x.venue or "").lower() == v]
        c_use = [c for c in conns if _conn_belongs(c.get("name") or "", v)]
        last_ws = float(last_ws_map.get(v) or 0.0)
        rest_err = {k: e for k, e in rest_err.items() if str(k).lower().startswith(v + ":")}
    else:
        q_use, c_use = q, conns
        last_ws = max(last_ws_map.values(), default=0.0)
    mode, live, rest = _freshness(q_use, c_use, last_ws, now)
    hb = _loop_heartbeat
    kick_at = _last_zombie_kick_at
    ages = [c.get("last_msg_age_sec") for c in c_use
            if c.get("status") in ("connected", "stale") and c.get("last_msg_age_sec") is not None]
    early_at = _last_early_stall_fill_at
    out = {"mode": mode, "connections": conns, "quotes_ws_fresh": live, "quotes_rest_fresh": rest,
           "quotes_total": len(q_use), "rest_errors": rest_err, "running": bool(_thread and _thread.is_alive()),
           "watchdog_running": bool(_watchdog_thread and _watchdog_thread.is_alive()),
           "loop_heartbeat_age_sec": round(time.time() - hb, 1) if hb else None,
           "rest_fill_inflight": int(_rest_fill_depth) > 0,
           "stall_suspect_count": int(_stall_suspect_count),
           "host_freeze_count": int(_host_freeze_count),
           "last_host_freeze_gap_sec": _last_host_freeze_gap_sec,
           "last_host_freeze_age_sec": round(time.time() - _last_host_freeze_at, 1) if _last_host_freeze_at else None,
           "ws_conn_max_age_sec": round(max(ages), 1) if ages else None,
           "early_stall_fill_count": int(_early_stall_fill_count),
           "early_fill_inflight": bool(_early_fill_inflight),
           "last_early_stall_fill_age_sec": round(time.time() - early_at, 1) if early_at else None,
           "last_early_stall_fill_n": int(_last_early_stall_fill_n) if early_at else None,
           "last_zombie_kick_age_sec": round(time.time() - kick_at, 1) if kick_at else None,
           "last_zombie_max_age_sec": _last_zombie_max_age_sec}
    if v:
        out["venue"] = v
    last_errs = [c.get("last_error") or "" for c in c_use]
    disabled = bool(_okx_ws_disabled_current)
    out["okx_ws_disabled"] = disabled
    out["hint"] = venue_unreachable_hint(
        venue=v or "",
        mode=mode,
        quotes_ws_fresh=live,
        quotes_rest_fresh=rest,
        rest_errors=rest_err,
        last_errors=last_errs,
        okx_ws_disabled=disabled,
    )
    out["unreachable"] = bool(
        live == 0 and rest == 0 and mode in ("rest", "down") and (rest_err or last_errs)
    )
    return out


def snapshot(venue: str) -> dict:
    now = time.time()
    with _lock:
        items = [(k, v) for k, v in _quotes.items() if k[0] == venue]
        forming = {f"{k[1]}:{k[2]}:{k[3]}": v for k, v in _forming.items() if k[0] == venue}
    prices: dict = {}
    for (v, sym, mkt), q in items:
        prices.setdefault(sym, {})[mkt] = {"price": q.price, "kind": q.kind, "ts": iso(q.ts), "source": q.data_source,
                                          "age_sec": round(now - q.ts.timestamp(), 1)}
    # Latest OKX mark-price candle per symbol (market=perp_mark). Display only; not used by signals.
    mark_candles: dict = {}
    for key, val in forming.items():
        parts = str(key).split(":")
        if len(parts) >= 3 and parts[-1] == "perp_mark":
            mark_candles[parts[1]] = dict(val)
    return {"venue": venue, "prices": prices, "forming": forming, "mark_candles": mark_candles}


def _ms(x) -> datetime:
    return datetime.fromtimestamp(int(float(x)) / 1000, tz=timezone.utc)


_STORE_SQL = (
    "INSERT INTO candles(venue,market,symbol,interval,open_time,open,high,low,close,volume,data_source,source_host,fetched_at) "
    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(venue,market,symbol,interval,open_time) DO UPDATE SET "
    "open=excluded.open,high=excluded.high,low=excluded.low,close=excluded.close,volume=excluded.volume,"
    "data_source=excluded.data_source,source_host=excluded.source_host,fetched_at=excluded.fetched_at"
)


def _store_closed_sync(args: tuple) -> None:
    try:
        db.execute(_STORE_SQL, args)
    except Exception:  # noqa: BLE001
        log.exception("candle store failed")


def _store_closed(venue, market, symbol, interval, open_ms, o, h, l, c, v, source, host):
    """Persist a confirmed closed candle without blocking the WS event loop.

    SQLite writes share a process-wide lock with the paper book / worker. Doing
    them inline inside recv handlers freezes ping/pong and wait_for timeouts, so
    all sockets can sit at status=connected with a multi-minute-old last_msg.
    """
    args = (venue, market, symbol, interval, int(open_ms), float(o), float(h), float(l), float(c),
            float(v or 0), source, host, iso(utcnow()))
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        _store_closed_sync(args)
        return
    loop.run_in_executor(_ensure_io_pool(), _store_closed_sync, args)


def _forming_put(venue, market, symbol, interval, open_ms, o, h, l, c, closed, source):
    with _lock:
        _forming[(venue, interval, symbol, market)] = {"time": int(open_ms) // 1000, "open": float(o), "high": float(h),
                                                      "low": float(l), "close": float(c), "closed": closed, "source": source}
        _bump()


# ---------------------------------------------------------------- 连接
def is_keepalive(raw) -> bool:
    """True for OKX/Gate application-level ping/pong frames (not market data).

    OKX replies to the text ``ping`` with the text ``pong`` (sometimes
    ``{"event": "pong"}``). Gate replies to ``{"channel": "spot.ping"}`` /
    ``futures.ping`` with JSON whose ``channel`` ends in ``.pong``.
    These count as connection activity and must not be passed to handlers.
    """
    if raw is None:
        return False
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return False
    if not isinstance(raw, str):
        return False
    text = raw.strip()
    if text in ("pong", "ping"):
        return True
    if not text.startswith("{"):
        return False
    try:
        msg = json.loads(text)
    except (TypeError, ValueError):
        return False
    if not isinstance(msg, dict):
        return False
    ch = msg.get("channel")
    if ch is None and isinstance(msg.get("arg"), dict):
        ch = msg["arg"].get("channel")
    ch = str(ch or "")
    if ch.endswith(".pong") or ch.endswith(".ping") or ch == "pong":
        return True
    return msg.get("event") in ("pong", "ping")


def _note_activity(name: str) -> None:
    """Refresh last_msg so status/UI see pongs as well as market data.

    Also bumps the supervisor heartbeat: a healthy recv/pong path proves the
    asyncio loop is alive even when ``_supervisor`` is blocked in
    ``run_in_executor`` (settings/DB). Without this, a long S.load wait aged
    the heartbeat while sockets were fine, then a brief quiet stretch looked
    like a multi-minute loop stall.
    """
    ts = iso(utcnow())
    _bump_loop_heartbeat()
    with _lock:
        st = _conns.get(name)
        if st is not None:
            st["last_msg"] = ts


async def _send(ws, payload):
    """Send with a timeout so a half-open socket cannot freeze the recv loop."""
    try:
        await asyncio.wait_for(ws.send(payload), SEND_WAIT_SEC)
    except asyncio.TimeoutError:
        raise ConnectionError(f"{SEND_WAIT_SEC} 秒内未能发出心跳/订阅（连接可能已半开）") from None


async def _connect_ws(url: str, *, opener=None):
    """Open a WebSocket with a hard outer timeout around the handshake.

    ``websockets.connect(..., open_timeout=N)`` can still stall (DNS lookup or
    a half-open TCP that never completes the upgrade). ``_run_ws`` sets
    status=connecting *before* the handshake, and ``_ws_refs`` is only filled
    after it succeeds, so a hung connect would sit at connecting forever and
    the zombie kicker could not abort it. Cancelling via wait_for forces the
    reconnect loop to make progress.

    Default ``websockets`` 15 sets ``proxy=True`` (env / OS proxy autodetect).
    Autodetect can stall four simultaneous handshakes, so we only pass a proxy
    when ``QTW_PROXY`` / ``HTTPS_PROXY`` / ``HTTP_PROXY`` / ``ALL_PROXY`` is
    explicitly set; otherwise ``proxy=None`` (go direct). Restrict ``family``
    to IPv4 so a broken IPv6 path cannot hold the loop in getaddrinfo.
    """
    import websockets
    fn = opener or websockets.connect
    kw = dict(open_timeout=OPEN_TIMEOUT_SEC, ping_interval=None, close_timeout=3, max_size=2**22)
    if opener is None:
        kw["proxy"] = resolve_proxy()
        kw["family"] = socket.AF_INET
    _bump_loop_heartbeat()
    try:
        ws = await asyncio.wait_for(fn(url, **kw), CONNECT_GUARD_SEC)
        _bump_loop_heartbeat()
        return ws
    except asyncio.TimeoutError:
        raise ConnectionError(f"{CONNECT_GUARD_SEC} 秒内未能完成 WebSocket 握手") from None


async def _close_ws_quietly(ws) -> None:
    try:
        await asyncio.wait_for(ws.close(), 3)
    except Exception:
        try:
            transport = getattr(ws, "transport", None)
            if transport is not None and not transport.is_closing():
                transport.abort()
        except Exception:  # noqa: BLE001
            pass


def _log_ws_disconnect(name: str, exc: BaseException, fail_count: int, backoff: float) -> None:
    """Log a WS drop: first few at INFO, then a throttled WARNING with a fix hint."""
    typ, reason = classify_ws_error(exc)
    now = time.time()
    last = _reconnect_log_at.get(name) or 0.0
    if not should_log_reconnect(fail_count, last, now):
        return
    _reconnect_log_at[name] = now
    if fail_count <= RECONNECT_LOG_FIRST:
        log.info("%s 断开（%s），%.0f 秒后重连", name, typ, backoff)
        return
    log.warning("%s", reconnect_summary(name, fail_count, reason, backoff))


async def _run_ws(name, urls, subscribe_msgs, handle, ping):
    backoff, i, fail_n = RECONNECT_BACKOFF_START_SEC, 0, 0
    while True:
        url = urls[i % len(urls)]
        was_connected = False
        _conn_state(name, status="connecting", url=url)
        ws = None
        try:
            # Keep library protocol ping disabled: OKX/Gate use app-level ping/pong
            # and we do not want a second heartbeat to interfere. Quiet stretches
            # are handled by the grace-retry below.
            ws = await _connect_ws(url)
            _ws_refs[name] = ws
            try:
                for m in subscribe_msgs():
                    await _send(ws, m)
                _conn_state(name, status="connected", connected_at=iso(utcnow()), last_msg=iso(utcnow()), last_error="")
                if fail_n:
                    log.info("%s 实时连接已恢复（此前连续失败 %d 次）", name, fail_n)
                backoff, was_connected, fail_n = RECONNECT_BACKOFF_START_SEC, True, 0
                _reconnect_log_at.pop(name, None)
                last_ping = time.time()
                while True:
                    if time.time() - last_ping > PING_EVERY_SEC:
                        await _send(ws, ping())
                        last_ping = time.time()
                    try:
                        raw = await asyncio.wait_for(ws.recv(), RECV_WAIT_SEC)
                    except asyncio.TimeoutError:
                        # Grace retry: one extra app-level ping + one more recv wait
                        # so a brief quiet period does not flap all sockets at once.
                        try:
                            await _send(ws, ping())
                            last_ping = time.time()
                            raw = await asyncio.wait_for(ws.recv(), RECV_WAIT_SEC)
                        except asyncio.TimeoutError:
                            raise ConnectionError(f"{RECV_WAIT_SEC} 秒未收到消息（grace ping 后仍无响应）") from None
                    _note_activity(name)
                    if is_keepalive(raw):
                        _bump()
                        continue
                    try:
                        handle(json.loads(raw), url)
                    except Exception as e:  # noqa: BLE001
                        log.warning("%s handle error: %s", name, e)
            finally:
                if _ws_refs.get(name) is ws:
                    _ws_refs.pop(name, None)
                # Close before the reconnect sleep (same timing as the old async with).
                await _close_ws_quietly(ws)
        except asyncio.CancelledError:
            _conn_state(name, status="stopped")
            raise
        except Exception as e:  # noqa: BLE001
            with _lock:
                _conns[name]["reconnects"] += 1
            typ, _reason = classify_ws_error(e)
            _conn_state(name, status="reconnecting", last_error=f"{typ}: {str(e)[:160]}")
            fail_n += 1
            backoff = reconnect_backoff(fail_n)
            _log_ws_disconnect(name, e, fail_n, backoff)
            if not was_connected:
                i += 1  # 这个地址连不上就换下一个官方地址；连上过的地址断线后先原地重连
            await asyncio.sleep(backoff)


def _host(url):
    return url.split("/")[2]


def parse_okx_ws_candle(channel: str, row) -> dict | None:
    """Parse one official OKX WS candle row. Returns None if the row is unusable.

    Trade-price candles (channel ``candle{bar}``):
      [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    Mark-price candles (channel ``mark-price-candle{bar}``, docs: business WS):
      [ts, o, h, l, c, confirm]  — no volume; confirm is the last field.
    """
    if not isinstance(row, (list, tuple)) or len(row) < 5:
        return None
    ch = str(channel or "")
    is_mark = ch.startswith("mark-price-candle")
    try:
        open_ms = int(float(row[0]))
        o, h, l, c = (float(row[1]), float(row[2]), float(row[3]), float(row[4]))
    except (TypeError, ValueError, IndexError):
        return None
    if is_mark:
        if len(row) < 6:
            return None
        closed = str(row[5]) == "1"
        vol = 0.0
        kind = "mark"
    else:
        # Unconfirmed / short rows: treat as open (not closed) if confirm is missing.
        closed = len(row) > 8 and str(row[8]) == "1"
        try:
            vol = float(row[5]) if len(row) > 5 else 0.0
        except (TypeError, ValueError):
            vol = 0.0
        kind = "trade"
    return {"open_ms": open_ms, "open": o, "high": h, "low": l, "close": c,
            "volume": vol, "closed": closed, "kind": kind}


def apply_okx_candle_message(m, url, interval, inst_map) -> int:
    """Apply one OKX business-channel candle / mark-price-candle push.

    Mark-price bars are stored as market='perp_mark' with data_source
    ``okx_mark_price_ws`` so they never mix into trade-price perp candles
    used by signals and backtests. Returns the number of rows applied.
    """
    arg = m.get("arg") or {}
    ch = str(arg.get("channel") or "")
    sym, mkt = inst_map.get(arg.get("instId"), (None, None))
    if not sym:
        return 0
    is_mark = ch.startswith("mark-price-candle")
    if is_mark:
        if mkt != "perp":
            return 0
        store_mkt, source = "perp_mark", "okx_mark_price_ws"
    else:
        store_mkt, source = mkt, "okx_public_ws"
    n = 0
    if ch in ("candle1m", "mark-price-candle1m"):
        if is_mark:
            return 0  # 1m 只订阅成交价 K 线
        interval = "1m"
    for row in m.get("data", []) or []:
        parsed = parse_okx_ws_candle(ch, row)
        if not parsed:
            continue
        _forming_put("okx", store_mkt, sym, interval, parsed["open_ms"],
                     parsed["open"], parsed["high"], parsed["low"], parsed["close"],
                     parsed["closed"], source)
        if parsed["closed"]:
            _store_closed("okx", store_mkt, sym, interval, parsed["open_ms"],
                          parsed["open"], parsed["high"], parsed["low"], parsed["close"],
                          parsed["volume"], source, _host(url))
        n += 1
    return n


def _okx_tasks(symbols, interval):
    spot = [f"{s[:-4]}-USDT" for s in symbols]
    swap = [f"{s[:-4]}-USDT-SWAP" for s in symbols]
    rev = {**{a: (s, "spot") for a, s in zip(spot, symbols)}, **{a: (s, "perp") for a, s in zip(swap, symbols)}}
    bar = OKX_BAR[interval]

    def sub_pub():
        args = [{"channel": "tickers", "instId": x} for x in spot] + [{"channel": "mark-price", "instId": x} for x in swap]
        return [json.dumps({"op": "subscribe", "args": args})]

    def sub_bus():
        args = [{"channel": f"candle{bar}", "instId": x} for x in spot + swap]
        # Official mark-price candlesticks on the same business socket (SWAP only).
        args += [{"channel": f"mark-price-candle{bar}", "instId": x} for x in swap]
        if bar != "1m":
            args += [{"channel": "candle1m", "instId": x} for x in spot + swap]
        return [json.dumps({"op": "subscribe", "args": args})]

    def h_pub(m, url):
        arg = m.get("arg", {})
        for d in m.get("data", []) or []:
            sym, mkt = rev.get(d.get("instId"), (None, None))
            if not sym:
                continue
            if arg.get("channel") == "tickers" and mkt == "spot":
                _put(Quote(sym, "spot", float(d["last"]), "last", _ms(d["ts"]), "OKX", _host(url), "okx_public_ws", iso(utcnow())))
            elif arg.get("channel") == "mark-price" and mkt == "perp":
                _put(Quote(sym, "perp", float(d["markPx"]), "mark", _ms(d["ts"]), "OKX", _host(url), "okx_public_ws", iso(utcnow())))
        if m.get("event") == "error":
            _conn_state("okx_public", last_error=str(m)[:200])

    def h_bus(m, url):
        if m.get("event") == "error":
            _conn_state("okx_business", last_error=str(m)[:200])
            return
        apply_okx_candle_message(m, url, interval, rev)

    _conn_state("okx_public", channels=["tickers(spot)", "mark-price(swap)"])
    _conn_state("okx_business", channels=[f"candle{bar}(spot+swap)", f"mark-price-candle{bar}(swap)", "candle1m(spot+swap)"])
    return [_run_ws("okx_public", okx_ws_urls("public"), sub_pub, h_pub, lambda: "ping"),
            _run_ws("okx_business", okx_ws_urls("business"), sub_bus, h_bus, lambda: "ping")]


def _gate_tasks(symbols, interval):
    pairs = [f"{s[:-4]}_USDT" for s in symbols]
    rev = dict(zip(pairs, symbols))

    def subs(prefix):
        def f():
            t = int(time.time())
            out = [json.dumps({"time": t, "channel": f"{prefix}.tickers", "event": "subscribe", "payload": pairs})]
            out += [json.dumps({"time": t, "channel": f"{prefix}.candlesticks", "event": "subscribe", "payload": [iv, p]})
                    for iv in dict.fromkeys([interval, FAST_WS_INTERVAL]) for p in pairs]
            return out
        return f

    def handler(prefix, market, name):
        def h(m, url):
            if str(m.get("channel") or "").endswith(".pong"):
                return
            if m.get("event") != "update":
                if m.get("error"):
                    _conn_state(name, last_error=str(m.get("error"))[:200])
                return
            ch, res = m.get("channel"), m.get("result")
            ts = _ms(m.get("time_ms") or int(time.time() * 1000))
            if ch == f"{prefix}.tickers":
                for r in res if isinstance(res, list) else [res]:
                    sym = rev.get(r.get("currency_pair") or r.get("contract"))
                    if not sym:
                        continue
                    if market == "spot":
                        _put(Quote(sym, "spot", float(r["last"]), "last", ts, "Gate", _host(url), "gate_public_ws", iso(utcnow())))
                    elif r.get("mark_price"):
                        _put(Quote(sym, "perp", float(r["mark_price"]), "mark", ts, "Gate", _host(url), "gate_public_ws", iso(utcnow())))
            elif ch == f"{prefix}.candlesticks":
                for r in res if isinstance(res, list) else [res]:
                    n = r.get("n", "")
                    sym = rev.get(n.split("_", 1)[1] if "_" in n else "")
                    if not sym:
                        continue
                    civ = n.split("_", 1)[0] if "_" in n else interval
                    civ = civ if civ in (interval, FAST_WS_INTERVAL) else interval
                    closed = bool(r.get("w"))
                    om = int(r["t"]) * 1000
                    _forming_put("gate", market, sym, civ, om, r["o"], r["h"], r["l"], r["c"], closed, "gate_public_ws")
                    if closed:
                        _store_closed("gate", market, sym, civ, om, r["o"], r["h"], r["l"], r["c"], r.get("a") or r.get("v") or 0,
                                      "gate_public_ws", _host(url))
        return h

    _conn_state("gate_spot", channels=["spot.tickers", f"spot.candlesticks({interval}+{FAST_WS_INTERVAL})"])
    _conn_state("gate_futures", channels=["futures.tickers(mark_price)", f"futures.candlesticks({interval}+{FAST_WS_INTERVAL})"])
    return [_run_ws("gate_spot", GATE_SPOT, subs("spot"), handler("spot", "spot", "gate_spot"),
                    lambda: json.dumps({"time": int(time.time()), "channel": "spot.ping"})),
            _run_ws("gate_futures", GATE_FUT, subs("futures"), handler("futures", "perp", "gate_futures"),
                    lambda: json.dumps({"time": int(time.time()), "channel": "futures.ping"}))]


REST_FILL_CONCURRENCY = 6


def _venue_fill_order(preferred: str | None = None, venues=("okx", "gate")) -> list[str]:
    """Active paper venue first, then the rest — paper marks must not wait on the other exchange."""
    pref = (preferred or "").strip().lower()
    ordered: list[str] = []
    if pref and pref in venues:
        ordered.append(pref)
    for v in venues:
        if v not in ordered:
            ordered.append(v)
    return ordered


async def _rest_fill_stale(symbols, venues=("okx", "gate"), *, preferred_venue: str | None = None) -> int:
    """One-shot official REST fill for quotes older than STALE_SEC. Returns fills.

    Prefer ``preferred_venue`` (settings.venue) so the paper book recovers marks
    before secondary-exchange gap fills. Within each venue batch, run a few HTTP
    calls concurrently — sequential 8×2×2 round-trips used to leave marks stale
    for many seconds after a zombie kick.

    Uses a dedicated IO pool + short-timeout quote client, bumps the loop
    heartbeat as each request finishes, and tracks ``_rest_fill_depth`` so the
    side-thread watchdog does not treat a busy (but healthy) fill as a stall and
    abort sockets that are mid-reconnect.
    """
    loop = asyncio.get_running_loop()
    pool = _ensure_io_pool()
    order = _venue_fill_order(preferred_venue, venues)
    jobs: list[tuple[str, str, str]] = []
    for venue in order:
        for sym in symbols:
            for mkt in ("spot", "perp"):
                if latest(venue, sym, mkt, STALE_SEC):
                    continue
                jobs.append((venue, sym, mkt))
    if not jobs:
        return 0

    sem = asyncio.Semaphore(REST_FILL_CONCURRENCY)
    _rest_fill_begin()
    _bump_loop_heartbeat()
    try:
        async def one(venue: str, sym: str, mkt: str) -> int:
            key = f"{venue}:{sym}:{mkt}"
            async with sem:
                if latest(venue, sym, mkt, STALE_SEC):
                    return 0
                try:
                    q = await loop.run_in_executor(pool, _quote_for_gap_fill, venue, sym, mkt)
                    _put(q)
                    _rest_errors.pop(key, None)
                    return 1
                except (MarketDataError, Exception) as e:  # noqa: BLE001
                    _rest_errors[key] = str(e)[:200]
                    return 0
                finally:
                    # Keep heartbeat fresh while IO workers are busy so watchdog
                    # does not false-positive a "loop stall" during a long fill.
                    _bump_loop_heartbeat()

        pref = (preferred_venue or "").strip().lower()
        primary = [j for j in jobs if j[0] == pref] if pref else list(jobs)
        secondary = [j for j in jobs if j not in primary] if pref else []
        filled = 0
        for batch in (primary, secondary):
            if not batch:
                continue
            _bump_loop_heartbeat()
            results = await asyncio.gather(*(one(*j) for j in batch), return_exceptions=True)
            for r in results:
                if isinstance(r, int):
                    filled += r
        return filled
    finally:
        _rest_fill_end()
        _bump_loop_heartbeat()



def _rest_fill_stale_sync(symbols, venues=("okx", "gate"), *, preferred_venue: str | None = None) -> int:
    """Watchdog-thread REST gap-fill that does not need the asyncio loop.

    When the stream event loop is frozen, ``run_coroutine_threadsafe(_rest_fill_stale)``
    only queues work that never runs until the loop recovers — leaving paper marks
    blank for the whole stall. This path uses the dedicated IO pool and ``_put``s
    official public REST quotes directly (called from the stall-fill worker, not
    the watchdog scan loop).
    """
    if not symbols:
        return 0
    order = _venue_fill_order(preferred_venue, venues)
    jobs: list[tuple[str, str, str]] = []
    for venue in order:
        for sym in symbols:
            for mkt in ("spot", "perp"):
                if latest(venue, sym, mkt, STALE_SEC):
                    continue
                jobs.append((venue, sym, mkt))
    if not jobs:
        return 0
    pool = _ensure_io_pool()
    _rest_fill_begin()
    try:
        pref = (preferred_venue or "").strip().lower()
        primary = [j for j in jobs if j[0] == pref] if pref else list(jobs)
        secondary = [j for j in jobs if j not in primary] if pref else []
        filled = 0
        # Cap wait so a wedged host cannot pin the watchdog forever.
        per_batch_timeout = GAP_FILL_TIMEOUT_SEC * (GAP_FILL_RETRIES + 1) + 2.0
        for batch in (primary, secondary):
            if not batch:
                continue
            futs = {
                pool.submit(_quote_for_gap_fill, v, s, m): (v, s, m)
                for v, s, m in batch
            }
            try:
                done, not_done = concurrent.futures.wait(
                    futs.keys(), timeout=per_batch_timeout,
                    return_when=concurrent.futures.ALL_COMPLETED,
                )
            except Exception:  # noqa: BLE001
                log.exception("watchdog sync REST wait failed")
                done, not_done = set(), set(futs.keys())
            for fut in not_done:
                fut.cancel()
            for fut in done:
                v, s, m = futs[fut]
                key = f"{v}:{s}:{m}"
                try:
                    q = fut.result()
                    _put(q)
                    _rest_errors.pop(key, None)
                    filled += 1
                except Exception as e:  # noqa: BLE001
                    _rest_errors[key] = str(e)[:200]
        return filled
    finally:
        _rest_fill_end()


def _stall_fill_worker() -> None:
    """Official REST gap-fill that must not run on the watchdog or stream loop."""
    global _early_fill_inflight, _early_stall_fill_count
    global _last_early_stall_fill_at, _last_early_stall_fill_n
    try:
        syms = list(_watch_symbols)
        pref = _watch_venue
        try:
            n = _rest_fill_stale_sync(syms, preferred_venue=pref)
        except Exception:  # noqa: BLE001
            log.exception("watchdog sync REST fill failed")
            return
        _early_stall_fill_count += 1
        _last_early_stall_fill_at = time.time()
        _last_early_stall_fill_n = int(n)
        if n:
            log.info("watchdog: sync REST filled %d stale quotes (loop stall)", n)
        else:
            log.info("watchdog: sync REST fill on stall (0 stale / no symbols)")
    finally:
        _early_fill_inflight = False


def _spawn_stall_fill() -> bool:
    """Start at most one background stall fill (in-flight merge + cooldown)."""
    global _early_fill_inflight
    now = time.time()
    with _fill_state_lock:
        if _early_fill_inflight:
            return False
        if _last_early_stall_fill_at and (now - _last_early_stall_fill_at) < EARLY_FILL_COOLDOWN_SEC:
            return False
        _early_fill_inflight = True
    threading.Thread(target=_stall_fill_worker, name="qtw-stall-fill", daemon=True).start()
    return True


def _watchdog_rest_fill(*, stalled: bool) -> int:
    """Fill stale marks after a watchdog decision.

    Stall path: kick a **background** sync fill (loop may be dead). The
    watchdog thread itself must return immediately — a 32-quote REST round
    trip used to pin this thread for several seconds so the next stall
    tick (and socket abort) could not run.
    Healthy path: schedule async fill on the live stream loop.
    """
    if not stalled:
        _schedule_rest_fill_from_watchdog()
        return 0
    return 1 if _spawn_stall_fill() else 0


async def _rest_fallback(symbols):
    """WS 价格过期（>20 秒）时，用官方公共 REST 拉取真实报价；失败只记录错误。"""
    while True:
        await asyncio.sleep(10)
        try:
            cfg = await _load_settings()
            pref = cfg.get("venue")
        except Exception:  # noqa: BLE001
            pref = None
        await _rest_fill_stale(symbols, preferred_venue=pref)


def _ws_raw_socket(ws):
    """Best-effort TCP socket under a websockets ClientConnection / transport."""
    transport = getattr(ws, "transport", None)
    getter = getattr(transport, "get_extra_info", None) if transport is not None else None
    if callable(getter):
        try:
            sock = getter("socket")
            if sock is not None:
                return sock
        except Exception:  # noqa: BLE001
            pass
    return getattr(ws, "socket", None)


def _shutdown_ws_socket(ws, name: str) -> bool:
    """Thread-safe kernel shutdown so a wedged peer unblocks without touching SSLProtocol."""
    sock = _ws_raw_socket(ws)
    if sock is None:
        return False
    try:
        sock.shutdown(socket.SHUT_RDWR)
        return True
    except Exception:
        try:
            sock.close()
            return True
        except Exception as e:  # noqa: BLE001
            log.info("%s zombie socket shutdown: %s", name, type(e).__name__)
            return False


def _abort_transport_only(ws, name: str) -> bool:
    """Call transport.abort() (must run on the stream loop when the loop is alive)."""
    transport = getattr(ws, "transport", None)
    try:
        if transport is not None and not transport.is_closing():
            transport.abort()
            return True
    except Exception as e:  # noqa: BLE001
        log.info("%s zombie abort: %s", name, type(e).__name__)
    return False


def _on_stream_loop() -> bool:
    loop = _loop
    if loop is None:
        return False
    try:
        return asyncio.get_running_loop() is loop
    except RuntimeError:
        return False


def _abort_ws_transport_sync(ws, name: str, *, reason: str = "zombie: forced close") -> bool:
    """Hard-abort a websocket transport without awaiting (safe from watchdog thread).

    Returns True if the socket was hard-stopped (raw-socket shutdown and/or
    transport.abort). Always flips status to reconnecting and drops
    ``_ws_refs[name]`` when it still points at ``ws``.

    websockets 15 ``ClientConnection`` stores ``transport`` as an instance
    attribute (set in ``connection_made``); class ``dir()`` does not list it.

    Do **not** call ``set_recv_exc`` / ``recv_messages.close()`` from this
    helper. ``Assembler.close()`` makes a later ``put()`` raise ``EOFError``
    ("stream of frames ended"). When that happens inside
    ``SSLProtocol._do_read`` → ``data_received`` (the loop may still be
    delivering a buffered frame after a cross-thread abort), asyncio logs
    ``Fatal error on SSL protocol`` and the SSL stack can wedge — observed
    2026-11-10 07:11 CST+8, followed by a 98s loop stall at 07:12. The
    assembler is closed correctly by ``connection_lost`` after abort.

    From the watchdog thread: shutdown the raw TCP socket (kernel-level,
    thread-safe) and schedule ``transport.abort()`` on the stream loop via
    ``call_soon_threadsafe``. Direct ``transport.abort()`` only when we are
    already on that loop, or no loop is running (tests / dead loop).
    When abort is unavailable, schedule an async ``close()`` as a fallback.
    """
    _conn_state(name, status="reconnecting", last_error=reason)
    if _ws_refs.get(name) is ws:
        _ws_refs.pop(name, None)
    stopped = _shutdown_ws_socket(ws, name)
    if _on_stream_loop():
        stopped = _abort_transport_only(ws, name) or stopped
    else:
        loop = _loop
        if loop is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(_abort_transport_only, ws, name)
                stopped = True
            except Exception as e:  # noqa: BLE001
                log.info("%s zombie abort schedule: %s", name, type(e).__name__)
                stopped = _abort_transport_only(ws, name) or stopped
        else:
            stopped = _abort_transport_only(ws, name) or stopped
    if not stopped:
        loop = _loop
        if loop is not None and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(_close_ws_quietly(ws), loop)
                stopped = True
            except Exception as e:  # noqa: BLE001
                log.info("%s zombie close schedule: %s", name, type(e).__name__)
    return stopped


async def _force_close_ws(ws, name: str) -> None:
    """Hard-stop a zombie socket so `_run_ws` exits into its reconnect loop.

    Half-open peers often never finish the WebSocket close handshake. A plain
    ``await wait_for(ws.close(), …)`` can cancel the close coroutine *before*
    websockets aborts the TCP transport, leaving ``recv()`` blocked and
    reconnects stuck at 0 while the supervisor spends ~3s per socket.
    Prefer ``transport.abort()`` (instant), with a short close() fallback.
    """
    if _abort_ws_transport_sync(ws, name, reason="zombie: forced close"):
        return
    try:
        await asyncio.wait_for(ws.close(), 0.5)
    except Exception as e:  # noqa: BLE001
        log.info("%s zombie close: %s", name, type(e).__name__)
        try:
            transport = getattr(ws, "transport", None)
            if transport is not None and not transport.is_closing():
                transport.abort()
        except Exception:  # noqa: BLE001
            pass


def _schedule_rest_fill_from_watchdog() -> None:
    """Ask the stream loop to REST-fill stale marks after a side-thread abort."""
    syms = list(_watch_symbols)
    pref = _watch_venue
    loop = _loop
    if not syms or loop is None or not loop.is_running():
        return
    try:
        fut = asyncio.run_coroutine_threadsafe(
            _rest_fill_stale(syms, preferred_venue=pref),
            loop,
        )
    except Exception:  # noqa: BLE001
        log.exception("watchdog REST fill schedule failed")
        return

    def _done(f):
        try:
            n = f.result()
            if n:
                log.info("watchdog: REST filled %d stale quotes", n)
        except Exception:  # noqa: BLE001
            log.exception("watchdog REST fill failed")

    fut.add_done_callback(_done)


def _watchdog_tick() -> int:
    """Abort zombies from a side thread when the asyncio supervisor cannot.

    If the loop heartbeat is fresh, give the in-loop kicker
    ``WATCHDOG_GRACE_SEC`` after ``ZOMBIE_SEC`` so we do not race a healthy
    supervisor. When the heartbeat is stale (loop stall) or a zombie survives
    past that grace window, abort transports immediately.

    Stall path uses ``STALL_ZOMBIE_SEC`` (shorter than ``ZOMBIE_SEC``) so a
    frozen loop recovers sockets in ~30s instead of waiting a full quiet
    window, and starts a **background** REST gap-fill (not on this thread)
    so paper marks do not depend on the frozen asyncio loop *and* this
    watchdog can keep scanning. A wedged ``rest_fill_inflight`` older than
    ``FILLING_STALL_SEC`` drops the filling shield (depth can stick if the
    fill task never runs finally on a dead loop).
    """
    global _stall_suspect_count
    now = time.time()
    hb = _loop_heartbeat
    hb_age = (now - hb) if hb else None
    # A long official REST gap-fill yields on the event loop but can leave the
    # supervisor heartbeat idle for > LOOP_STALL_SEC. That is not a frozen loop —
    # aborting mid-reconnect just recreates zombies. True zombies past
    # ZOMBIE+grace are still kicked below. If depth stays raised past
    # FILLING_STALL_SEC the fill itself is wedged — treat as stall.
    filling = _rest_fill_depth > 0
    fill_age = (now - _rest_fill_started_at) if (filling and _rest_fill_started_at) else None
    filling_wedged = bool(filling and fill_age is not None and fill_age > FILLING_STALL_SEC)
    if filling_wedged:
        filling = False
        log.warning(
            "rest_fill_inflight wedged (%.0fs > %.0fs); dropping fill shield",
            fill_age, FILLING_STALL_SEC,
        )
    stalled = (not filling) and (hb_age is None or hb_age > LOOP_STALL_SEC)
    age_floor = STALL_ZOMBIE_SEC if stalled else ZOMBIE_SEC
    with _lock:
        rows = [(n, dict(st)) for n, st in _conns.items()]
    jobs: list[tuple[str, object, float]] = []
    for name, st in rows:
        if st.get("status") != "connected":
            continue
        age = _activity_age_sec(st, now)
        if age is None or age <= age_floor:
            continue
        if not stalled and age <= ZOMBIE_SEC + WATCHDOG_GRACE_SEC:
            continue
        ws = _ws_refs.get(name)
        if ws is None:
            _conn_state(name, status="reconnecting", last_error="zombie: no live socket ref")
            continue
        jobs.append((name, ws, age))
    # Even before sockets cross the zombie floor: if the loop heartbeat is dead,
    # REST-fill marks from THIS thread so the paper book does not wait on a
    # frozen asyncio loop (run_coroutine_threadsafe would only queue work).
    if stalled and not jobs:
        _watchdog_rest_fill(stalled=True)
        return 0
    if not jobs:
        return 0
    if stalled:
        _stall_suspect_count += 1
        log.warning(
            "stream loop stall suspected (heartbeat %s); watchdog aborting %d zombie(s) [stall#%d]",
            f"{hb_age:.0f}s old" if hb_age is not None else "missing",
            len(jobs),
            _stall_suspect_count,
        )
    _note_zombie_kick([age for _, _, age in jobs])
    for name, ws, age in jobs:
        log.warning(
            "%s zombie (last_msg %.0fs ago > %ss), watchdog forcing abort",
            name, age, age_floor,
        )
        _abort_ws_transport_sync(ws, name, reason="zombie: watchdog abort")
    _watchdog_rest_fill(stalled=stalled)
    return len(jobs)


def _note_watchdog_gap(prev: float, now: float) -> bool:
    """Record a host/process freeze when the watchdog itself missed ticks.

    Returns True when ``now - prev`` exceeds ``HOST_FREEZE_GAP_SEC``.
    """
    global _host_freeze_count, _last_host_freeze_at, _last_host_freeze_gap_sec
    if not prev:
        return False
    gap = now - prev
    if gap <= HOST_FREEZE_GAP_SEC:
        return False
    _host_freeze_count += 1
    _last_host_freeze_at = now
    _last_host_freeze_gap_sec = round(gap, 1)
    log.warning(
        "host/process freeze detected: watchdog idle %.0fs (> %.0fs) [freeze#%d]; "
        "following stall recovery is resume-after-freeze, not a stream bug",
        gap, HOST_FREEZE_GAP_SEC, _host_freeze_count,
    )
    for cb in list(_on_host_freeze):
        try:
            cb(gap)
        except Exception:  # noqa: BLE001
            log.exception("host-freeze callback failed")
    return True


def _watchdog_main() -> None:
    last = time.time()
    while not _stop.wait(WATCHDOG_INTERVAL_SEC):
        now = time.time()
        _note_watchdog_gap(last, now)
        last = now
        try:
            _watchdog_tick()
        except Exception:  # noqa: BLE001
            log.exception("stream watchdog tick failed")


async def _kick_zombies(symbols: list[str] | None = None, *, preferred_venue: str | None = None) -> int:
    """Close sockets that look connected but have been silent past ZOMBIE_SEC.

    recv/grace should already reconnect; this is a safety net when the library
    recv wait never returns while the event loop is otherwise healthy.
    Kicks run in parallel so one hung close cannot stall the other three.
    After a kick, immediately REST-fill stale marks (active venue first) so the
    paper book does not wait for the next 10s fallback tick during reconnect.
    """
    now = time.time()
    with _lock:
        rows = [(n, dict(st)) for n, st in _conns.items()]
    jobs = []
    for name, st in rows:
        if st.get("status") != "connected":
            continue
        age = _activity_age_sec(st, now)
        if age is None or age <= ZOMBIE_SEC:
            continue
        ws = _ws_refs.get(name)
        if ws is None:
            # Still mark reconnecting so mode leaves "rest"/stale if the task
            # is wedged without a live socket ref.
            _conn_state(name, status="reconnecting", last_error="zombie: no live socket ref")
            continue
        log.warning("%s zombie (last_msg %.0fs ago > %ss), forcing socket close", name, age, ZOMBIE_SEC)
        jobs.append((_force_close_ws(ws, name), age))
    if jobs:
        _note_zombie_kick([a for _, a in jobs])
        await asyncio.gather(*[j for j, _ in jobs], return_exceptions=True)
        if symbols:
            try:
                n = await _rest_fill_stale(symbols, preferred_venue=preferred_venue)
                if n:
                    log.info("zombie kick: REST filled %d stale quotes", n)
            except Exception:  # noqa: BLE001
                log.exception("zombie kick REST fill failed")
    return len(jobs)


async def _load_settings():
    """Load settings off the WS event loop so a contended SQLite lock cannot freeze recv/ping."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_ensure_io_pool(), S.load)


def _market_ws_coros(symbols, interval):
    """Build the live WS + REST-fallback coroutines for the supervisor."""
    global _okx_ws_disabled_current
    coros = []
    disabled = env_flag("QTW_DISABLE_OKX_WS")
    _okx_ws_disabled_current = disabled
    if disabled:
        log.info("QTW_DISABLE_OKX_WS=1：不连接 OKX WebSocket，OKX 价格走官方 REST 轮询；Gate 不受影响")
    else:
        coros.extend(_okx_tasks(symbols, interval))
    coros.extend(_gate_tasks(symbols, interval))
    coros.append(_rest_fallback(symbols))
    return coros


async def _supervisor():
    global _loop_heartbeat, _watch_symbols, _watch_venue
    cur, tasks = None, []
    syms: list[str] = []
    while not _stop.is_set():
        # S.load() hits SQLite under db._LOCK. Paper save / candle upsert / WAL
        # checkpoint can hold that lock for seconds; doing it inline here used to
        # stall the whole stream loop so all four sockets looked connected while
        # last_msg aged well past ZOMBIE_SEC (zombie kick only runs after load).
        cfg = await _load_settings()
        want = (tuple(cfg["symbols"]), cfg["strategy"]["interval"])
        if want != cur:
            for t in tasks:
                t.cancel()
            with _lock:
                _conns.clear()
                _forming.clear()
                _ws_refs.clear()
            syms, interval = list(want[0]), want[1]
            proxy = resolve_proxy()
            if proxy:
                log.info("行情 WebSocket / REST 将使用代理 %s", redact_proxy(proxy))
            coros = _market_ws_coros(syms, interval)
            tasks = [asyncio.create_task(c) for c in coros]
            cur = want
            if _okx_ws_disabled_current:
                log.info("实时行情订阅：%d 个标的 · %s · Gate WebSocket + OKX REST（已关闭 OKX WS）", len(syms), interval)
            else:
                log.info("实时行情订阅：%d 个标的 · %s · OKX + Gate（现货 + 永续）", len(syms), interval)
        _watch_symbols = list(syms)
        _watch_venue = cfg.get("venue")
        _loop_heartbeat = time.time()
        await _kick_zombies(syms, preferred_venue=_watch_venue)
        # Interruptible sleep so stop() can end the supervisor without waiting a full 5s.
        # Refresh heartbeat each slice so a healthy loop is never mistaken for stalled.
        for _ in range(50):
            if _stop.is_set():
                break
            _loop_heartbeat = time.time()
            await asyncio.sleep(0.1)
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    with _lock:
        _conns.clear()
        _forming.clear()
        _ws_refs.clear()
    log.info("实时行情 supervisor 已停止")


def start():
    global _thread, _loop, _watchdog_thread, _loop_heartbeat
    _ensure_cb_dispatcher()
    _ensure_io_pool()
    if not (_thread and _thread.is_alive()):
        _stop.clear()
        _loop_heartbeat = time.time()

        def run():
            global _loop
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
            try:
                _loop.run_until_complete(_supervisor())
            finally:
                try:
                    _loop.close()
                except Exception:  # noqa: BLE001
                    pass
                _loop = None

        _thread = threading.Thread(target=run, name="qtw-stream", daemon=True)
        _thread.start()
    # Always (re)attach watchdog even when the stream thread was already up —
    # a dead watchdog used to leave zombies until the in-loop kicker finally ran.
    if not (_watchdog_thread and _watchdog_thread.is_alive()):
        _watchdog_thread = threading.Thread(target=_watchdog_main, name="qtw-stream-watchdog", daemon=True)
        _watchdog_thread.start()


def stop(timeout: float = 3.0) -> None:
    """Ask the stream supervisor + watchdog to exit (used by FastAPI lifespan shutdown)."""
    _stop.set()
    _cb_stop.set()
    if _cb_queue is not None:
        try:
            _cb_queue.put_nowait(None)
        except Exception:  # noqa: BLE001
            pass
    t = _thread
    if t and t.is_alive():
        t.join(timeout=timeout)
    w = _watchdog_thread
    if w and w.is_alive():
        w.join(timeout=min(timeout, 1.5))
    c = _cb_thread
    if c and c.is_alive():
        c.join(timeout=min(timeout, 1.0))
    pool = _io_pool
    if pool is not None:
        # Do not wait on in-flight HTTP; process exit / next start creates a fresh pool.
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            pool.shutdown(wait=False)
        globals()["_io_pool"] = None


def interval_ms(interval: str) -> int:
    return INTERVAL_MS[interval]
