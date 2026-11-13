"""多策略影子纸面子账本（v7）：每套「采用 / 观察」策略各一本独立 1000U 纸面账，事件驱动，只做记录。

* 不碰默认 1000U 账本（engine._BOOK）、不下任何真实 / 交易所模拟单、不经过实盘闸门；
* 决策：该策略周期（4h / 1h）官方 K 线「已收盘确认」事件（stream.on_bar_close）→ 后台线程按最新已收盘 K 线算信号，
  按当前 WS 最新价（无则用该根收盘价）吃单成交，费率与回测相同（现货 / 永续 taker）；
* 止损：每个 WS tick（stream.on_quote）按同一价位检查 ATR 止损，触发即按该价平仓并锁定到信号方向改变；
* 简化：不做 10% 调仓带（回测里有），持仓名义只在开仓时确定；资金费率套利不进影子账本。
数据存 SQLite 表 shadow_books（data/，不入库）。
"""
from __future__ import annotations

import json
import logging
import threading
import time

import numpy as np
import pandas as pd

from . import db
from . import settings as S
from . import strategies as R
from .risk import scale_to_room, size
from .strategy import name_vol_mult
from .timeutil import iso, utcnow

log = logging.getLogger(__name__)
START_EQ = 1000.0
STATUSES = ("采用", "观察")
_LOCK = threading.RLock()
_BOOKS: dict[str, dict] = {}
_SEEN: dict[str, int] = {}
_LAST: dict = {"decisions": []}
_READY = {"ok": False}


def _ensure():
    if _READY["ok"]:
        return
    db.execute("CREATE TABLE IF NOT EXISTS shadow_books (sid TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at TEXT NOT NULL)")
    _READY["ok"] = True


def active_ids() -> list[str]:
    out = []
    for s in R.STRATEGIES:
        v = R.VERDICTS.get(s["id"], {})
        if s["signal"] is not None and not s.get("separate_sim") and v.get("status") in STATUSES:
            out.append(s["id"])
    return out


def _new(sid: str) -> dict:
    return {"sid": sid, "start_equity": START_EQ, "realized": START_EQ, "positions": {}, "blocked": {}, "trades": [],
            "fees": 0.0, "created_at": iso(utcnow()), "last_decision": None, "venue": None, "marks": {}}


def book(sid: str) -> dict:
    with _LOCK:
        if sid not in _BOOKS:
            _ensure()
            r = db.query("SELECT state FROM shadow_books WHERE sid=?", (sid,))
            _BOOKS[sid] = json.loads(r[0]["state"]) if r else _new(sid)
        return _BOOKS[sid]


def _save(sid: str) -> None:
    _ensure()
    b = _BOOKS[sid]
    b["trades"] = b["trades"][-400:]
    db.execute("INSERT OR REPLACE INTO shadow_books(sid,state,updated_at) VALUES(?,?,?)", (sid, json.dumps(b), iso(utcnow())))


def _fee(cfg, market):
    return S.taker_rate(cfg, market)


def _px(venue, sym, market, fallback):
    from . import stream
    q = stream.latest(venue, sym, market, max_age_sec=30)
    if q is not None and q.price and q.price > 0:
        return float(q.price), q.data_source or "ws"
    return float(fallback), "bar_close"


def _mark(b, sym, p):
    return float(b["marks"].get(sym, {}).get("px", p["entry"]))


def equity(b: dict) -> float:
    u = 0.0
    for s, p in b["positions"].items():
        d = 1 if p["side"] == "long" else -1
        u += d * p["qty"] * (_mark(b, s, p) - p["entry"])
    return b["realized"] + u


def _close(cfg, b, s, px, reason, when, src):
    p = b["positions"].pop(s)
    d = 1 if p["side"] == "long" else -1
    f = abs(p["qty"] * px) * _fee(cfg, p["market"])
    g = d * p["qty"] * (px - p["entry"])
    b["realized"] += g - f
    b["fees"] += f
    pnl = g - f - p["fee_in"]
    b["trades"].append({**p, "exit_time": when, "exit_price": px, "exit_reason": reason, "exit_src": src,
                        "pnl_usdt": pnl, "return_pct": pnl / p["notional"] if p["notional"] else 0.0, "status": "closed"})


