"""FastAPI 服务：REST API + 静态单页前端。只监听 127.0.0.1。"""
from __future__ import annotations

import csv
import logging
import math
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from fastapi import Body, FastAPI, HTTPException
import asyncio
import json

from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, db, engine, stream, vault, worker
from . import settings as S
from .backtest import run_backtest
from .live import guard
from .logsafe import setup_logging
from .market import MarketDataError
from .market import cache as mcache
from .paths import OUTPUT_DIR, STATIC_DIR, ensure_dirs
from .strategy import indicators
from .timeutil import iso, la, sh, utcnow

setup_logging()
log = logging.getLogger("qtw")
ensure_dirs()
app = FastAPI(title="QTW 量化交易控制台", version=__version__)
_bt_lock = threading.Lock()
_last_bt: dict[str, Any] = {}


def clean(o):
    """NaN/Inf → None，numpy → python，保证 JSON 可序列化。"""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        try:
            o = o.item()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def ok(data) -> JSONResponse:
    return JSONResponse(clean(data))


def _mark_persister():
    import time as _t
    while True:
        _t.sleep(15)
        try:
            engine.persist_marks()
        except Exception:  # noqa: BLE001
            log.exception("persist marks failed")
        try:
            db.checkpoint_wal("PASSIVE")
        except Exception:  # noqa: BLE001
            log.debug("wal checkpoint skipped", exc_info=True)


@app.on_event("startup")
def _startup():
    db.connect()
    cfg = S.save(S.load())  # 确保非敏感设置落在 SQLite
    bk = engine.book(cfg)
    if bk.migrated:
        log.info("已把旧版 CSV 纸面账本迁移到 SQLite：%s", bk.migrated)
    stream.on_quote(engine.mark_from_stream)
    stream.start()
    threading.Thread(target=_mark_persister, name="qtw-mark-persist", daemon=True).start()
    if cfg["worker"]["enabled"]:
        worker.start()
    log.info("QTW %s 已启动；模式=%s；实盘闸门=%s", __version__, cfg["live"]["mode"],
             "通过" if guard.check(cfg, cfg["venue"])[0] else "关闭")


# ---------------- 状态 / 总览 ----------------
@app.get("/api/status")
def status():
    cfg = S.load()
    live_ok, reasons = guard.check(cfg, cfg["venue"])
    return ok({"version": __version__, "time": iso(utcnow()), "time_la": la(utcnow()), "time_sh": sh(utcnow()), "settings": cfg,
               "mode": "live" if S.live_armed(cfg) else "paper", "live_gate_open": live_ok,
               "live_block_reasons": reasons, "worker": worker.status(), "vault": vault.status(),
               "stream": stream.status(), "db": {"path": str(db.db_path()), "counts": db.counts()},
               "confirm_phrase_required": S.LIVE_CONFIRM_PHRASE})


@app.get("/api/health")
def health():
    """Lightweight smoke probe. No secrets, no vault, no full settings dump."""
    cfg = S.load()
    st = stream.status()
    w = worker.status()
    return ok({
        "ok": True,
        "mode": "live" if S.live_armed(cfg) else "paper",
        "stream": {
            "mode": st.get("mode"),
            "quotes_ws_fresh": st.get("quotes_ws_fresh"),
            "quotes_rest_fresh": st.get("quotes_rest_fresh"),
        },
        "quotes_ws_fresh": st.get("quotes_ws_fresh"),
        "worker": {"running": bool(w.get("running"))},
        "time": iso(utcnow()),
    })


def _closed_trades(fills: list[dict]) -> list[dict]:
    return [f for f in fills if f["action"] == "close"]


