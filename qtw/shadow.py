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
from . import logtable as LT
from . import strategies as R
from .risk import scale_to_room, size
from .strategy import name_vol_mult
from .timeutil import iso, utcnow

log = logging.getLogger(__name__)
START_EQ = 1000.0
# 事件型策略（#13 / #14）：只在触发 K 线收盘后的这么多根内入场；重启 / 停机后发现触发已过更久，就不补开（回测里不存在这种晚到的入场）
EVENT_GRACE_BARS = 1
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
    if len(b["trades"]) > 400:  # 只保留最近 400 笔明细；被裁掉的盈亏累计到 trimmed_pnl，对账仍然闭合
        cut = b["trades"][:-400]
        b["trimmed_pnl"] = float(b.get("trimmed_pnl", 0.0)) + sum(float(t["pnl_usdt"]) for t in cut)
        b["trimmed_n"] = int(b.get("trimmed_n", 0)) + len(cut)
        b["trades"] = b["trades"][-400:]
    db.execute("INSERT OR REPLACE INTO shadow_books(sid,state,updated_at) VALUES(?,?,?)", (sid, json.dumps(b), iso(utcnow())))


def _bar_td(sid: str) -> pd.Timedelta:
    return pd.Timedelta(str(R.BY_ID[sid].get("interval") or "1h"))


def _hold_bars(sid: str) -> int:
    return int((R.BY_ID[sid].get("params") or {}).get("hold") or 0)


def _ts(x) -> pd.Timestamp | None:
    try:
        t = pd.Timestamp(x)
    except Exception:  # noqa: BLE001
        return None
    if pd.isna(t):
        return None
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def event_expiry(sid: str, p: dict) -> pd.Timestamp | None:
    """事件型持仓的到期时刻（UTC）：固定为「原始触发 K 线开盘 + (H+1) 根」= 准时入场时刻 + H 根，与回测一致。
    开仓时写入 expires_at 并随账本持久化（重启不重置）；旧持仓没有 expires_at 时按 signal_bar 推算，再没有就按 entry_time + H 根。
    之后再出现的触发（同一事件持续 / 新事件）都不会延长这张单的持有期。"""
    H = _hold_bars(sid)
    if H <= 0:
        return None
    t = _ts(p.get("expires_at")) if p.get("expires_at") else None
    if t is not None:
        return t
    bar = _bar_td(sid)
    sb = _ts(p.get("signal_bar")) if p.get("signal_bar") else None
    if sb is not None:
        return sb + (H + 1) * bar
    et = _ts(p.get("entry_time")) if p.get("entry_time") else None
    return et + H * bar if et is not None else None


def overdue(sid: str, b: dict, now: pd.Timestamp | None = None) -> list[str]:
    """已过到期时刻仍未平的事件型持仓（用于启动时立刻补做一次离场决策）。"""
    if not R.is_event(sid):
        return []
    now = now or pd.Timestamp.now(tz="UTC")
    out = []
    for s, p in b["positions"].items():
        e = event_expiry(sid, p)
        if e is not None and now >= e:
            out.append(s)
    return out


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
    b["trades"].append({**p, "exit_time": when, "exit_price": px, "exit_reason": reason, "exit_src": src, "fee_out": f,
                        "pnl_usdt": pnl, "return_pct": pnl / p["notional"] if p["notional"] else 0.0, "status": "closed"})
    return pnl


def _mk_cn(side, mkt, verb):
    return f"{verb}{'多' if side == 'long' else '空'}·{'现货' if mkt == 'spot' else '永续'}"


