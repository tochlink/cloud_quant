"""影子子账本 #18 btc_witness_mom_1h：比特币区块见证数据占比（铭文 / 数据承载活动代理）4 小时突发 → 8 币永续篮子顺势，持有 48h（只记录，纸面）。

* 研究：docs/btc_witness_bytes_burst_event_1h.md，output/research_btc_witness_bytes_burst_event_1h.csv（+ _supp.csv）。
  预注册先验（burst / contra 做空）与回退均否决；非先验格 wit_share L4 k3 twosided mom H48 在 OKX d8 / new8 deep·test·post 与 Gate post 8/8 为正、
  胜过 14 个时间平移安慰剂，但 deep 段 t 仅 0.7、k≤2.5 邻域崩，按规则只能「弱观察」→ 只做纸面影子前向检验，不进默认、不碰实盘。
* 默认关闭；只有进程环境变量 QTW_SHADOW_BTCWIT=1 时才启动线程（本机只在 8801 paper-btcwit 打开）。
  测试 / 安全模式（QTW_FORBID_LIVE=1）下永不启动、不访问网络。
* 不碰默认 1000U 账本（engine._BOOK）、不下任何真实 / 交易所模拟单、不经过实盘闸门。
* 数据：mempool.space 官方 esplora `GET /api/blocks/:height`（每页 10 块：timestamp / size / weight / tx_count），失败时用 blockstream.info 同接口
  （比特币共识字段逐块相同）。见证字节 = (4·size − weight)/3（BIP141：weight = 3·stripped + size）。
* 信号（与 scratch/btcwitness1h/run.py 完全同口径）：x_h = 该 UTC 小时（按区块时间戳）Σ见证字节 / Σsize，无出块小时为 NaN（不补）；
  mu / sd = x 在 h−168 … h−1 的均值 / 样本标准差（≥84 个有效值）；z = (x_{h−3}+…+x_h − 4·mu) / (2·sd)。
  每个整点过 DECIDE_DELAY_SEC 后判定刚收盘的小时 h；|z| ≥ 3 且本账无持仓 → 按 sign(z) 等权开 8 币永续（总名义 1.0 × 权益），
  晚于整点 MAX_LATE_SEC 才判定就跳过该小时（不补开）。
* 离场：开仓满 48h 后的第一次检查按 OKX 官方实时价平仓。费用：taker 5.1 bps 每边；资金费不计（与 #13–#17 影子一致，回测含资金费）。
数据存 SQLite 表 shadow_books（sid = btc_witness_mom_1h，data/，不入库）。
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
from datetime import datetime, timezone

from . import logtable as LT
from .timeutil import iso, utcnow

log = logging.getLogger(__name__)

SID = "btc_witness_mom_1h"
NO = 18
NAME = "比特币区块见证占比 4h 突发顺势（短线 1h，影子·弱观察）"
START_EQ = 1000.0
CHECK_SEC = 60
HOUR_MS = 3_600_000
W = 168
MIN_W = 84
L = 4
K = 3.0
HOLD_MS = 48 * HOUR_MS
DECIDE_DELAY_SEC = 120      # 整点后 2 分钟再判定（等该小时最后的区块传播）
MAX_LATE_SEC = 1800         # 整点后 30 分钟仍未判定 → 跳过该小时
GROSS = 1.0                 # 8 币总名义 = 1.0 × 权益
FEE_RATE = 0.00051
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
KEEP_HOURS = W + L + 8
SOURCES = ("https://mempool.space/api", "https://blockstream.info/api")
OPEN_HEADERS = ["币种", "方向", "金额(U)", "开仓价"]
CLOSE_HEADERS = ["币种", "方向", "开仓价", "平仓价", "盈亏(U)"]

_LOCK = threading.RLock()
_STATE: dict = {"book": None, "thread": None, "running": False, "last_check": None, "last_error": "", "checks": 0, "last_z": None}
_STOP = threading.Event()


def _iso_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- 纯函数（离线可测）
def witness_bytes(size: float, weight: float) -> float:
    return (4.0 * size - weight) / 3.0


def hourly_share(blocks: list) -> dict[int, float]:
    """blocks: [[height, ts_sec, size, weight], ...] → {hour_ms: Σwitness / Σsize}（只含有出块的小时）。"""
    acc: dict[int, list] = {}
    for _h, ts, size, wt in blocks:
        hr = int(ts) // 3600 * HOUR_MS
        a = acc.setdefault(hr, [0.0, 0.0])
        a[0] += witness_bytes(float(size), float(wt))
        a[1] += float(size)
    return {h: (a[0] / a[1]) for h, a in acc.items() if a[1] > 0}


def burst_z(share: dict[int, float], hour_ms: int) -> float | None:
    """z_L at hour_ms（与研究 burst_z 相同：窗口 168h 截至 hour−1，L=4 小时和）。无效返回 None。"""
    xs = [share.get(hour_ms - i * HOUR_MS) for i in range(1, W + 1)]
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if len(xs) < MIN_W:
        return None
    mu = sum(xs) / len(xs)
    var = sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)
    sd = math.sqrt(var)
    if not sd > 0:
        return None
    last = [share.get(hour_ms - i * HOUR_MS) for i in range(L)]
    if any(x is None or not math.isfinite(x) for x in last):
        return None
    return (sum(last) - L * mu) / (sd * math.sqrt(L))


def new_book() -> dict:
    return {"sid": SID, "start_equity": START_EQ, "realized": START_EQ, "positions": {}, "trades": [], "fees": 0.0,
            "created_at": iso(utcnow()), "last_decision": None, "venue": "okx", "marks": {}, "blocks": [],
            "decided": [], "skips": [], "signals": []}


def equity(b: dict) -> float:
    u = 0.0
    for k, p in b["positions"].items():
        px = float((b["marks"].get(k) or {}).get("px", p["entry"]))
        d = 1.0 if p["side"] == "long" else -1.0
        u += d * p["qty"] * (px - p["entry"])
    return b["realized"] + u


def step_decide(b: dict, now_ms: int, price) -> dict:
    """判定刚收盘的小时并按需开仓。price(symbol) → OKX 官方实时价。返回 {"open": [...], "skip": [...], "z": z, "hour": iso}。"""
    out: dict = {"open": [], "skip": [], "z": None, "hour": None}
    cur = now_ms // HOUR_MS * HOUR_MS
    hour = cur - HOUR_MS
    since = (now_ms - cur) / 1000.0
    key = _iso_ms(hour)
    decided = set(b.get("decided", []))
    if key in decided or since < DECIDE_DELAY_SEC:
        return out
    decided.add(key)
    b["decided"] = sorted(decided)[-400:]
    out["hour"] = key
    if since > MAX_LATE_SEC:
        b.setdefault("skips", []).append({"hour": key, "reason": f"整点后 {since / 60:.0f} 分钟才判定，跳过", "at": _iso_ms(now_ms)})
        out["skip"].append([key, "判定过晚"])
        return out
    z = burst_z(hourly_share(b.get("blocks") or []), hour)
    out["z"] = z
    _STATE["last_z"] = {"hour": key, "z": z}
    if z is None:
        out["skip"].append([key, "z 无效（区块数据不足）"])
        return out
    if abs(z) < K:
        return out
    side = "long" if z > 0 else "short"
    b.setdefault("signals", []).append({"hour": key, "z": round(z, 3), "side": side, "at": _iso_ms(now_ms),
                                        "taken": not b["positions"]})
    b["signals"] = b["signals"][-200:]
    if b["positions"]:
        out["skip"].append([key, f"z={z:+.2f} 触发但仍有持仓（不重叠）"])
        return out
    eq = equity(b)
    per = GROSS * eq / len(COINS)
    for sym in COINS:
        try:
            px = float(price(sym))
        except Exception as e:  # noqa: BLE001
            out["skip"].append([sym, f"取价失败 {e}"])
            continue
        if not px > 0:
            out["skip"].append([sym, "价格无效"])
            continue
        f = per * FEE_RATE
        b["realized"] -= f
        b["fees"] += f
        b["positions"][sym] = {"symbol": sym, "side": side, "market": "perp", "venue": "okx", "qty": per / px, "entry": px,
                               "notional": per, "fee_in": f, "entry_time": _iso_ms(now_ms), "signal_hour": key, "z": round(z, 3),
                               "exit_due_ms": now_ms + HOLD_MS, "strategy": SID, "entry_src": "okx_public/mark"}
        b["marks"][sym] = {"px": px, "t": _iso_ms(now_ms)}
        out["open"].append([sym, "开多·永续" if side == "long" else "开空·永续", f"{per:.1f}", f"{px:.6g}"])
    return out


def step_exits(b: dict, now_ms: int, price) -> list[list]:
    rows = []
    for k in list(b["positions"]):
        p = b["positions"][k]
        if now_ms < int(p["exit_due_ms"]):
            continue
        try:
            px = float(price(p["symbol"]))
        except Exception as e:  # noqa: BLE001
            log.warning("#18 %s 平仓取价失败，下次再试：%s", k, e)
            continue
        if not px > 0:
            continue
        b["positions"].pop(k)
        d = 1.0 if p["side"] == "long" else -1.0
        g = d * p["qty"] * (px - p["entry"])
        f = p["qty"] * px * FEE_RATE
        b["realized"] += g - f
        b["fees"] += f
        pnl = g - f - p["fee_in"]
        b["trades"].append({**p, "exit_time": _iso_ms(now_ms), "exit_price": px, "exit_reason": "持有 48h 到期", "fee_out": f,
                            "pnl_usdt": pnl, "return_pct": pnl / p["notional"] if p["notional"] else 0.0, "status": "closed"})
        rows.append([p["symbol"], "平多·永续" if d > 0 else "平空·永续", f"{p['entry']:.6g}", f"{px:.6g}", f"{g:+.2f}"])
    return rows


def merge_blocks(b: dict, new_rows: list, now_ms: int) -> None:
    seen = {int(r[0]): r for r in (b.get("blocks") or [])}
    for r in new_rows:
        seen[int(r[0])] = [int(r[0]), int(r[1]), int(r[2]), int(r[3])]
    lo = (now_ms // 1000) - KEEP_HOURS * 3600
    b["blocks"] = [seen[h] for h in sorted(seen) if seen[h][1] >= lo]


def log_text(out: dict, closes: list[list]) -> str:
    tag = f"影子子账本 {SID}（#{NO}，不计入主账本）"
    parts = []
    if closes:
        parts.append(LT.block(f"{tag} 平仓", CLOSE_HEADERS, closes))
    if out.get("open"):
        parts.append(LT.block(f"{tag} 开仓（{out.get('hour')} z={out.get('z'):+.2f}）", OPEN_HEADERS, out["open"]))
    for c, why in out.get("skip") or []:
        parts.append(f"\n{LT.stamp()} {tag}：{c} 跳过（{why}）")
    return "".join(parts)


# ---------------------------------------------------------------- 网络（只在线程里用；测试不走这里）
def _get(url: str, timeout: float = 20):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "QTW-shadow/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode()


def fetch_new_blocks(have: int, now_ms: int, max_pages: int = 150) -> tuple[list, str]:
    """从链顶往下取到已缓存高度 have（或 KEEP_HOURS 之前）；每页 10 块。不持锁、不改账本；返回 (rows, source)。"""
    lo_ts = now_ms // 1000 - KEEP_HOURS * 3600
    for base in SOURCES:
        try:
            tip = int(_get(f"{base}/blocks/tip/height").strip())
            rows, h, pages = [], tip, 0
            while h > have and pages < max_pages:
                arr = json.loads(_get(f"{base}/blocks/{h}"))
                if not arr:
                    break
                rows += [[x["height"], x["timestamp"], x["size"], x["weight"]] for x in arr]
                pages += 1
                if min(int(x["timestamp"]) for x in arr) < lo_ts:
                    break
                h = min(int(x["height"]) for x in arr) - 1
                time.sleep(0.25)
            return rows, base
        except Exception as e:  # noqa: BLE001
            log.warning("#18 区块数据 %s 获取失败：%s", base, e)
    raise RuntimeError("mempool.space / blockstream 都取不到区块")


def price_live(symbol: str) -> float:
    from .market import get_client
    return float(get_client("okx").quote(symbol, "perp").price)


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
    return os.environ.get("QTW_SHADOW_BTCWIT") == "1" and os.environ.get("QTW_FORBID_LIVE") != "1"


def _loop() -> None:
    last_fetch = 0.0
    while not _STOP.is_set():
        try:
            now = int(time.time() * 1000)
            since = (now % HOUR_MS) / 1000.0
            if time.time() - last_fetch > 600 or (DECIDE_DELAY_SEC <= since < DECIDE_DELAY_SEC + 2 * CHECK_SEC):
                with _LOCK:
                    have = max((int(r[0]) for r in (book().get("blocks") or [])), default=0)
                rows, src = fetch_new_blocks(have, now)   # 网络在锁外
                with _LOCK:
                    merge_blocks(book(), rows, now)
                    book()["block_source"] = src
                last_fetch = time.time()
            now = int(time.time() * 1000)
            with _LOCK:
                b = book()
                out = step_decide(b, now, price_live)
                closes = step_exits(b, now, price_live)
                for k, p in b["positions"].items():
                    try:
                        b["marks"][k] = {"px": price_live(p["symbol"]), "t": iso(utcnow())}
                    except Exception:  # noqa: BLE001
                        pass
                if out.get("hour"):
                    b["last_decision"] = {"at": iso(utcnow()), "hour": out["hour"], "z": out.get("z"), "opened": len(out["open"]),
                                          "closed": len(closes)}
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
    t = threading.Thread(target=_loop, name="shadow-btc-witness", daemon=True)
    _STATE["thread"], _STATE["running"] = t, True
    t.start()
    log.info("影子子账本 %s（#%d）已启动：BTC 区块见证占比 L%d z≥%.1f 顺势 8 币永续，持有 48h", SID, NO, L, K)
    return True


def stop() -> None:
    _STOP.set()
    _STATE["running"] = False


def status() -> dict:
    base = {"sid": SID, "no": NO, "name": NAME, "enabled": enabled(),
            "running": bool(_STATE["thread"] and _STATE["thread"].is_alive()), "last_check": _STATE["last_check"],
            "checks": _STATE["checks"], "last_error": _STATE["last_error"], "last_z": _STATE["last_z"],
            "params": {"window_h": W, "L": L, "k": K, "hold_h": HOLD_MS // HOUR_MS, "gross": GROSS, "fee_rate": FEE_RATE,
                       "coins": COINS, "decide_delay_sec": DECIDE_DELAY_SEC, "max_late_sec": MAX_LATE_SEC}}
    b = book() if enabled() or _STATE["book"] is not None else None
    if b is None:
        return base
    bl = b.get("blocks") or []
    return {**base, "equity": equity(b), "start_equity": b["start_equity"], "positions": list(b["positions"].values()),
            "realized": b["realized"], "fees": b["fees"], "closed": len(b["trades"]) + int(b.get("trimmed_n", 0)),
            "recent_trades": b["trades"][-20:][::-1], "signals": (b.get("signals") or [])[-20:], "skips": (b.get("skips") or [])[-20:],
            "blocks_cached": len(bl), "block_tip": (bl[-1][0] if bl else None), "block_source": b.get("block_source"),
            "last_decision": b.get("last_decision")}
