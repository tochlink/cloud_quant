"""系统化信号 → 进出场时机 → 纸面执行（默认）/ 实盘（三重闸门）。"""
from __future__ import annotations

import csv
import logging
import threading

import pandas as pd

from . import settings as S
from .live import guard
from .market import MarketDataError, get_client
from .market import cache as mcache
from .market.base import INTERVAL_MS
from . import db
from .paper import ORDER_COLS, PaperBook
from .paths import OUTPUT_DIR
from .risk import cap_at_entry, scale_to_room, size
from .strategy import combine, indicators, last_cross, market_of, side_of
from .timeutil import iso, la, sh, utcnow

log = logging.getLogger(__name__)
ADVICE = {1: "做多", -1: "做空", 0: "空仓"}
MARKET_CN = {"spot": "现货", "perp": "USDT 永续", "-": "—"}
_BOOK: PaperBook | None = None
_BOOK_LOCK = threading.Lock()
CYCLE_LOCK = threading.Lock()


def book(cfg: dict | None = None) -> PaperBook:
    global _BOOK
    with _BOOK_LOCK:
        if _BOOK is None:
            cfg = cfg or S.load()
            _BOOK = PaperBook(cfg["risk"]["starting_equity_usdt"], cfg["fees"]["taker_bps"])
        elif cfg:
            _BOOK.fee = cfg["fees"]["taker_bps"] / 10_000
        if cfg:
            _MARK["venue"] = cfg["venue"]
        return _BOOK


_MARK = {"venue": None, "dirty": False}


def mark_from_stream(q) -> None:
    """WS/REST 实时报价回调：只给“同交易所 + 同市场”的纸面持仓计价（现货多用现货价，永续空用永续标记价）。"""
    if _BOOK is None or q.venue.lower() != _MARK["venue"]:
        return
    p = _BOOK.positions.get(q.symbol)
    if p and p.market == q.market:
        _BOOK.mark(q.symbol, q.price, iso(q.ts), q.data_source)
        _MARK["dirty"] = True


def persist_marks() -> bool:
    if _BOOK is not None and _MARK["dirty"]:
        _MARK["dirty"] = False
        _BOOK.save()
        return True
    return False


def poll_stops(cfg: dict | None = None) -> list[str]:
    """Worker 周期之间用最新公共价检查 ATR 止损，避免最多等 interval_sec 才离场。

    只平仓已触及止损的纸面持仓；信号反转仍由 run_cycle 处理。拿不到报价就跳过该币。
    """
    events: list[str] = []
    if not CYCLE_LOCK.acquire(blocking=False):
        return events  # 正在跑完整周期，让 run_cycle 自己处理
    try:
        cfg = cfg or S.load()
        bk = book(cfg)
        venue = cfg["venue"]
        if not bk.positions:
            return events
        touched = False
        for s, p in list(bk.positions.items()):
            try:
                px, kind, q = _quote(venue, s, p.market)
            except MarketDataError:
                continue
            bk.mark(s, px, iso(q.ts), q.data_source)
            touched = True
            hit = (p.side == "long" and px <= p.stop_price) or (p.side == "short" and px >= p.stop_price)
            if not hit:
                continue
            side = p.side
            qty = p.qty
            mkt = p.market
            bk.blocks[s] = p.direction
            pnl = bk.close(s, px, kind, "ATR止损", venue, data_source=q.data_source, price_time=iso(q.ts))
            _route(cfg, s, mkt, "close_long" if side == "long" else "close_short", qty, px)
            events.append(f"{s} 平{('多' if side == 'long' else '空')} @ {px:g}（ATR止损·实时，盈亏 {pnl:+.2f}）")
        if events:
            bk.snapshot("；".join(events)[:240])
            export_paper_csv(cfg)
        elif touched:
            bk.save()
        return events
    finally:
        CYCLE_LOCK.release()



def _quote(venue: str, sym: str, market: str):
    """真实公共报价：现货最新价 / 永续标记价。

    优先用官方公共 WebSocket 推送的最新值（≤ 30 秒内），否则走官方公共 REST。
    失败抛 MarketDataError，绝不回退到虚构价格。
    """
    from . import stream
    q = stream.latest(venue, sym, market, max_age_sec=30)
    if q is None:
        q = get_client(venue).quote(sym, market)
    return q.price, q.kind, q