def decide(sid: str, data: dict, cfg: dict, when: str | None = None, rows: dict | None = None) -> list[str]:
    """按最新已收盘 K 线做一次决策（离场 → 解锁 → 开仓）。data = {"spot": {sym: df}, "perp": {...}}。
    rows（可选）收集结构化的开 / 平明细 {"open": [...], "close": [...], "stale": [...]}，用于日志表格。"""
    spec = R.BY_ID[sid]
    sig, ages, idx = R.latest_signals(sid, data, cfg, detail=True)
    event = R.is_event(sid)
    rows = rows if rows is not None else {}
    for k in ("open", "close", "stale"):
        rows.setdefault(k, [])

    def bar_t(age):
        try:
            return iso(pd.Timestamp(idx[-1 - int(age)]).to_pydatetime())
        except Exception:  # noqa: BLE001
            return ""
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
        # 最新已收盘 K 线的收盘时刻（事件型持仓按它判断是否到期，不看重算出来的信号是否还在）
        now_close = _ts(idx[-1]) + _bar_td(sid) if event and idx is not None and len(idx) else None
        for s in list(b["positions"]):
            p = b["positions"][s]
            want = {1: "long", -1: "short"}.get(sig.get(s, 0), "flat")
            if event:
                exp = event_expiry(sid, p)
                if exp is None or now_close is None:
                    if want == p["side"]:
                        continue
                    reason = "持有期满"
                elif now_close >= exp:
                    late_h = (now_close - exp) / _bar_td(sid)
                    reason = "持有期满" + (f"（到期 {iso(exp.to_pydatetime())}，晚 {late_h:.0f} 根离场）" if late_h >= 1 else "")
                else:
                    continue  # 未到期：持有到 entry+H，不因重算信号提前 / 推迟离场
            elif want == p["side"]:
                continue
            else:
                reason = "信号转空仓" if want == "flat" else "信号反转"
            px, src = _px(venue, s, p["market"], last[p["market"]][s]["close"])
            pnl = _close(c, b, s, px, reason, when, src)
            ev.append(f"{s} 平{('多' if p['side'] == 'long' else '空')} @{px:.6g}")
            rows["close"].append([s, _mk_cn(p["side"], p["market"], "平"), f"{p['entry']:.6g}", f"{px:.6g}", f"{pnl:+.2f}"])
        for s in list(b["blocked"]):
            if sig.get(s, 0) != b["blocked"][s]:
                b["blocked"].pop(s)
        eq = equity(b)
        gross = sum(abs(p["qty"]) * _mark(b, s, p) for s, p in b["positions"].items())
        want = {}
        stale = {}
        for s, g in sig.items():
            if not g or s in b["positions"] or s in b["blocked"]:
                continue
            age = ages.get(s)
            if event and age is not None and age > EVENT_GRACE_BARS:
                stale[s] = age
                continue
            if event:
                # 同一持有段内不重复触发：新触发 K 线必须不早于上一笔入场触发 K 线 + H 根（重启后同样成立，记录在账本里）
                tb, prev = _ts(bar_t(age or 0)), _ts((b.get("last_trigger") or {}).get(s))
                if tb is not None and prev is not None and tb < prev + _hold_bars(sid) * _bar_td(sid):
                    continue
                if tb is not None and now_close is not None and tb + (_hold_bars(sid) + 1) * _bar_td(sid) <= now_close:
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
                want[s] = (side, mkt, px, src, z, ages.get(s))
        alloc = scale_to_room({s: w[4].notional for s, w in want.items()}, eq * float(rk["max_gross_exposure"]) - gross, _fee(c, "spot"))
        if stale:
            t0 = bar_t(max(stale.values()))
            if b.get("stale_skip") != t0:  # 同一次触发只记一次，避免持有期内每根都刷屏
                b["stale_skip"] = t0
                a = max(stale.values())
                ev.append(f"触发已过 {a} 根（触发 K 线开盘 {t0}），超过 {EVENT_GRACE_BARS} 根宽限，不补开 {len(stale)} 个币")
                rows["stale"].append([len(stale), a, t0])
        for s, (side, mkt, px, src, z, age) in want.items():
            n = alloc.get(s, 0.0)
            if n <= 1.0:
                continue
            f = n * _fee(c, mkt)
            b["realized"] -= f
            b["fees"] += f
            b["positions"][s] = {"symbol": s, "side": side, "market": mkt, "qty": n / px, "entry": px, "stop": z.stop_price,
                                 "notional": n, "fee_in": f, "entry_time": when, "entry_src": src, "venue": venue, "strategy": sid,
                                 "signal_bar": bar_t(age or 0), "late_bars": int(age or 0)}
            if event:
                tb = _ts(bar_t(age or 0))
                if tb is not None:
                    b["positions"][s]["expires_at"] = iso((tb + (_hold_bars(sid) + 1) * _bar_td(sid)).to_pydatetime())
                    b.setdefault("last_trigger", {})[s] = iso(tb.to_pydatetime())
            b["marks"][s] = {"px": px, "t": when}
            ev.append(f"{s} {_mk_cn(side, mkt, '开')} {n:.1f}U @{px:.6g}")
            rows["open"].append([s, _mk_cn(side, mkt, "开"), f"{n:.1f}", f"{px:.6g}"])
        b["last_decision"] = {"at": when, "events": ev, "signals": sig}
        _save(sid)
    return ev


OPEN_HEADERS = ["币种", "方向", "金额(U)", "开仓价"]
CLOSE_HEADERS = ["币种", "方向", "开仓价", "平仓价", "盈亏(U)"]


def log_text(sid: str, rows: dict) -> str:
    """影子子账本一次决策的日志：平仓表、开仓表各一张（一行一个币），过期触发单独一行说明。"""
    no = R.BY_ID.get(sid, {}).get("no")
    tag = f"影子子账本 {sid}" + (f"（#{no}，不计入主账本）" if no else "")
    parts = []
    if rows.get("close"):
        parts.append(LT.block(f"{tag} 平仓", CLOSE_HEADERS, rows["close"]))
    if rows.get("open"):
        parts.append(LT.block(f"{tag} 开仓", OPEN_HEADERS, rows["open"]))
    for n, a, t0 in rows.get("stale") or []:
        parts.append(f"\n{LT.stamp()} {tag}：触发已过 {a} 根（触发 K 线开盘 {t0} UTC），超过 {EVENT_GRACE_BARS} 根宽限，不补开 {n} 个币")
    return "".join(parts)


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
                pnl = _close(R.strategy_cfg(cfg, sid) if sid in R.BY_ID else cfg, b, q.symbol, px, "ATR止损", iso(utcnow()), q.data_source or "ws")
                log.info("%s", LT.block(f"影子子账本 {sid} · ATR 止损（不计入主账本）", CLOSE_HEADERS,
                                        [[q.symbol, _mk_cn(p["side"], p["market"], "平"), f"{p['entry']:.6g}", f"{px:.6g}", f"{pnl:+.2f}"]]))
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
        rows: dict = {}
        ev = decide(sid, fr, cfg, iso(utcnow()), rows=rows)
        _LAST["decisions"] = (_LAST["decisions"] + [{"sid": sid, "at": time.time(), "close_ms": close_ms, "events": ev}])[-50:]
        if ev:
            log.info("%s", log_text(sid, rows))
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
        b = book(sid)
        # 从未决策过的账本，或事件型持仓已过 entry+H 到期（停机 / 重启期间错过了离场）→ 启动后立刻补做一次决策
        if b.get("last_decision") is None or overdue(sid, b):
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