def decide(sid: str, data: dict, cfg: dict, when: str | None = None) -> list[str]:
    """按最新已收盘 K 线做一次决策（离场 → 解锁 → 开仓）。data = {"spot": {sym: df}, "perp": {...}}。"""
    spec = R.BY_ID[sid]
    sig = R.latest_signals(sid, data, cfg)
    venue = cfg["venue"]
    when = when or iso(utcnow())
    ev: list[str] = []
    c = R.strategy_cfg(cfg, sid)
    st, rk = c["strategy"], c["risk"]
    with _LOCK:
        b = book(sid)
        if b.get("venue") and b["venue"] != venue and b["positions"]:
            return [f"行情源已切换到 {venue}，影子账本仍有 {b['venue']} 持仓，跳过"]
        b["venue"] = venue
        last = {m: {s: data[m][s].iloc[-1] for s in data[m]} for m in ("spot", "perp")}
        for s in list(b["positions"]):
            p = b["positions"][s]
            want = {1: "long", -1: "short"}.get(sig.get(s, 0), "flat")
            if want != p["side"]:
                px, src = _px(venue, s, p["market"], last[p["market"]][s]["close"])
                _close(c, b, s, px, "信号反转" if want != "flat" else "信号转空仓", when, src)
                ev.append(f"{s} 平{('多' if p['side'] == 'long' else '空')} @{px:.6g}")
        for s in list(b["blocked"]):
            if sig.get(s, 0) != b["blocked"][s]:
                b["blocked"].pop(s)
        eq = equity(b)
        gross = sum(abs(p["qty"]) * _mark(b, s, p) for s, p in b["positions"].items())
        want = {}
        for s, g in sig.items():
            if not g or s in b["positions"] or s in b["blocked"]:
                continue
            long_mkt = "perp" if rk.get("trade_mode") == "perp_both" else "spot"  # 跟随风控「交易方式」
            side, mkt = ("long", long_mkt) if g > 0 else ("short", "perp")
            if side == "long" and not rk["allow_spot_long"] or side == "short" and not rk["allow_perp_short"]:
                continue
            df = data[mkt][s]
            hi, lo, cl = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
            tr = pd.concat([hi - lo, (hi - cl.shift()).abs(), (lo - cl.shift()).abs()], axis=1).max(axis=1)
            atr = float(tr.rolling(int(st["atr_period"])).mean().iloc[-1])
            nv = float(st.get("name_vol_target", 0) or 0)
            m = float(name_vol_mult(cl.to_numpy(), nv, int(st.get("name_vol_lookback", 120) or 120))[-1]) if nv else 1.0
            px, src = _px(venue, s, mkt, cl.iloc[-1])
            z = size(side=side, equity=eq, price=px, atr=atr, max_risk=float(rk["max_risk_per_trade"]) * m,
                     max_weight=float(rk["max_weight_per_name"]) * m, atr_mult=float(st["atr_stop_mult"]))
            if z.notional > 0:
                want[s] = (side, mkt, px, src, z)
        alloc = scale_to_room({s: w[4].notional for s, w in want.items()}, eq * float(rk["max_gross_exposure"]) - gross, _fee(c, "spot"))
        for s, (side, mkt, px, src, z) in want.items():
            n = alloc.get(s, 0.0)
            if n <= 1.0:
                continue
            f = n * _fee(c, mkt)
            b["realized"] -= f
            b["fees"] += f
            b["positions"][s] = {"symbol": s, "side": side, "market": mkt, "qty": n / px, "entry": px, "stop": z.stop_price,
                                 "notional": n, "fee_in": f, "entry_time": when, "entry_src": src, "venue": venue, "strategy": sid}
            b["marks"][s] = {"px": px, "t": when}
            ev.append(f"{s} 开{'多' if side == 'long' else '空'}·{'现货' if mkt == 'spot' else '永续'} {n:.1f}U @{px:.6g}")
        b["last_decision"] = {"at": when, "events": ev, "signals": sig}
        _save(sid)
    return ev


