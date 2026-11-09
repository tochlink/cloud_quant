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
  * 状态 mode 带迟滞：WS 断线重连 / 报价短暂被 REST 填隙时标为 recovering，不立刻翻成 rest，避免 UI 误报「REST 兜底」。
  * 拿不到就报错 / 标记过期，绝不编造价格；永续价格只来自永续频道，现货只来自现货频道。
"""
from __future__ import annotations

import asyncio
import json
import logging
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
# connected + last_msg older than this → report as stale (recv/grace should have
# reconnected already; if the event loop was blocked, status must not lie).
ZOMBIE_SEC = RECV_WAIT_SEC * 2 + PING_EVERY_SEC  # 70

_lock = threading.RLock()
_quotes: dict[tuple, Quote] = {}
_forming: dict[tuple, dict] = {}
_conns: dict[str, dict] = {}
_version = 0
_thread: threading.Thread | None = None
_loop: asyncio.AbstractEventLoop | None = None
_rest_errors: dict[str, str] = {}
_on_quote = []  # 回调：用于给纸面持仓实时计价
_last_ws_at: float = 0.0  # monotonic-ish wall time of last *_ws quote


def _bump():
    global _version
    _version += 1


def version() -> int:
    return _version


def _put(q: Quote):
    global _last_ws_at
    with _lock:
        _quotes[(q.venue.lower(), q.symbol, q.market)] = q
        if q.data_source.endswith("_ws"):
            _last_ws_at = time.time()
        _bump()
    for cb in _on_quote:
        try:
            cb(q)
        except Exception:  # noqa: BLE001
            log.exception("quote callback failed")


def on_quote(cb):
    _on_quote.append(cb)


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


def annotate_conn(conn: dict, *, now: float | None = None, zombie_sec: float = ZOMBIE_SEC) -> dict:
    """Copy a connection row and mark zombie sockets as status=stale for API/UI."""
    c = dict(conn)
    age = _last_msg_age_sec(c, now)
    if age is not None:
        c["last_msg_age_sec"] = round(age, 1)
    if c.get("status") == "connected" and (age is None or age > zombie_sec):
        c["status"] = "stale"
    return c


def status() -> dict:
    with _lock:
        raw = [dict(v) for v in _conns.values()]
        now = time.time()
        q = list(_quotes.values())
        last_ws = _last_ws_at
    conns = [annotate_conn(c, now=now) for c in raw]
    live = sum(1 for x in q if x.data_source.endswith("_ws") and (now - x.ts.timestamp()) < STALE_SEC)
    rest = sum(1 for x in q if x.data_source.endswith("_rest") and (now - x.ts.timestamp()) < 60)
    # stale sockets must not count as "up" or we keep advertising a live WS path
    up = sum(1 for c in conns if c["status"] == "connected")
    trying = sum(1 for c in conns if c["status"] in ("connected", "reconnecting", "connecting"))
    recent_ws = bool(last_ws) and (now - last_ws) < WS_MODE_HOLD_SEC
    mode = classify_mode(live=live, rest=rest, up=up, trying=trying, recent_ws=recent_ws)
    return {"mode": mode, "connections": conns, "quotes_ws_fresh": live, "quotes_rest_fresh": rest,
            "quotes_total": len(q), "rest_errors": dict(_rest_errors), "running": bool(_thread and _thread.is_alive())}


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
    loop.run_in_executor(None, _store_closed_sync, args)


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
    """Refresh last_msg so status/UI see pongs as well as market data."""
    ts = iso(utcnow())
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


async def _run_ws(name, urls, subscribe_msgs, handle, ping):
    import websockets
    backoff, i = 1.0, 0
    while True:
        url = urls[i % len(urls)]
        was_connected = False
        _conn_state(name, status="connecting", url=url)
        try:
            # Keep library protocol ping disabled: OKX/Gate use app-level ping/pong
            # and we do not want a second heartbeat to interfere. Quiet stretches
            # are handled by the grace-retry below.
            async with websockets.connect(url, open_timeout=10, ping_interval=None, close_timeout=3, max_size=2**22) as ws:
                for m in subscribe_msgs():
                    await _send(ws, m)
                _conn_state(name, status="connected", connected_at=iso(utcnow()), last_error="")
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


async def _rest_fallback(symbols):
    """WS 价格过期（>20 秒）时，用官方公共 REST 拉取真实报价；失败只记录错误。"""
    loop = asyncio.get_running_loop()
    while True:
        await asyncio.sleep(10)
        for venue in ("okx", "gate"):
            for sym in symbols:
                for mkt in ("spot", "perp"):
                    if latest(venue, sym, mkt, STALE_SEC):
                        continue
                    key = f"{venue}:{sym}:{mkt}"
                    try:
                        q = await loop.run_in_executor(None, get_client(venue).quote, sym, mkt)
                        _put(q)
                        _rest_errors.pop(key, None)
                    except (MarketDataError, Exception) as e:  # noqa: BLE001
                        _rest_errors[key] = str(e)[:200]


async def _supervisor():
    cur, tasks = None, []
    while True:
        cfg = S.load()
        want = (tuple(cfg["symbols"]), cfg["strategy"]["interval"])
        if want != cur:
            for t in tasks:
                t.cancel()
            with _lock:
                _conns.clear()
                _forming.clear()
            syms, interval = list(want[0]), want[1]
            coros = _okx_tasks(syms, interval) + _gate_tasks(syms, interval) + [_rest_fallback(syms)]
            tasks = [asyncio.create_task(c) for c in coros]
            cur = want
            log.info("实时行情订阅：%d 个标的 · %s · OKX + Gate（现货 + 永续）", len(syms), interval)
        await asyncio.sleep(15)


def start():
    global _thread, _loop
    if _thread and _thread.is_alive():
        return

    def run():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop.run_until_complete(_supervisor())

    _thread = threading.Thread(target=run, name="qtw-stream", daemon=True)
    _thread.start()


def interval_ms(interval: str) -> int:
    return INTERVAL_MS[interval]