def compute_signals(cfg: dict, with_quotes: bool = True) -> dict:
    st, rk = cfg["strategy"], cfg["risk"]
    venue = cfg["venue"]
    need = max(st["lookback_bars"], st["slow_ma"] + st["atr_period"] + 5)
    frames, errs = mcache.many(venue, cfg["symbols"], st["interval"], need)
    bk = book(cfg)
    eq = bk.equity()
    step = pd.Timedelta(milliseconds=INTERVAL_MS[st["interval"]])
    rows = []
    for sym in cfg["symbols"]:
        ind = {}
        for m in ("spot", "perp"):
            df = frames.get(m, {}).get(sym)
            if df is not None and len(df) >= st["slow_ma"] + 1:
                ind[m] = indicators(df, st["fast_ma"], st["slow_ma"], st["atr_period"])
                ind[m].attrs.update(df.attrs)
        if not ind:
            rows.append({"symbol": sym, "error": "；".join(v for k, v in errs.items() if k.startswith(sym + ":")) or "K 线不足"})
            continue
        ssig = int(ind["spot"]["signal"].iloc[-1]) if "spot" in ind else 0
        psig = int(ind["perp"]["signal"].iloc[-1]) if "perp" in ind else 0
        sig = int(combine([ssig], [psig])[0])
        side, mkt = side_of(sig), market_of(sig)
        use = mkt if mkt in ind else ("spot" if "spot" in ind else "perp")
        src = ind[use]
        last = src.iloc[-1]
        # 合成信号序列（两市场按开盘时间对齐）→ 信号起始时间
        if "spot" in ind and "perp" in ind:
            j = ind["spot"][["open_time", "close_time", "signal"]].merge(
                ind["perp"][["open_time", "signal"]], on="open_time", suffixes=("_s", "_p"))
            j["signal"] = combine(j["signal_s"], j["signal_p"])
        else:
            j = src[["open_time", "close_time", "signal"]].copy()
            if "perp" not in ind:
                j["signal"] = combine(j["signal"], [0] * len(j))
            else:
                j["signal"] = combine([0] * len(j), j["signal"])
        cross = last_cross(j)
        as_of = last["close_time"]
        warn = [f"{m} 数据不可用：{errs.get(f'{sym}:{m}', 'K 线不足')}" for m in ("spot", "perp") if m not in ind]
        if "spot" in ind and "perp" in ind and ind["spot"]["close_time"].iloc[-1] != ind["perp"]["close_time"].iloc[-1]:
            warn.append("现货与永续最新收盘 K 线时间不一致")
        row = {
            "symbol": sym, "rule_id": st["rule_id"], "signal": sig, "advice": ADVICE[sig], "side": side,
            "market": mkt, "market_cn": MARKET_CN[mkt], "signal_market": use,
            "spot_signal": ssig, "perp_signal": psig, "conflict": bool(ssig == 1 and psig == -1),
            "bar_close": float(last["close"]),
            "sma_fast": float(last["sma_fast"]), "sma_slow": float(last["sma_slow"]), "atr": float(last["atr"]),
            "spot_close": float(ind["spot"]["close"].iloc[-1]) if "spot" in ind else None,
            "perp_close": float(ind["perp"]["close"].iloc[-1]) if "perp" in ind else None,
            "as_of": iso(as_of.to_pydatetime()), "as_of_la": la(as_of.to_pydatetime()),
            "as_of_sh": sh(as_of.to_pydatetime()),
            "signal_since": iso(cross.to_pydatetime()) if cross is not None else "",
            "next_check": iso((as_of + step).to_pydatetime()), "next_check_la": la((as_of + step).to_pydatetime()),
            "next_check_sh": sh((as_of + step).to_pydatetime()),
            "venue": venue, "data_source": src.attrs.get("data_source", ""), "source_host": src.attrs.get("source_host", ""),
            "fetched_at": src.attrs.get("fetched_at", ""), "candle_cache": src.attrs.get("cache", ""),
            "error": "", "warning": "；".join(warn),
        }
        px, kind = float(last["close"]), "bar_close"
        if with_quotes and mkt != "-":
            try:
                px, kind, q = _quote(venue, sym, mkt)
                row.update(ref_price_time=iso(q.ts), ref_price_source=q.data_source, ref_price_host=q.source_host)
            except MarketDataError as e:
                row["error"] = f"报价失败：{e}"
        row["ref_price"], row["ref_price_kind"] = px, kind
        pos = bk.positions.get(sym)
        z = size(side=side, equity=eq, price=px, atr=row["atr"], max_risk=rk["max_risk_per_trade"],
                 max_weight=rk["max_weight_per_name"], atr_mult=st["atr_stop_mult"])
        row.update({"target_notional_usdt": z.notional, "target_qty": z.qty, "target_weight": z.weight,
                    "stop_price": z.stop_price, "stop_pct": z.stop_pct, "risk_usdt": z.risk_usdt, "capped_by": z.capped_by})
        blocked = bk.blocks.get(sym) == sig and sig != 0
        if pos and pos.side == side:
            entry = f"持有中：{pos.entry_time} 以 {pos.entry_price:g} 入场"
            exit_ = f"出现反向/归零信号（下次收盘检查 {row['next_check_sh']}）或价格触及止损 {pos.stop_price:g} 时离场"
            row["stop_price"] = pos.stop_price
            state = "holding"
        elif sig == 0:
            entry, exit_, state = "无信号，保持空仓", "—", "flat"
        elif blocked:
            entry = "已止损，观望中：等待信号方向改变后再入场"
            exit_, state = "—", "blocked"
        else:
            entry = f"信号自 {row['signal_since'] or '数据起点'} 生效 → 下一个执行周期按最新{('现货价' if mkt == 'spot' else '标记价')}入场"
            exit_ = f"止损 {z.stop_price:.6g}（{st['atr_stop_mult']}×ATR）；或收盘出现反向交叉时离场"
            state = "entry_pending"
        row.update({"entry_timing": entry, "exit_timing": exit_, "state": state,
                    "position_side": pos.side if pos else "flat"})
        rows.append(row)
    # 待入场标的：按剩余总敞口等比缩放后的建议仓位
    pend = {r["symbol"]: r for r in rows if r.get("state") == "entry_pending"}
    alloc = scale_to_room({s: r["target_notional_usdt"] for s, r in pend.items()},
                          eq * rk["max_gross_exposure"] - bk.gross(), bk.fee)
    for s, r in pend.items():
        if alloc[s] < r["target_notional_usdt"] - 1e-9:
            r["capped_by"] = "gross"
        r["target_notional_usdt"] = alloc[s]
        r["target_qty"] = alloc[s] / r["ref_price"] if r["ref_price"] else 0
        r["target_weight"] = alloc[s] / eq if eq else 0
        r["risk_usdt"] = alloc[s] * r["stop_pct"]
    led = bk.ledger()
    for r in rows:  # 已持仓的显示实际仓位，并用开仓数据回填真正收紧仓位的约束
        p = bk.positions.get(r["symbol"])
        if p and r.get("state") == "holding":
            r["target_notional_usdt"] = abs(p.qty * p.mark_price)
            r["target_qty"] = p.qty
            r["target_weight"] = r["target_notional_usdt"] / eq if eq else 0
            r["risk_usdt"] = abs(p.qty * (p.stop_price - p.mark_price)) if p.direction * (p.mark_price - p.stop_price) > 0 else 0.0
            r["capped_by"] = cap_at_entry(
                entry_notional=p.notional_entry, entry_price=p.entry_price, stop_price=p.stop_price,
                entry_equity=_equity_near(led, p.entry_time, bk.starting),
                max_risk=rk["max_risk_per_trade"], max_weight=rk["max_weight_per_name"])
    return {"generated_at": iso(utcnow()), "generated_at_la": la(utcnow()), "generated_at_sh": sh(utcnow()),
            "venue": venue, "equity": eq,
            "rows": rows, "errors": errs}


