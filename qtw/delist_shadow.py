"""影子子账本 #15 binance_delist_short_1h：币安官方现货下架公告 → 做空该币 USDT 永续，持有 24 小时（只记录，纸面）。

* 默认关闭（可选策略）；只有进程环境变量 QTW_SHADOW_DELIST=1 时才启动轮询线程（本机只在 8788 paper-default 打开）。
  测试 / 安全模式（QTW_FORBID_LIVE=1）下永不启动、不访问网络。
* 不碰默认 1000U 账本（engine._BOOK）、不下任何真实 / 交易所模拟单、不经过实盘闸门。
* 信号源：币安官方 CMS 公告列表（catalog 161 Delisting，bapi/composite/v1/public/cms/article/list/query），
  每 POLL_SEC 秒轮询一次；标题解析与研究脚本 scratch/bnbannounce1h/parse.py 的 spot_delist 完全相同：
  「^Binance Will Delist <币1>, <币2> and <币3> on <日期>」，标题含 Margin / Futures 的不算。
* 入场：releaseDate + 60 秒之后的第一次轮询；对每个点名的币，若 OKX 有 live 的 <币>-USDT-SWAP 且上线 ≥ 24h（主场所），
  否则 Gate 有 <币>_USDT 永续且上线 ≥ 24h、未在下架流程中，就按该场所官方实时价（标记价）开纸面空单；
  每条公告预算 EVENT_BUDGET（权益比例）在可交易币之间等权；同一币已有持仓不重复开；无永续的币记日志跳过。
  发现时已晚于 releaseDate MAX_LATE_SEC（例如重启 / 首次启动时看到的旧公告）不补开，只记「已过时」。
* 离场：开仓满 HOLD_SEC（24h）后的第一次检查（每 CHECK_SEC 秒），按同一场所官方实时价平仓。
* 费用：taker FEE_RATE（5.1 bps）每边；资金费不计（与 #13 / #14 影子一致，文档里说明）。
数据存 SQLite 表 shadow_books（sid = binance_delist_short_1h，与 #13 / #14 同一结构，data/，不入库）。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.request

from . import logtable as LT
from .timeutil import iso, utcnow

log = logging.getLogger(__name__)

SID = "binance_delist_short_1h"
NO = 15
NAME = "币安官方现货下架公告做空（短线 1h，影子）"
START_EQ = 1000.0
POLL_SEC = 300          # 公告轮询间隔
CHECK_SEC = 60          # 到期平仓 / 标记价检查间隔
ENTRY_DELAY_MS = 60_000  # releaseDate + 60s 之后才入场（与回测 entry = 首根 open_time ≥ release+60s 同口径）
MAX_LATE_SEC = 2 * 3600  # 晚于发布 2h 才发现就不补开（研究：一半收益在前 1–2h）
HOLD_SEC = 24 * 3600
MIN_HISTORY_SEC = 24 * 3600
EVENT_BUDGET = 0.20     # 每条公告名义 = 0.2 × 当前权益，在可交易币之间等权
MAX_GROSS = 1.0         # 本账全部持仓名义上限 = 1.0 × 权益
FEE_RATE = 0.00051      # taker 5.1 bps / 边
CATALOG = 161
LIST_URL = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId={c}&pageNo=1&pageSize=20"
STOP = {"USDT", "USDC", "BUSD", "BTC", "ETH", "BNB", "FDUSD", "TRY", "EUR", "USD", "USDS", "COIN", "M", "S", "II"}
OPEN_HEADERS = ["币种", "方向", "金额(U)", "开仓价"]
CLOSE_HEADERS = ["币种", "方向", "开仓价", "平仓价", "盈亏(U)"]

_LOCK = threading.RLock()
_STATE: dict = {"book": None, "thread": None, "running": False, "last_poll": None, "last_error": "", "polls": 0}
_STOP = threading.Event()


# ---------------------------------------------------------------- 解析（与 parse.py 一致）
def _norm(t: str) -> str:
    t = t.upper()
    return re.sub(r"^(1000000|1000|1M)(?=[A-Z])", "", t)


def parse_title(title: str) -> list[str]:
    """spot_delist 标题 → 币列表；不是现货下架公告返回 []。"""
    ti = (title or "").strip()
    if not re.match(r"^Binance Will Delist ", ti) or "Margin" in ti or "Futures" in ti:
        return []
    body = re.sub(r" on \d{4}-\d{2}-\d{2}.*$", "", ti[len("Binance Will Delist "):])
    toks = [t.strip() for t in re.split(r",| and |&", body) if t.strip()]
    toks = [_norm(t) for t in toks if re.fullmatch(r"[A-Za-z0-9]{2,12}", t)]
    return [t for t in dict.fromkeys(toks) if t not in STOP]


# ---------------------------------------------------------------- 账本
def new_book() -> dict:
    return {"sid": SID, "start_equity": START_EQ, "realized": START_EQ, "positions": {}, "blocked": {}, "trades": [],
            "fees": 0.0, "created_at": iso(utcnow()), "last_decision": None, "venue": "okx", "marks": {},
            "seen": [], "events": [], "skips": []}


def equity(b: dict) -> float:
    u = 0.0
    for s, p in b["positions"].items():
        m = float((b["marks"].get(s) or {}).get("px", p["entry"]))
        u += (1 if p["side"] == "long" else -1) * p["qty"] * (m - p["entry"])
    return b["realized"] + u


def _iso_ms(ms: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def step_entries(b: dict, articles: list[dict], now_ms: int, resolve, price) -> dict:
    """处理一批公告（{id, title, releaseDate}）。resolve(coin, release_ms) → (venue, symbol) 或 None；
    price(venue, symbol) → 官方实时价。返回 {"open": [...], "skip": [...], "stale": [...], "wait": [...]}。纯函数式，可离线测试。"""
    out = {"open": [], "skip": [], "stale": [], "wait": []}
    seen = set(str(x) for x in b.get("seen", []))
    for a in sorted(articles, key=lambda x: int(x.get("releaseDate") or 0)):
        aid = str(a.get("id"))
        if aid in seen:
            continue
        rel = int(a.get("releaseDate") or 0)
        coins = parse_title(a.get("title", ""))
        if not coins:
            seen.add(aid)
            continue
        if now_ms < rel + ENTRY_DELAY_MS:
            out["wait"].append(aid)  # 还没到 release+60s，下次轮询再看（不标记 seen）
            continue
        seen.add(aid)
        late = (now_ms - rel) / 1000.0
        if late > MAX_LATE_SEC:
            out["stale"].append([aid, a.get("title", ""), round(late)])
            b.setdefault("skips", []).append({"id": aid, "title": a.get("title", ""), "reason": f"发现时已晚 {late / 3600:.1f}h，不补开",
                                              "at": _iso_ms(now_ms)})
            continue
        tradable = []
        for c in coins:
            sym = f"{c}USDT"
            if sym in b["positions"]:
                out["skip"].append([c, "同币已有持仓，不重复开"])
                continue
            r = resolve(c, rel)
            if not r:
                out["skip"].append([c, "OKX / Gate 无上线 ≥24h 的 USDT 永续"])
                continue
            tradable.append((c, r[0], r[1]))
        ev = {"id": aid, "title": a.get("title", ""), "release": _iso_ms(rel), "detected": _iso_ms(now_ms),
              "delay_sec": round(late, 1), "coins": coins, "traded": [t[2] for t in tradable]}
        b.setdefault("events", []).append(ev)
        if not tradable:
            continue
        eq = equity(b)
        gross = sum(p["notional"] for p in b["positions"].values())
        budget = min(EVENT_BUDGET * eq, max(0.0, MAX_GROSS * eq - gross))
        per = budget / len(tradable)
        if per <= 1.0:
            for c, _, _ in tradable:
                out["skip"].append([c, "总敞口已满"])
            continue
        for c, venue, sym in tradable:
            try:
                px = float(price(venue, sym))
            except Exception as e:  # noqa: BLE001
                out["skip"].append([c, f"取价失败 {e}"])
                continue
            if not px > 0:
                out["skip"].append([c, "价格无效"])
                continue
            f = per * FEE_RATE
            b["realized"] -= f
            b["fees"] += f
            b["positions"][sym] = {"symbol": sym, "side": "short", "market": "perp", "qty": per / px, "entry": px,
                                   "stop": None, "notional": per, "fee_in": f, "entry_time": _iso_ms(now_ms),
                                   "entry_src": f"{venue}_public/mark", "venue": venue, "strategy": SID,
                                   "signal_bar": _iso_ms(rel), "late_bars": 0, "ann_id": aid,
                                   "entry_delay_sec": round(late, 1), "exit_due_ms": now_ms + HOLD_SEC * 1000}
            b["marks"][sym] = {"px": px, "t": _iso_ms(now_ms)}
            out["open"].append([sym, "开空·永续", f"{per:.1f}", f"{px:.6g}", venue, round(late)])
    b["seen"] = sorted(seen)[-500:]
    return out


def step_exits(b: dict, now_ms: int, price) -> list[list]:
    """持满 24h 的仓按官方实时价平仓；返回平仓表格行。取价失败的留到下次检查。"""
    rows = []
    for s in list(b["positions"]):
        p = b["positions"][s]
        if now_ms < int(p["exit_due_ms"]):
            continue
        try:
            px = float(price(p["venue"], s))
        except Exception as e:  # noqa: BLE001
            log.warning("#15 %s 平仓取价失败，下次再试：%s", s, e)
            continue
        if not px > 0:
            continue
        b["positions"].pop(s)
        d = 1 if p["side"] == "long" else -1
        f = abs(p["qty"] * px) * FEE_RATE
        g = d * p["qty"] * (px - p["entry"])
        b["realized"] += g - f
        b["fees"] += f
        pnl = g - f - p["fee_in"]
        b["marks"].pop(s, None)
        b["trades"].append({**p, "exit_time": _iso_ms(now_ms), "exit_price": px, "exit_reason": "持有期满 24h",
                            "exit_src": f"{p['venue']}_public/mark", "fee_out": f, "pnl_usdt": pnl,
                            "return_pct": pnl / p["notional"] if p["notional"] else 0.0, "status": "closed"})
        rows.append([s, "平空·永续", f"{p['entry']:.6g}", f"{px:.6g}", f"{pnl:+.2f}"])
    return rows


def log_text(out: dict, closes: list[list]) -> str:
    tag = f"影子子账本 {SID}（#{NO}，不计入主账本）"
    parts = []
    if closes:
        parts.append(LT.block(f"{tag} 平仓", CLOSE_HEADERS, closes))
    if out.get("open"):
        parts.append(LT.block(f"{tag} 开仓", OPEN_HEADERS, [r[:4] for r in out["open"]]))
        parts.append("\n" + "；".join(f"{r[0]} 场所 {r[4]}，入场比公告发布晚 {r[5]} 秒" for r in out["open"]))
    for c, why in out.get("skip") or []:
        parts.append(f"\n{LT.stamp()} {tag}：{c} 跳过（{why}）")
    for aid, ti, late in out.get("stale") or []:
        parts.append(f"\n{LT.stamp()} {tag}：公告 {aid}「{ti}」发现时已晚 {late} 秒，超过 {MAX_LATE_SEC} 秒，不补开")
    return "".join(parts)


# ---------------------------------------------------------------- 网络（只在线程里用；测试不走这里）
def _get(url: str, timeout: float = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_articles() -> list[dict]:
    d = _get(LIST_URL.format(c=CATALOG))
    cats = (d.get("data") or {}).get("catalogs") or []
    return list(cats[0].get("articles") or []) if cats else []


def resolve_live(coin: str, release_ms: int):
    """OKX 优先：live 且 listTime ≤ release − 24h；否则 Gate：trading、未下架中、create_time ≤ release − 24h。"""
    cut = release_ms - MIN_HISTORY_SEC * 1000
    try:
        d = _get(f"https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId={coin}-USDT-SWAP", 10)
        x = (d.get("data") or [None])[0]
        if x and x.get("state") == "live" and int(x.get("listTime") or 0) and int(x["listTime"]) <= cut:
            return ("okx", f"{coin}USDT")
    except Exception:  # noqa: BLE001
        pass
    try:
        x = _get(f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{coin}_USDT", 10)
        if isinstance(x, dict) and x.get("name") and not x.get("in_delisting") and x.get("status", "trading") == "trading" \
                and int(x.get("create_time") or 0) * 1000 <= cut:
            return ("gate", f"{coin}USDT")
    except Exception:  # noqa: BLE001
        pass
    return None


def price_live(venue: str, symbol: str) -> float:
    from .market import get_client
    return float(get_client(venue).quote(symbol, "perp").price)


# ---------------------------------------------------------------- 持久化 + 线程
def _db_load() -> dict:
    from . import db
    db.execute("CREATE TABLE IF NOT EXISTS shadow_books (sid TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at TEXT NOT NULL)")
    r = db.query("SELECT state FROM shadow_books WHERE sid=?", (SID,))
    return json.loads(r[0]["state"]) if r else new_book()


def _db_save(b: dict) -> None:
    from . import db
    for k, n in (("events", 200), ("skips", 200), ("trades", 400)):
        if len(b.get(k) or []) > n:
            if k == "trades":
                cut = b[k][:-n]
                b["trimmed_pnl"] = float(b.get("trimmed_pnl", 0.0)) + sum(float(t["pnl_usdt"]) for t in cut)
                b["trimmed_n"] = int(b.get("trimmed_n", 0)) + len(cut)
            b[k] = b[k][-n:]
    db.execute("INSERT OR REPLACE INTO shadow_books(sid,state,updated_at) VALUES(?,?,?)", (SID, json.dumps(b), iso(utcnow())))


def book() -> dict:
    with _LOCK:
        if _STATE["book"] is None:
            _STATE["book"] = _db_load()
        return _STATE["book"]


def enabled() -> bool:
    return os.environ.get("QTW_SHADOW_DELIST") == "1" and os.environ.get("QTW_FORBID_LIVE") != "1"


def _mark_all(b: dict) -> None:
    for s, p in b["positions"].items():
        try:
            b["marks"][s] = {"px": price_live(p["venue"], s), "t": iso(utcnow())}
        except Exception:  # noqa: BLE001
            pass


def _loop() -> None:
    last_poll = 0.0
    while not _STOP.is_set():
        try:
            now = time.time()
            with _LOCK:
                b = book()
                out = {"open": [], "skip": [], "stale": [], "wait": []}
                if now - last_poll >= POLL_SEC:
                    last_poll = now
                    arts = fetch_articles()
                    first = b.get("last_decision") is None
                    if first:  # 首次启动：只把已有公告记为已见（超过 2h 的会自动记「已过时」，不会补开）
                        log.info("影子子账本 %s（#%d）首次启动，现有 %d 条下架公告标记为已见", SID, NO, len(arts))
                    out = step_entries(b, arts, int(time.time() * 1000), resolve_live, price_live)
                    if first:
                        out["stale"] = []
                    _STATE["polls"] += 1
                    _STATE["last_poll"] = iso(utcnow())
                    b["last_decision"] = {"at": iso(utcnow()), "articles": len(arts), "opened": len(out["open"])}
                closes = step_exits(b, int(time.time() * 1000), price_live)
                _mark_all(b)
                _db_save(b)
            txt = log_text(out, closes)
            if txt.strip():
                log.info("%s", txt)
            _STATE["last_error"] = ""
        except Exception as e:  # noqa: BLE001
            _STATE["last_error"] = str(e)[:300]
            log.warning("影子子账本 %s 轮询失败：%s", SID, e)
        _STOP.wait(CHECK_SEC)


def start() -> bool:
    if not enabled() or (_STATE["thread"] and _STATE["thread"].is_alive()):
        return False
    _STOP.clear()
    t = threading.Thread(target=_loop, name="shadow-binance-delist", daemon=True)
    _STATE["thread"], _STATE["running"] = t, True
    t.start()
    log.info("影子子账本 %s（#%d）已启动：每 %ds 轮询币安官方下架公告（catalog %d），纸面做空 24h", SID, NO, POLL_SEC, CATALOG)
    return True


def stop() -> None:
    _STOP.set()
    _STATE["running"] = False


def status() -> dict:
    b = book() if enabled() or _STATE["book"] is not None else None
    base = {"sid": SID, "no": NO, "name": NAME, "enabled": enabled(),
            "running": bool(_STATE["thread"] and _STATE["thread"].is_alive()), "last_poll": _STATE["last_poll"],
            "polls": _STATE["polls"], "last_error": _STATE["last_error"],
            "params": {"poll_sec": POLL_SEC, "entry_delay_ms": ENTRY_DELAY_MS, "max_late_sec": MAX_LATE_SEC,
                       "hold_sec": HOLD_SEC, "event_budget": EVENT_BUDGET, "max_gross": MAX_GROSS, "fee_rate": FEE_RATE}}
    if b is None:
        return base
    return {**base, "equity": equity(b), "start_equity": b["start_equity"], "positions": list(b["positions"].values()),
            "closed": len(b["trades"]) + int(b.get("trimmed_n", 0)), "recent_trades": b["trades"][-20:][::-1],
            "events": b.get("events", [])[-20:], "skips": b.get("skips", [])[-20:]}
