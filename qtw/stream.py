"""官方公共 WebSocket 实时行情（无需 API Key）+ REST 轮询兜底。

连接（每个交易所现货 / 永续各一条，外加 OKX K 线 business 通道）：
  OKX  public   wss://ws.okx.com/ws/v5/public（优先 443；被拦时再试 :8443 / wsaws）
       频道：tickers（现货 BTC-USDT…）、mark-price（永续 BTC-USDT-SWAP…）
  OKX  business wss://ws.okx.com/ws/v5/business（优先 443；回退 :8443 / wsaws）  频道：candle4H（现货 + 永续）
  Gate spot     wss://api.gateio.ws/ws/v4/            频道：spot.tickers、spot.candlesticks
  Gate futures  wss://fx-ws.gateio.ws/v4/ws/usdt       频道：futures.tickers（含 mark_price）、futures.candlesticks
规则：
  * 只保存交易所真实推送的数据；收盘确认的 K 线（OKX confirm=1 / Gate w=true）写入 SQLite candles 表，
    data_source = okx_public_ws / gate_public_ws；未收盘 K 线只推给前端图表，不参与信号。
  * 断线指数退避自动重连；某个价格超过 20 秒没有 WS 更新 → 用官方公共 REST 拉取（data_source=*_public_rest）。
  * 应用层心跳：OKX 文本 ping/pong；Gate JSON 的 channel 以 .pong 结尾（不是字符串 "pong"）。二者都视为连接活跃并刷新 last_msg，不交给行情 handle。
    recv 超时后先再发一次 ping 并多等一轮，仍无消息才重连，避免短暂静默导致连接一起抖动。
    发出订阅 / ping 也有超时：半开 TCP 让 send 挂起时会主动重连，避免状态仍是 connected 但 last_msg 数分钟不刷新。
  * 已收盘 K 线写入 SQLite 放到线程池，避免 db 锁/WAL 卡住 asyncio 事件循环，导致四条连接同时假死（status=connected 但 last_msg 数分钟不刷新）。
  * status() 把「已连接但 last_msg 超过 ZOMBIE_SEC」标为 stale，不计入 up，避免 UI 误报实时。
  * status(venue) 的 mode / quotes_ws_fresh / quotes_rest_fresh 只统计该行情源：OKX 标记价全走 REST 时，不会因为 Gate WS 仍新鲜而显示 mode=ws。
  * WebSocket 握手除库自带 open_timeout 外再包一层 wait_for，避免 DNS / 半开 TCP 让状态一直停在 connecting（此时还没有 _ws_refs，僵尸踢除无法中断）。
  * supervisor 每轮检查僵尸连接：last_msg 过旧仍标 connected 时强制中断套接字（优先 transport.abort，避免 close 握手挂起），并行踢掉并标 reconnecting，迫使 _run_ws 走重连；刚连上时写入 last_msg，空 last_msg 则用 connected_at 计龄；踢掉后立刻 REST 填一次标记价，不等 10 秒轮询。
  * supervisor 读配置走线程池（run_in_executor），避免 S.load()/SQLite 锁被纸面写库或 K 线缓存占用时卡住 asyncio，导致四条 WS 同时假死、zombie age 远超 ZOMBIE_SEC。
  * 侧线程 watchdog：supervisor 的僵尸踢除跑在 asyncio 循环内；若事件循环被卡住，踢除本身也无法执行，last_msg 会拖到 90s+。watchdog 独立扫描；循环心跳过旧或僵尸年龄超过 ZOMBIE+宽限时，直接 transport.abort()（websockets 15 ClientConnection 实例属性），并经 call_soon / run_coroutine_threadsafe 触发 REST 填隙；abort 失败时再 threadsafe 调度 close()。start() 在行情线程已存活时也会补拉 watchdog。
  * 报价回调（纸面 mark）不在 asyncio 线程同步执行：经单线程队列派发，避免 PaperBook._LOCK / SQLite 写锁卡住 recv/ping/zombie kick（曾出现 last_msg 龄到 200s+ 而 watchdog 日志缺失的假死）。
  * supervisor / watchdog 踢僵尸时记录 last_zombie_kick_age_sec / last_zombie_max_age_sec，供 /api/health 与打磨例程一眼看出「上次踢除多久前、当时最大静默龄」。
  * REST 填隙用独立线程池 + 短超时报价客户端，并在填隙期间刷新 loop heartbeat；watchdog 在 rest_fill_inflight 时不把心跳迟滞当成 loop stall（仍会踢超过 ZOMBIE+宽限的真僵尸），避免「填隙拖心跳 → 误杀重连中的套接字 → 再填隙」的正反馈。
  * 若 rest_fill_inflight 持续超过 FILLING_STALL_SEC（填隙协程卡在已冻结的 loop 上、depth 无法清零），取消 filling 护盾，按真 stall 处理。
  * `_note_activity`（recv/pong）也刷新 loop heartbeat：supervisor 卡在 S.load/DB 时，只要事件循环仍在处理帧就不误报 stall。
  * 真 stall 时用更短的 STALL_ZOMBIE_SEC 门槛踢套接字，并在尚无僵尸前就调度 REST 填隙，缩短纸面标记价空白窗。
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
import threading
import time
from datetime import datetime, timezone

from . import db
from . import settings as S
from .market.base import INTERVAL_MS, MarketDataError, Quote, get_client
from .timeutil import iso, utcnow

log = logging.getLogger("qtw.stream")

OKX_PUBLIC = ["wss://ws.okx.com/ws/v5/public", "wss://ws.okx.com:8443/ws/v5/public", "wss://wsaws.okx.com/ws/v5/public", "wss://wsaws.okx.com:8443/ws/v5/public"]
OKX_BUSINESS = ["wss://ws.okx.com/ws/v5/business", "wss://ws.okx.com:8443/ws/v5/business", "wss://wsaws.okx.com/ws/v5/business", "wss://wsaws.okx.com:8443/ws/v5/business"]
GATE_SPOT = ["wss://api.gateio.ws/ws/v4/"]
GATE_FUT = ["wss://fx-ws.gateio.ws/v4/ws/usdt"]
OKX_BAR = {"15m": "15m", "1h": "1H", "4h": "4H", "1d": "1Dutc"}
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
_stall_suspect_count = 0  # watchdog mass-abort / stall recoveries (health polish)
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
    if age is not None:
        c["last_msg_age_sec"] = round(age, 1)
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
    out = {"mode": mode, "connections": conns, "quotes_ws_fresh": live, "quotes_rest_fresh": rest,
           "quotes_total": len(q_use), "rest_errors": rest_err, "running": bool(_thread and _thread.is_alive()),
           "watchdog_running": bool(_watchdog_thread and _watchdog_thread.is_alive()),
           "loop_heartbeat_age_sec": round(time.time() - hb, 1) if hb else None,
           "rest_fill_inflight": int(_rest_fill_depth) > 0,
           "stall_suspect_count": int(_stall_suspect_count),
           "last_zombie_kick_age_sec": round(time.time() - kick_at, 1) if kick_at else None,
           "last_zombie_max_age_sec": _last_zombie_max_age_sec}
    if v:
        out["venue"] = v
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
    return {"venue": venue, "prices": prices, "forming": forming}


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
    """
    import websockets
    fn = opener or websockets.connect
    try:
        return await asyncio.wait_for(
            fn(url, open_timeout=OPEN_TIMEOUT_SEC, ping_interval=None, close_timeout=3, max_size=2**22),
            CONNECT_GUARD_SEC,
        )
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