def _equity_near(ledger: list[dict], when: str, fallback: float) -> float:
    """Ledger equity at or just before entry; else the first snapshot / starting capital."""
    if not ledger:
        return fallback
    before = [float(r["equity_usdt"]) for r in ledger if r.get("time") and when and r["time"] <= when]
    if before:
        return before[-1]
    return float(ledger[0].get("equity_usdt") or fallback)


def _log_order(**kw):
    book().log_order(**kw)


def _trader(cfg):
    from . import vault
    keys = vault.get_keys(cfg["venue"])
    if not keys:
        return None
    if cfg["venue"] == "okx":
        from .live.okx import OkxTrader
        return OkxTrader(keys, demo=cfg["live"]["okx_demo"])
    from .live.gate import GateTrader
    return GateTrader(keys, testnet=cfg["live"]["gate_testnet"])


def _route(cfg, sym, market, action, qty, price):
    """纸面执行之外，若实盘闸门全部通过才会发单；否则只记录被拦截原因。"""
    mode = "live" if S.live_armed(cfg) else "paper"
    if mode == "paper":
        _log_order(mode="paper", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="paper_filled", detail="纸面成交")
        return
    ok, reasons = guard.check(cfg, cfg["venue"])
    if not ok:
        _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="blocked", detail="；".join(reasons))
        return
    try:
        tr = _trader(cfg)
        spec = get_client(cfg["venue"]).perp_spec(sym) if market == "perp" else None
        res = tr.place_order(cfg, sym, market, action, qty, price, spec)
        _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="sent", detail=str(res)[:300])
    except Exception as e:  # noqa: BLE001
        _log_order(mode="live", venue=cfg["venue"], symbol=sym, market=market, action=action, qty=qty,
                   ref_price=price, status="error", detail=str(e)[:300])