@app.get("/api/dashboard")
def dashboard():
    cfg = S.load()
    bk = engine.book(cfg)
    eq = bk.equity()
    positions = [{"symbol": p.symbol, "market": p.market, "side": p.side, "qty": p.qty, "entry_price": p.entry_price,
                  "entry_time": p.entry_time, "mark_price": p.mark_price, "mark_time": p.mark_time,
                  "mark_source": p.mark_source, "venue": p.venue,
                  "stop_price": p.stop_price, "notional": p.qty * p.mark_price,
                  "weight": (p.qty * p.mark_price / eq) if eq else 0, "upnl": p.upnl()}
                 for p in bk.positions.values()]
    fills = bk.fills()
    ledger = bk.ledger()
    closed = _closed_trades(fills)
    wins = [f for f in closed if float(f["realized_pnl_usdt"]) > 0]
    week_ago = (utcnow() - timedelta(days=7)).isoformat()
    week_fills = [f for f in fills if f["time"].replace("Z", "+00:00") >= week_ago]
    eqs = [float(r["equity_usdt"]) for r in ledger] or [eq]
    peak, dd = -1e18, []
    for v in eqs:
        peak = max(peak, v)
        dd.append(v / peak - 1 if peak > 0 else 0)
    week_ledger = [r for r in ledger if r["time"].replace("Z", "+00:00") >= week_ago]
    week_start_eq = float(week_ledger[0]["equity_usdt"]) if week_ledger else bk.starting
    return ok({
        "time": iso(utcnow()), "time_la": la(utcnow()), "time_sh": sh(utcnow()), "mode": "live" if S.live_armed(cfg) else "paper",
        "venue": cfg["venue"], "starting_equity": bk.starting, "equity": eq, "realized": bk.realized,
        "unrealized": eq - bk.realized, "cash_free": max(0.0, eq - bk.gross()) if abs(eq - bk.gross()) < 1e-6 else eq - bk.gross(), "gross": bk.gross(), "net": bk.net(),
        "total_pnl": eq - bk.starting, "total_return": eq / bk.starting - 1,
        "week": {"pnl": eq - week_start_eq,
                 "gains": sum(float(f["realized_pnl_usdt"]) for f in week_fills if float(f["realized_pnl_usdt"]) > 0),
                 "losses": sum(float(f["realized_pnl_usdt"]) for f in week_fills if float(f["realized_pnl_usdt"]) < 0),
                 "fills": len(week_fills)},
        "positions": positions, "recent_fills": list(reversed(fills[-12:])),
        "ledger": [{"time": r["time"], "equity": float(r["equity_usdt"]), "gross": float(r["gross_exposure_usdt"]),
                    "net": float(r["net_exposure_usdt"])} for r in ledger[-300:]],
        "drawdown": dd[-300:], "max_drawdown": min(dd) if dd else 0, "closed_trades": len(closed),
        "win_rate": (len(wins) / len(closed)) if closed else None, "worker": worker.status(),
        "pnl_by_trade": [float(f["realized_pnl_usdt"]) for f in closed[-30:]],
    })


@app.get("/api/signals")
def signals(quotes: bool = True):
    cfg = S.load()
    sig = engine.compute_signals(cfg, with_quotes=quotes)
    sig["csv"] = engine.export_signals_csv(sig)
    return ok(sig)


@app.get("/api/candles")
def candles(symbol: str, bars: int = 300, market: str = "spot"):
    cfg = S.load()
    st = cfg["strategy"]
    if market not in ("spot", "perp"):
        raise HTTPException(400, "market 只能是 spot 或 perp")
    bars = max(st["slow_ma"] + 10, min(1000, bars))
    try:
        df = mcache.candles(cfg["venue"], symbol.upper(), st["interval"], bars, market)
    except MarketDataError as e:
        raise HTTPException(502, f"行情获取失败：{e}") from e
    ind = indicators(df, st["fast_ma"], st["slow_ma"], st["atr_period"])
    t = ((ind["open_time"] - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)).astype(int).tolist()
    ch = ind["signal"].ne(ind["signal"].shift(1)) & ind["sma_slow"].notna() & ind["signal"].shift(1).notna()
    markers = [{"time": int(t[i]), "signal": int(ind["signal"].iloc[i])} for i in range(len(ind)) if ch.iloc[i] and i > 0]
    return ok({"symbol": symbol.upper(), "venue": cfg["venue"], "interval": st["interval"], "market": market,
               "data_source": df.attrs.get("data_source"), "source_host": df.attrs.get("source_host"),
               "fetched_at": df.attrs.get("fetched_at"),
               "candles": [{"time": int(t[i]), "open": r.open, "high": r.high, "low": r.low, "close": r.close}
                           for i, r in enumerate(ind.itertuples())],
               "fast": [{"time": int(t[i]), "value": v} for i, v in enumerate(ind["sma_fast"]) if not pd.isna(v)],
               "slow": [{"time": int(t[i]), "value": v} for i, v in enumerate(ind["sma_slow"]) if not pd.isna(v)],
               "markers": markers})