async def _run_ws(name, urls, subscribe_msgs, handle, ping):
    backoff, i = 1.0, 0
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
                backoff, was_connected = 1.0, True
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
            _conn_state(name, status="reconnecting", last_error=f"{type(e).__name__}: {str(e)[:160]}")
            log.info("%s 断开（%s），%.0f 秒后重连", name, type(e).__name__, backoff)
            if not was_connected:
                i += 1  # 这个地址连不上就换下一个官方地址；连上过的地址断线后先原地重连
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


def _host(url):
    return url.split("/")[2]


def _okx_tasks(symbols, interval):
    spot = [f"{s[:-4]}-USDT" for s in symbols]
    swap = [f"{s[:-4]}-USDT-SWAP" for s in symbols]
    rev = {**{a: (s, "spot") for a, s in zip(spot, symbols)}, **{a: (s, "perp") for a, s in zip(swap, symbols)}}
    bar = OKX_BAR[interval]

    def sub_pub():
        args = [{"channel": "tickers", "instId": x} for x in spot] + [{"channel": "mark-price", "instId": x} for x in swap]
        return [json.dumps({"op": "subscribe", "args": args})]

    def sub_bus():
        return [json.dumps({"op": "subscribe", "args": [{"channel": f"candle{bar}", "instId": x} for x in spot + swap]})]

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
        sym, mkt = rev.get(m.get("arg", {}).get("instId"), (None, None))
        for d in m.get("data", []) or []:
            if not sym:
                continue
            closed = len(d) > 8 and str(d[8]) == "1"
            _forming_put("okx", mkt, sym, interval, d[0], d[1], d[2], d[3], d[4], closed, "okx_public_ws")
            if closed:
                _store_closed("okx", mkt, sym, interval, d[0], d[1], d[2], d[3], d[4], d[5], "okx_public_ws", _host(url))

    _conn_state("okx_public", channels=["tickers(spot)", "mark-price(swap)"])
    _conn_state("okx_business", channels=[f"candle{bar}(spot+swap)"])
    return [_run_ws("okx_public", OKX_PUBLIC, sub_pub, h_pub, lambda: "ping"),
            _run_ws("okx_business", OKX_BUSINESS, sub_bus, h_bus, lambda: "ping")]