def run_cycle(cfg: dict | None = None, note: str = "") -> dict:
    with CYCLE_LOCK:
        cfg = cfg or S.load()
        bk = book(cfg)
        venue, st, rk = cfg["venue"], cfg["strategy"], cfg["risk"]
        sig = compute_signals(cfg, with_quotes=False)
        events, errors = [], dict(sig["errors"])
        rows = {r["symbol"]: r for r in sig["rows"] if not r.get("error")}
        # 1) 用最新公共价格给持仓计价
        prices = {}
        for s, p in list(bk.positions.items()):
            try:
                px, kind, q = _quote(venue, s, p.market)
                prices[s] = (px, kind, q)
                bk.mark(s, px, iso(q.ts), q.data_source)
            except MarketDataError as e:
                errors[s] = f"报价失败：{e}"
        # 2) 离场：信号改变 / 触及止损
        for s, p in list(bk.positions.items()):
            if s not in prices or s not in rows:
                continue
            px, kind, q = prices[s]
            want = rows[s]["side"]
            reason = None
            if want != p.side:
                reason = "信号反转" if want != "flat" else "信号转空仓"
            elif (p.side == "long" and px <= p.stop_price) or (p.side == "short" and px >= p.stop_price):
                reason = "ATR止损"
                bk.blocks[s] = p.direction
            if reason:
                pnl = bk.close(s, px, kind, reason, venue, data_source=q.data_source, price_time=iso(q.ts))
                _route(cfg, s, p.market, "close_long" if p.side == "long" else "close_short", p.qty, px)
                events.append(f"{s} 平{('多' if p.side == 'long' else '空')} @ {px:g}（{reason}，盈亏 {pnl:+.2f}）")
        # 解除止损锁
        for s in list(bk.blocks):
            if s in rows and rows[s]["signal"] != bk.blocks[s]:
                bk.blocks.pop(s)
        bk.save()
        # 3) 入场（多个新仓按剩余总敞口额度等比缩放，并预留手续费）
        eq = bk.equity()
        want = {}
        for s in cfg["symbols"]:
            r = rows.get(s)
            if not r or s in bk.positions or r["signal"] == 0 or bk.blocks.get(s) == r["signal"]:
                continue
            if r["side"] == "long" and not rk["allow_spot_long"] or r["side"] == "short" and not rk["allow_perp_short"]:
                continue
            try:
                px, kind, q = _quote(venue, s, r["market"])
            except MarketDataError as e:
                errors[s] = f"报价失败：{e}"
                continue
            # 止损所用 ATR 必须来自该市场自己的 K 线（做多=现货，做空=永续）
            if r["signal_market"] != r["market"]:
                errors[s] = f"{r['market']} K 线不可用，跳过入场"
                continue
            z = size(side=r["side"], equity=eq, price=px, atr=r["atr"], max_risk=rk["max_risk_per_trade"],
                     max_weight=rk["max_weight_per_name"], atr_mult=st["atr_stop_mult"])
            if z.notional > 0:
                want[s] = (r, px, kind, z, q)
        room = eq * rk["max_gross_exposure"] - bk.gross()
        alloc = scale_to_room({s: w[3].notional for s, w in want.items()}, room, bk.fee)
        for s, (r, px, kind, z, q) in want.items():
            if alloc[s] < 1.0:
                continue
            qty = alloc[s] / px
            bk.open(symbol=s, market=r["market"], side=r["side"], qty=qty, price=px, price_kind=kind,
                    stop=z.stop_price, signal_bar=r["as_of"], reason=f"{r['advice']}信号（{st['rule_id']}）", venue=venue,
                    data_source=q.data_source, price_time=iso(q.ts))
            _route(cfg, s, r["market"], "open_long" if r["side"] == "long" else "open_short", qty, px)
            events.append(f"{s} 开{('多·现货' if r['side'] == 'long' else '空·永续')} {qty:.6g} @ {px:g}，止损 {z.stop_price:.6g}")
        snap = bk.snapshot(note or ("; ".join(events)[:240] if events else "无变化"))
        export_paper_csv(cfg)
        return {"time": snap["time"], "time_la": la(utcnow()), "time_sh": sh(utcnow()), "events": events, "errors": errors, "snapshot": snap}


