"""影子子账本 #17 token_unlock_short_1h：官方排期的团队 / 投资人代币解锁前 72h 做空该币 USDT 永续 + 等额做多 BTC 永续，
解锁日 00:00 UTC 平仓（只记录，纸面）。

* 研究：docs/token_unlock_event_1h.md，output/research_token_unlock_event_1h.csv（+ _supp.csv）。先验格（−24h→+24h）否决；
  非先验格 short a=−72 b=0 BTC 对冲在 deep / test / post 与 OKX / Gate 6/6 为正、胜过 ±7d / ±15d 平移安慰剂，按预注册规则只能「弱观察」，
  因此只做纸面影子前向检验，不进默认、不碰实盘。
* 默认关闭；只有进程环境变量 QTW_SHADOW_UNLOCK=1 时才启动线程（本机只在 8788 paper-default 打开）。
  测试 / 安全模式（QTW_FORBID_LIVE=1）下永不启动、不访问网络。
* 不碰默认 1000U 账本（engine._BOOK）、不下任何真实 / 交易所模拟单、不经过实盘闸门。
* 日历（官方 tokenomics 文档，代码内写死，和研究 scratch/tokenunlock1h/events.py 同一规则）：ARB 每月 16 日、STRK 15 日、JTO 7 日、
  ZK 17 日、ZRO 20 日、PYTH 每年 5-20；T0 = 当日 00:00 UTC。
* 入场：T0 − 72h 之后的第一次检查（晚于 MAX_LATE_SEC 不补开）；OKX 有 live 的 <币>-USDT-SWAP 优先，否则 Gate；
  每个事件名义 EVENT_BUDGET × 权益（币腿），BTC 腿等额反向；总币腿名义不超过 MAX_GROSS × 权益。
* 离场：now ≥ T0 后的第一次检查，两腿都按同一场所官方实时价平仓。
* 费用：taker FEE_RATE（5.1 bps）每边每腿；资金费不计（与 #13–#15 影子一致）。
数据存 SQLite 表 shadow_books（sid = token_unlock_short_1h，data/，不入库）。
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

from . import logtable as LT
from .timeutil import iso, utcnow

log = logging.getLogger(__name__)

SID = "token_unlock_short_1h"
NO = 17
NAME = "代币解锁前 72h 做空（BTC 对冲，短线 1h，影子·弱观察）"
START_EQ = 1000.0
CHECK_SEC = 60
PRE_SEC = 72 * 3600        # 解锁前 72h 入场
MAX_LATE_SEC = 2 * 3600     # 晚于入场时刻 2h 才发现（重启等）就不补开
EVENT_BUDGET = 0.25         # 每个事件币腿名义 = 0.25 × 权益；BTC 腿等额
MAX_GROSS = 1.0             # 全部币腿名义上限 = 1.0 × 权益
FEE_RATE = 0.00051
HEDGE = "BTCUSDT"
# (币, 每月几号, 首个 YYYY-MM, 最后 YYYY-MM)；PYTH 单独按年
MONTHLY = [("ARB", 16, "2024-03", "2027-03"), ("STRK", 15, "2024-04", "2027-03"), ("JTO", 7, "2024-12", "2026-12"),
           ("ZK", 17, "2025-06", "2028-06"), ("ZRO", 20, "2025-06", "2027-06"), ("APT", 12, "2023-11", "2026-10")]
YEARLY = [("PYTH", 5, 20, (2024, 2025, 2026, 2027))]
OPEN_HEADERS = ["币种", "方向", "金额(U)", "开仓价"]
CLOSE_HEADERS = ["币种", "方向", "开仓价", "平仓价", "盈亏(U)"]

_LOCK = threading.RLock()
_STATE: dict = {"book": None, "thread": None, "running": False, "last_check": None, "last_error": "", "checks": 0}
_STOP = threading.Event()


def _ms(y: int, m: int, d: int) -> int:
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)


def _iso_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def calendar() -> list[tuple[str, int]]:
    """全部 (币, T0_ms) 解锁事件，按时间排序。"""
    ev = []
    for c, day, a, b in MONTHLY:
        y, m = map(int, a.split("-"))
        y2, m2 = map(int, b.split("-"))
        while (y, m) <= (y2, m2):
            ev.append((c, _ms(y, m, day)))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    for c, mo, day, years in YEARLY:
        ev += [(c, _ms(y, mo, day)) for y in years]
    return sorted(ev, key=lambda x: (x[1], x[0]))


def upcoming(now_ms: int, n: int = 8) -> list[dict]:
    return [{"coin": c, "unlock_utc": _iso_ms(t0), "entry_utc": _iso_ms(t0 - PRE_SEC * 1000)}
            for c, t0 in calendar() if t0 > now_ms][:n]


# ---------------------------------------------------------------- 账本
def new_book() -> dict:
    return {"sid": SID, "start_equity": START_EQ, "realized": START_EQ, "positions": {}, "trades": [], "fees": 0.0,
            "created_at": iso(utcnow()), "last_decision": None, "venue": "okx", "marks": {}, "seen": [], "skips": []}


def _mark(b: dict, venue: str, sym: str, fallback: float) -> float:
    return float((b["marks"].get(f"{venue}:{sym}") or {}).get("px", fallback))


def equity(b: dict) -> float:
    u = 0.0
    for p in b["positions"].values():
        u += -p["qty"] * (_mark(b, p["venue"], p["symbol"], p["entry"]) - p["entry"])
        u += p["hedge_qty"] * (_mark(b, p["venue"], HEDGE, p["hedge_entry"]) - p["hedge_entry"])
    return b["realized"] + u


def step_entries(b: dict, now_ms: int, resolve, price) -> dict:
    """到入场时刻的解锁事件开仓。resolve(coin) → venue 或 None；price(venue, symbol) → 官方实时价。纯函数，可离线测试。"""
    out = {"open": [], "skip": [], "stale": []}
    seen = set(b.get("seen", []))
    for c, t0 in calendar():
        key = f"{c}@{_iso_ms(t0)[:10]}"
        ent = t0 - PRE_SEC * 1000
        if key in seen or now_ms < ent or now_ms >= t0:
            continue
        seen.add(key)
        late = (now_ms - ent) / 1000.0
        if late > MAX_LATE_SEC:
            out["stale"].append([key, round(late)])
            b.setdefault("skips", []).append({"event": key, "reason": f"发现时已晚 {late / 3600:.1f}h，不补开", "at": _iso_ms(now_ms)})
            continue
        venue = resolve(c)
        if not venue:
            out["skip"].append([c, "OKX / Gate 无 live 的 USDT 永续"])
            continue
        eq = equity(b)
        gross = sum(p["notional"] for p in b["positions"].values())
        per = min(EVENT_BUDGET * eq, max(0.0, MAX_GROSS * eq - gross))
        if per <= 1.0:
            out["skip"].append([c, "总敞口已满"])
            continue
        sym = f"{c}USDT"
        try:
            px, hpx = float(price(venue, sym)), float(price(venue, HEDGE))
        except Exception as e:  # noqa: BLE001
            out["skip"].append([c, f"取价失败 {e}"])
            seen.discard(key)  # 下次检查再试（仍受 MAX_LATE_SEC 限制）
            continue
        if not (px > 0 and hpx > 0):
            out["skip"].append([c, "价格无效"])
            continue
        f = 2 * per * FEE_RATE
        b["realized"] -= f
        b["fees"] += f
        b["positions"][key] = {"key": key, "symbol": sym, "side": "short", "market": "perp", "qty": per / px, "entry": px,
                               "hedge_symbol": HEDGE, "hedge_side": "long", "hedge_qty": per / hpx, "hedge_entry": hpx,
                               "notional": per, "fee_in": f, "entry_time": _iso_ms(now_ms), "venue": venue, "strategy": SID,
                               "unlock_utc": _iso_ms(t0), "exit_due_ms": t0, "entry_delay_sec": round(late, 1),
                               "entry_src": f"{venue}_public/mark"}
        b["marks"][f"{venue}:{sym}"] = {"px": px, "t": _iso_ms(now_ms)}
        b["marks"][f"{venue}:{HEDGE}"] = {"px": hpx, "t": _iso_ms(now_ms)}
        out["open"].append([sym, "开空·永续", f"{per:.1f}", f"{px:.6g}", venue, round(late)])
        out["open"].append([HEDGE, "开多·永续（对冲）", f"{per:.1f}", f"{hpx:.6g}", venue, round(late)])
    b["seen"] = sorted(seen)[-500:]
    return out


def step_exits(b: dict, now_ms: int, price) -> list[list]:
    """到 T0（解锁日 00:00 UTC）的仓两腿一起按官方实时价平；取价失败留到下次。"""
    rows = []
    for k in list(b["positions"]):
        p = b["positions"][k]
        if now_ms < int(p["exit_due_ms"]):
            continue
        try:
            px, hpx = float(price(p["venue"], p["symbol"])), float(price(p["venue"], HEDGE))
        except Exception as e:  # noqa: BLE001
            log.warning("#17 %s 平仓取价失败，下次再试：%s", k, e)
            continue
        if not (px > 0 and hpx > 0):
            continue
        b["positions"].pop(k)
        g1 = -p["qty"] * (px - p["entry"])
        g2 = p["hedge_qty"] * (hpx - p["hedge_entry"])
        f = (p["qty"] * px + p["hedge_qty"] * hpx) * FEE_RATE
        b["realized"] += g1 + g2 - f
        b["fees"] += f
        pnl = g1 + g2 - f - p["fee_in"]
        b["trades"].append({**p, "exit_time": _iso_ms(now_ms), "exit_price": px, "hedge_exit": hpx, "exit_reason": "解锁时刻 T0 平仓",
                            "fee_out": f, "pnl_token_leg": g1, "pnl_hedge_leg": g2, "pnl_usdt": pnl,
                            "return_pct": pnl / p["notional"] if p["notional"] else 0.0, "status": "closed"})
        rows.append([p["symbol"], "平空·永续", f"{p['entry']:.6g}", f"{px:.6g}", f"{g1:+.2f}"])
        rows.append([HEDGE, "平多·永续（对冲）", f"{p['hedge_entry']:.6g}", f"{hpx:.6g}", f"{g2:+.2f}"])
    return rows


def log_text(out: dict, closes: list[list]) -> str:
    tag = f"影子子账本 {SID}（#{NO}，不计入主账本）"
    parts = []
    if closes:
        parts.append(LT.block(f"{tag} 平仓", CLOSE_HEADERS, closes))
    if out.get("open"):
        parts.append(LT.block(f"{tag} 开仓", OPEN_HEADERS, [r[:4] for r in out["open"]]))
    for c, why in out.get("skip") or []:
        parts.append(f"\n{LT.stamp()} {tag}：{c} 跳过（{why}）")
    for key, late in out.get("stale") or []:
        parts.append(f"\n{LT.stamp()} {tag}：{key} 入场时刻已过 {late} 秒，超过 {MAX_LATE_SEC} 秒，不补开")
    return "".join(parts)


# ---------------------------------------------------------------- 网络（只在线程里用；测试不走这里）
def _get(url: str, timeout: float = 10):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def resolve_live(coin: str):
    try:
        d = _get(f"https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId={coin}-USDT-SWAP")
        x = (d.get("data") or [None])[0]
        if x and x.get("state") == "live":
            return "okx"
    except Exception:  # noqa: BLE001
        pass
    try:
        x = _get(f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{coin}_USDT")
        if isinstance(x, dict) and x.get("name") and not x.get("in_delisting") and x.get("status", "trading") == "trading":
            return "gate"
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
    for k, n in (("skips", 200), ("trades", 400)):
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
    return os.environ.get("QTW_SHADOW_UNLOCK") == "1" and os.environ.get("QTW_FORBID_LIVE") != "1"


def _mark_all(b: dict) -> None:
    for p in b["positions"].values():
        for s in (p["symbol"], HEDGE):
            try:
                b["marks"][f"{p['venue']}:{s}"] = {"px": price_live(p["venue"], s), "t": iso(utcnow())}
            except Exception:  # noqa: BLE001
                pass


def _loop() -> None:
    while not _STOP.is_set():
        try:
            now = int(time.time() * 1000)
            with _LOCK:
                b = book()
                out = step_entries(b, now, resolve_live, price_live)
                closes = step_exits(b, now, price_live)
                _mark_all(b)
                b["last_decision"] = {"at": iso(utcnow()), "opened": len(out["open"]) // 2, "closed": len(closes) // 2}
                _STATE["checks"] += 1
                _STATE["last_check"] = iso(utcnow())
                _db_save(b)
            txt = log_text(out, closes)
            if txt.strip():
                log.info("%s", txt)
            _STATE["last_error"] = ""
        except Exception as e:  # noqa: BLE001
            _STATE["last_error"] = str(e)[:300]
            log.warning("影子子账本 %s 检查失败：%s", SID, e)
        _STOP.wait(CHECK_SEC)


def start() -> bool:
    if not enabled() or (_STATE["thread"] and _STATE["thread"].is_alive()):
        return False
    _STOP.clear()
    t = threading.Thread(target=_loop, name="shadow-token-unlock", daemon=True)
    _STATE["thread"], _STATE["running"] = t, True
    t.start()
    log.info("影子子账本 %s（#%d）已启动：解锁前 72h 做空该币永续 + 等额做多 BTC，T0 平仓；下一批：%s", SID, NO,
             upcoming(int(time.time() * 1000), 3))
    return True


def stop() -> None:
    _STOP.set()
    _STATE["running"] = False


def status() -> dict:
    now = int(time.time() * 1000)
    base = {"sid": SID, "no": NO, "name": NAME, "enabled": enabled(),
            "running": bool(_STATE["thread"] and _STATE["thread"].is_alive()), "last_check": _STATE["last_check"],
            "checks": _STATE["checks"], "last_error": _STATE["last_error"], "upcoming": upcoming(now),
            "params": {"pre_sec": PRE_SEC, "max_late_sec": MAX_LATE_SEC, "event_budget": EVENT_BUDGET, "max_gross": MAX_GROSS,
                       "fee_rate": FEE_RATE, "hedge": HEDGE}}
    b = book() if enabled() or _STATE["book"] is not None else None
    if b is None:
        return base
    return {**base, "equity": equity(b), "start_equity": b["start_equity"], "positions": list(b["positions"].values()),
            "realized": b["realized"], "fees": b["fees"], "closed": len(b["trades"]) + int(b.get("trimmed_n", 0)),
            "recent_trades": b["trades"][-20:][::-1], "skips": b.get("skips", [])[-20:]}