def _gate_tasks(symbols, interval):
    pairs = [f"{s[:-4]}_USDT" for s in symbols]
    rev = dict(zip(pairs, symbols))

    def subs(prefix):
        def f():
            t = int(time.time())
            out = [json.dumps({"time": t, "channel": f"{prefix}.tickers", "event": "subscribe", "payload": pairs})]
            out += [json.dumps({"time": t, "channel": f"{prefix}.candlesticks", "event": "subscribe", "payload": [interval, p]})
                    for p in pairs]
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
                    closed = bool(r.get("w"))
                    om = int(r["t"]) * 1000
                    _forming_put("gate", market, sym, interval, om, r["o"], r["h"], r["l"], r["c"], closed, "gate_public_ws")
                    if closed:
                        _store_closed("gate", market, sym, interval, om, r["o"], r["h"], r["l"], r["c"], r.get("a") or r.get("v") or 0,
                                      "gate_public_ws", _host(url))
        return h

    _conn_state("gate_spot", channels=["spot.tickers", f"spot.candlesticks({interval})"])
    _conn_state("gate_futures", channels=["futures.tickers(mark_price)", f"futures.candlesticks({interval})"])
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
    global _rest_fill_depth, _rest_fill_started_at
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
    _rest_fill_depth += 1
    if _rest_fill_depth == 1:
        _rest_fill_started_at = time.time()
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
        _rest_fill_depth = max(0, _rest_fill_depth - 1)
        if _rest_fill_depth == 0:
            _rest_fill_started_at = 0.0
        _bump_loop_heartbeat()


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


def _abort_ws_transport_sync(ws, name: str, *, reason: str = "zombie: forced close") -> bool:
    """Hard-abort a websocket transport without awaiting (safe from watchdog thread).

    Returns True if the socket was hard-stopped (transport.abort and/or
    recv wakeup). Always flips status to reconnecting and drops
    ``_ws_refs[name]`` when it still points at ``ws``.

    websockets 15 ``ClientConnection`` stores ``transport`` as an instance
    attribute (set in ``connection_made``); class ``dir()`` does not list it.
    When abort is unavailable, poke ``set_recv_exc`` + ``recv_messages.close``
    and schedule an async ``close()`` on the stream loop as a fallback.
    """
    _conn_state(name, status="reconnecting", last_error=reason)
    if _ws_refs.get(name) is ws:
        _ws_refs.pop(name, None)
    stopped = False
    transport = getattr(ws, "transport", None)
    try:
        if transport is not None and not transport.is_closing():
            transport.abort()
            stopped = True
    except Exception as e:  # noqa: BLE001
        log.info("%s zombie abort: %s", name, type(e).__name__)
    # Wake a hung recv() even when transport.abort is missing/noop.
    try:
        set_exc = getattr(ws, "set_recv_exc", None)
        if set_exc is not None:
            set_exc(ConnectionError(reason))
            stopped = True
        recv_messages = getattr(ws, "recv_messages", None)
        close_asm = getattr(recv_messages, "close", None) if recv_messages is not None else None
        if close_asm is not None:
            close_asm()
            stopped = True
    except Exception as e:  # noqa: BLE001
        log.info("%s zombie recv wake: %s", name, type(e).__name__)
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
    frozen loop recovers paper marks in ~30s instead of waiting a full quiet
    window. A wedged ``rest_fill_inflight`` older than ``FILLING_STALL_SEC``
    drops the filling shield (depth can stick if the fill task never runs
    finally on a dead loop).
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
    # REST-fill marks so the paper book does not sit on multi-minute blanks.
    if stalled and not jobs:
        _schedule_rest_fill_from_watchdog()
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
    _schedule_rest_fill_from_watchdog()
    return len(jobs)


def _watchdog_main() -> None:
    while not _stop.wait(WATCHDOG_INTERVAL_SEC):
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
            coros = _okx_tasks(syms, interval) + _gate_tasks(syms, interval) + [_rest_fallback(syms)]
            tasks = [asyncio.create_task(c) for c in coros]
            cur = want
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