def kill_switch(cfg: dict | None = None) -> dict:
    """紧急停止：关闭自动交易与实盘开关，并按最新公共价平掉全部纸面持仓。"""
    cfg = S.update({"worker": {"enabled": False}, "live": {"mode": "paper", "live_enabled": False, "confirm_phrase": ""}})
    from . import worker
    worker.stop()
    with CYCLE_LOCK:
        bk = book(cfg)
        events = []
        for s, p in list(bk.positions.items()):
            try:
                px, kind, q = _quote(cfg["venue"], s, p.market)
                src, pt = q.data_source, iso(q.ts)
            except MarketDataError:
                # 拿不到新报价时使用该持仓最后一次真实公共标记价（明确标注时间），不编造价格
                px, kind, src, pt = p.mark_price, f"last_real_mark@{p.mark_time}", p.mark_source, p.mark_time
            pnl = bk.close(s, px, kind, "紧急停止(Kill Switch)", cfg["venue"], data_source=src, price_time=pt)
            events.append(f"{s} 已平仓 @ {px:g}（{kind}），盈亏 {pnl:+.2f}")
        bk.snapshot("Kill Switch：全部平仓并停止自动交易")
        export_paper_csv(cfg)
    return {"time": iso(utcnow()), "events": events}


def export_paper_csv(cfg: dict) -> list[str]:
    """把纸面账本导出为 output/ 下的 CSV 交付物。"""
    bk = book(cfg)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    pos_rows = []
    for p in bk.positions.values():
        pos_rows.append({"symbol": p.symbol, "market": p.market, "side": p.side, "qty": p.qty,
                         "entry_price": p.entry_price, "entry_time": p.entry_time, "mark_price": p.mark_price,
                         "mark_time": p.mark_time, "mark_source": p.mark_source, "venue": p.venue, "stop_price": p.stop_price,
                         "notional_usdt": p.qty * p.mark_price,
                         "weight": p.qty * p.mark_price / bk.equity() if bk.equity() else 0,
                         "unrealized_pnl_usdt": p.upnl()})
    for name, rows in (("paper_positions.csv", pos_rows), ("paper_fills.csv", bk.fills()), ("paper_ledger.csv", bk.ledger()),
                       ("paper_orders.csv", bk.orders(100000)[::-1])):
        path = OUTPUT_DIR / name
        cols = list(rows[0].keys()) if rows else ["empty"]
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        out.append(str(path))
    return out


def export_signals_csv(sig: dict) -> str:
    path = OUTPUT_DIR / "signals.csv"
    rows = [r for r in sig["rows"] if not r.get("error")]
    cols = ["symbol", "venue", "market", "data_source", "source_host", "fetched_at", "rule_id", "signal", "spot_signal",
            "perp_signal", "conflict", "advice", "signal_market", "ref_price", "ref_price_kind", "ref_price_time",
            "ref_price_source", "spot_close", "perp_close", "bar_close", "sma_fast",
            "sma_slow", "atr", "as_of", "signal_since", "next_check", "target_notional_usdt", "target_qty",
            "target_weight", "stop_price", "risk_usdt", "capped_by", "state", "entry_timing", "exit_timing"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return str(path)