# ---------------- 纸面 / 自动交易 ----------------
@app.post("/api/cycle")
def cycle():
    try:
        return ok(engine.run_cycle(S.load(), note="手动执行"))
    except MarketDataError as e:
        raise HTTPException(502, str(e)) from e


@app.post("/api/worker/{action}")
def worker_ctl(action: str):
    if action == "start":
        S.update({"worker": {"enabled": True}})
        worker.start()
    elif action == "stop":
        S.update({"worker": {"enabled": False}})
        worker.stop()
    else:
        raise HTTPException(404)
    return ok(worker.status())


@app.post("/api/kill")
def kill():
    return ok(engine.kill_switch())


@app.post("/api/paper/reset")
def paper_reset():
    cfg = S.load()
    if worker.status()["running"]:
        raise HTTPException(409, "请先停止自动交易")
    engine.book(cfg).reset(cfg["risk"]["starting_equity_usdt"])
    engine.export_paper_csv(cfg)
    return ok({"reset": True})


@app.get("/api/fills")
def fills():
    return ok(list(reversed(engine.book().fills())))


@app.get("/api/orders")
def orders():
    return ok(engine.book().orders(300))


# ---------------- 设置 / 密钥 ----------------
@app.get("/api/settings")
def get_settings():
    return ok(S.load())


@app.put("/api/settings")
def put_settings(patch: dict = Body(...)):
    patch.pop("live", None)  # 实盘相关只能走 /api/live
    # 有纸面持仓时禁止切换行情源：入场价/止损应按同一交易所公共价计价，避免 OKX↔Gate 混用
    if "venue" in patch:
        cur = S.load()
        want = str(patch.get("venue") or "").lower()
        if want in ("okx", "gate") and want != cur.get("venue"):
            bk = engine.book(cur)
            if bk.positions:
                n = len(bk.positions)
                raise HTTPException(
                    409,
                    f"当前有 {n} 个纸面持仓，不能切换行情源。请先平仓（紧急停止）或重置账本后再切换 OKX / Gate。",
                )
    try:
        return ok(S.update(patch))
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(400, str(e)) from e


@app.put("/api/live")
def put_live(body: dict = Body(...)):
    """切换纸面/实盘。开启实盘必须同时提交确认语；关闭随时可以。"""
    cur = S.load()["live"]
    new = {**cur, **{k: body[k] for k in ("mode", "live_enabled", "okx_demo", "gate_testnet", "confirm_phrase") if k in body}}
    if new["mode"] == "live" or new["live_enabled"]:
        if new.get("confirm_phrase") != S.LIVE_CONFIRM_PHRASE:
            raise HTTPException(400, f"开启实盘需要输入确认语：{S.LIVE_CONFIRM_PHRASE}")
    else:
        new["confirm_phrase"] = ""
    cfg = S.update({"live": new})
    okk, reasons = guard.check(cfg, cfg["venue"])
    return ok({"live": cfg["live"], "live_gate_open": okk, "live_block_reasons": reasons})


@app.get("/api/keys")
def keys_status():
    return ok(vault.status())


@app.put("/api/keys/{exchange}")
def keys_put(exchange: str, body: dict = Body(...)):
    try:
        vault.set_keys(exchange, body)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return ok(vault.status())


@app.delete("/api/keys/{exchange}")
def keys_delete(exchange: str):
    vault.delete_keys(exchange)
    return ok(vault.status())


@app.post("/api/keys/{exchange}/test")
def keys_test(exchange: str):
    """只读连通性测试：查询余额，不下单。"""
    k = vault.get_keys(exchange)
    if not k:
        raise HTTPException(400, "密钥未完整配置")
    cfg = S.load()
    try:
        if exchange == "okx":
            from .live.okx import OkxTrader
            r = OkxTrader(k, demo=cfg["live"]["okx_demo"]).balance()
            n = len((r.get("data") or [{}])[0].get("details", []))
        else:
            from .live.gate import GateTrader
            r = GateTrader(k).balance()
            n = len(r) if isinstance(r, list) else 0
        return ok({"ok": True, "message": f"连接成功（只读），返回 {n} 个币种余额"})
    except Exception as e:  # noqa: BLE001
        return ok({"ok": False, "message": str(e)[:300]})