def _label(sid: str) -> str:
    no = R.BY_ID.get(sid, {}).get("no")
    return f"影子 #{no}" if no else f"影子 {sid}"


def trade_rows(sids: list[str] | None = None) -> list[dict]:
    """影子子账本的开平记录，字段与 /api/trades 一致（供成交页单独一栏展示），book = 「影子 #13」等。
    这些记录只属于各自独立的 1000U 影子账本，不在主账本 paper_fills 里，也不计入主账本权益 / 成交数 / 盈亏。"""
    out = []
    ids = sids if sids is not None else active_ids()
    for sid in ids:
        b = book(sid)
        lab = _label(sid)
        recs = []
        for t in b["trades"]:
            d = 1 if t["side"] == "long" else -1
            g = d * t["qty"] * (float(t["exit_price"]) - t["entry"])
            f_out = t.get("fee_out")
            if f_out is None:  # 旧记录：pnl = 价差 − 平仓费 − 开仓费
                f_out = g - float(t["pnl_usdt"]) - float(t.get("fee_in") or 0)
            recs.append((t, "closed", float(t.get("fee_in") or 0) + float(f_out), float(t["pnl_usdt"]), None))
        for s, p in b["positions"].items():
            m = _mark(b, s, p)
            d = 1 if p["side"] == "long" else -1
            recs.append((p, "open", float(p.get("fee_in") or 0), d * p["qty"] * (m - p["entry"]) - float(p.get("fee_in") or 0), m))
        for i, (t, st, fee, pnl, m) in enumerate(recs):
            entry_reason = f"{R.BY_ID.get(sid, {}).get('name', sid)}"
            if t.get("late_bars"):
                entry_reason += f"（触发后第 {t['late_bars']} 根才入场）"
            out.append({
                "trade_id": f"{lab.replace('影子 #', 'S').replace('影子 ', 'S')}-{i + 1}", "book": lab, "shadow_sid": sid,
                "symbol": t["symbol"], "market": t["market"], "side": t["side"], "qty": t["qty"],
                "entry_time": t.get("entry_time") or "", "entry_price": t["entry"], "entry_reason": entry_reason,
                "entry_action": "开多" if t["side"] == "long" else "开空", "signal_bar": t.get("signal_bar") or "",
                "exit_time": t.get("exit_time") or "", "exit_price": t.get("exit_price"),
                "exit_reason": t.get("exit_reason") or "", "exit_action": "止损" if "止损" in str(t.get("exit_reason")) else ("平仓" if st == "closed" else ""),
                "exit_note": "",
                "fee_usdt": fee, "pnl_usdt": pnl, "pnl_pct": pnl / t["notional"] if t.get("notional") else None,
                "status": st, "mode": "paper", "venue": t.get("venue") or b.get("venue") or "",
                "mark_price": m, "mark_source": "", "mark_time": (b["marks"].get(t["symbol"], {}) or {}).get("t", "") if st == "open" else "",
                "partial_tp": False, "resizes": 0,
            })
    out.sort(key=lambda r: (r["exit_time"] or r["entry_time"] or ""), reverse=True)
    return out


def summary() -> list[dict]:
    """每本影子账的对账：起始 + 已平盈亏（含手续费）+ 持仓浮盈 − 持仓开仓费 = 权益。"""
    out = []
    for sid in active_ids():
        b = book(sid)
        closed = sum(float(t["pnl_usdt"]) for t in b["trades"]) + float(b.get("trimmed_pnl", 0.0))
        up = sum((1 if p["side"] == "long" else -1) * p["qty"] * (_mark(b, s, p) - p["entry"]) for s, p in b["positions"].items())
        fin = sum(float(p.get("fee_in") or 0) for p in b["positions"].values())
        eq = equity(b)
        out.append({"sid": sid, "book": _label(sid), "no": R.BY_ID[sid].get("no"), "name": R.BY_ID[sid]["name"],
                    "start_equity": b["start_equity"], "equity": eq, "closed_pnl_usdt": closed, "unrealized_usdt": up,
                    "open_fees_usdt": fin, "open": len(b["positions"]), "closed": len(b["trades"]) + int(b.get("trimmed_n", 0)),
                    "diff_usdt": eq - (b["start_equity"] + closed + up - fin), "venue": b.get("venue")})
    return out