def on_tick(q) -> None:
    """WS tick：更新影子持仓标记价并检查 ATR 止损。"""
    if not _BOOKS:
        return
    with _LOCK:
        for sid, b in _BOOKS.items():
            p = b["positions"].get(q.symbol)
            if not p or p["market"] != q.market or (b.get("venue") or "") != q.venue.lower():
                continue
            px = float(q.price)
            b["marks"][q.symbol] = {"px": px, "t": iso(q.ts) if getattr(q, "ts", None) else iso(utcnow())}
            hit = px <= p["stop"] if p["side"] == "long" else px >= p["stop"]
            if hit:
                cfg = S.load()
                _close(cfg, b, q.symbol, px, "ATR止损", iso(utcnow()), q.data_source or "ws")
                b["blocked"][q.symbol] = 1 if p["side"] == "long" else -1
                _save(sid)
                _LAST["decisions"].append({"sid": sid, "at": time.time(), "events": [f"{q.symbol} ATR 止损 @{px:.6g}"]})


def _run_bar(sid: str, venue: str, interval: str, close_ms: int) -> None:
    from .market import cache as mcache
    try:
        if close_ms:
            time.sleep(2.0)  # 合并同一时刻 8 个币 × 现货/永续的收盘事件，并等官方 K 线落库
        cfg = S.load()
        if cfg["venue"] != venue:
            return
        fr, err = mcache.many(venue, cfg["symbols"], interval, 1500)
        if not fr.get("spot") or not fr.get("perp"):
            log.warning("shadow %s: 行情获取失败 %s", sid, err)
            return
        ev = decide(sid, fr, cfg, iso(utcnow()))
        _LAST["decisions"] = (_LAST["decisions"] + [{"sid": sid, "at": time.time(), "close_ms": close_ms, "events": ev}])[-50:]
        if ev:
            log.info("影子子账本 %s：%s", sid, "；".join(ev))
    except Exception:  # noqa: BLE001
        log.exception("shadow decision failed: %s", sid)


def on_bar_close(ev: dict) -> None:
    """官方 K 线收盘确认事件 → 对应周期的影子策略各跑一次（同一收盘时刻只跑一次）。"""
    ids = active_ids()
    if not ids:
        return
    tf, venue, key = ev.get("tf"), str(ev.get("venue", "")).lower(), int(ev.get("close_ms") or 0)
    for sid in ids:
        if R.BY_ID[sid]["interval"] != tf:
            continue
        k = f"{sid}:{venue}"
        with _LOCK:
            if _SEEN.get(k) == key:
                continue
            _SEEN[k] = key
        threading.Thread(target=_run_bar, args=(sid, venue, tf, key), name=f"shadow-{sid}", daemon=True).start()


def load_all() -> None:
    """启动时载入影子账本；从未决策过的账本在启动约 15 秒后（等 WS 行情就绪）按最新已收盘 K 线做首次决策（一次性，不是定时）。"""
    fresh = []
    for sid in active_ids():
        if book(sid).get("last_decision") is None:
            fresh.append(sid)
    if fresh and __import__("os").environ.get("QTW_FORBID_LIVE") != "1":
        def _boot():
            time.sleep(15.0)
            cfg = S.load()
            for sid in fresh:
                _run_bar(sid, cfg["venue"], R.BY_ID[sid]["interval"], 0)
        threading.Thread(target=_boot, name="shadow-boot", daemon=True).start()


def status() -> list[dict]:
    out = []
    for sid in active_ids():
        b = book(sid)
        eq = equity(b)
        cl = [t for t in b["trades"] if t.get("status") == "closed"]
        pos = []
        for s, p in b["positions"].items():
            m = _mark(b, s, p)
            d = 1 if p["side"] == "long" else -1
            pos.append({**p, "mark": m, "upnl": d * p["qty"] * (m - p["entry"])})
        out.append({"sid": sid, "name": R.BY_ID[sid]["name"], "status": R.VERDICTS.get(sid, {}).get("status"),
                    "equity": eq, "start_equity": b["start_equity"], "ret": eq / b["start_equity"] - 1, "fees": b["fees"],
                    "positions": pos, "closed_trades": len(cl), "wins": sum(1 for t in cl if t["pnl_usdt"] > 0),
                    "recent_trades": cl[-20:][::-1], "last_decision": b.get("last_decision"), "venue": b.get("venue"),
                    "created_at": b.get("created_at")})
    return out