# ---------------- 回测 ----------------
def _bt_payload(run: dict, eqdf: pd.DataFrame, trades: pd.DataFrame) -> dict:
    step = max(1, len(eqdf) // 800)
    return {"run_id": run["run_id"], "summary": run["summary"], "data_errors": run.get("data_errors", {}),
            "generated_at": run["created_at"], "generated_at_la": la(pd.Timestamp(run["created_at"]).to_pydatetime()),
            "generated_at_sh": sh(pd.Timestamp(run["created_at"]).to_pydatetime()),
            "equity": [{"time": int(pd.Timestamp(r.time).timestamp()), "equity": r.equity, "drawdown": r.drawdown}
                       for r in eqdf.iloc[::step].itertuples()],
            "trades": trades.to_dict("records")}


@app.post("/api/backtest")
def backtest(body: dict = Body(default={})):
    cfg = S.load()
    if body.get("venue") in ("okx", "gate"):
        cfg["venue"] = body["venue"]
    for k in ("fast_ma", "slow_ma", "atr_stop_mult"):
        if body.get(k) is not None:
            cfg["strategy"][k] = body[k]
    cfg = S.validate(cfg)
    bars = int(body.get("bars", 1500))
    bars = max(cfg["strategy"]["slow_ma"] + 50, min(5000, bars))
    if not _bt_lock.acquire(blocking=False):
        raise HTTPException(409, "已有回测在运行")
    try:
        frames, errs = mcache.many(cfg["venue"], cfg["symbols"], cfg["strategy"]["interval"], bars)
        if not frames["spot"] or not frames["perp"]:
            raise HTTPException(502, f"官方公共行情获取失败（不会用任何替代数据）：{errs}")
        try:
            res = run_backtest(frames, cfg)
        except ValueError as e:
            raise HTTPException(502, f"{e}；行情错误：{errs}") from e
        prov = mcache.data_provenance(frames)
        created = iso(utcnow())
        summ = {**res["summary"], "venue": cfg["venue"], **prov, "bars_requested": bars,
                "data_errors": "; ".join(f"{k}: {v}" for k, v in errs.items())}
        eqdf, tr = res["equity"], res["trades"]
        with db.tx() as c:
            cur = c.execute("INSERT INTO backtest_runs(created_at,venue,data_source,fetched_at,params,summary) VALUES(?,?,?,?,?,?)",
                            (created, cfg["venue"], prov["data_source"], prov["fetched_at"],
                             db.dumps({"strategy": cfg["strategy"], "risk": cfg["risk"], "fees": cfg["fees"],
                                       "symbols": cfg["symbols"], "bars": bars}), db.dumps(clean(summ))))
            run_id = cur.lastrowid
            c.executemany("INSERT INTO backtest_equity VALUES(?,?,?,?,?,?,?)",
                          [(run_id, r.time, r.equity, r.drawdown, r.gross_exposure, r.net_exposure, int(r.positions))
                           for r in eqdf.itertuples()])
            cols = ["symbol", "market", "side", "entry_time", "entry_price", "qty", "notional_usdt", "stop_price", "exit_time",
                    "exit_price", "exit_reason", "pnl_usdt", "fees_usdt", "return_pct", "bars_held", "status"]
            c.executemany(f"INSERT INTO backtest_trades(run_id,seq,{','.join(cols)}) VALUES({','.join('?' * (len(cols) + 2))})",
                          [(run_id, i, *[clean(getattr(r, k)) for k in cols]) for i, r in enumerate(tr.itertuples())])
        _export_bt(run_id, summ, eqdf, tr, cfg["venue"], prov)
        return ok(_bt_payload({"run_id": run_id, "summary": {**summ, "run_id": run_id}, "created_at": created,
                               "data_errors": errs}, eqdf, tr))
    finally:
        _bt_lock.release()


def _export_bt(run_id, summ, eqdf, tr, venue, prov):
    d = OUTPUT_DIR / "backtest"
    d.mkdir(parents=True, exist_ok=True)
    tag = {"run_id": run_id, "venue": venue, "data_source": prov["data_source"], "fetched_at": prov["fetched_at"]}
    eqdf.assign(**tag).to_csv(d / "backtest_equity.csv", index=False)
    tr.assign(**tag, price_market=tr["side"].map({"long": "spot", "short": "perp"})).to_csv(d / "backtest_trades.csv", index=False)
    pd.DataFrame([{"metric": k, "value": v} for k, v in {"run_id": run_id, **summ}.items()]).to_csv(
        d / "backtest_summary.csv", index=False)


@app.get("/api/backtest/latest")
def backtest_latest():
    r = db.query("SELECT * FROM backtest_runs ORDER BY run_id DESC LIMIT 1")
    if not r:
        return ok({})
    run = r[0]
    run["summary"] = {**json.loads(run["summary"]), "run_id": run["run_id"]}
    eqdf = pd.DataFrame(db.query("SELECT time, equity, drawdown FROM backtest_equity WHERE run_id=? ORDER BY time", (run["run_id"],)))
    tr = pd.DataFrame(db.query("SELECT * FROM backtest_trades WHERE run_id=? ORDER BY seq", (run["run_id"],)))
    tr = tr.drop(columns=["run_id", "seq"], errors="ignore").fillna({"exit_time": "", "exit_reason": ""})
    return ok(_bt_payload(run, eqdf, tr))


@app.get("/api/backtest/runs")
def backtest_runs():
    rows = db.query("SELECT run_id, created_at, venue, data_source, fetched_at, summary FROM backtest_runs ORDER BY run_id DESC LIMIT 50")
    for r in rows:
        sm = json.loads(r.pop("summary"))
        r.update({k: sm.get(k) for k in ("total_return", "max_drawdown", "sharpe", "win_rate", "start_time", "end_time", "bars")})
    return ok(rows)


# ---------------- 实时推送（SSE） ----------------
def _live_payload() -> dict:
    cfg = S.load()
    bk = engine.book(cfg)
    eq = bk.equity()
    snap = stream.snapshot(cfg["venue"])
    return clean({
        "time": iso(utcnow()), "venue": cfg["venue"], "interval": cfg["strategy"]["interval"],
        "stream": {k: v for k, v in stream.status().items() if k != "connections"},
        "connections": [{k: c[k] for k in ("name", "status", "url", "last_msg", "reconnects", "last_error")}
                        for c in stream.status()["connections"]],
        "prices": snap["prices"], "forming": snap["forming"],
        "paper": {"equity": eq, "realized": bk.realized, "unrealized": eq - bk.realized, "gross": bk.gross(),
                  "net": bk.net(), "total_pnl": eq - bk.starting,
                  "positions": {p.symbol: {"mark": p.mark_price, "mark_time": p.mark_time, "source": p.mark_source,
                                           "upnl": p.upnl(), "weight": (p.qty * p.mark_price / eq) if eq else 0,
                                           "notional": p.qty * p.mark_price} for p in bk.positions.values()}},
        "worker": {k: v for k, v in worker.status().items() if k != "last_result"},
    })


@app.get("/api/stream")
async def sse():
    async def gen():
        last, beat = -1, 0.0
        yield "retry: 3000\n\n"
        while True:
            v = stream.version()
            now = asyncio.get_running_loop().time()
            if v != last or now - beat > 10:
                last, beat = v, now
                yield f"event: tick\ndata: {json.dumps(_live_payload(), ensure_ascii=False)}\n\n"
            await asyncio.sleep(1.5)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/stream/status")
def stream_status():
    return ok(stream.status())


EXPORTS = {"signals": "signals.csv", "paper_positions": "paper_positions.csv", "paper_fills": "paper_fills.csv",
           "paper_orders": "paper_orders.csv",
           "paper_ledger": "paper_ledger.csv", "backtest_equity": "backtest/backtest_equity.csv",
           "backtest_trades": "backtest/backtest_trades.csv", "backtest_summary": "backtest/backtest_summary.csv"}


@app.get("/api/export/{name}.csv")
def export(name: str):
    if name not in EXPORTS:
        raise HTTPException(404)
    if name.startswith("paper"):
        engine.export_paper_csv(S.load())
    p = OUTPUT_DIR / EXPORTS[name]
    if not p.exists():
        raise HTTPException(404, "尚未生成，请先运行对应功能")
    return FileResponse(p, media_type="text/csv; charset=utf-8", filename=p.name)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
