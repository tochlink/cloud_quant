"""影子子账本与主账本分开记账 / 展示；事件型影子策略不补开过期触发；日志表格按显示宽度对齐。"""
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from qtw import db, logtable as LT, shadow
from qtw import settings as S
from qtw import strategies as R
from qtw.paper import PaperBook

SYMS = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]


# ---------- 日志表格 ----------
def test_table_aligns_cjk_columns():
    t = LT.table(["币种", "方向", "金额(U)", "开仓价"],
                 [["ADAUSDT", "开多·永续", "45.0", "0.1461"], ["BTCUSDT", "开多·永续", "62.5", "63419.5"]])
    lines = t.splitlines()
    assert lines[0].startswith("┌") and lines[-1].startswith("└") and len(lines) == 6
    assert len({LT.dwidth(x) for x in lines}) == 1  # 每行显示宽度一致 → 竖线对齐
    assert LT.dwidth("币种") == 4 and LT.dwidth("ADA") == 3


def test_events_block_splits_main_book_events():
    rows = LT.event_rows(["BTCUSDT 开空·永续 0.012 @ 63419.5，止损 65000",
                          "ETHUSDT 平多 0.5 @ 1739（ATR止损·实时，盈亏 -3.21）", "注意：只是一句话"])
    assert rows[0][:4] == ["BTCUSDT", "开空·永续", "0.012", "63419.5"]
    assert rows[1][0] == "ETHUSDT" and rows[1][4] == "-3.21"
    assert rows[2][0] == "—" and rows[2][5] == "注意：只是一句话"
    blk = LT.events_block("主账本 收盘决策", ["BTCUSDT 开空·永续 0.012 @ 63419.5"])
    assert "主账本 收盘决策" in blk.splitlines()[1] and "│ BTCUSDT" in blk


# ---------- 事件型影子策略：过期触发不补开 ----------
def _data(n, event_at):
    t = pd.date_range("2026-11-01", periods=n, freq="h", tz="UTC")
    fr = {}
    for k, s in enumerate(SYMS):
        c = np.full(n, 100.0) * (1 + 0.001 * np.sin(np.arange(n) + k))
        c[event_at:] *= 0.85  # 8 个币一起跌 15% → #13 投降事件出现在 event_at 这根
        df = pd.DataFrame({"open_time": t, "open": c, "high": c * 1.001, "low": c * 0.999, "close": c, "volume": 1.0})
        fr[s] = df
    return {"spot": fr, "perp": {s: d.copy() for s, d in fr.items()}}


@pytest.fixture()
def fresh(monkeypatch):
    monkeypatch.setattr(shadow, "_px", lambda venue, sym, market, fb: (float(fb), "bar_close"))
    shadow._BOOKS.pop("capitulation_1h", None)
    db.execute("DELETE FROM shadow_books WHERE sid='capitulation_1h'") if db.query(
        "SELECT name FROM sqlite_master WHERE name='shadow_books'") else None
    yield
    shadow._BOOKS.pop("capitulation_1h", None)


def test_signal_age_counts_bars_since_trigger():
    sig, ages, idx = R.latest_signals("capitulation_1h", _data(120, 110), S.load(), detail=True)
    assert all(v == 1 for v in sig.values()) and set(ages.values()) == {9}
    sig, ages, _ = R.latest_signals("capitulation_1h", _data(120, 119), S.load(), detail=True)
    assert set(ages.values()) == {0}


def test_stale_trigger_is_not_back_filled(fresh):
    rows = {}
    ev = shadow.decide("capitulation_1h", _data(120, 110), S.load(), "2026-11-05T23:57:00Z", rows=rows)
    b = shadow.book("capitulation_1h")
    assert not b["positions"] and not rows["open"]
    assert rows["stale"] and "不补开" in ev[0]
    # 同一次触发后面每根都不再重复记录
    ev2 = shadow.decide("capitulation_1h", _data(121, 110), S.load(), "2026-11-06T00:57:00Z")
    assert ev2 == []


def test_fresh_trigger_enters_and_records_trigger_bar(fresh):
    rows = {}
    shadow.decide("capitulation_1h", _data(120, 119), S.load(), "2026-11-05T23:00:05Z", rows=rows)
    b = shadow.book("capitulation_1h")
    assert len(b["positions"]) == 8 and len(rows["open"]) == 8
    p = b["positions"]["BTCUSDT"]
    assert p["late_bars"] == 0 and p["signal_bar"].startswith("2026-11-05T23:00")
    txt = shadow.log_text("capitulation_1h", rows)
    assert "影子子账本 capitulation_1h" in txt and "│ BTCUSDT" in txt and "开仓价" in txt
    # 成交页用的影子记录：独立标记，不进主账本
    tr = [t for t in shadow.trade_rows(["capitulation_1h"])]
    assert len(tr) == 8 and all(t["book"] == "影子 #13" and t["status"] == "open" for t in tr)
    sm = [x for x in shadow.summary() if x["sid"] == "capitulation_1h"][0]
    assert abs(sm["diff_usdt"]) < 1e-9 and sm["open"] == 8


def test_hold_expiry_closes_and_reconciles(fresh):
    shadow.decide("capitulation_1h", _data(120, 119), S.load(), "2026-11-05T23:00:05Z")
    rows = {}
    shadow.decide("capitulation_1h", _data(144, 119), S.load(), "2026-11-06T23:00:05Z", rows=rows)  # 持有 24 根期满
    b = shadow.book("capitulation_1h")
    assert not b["positions"] and len(rows["close"]) == 8
    assert all(t["exit_reason"] == "持有期满" for t in b["trades"])
    sm = [x for x in shadow.summary() if x["sid"] == "capitulation_1h"][0]
    assert abs(sm["diff_usdt"]) < 1e-9 and sm["closed"] == 8
    tr = shadow.trade_rows(["capitulation_1h"])
    assert abs(sum(t["pnl_usdt"] for t in tr) - (sm["equity"] - 1000.0)) < 1e-9
    assert all(t["fee_usdt"] > 0 for t in tr)


# ---------- 主账本对账 ----------
def test_main_book_reconciles_trades_plus_funding(tmp_path):
    b = PaperBook(1000, 4, conn=db.connect(tmp_path / "r.sqlite"), fee_by_market={"spot": 0.001, "perp": 0.00051})
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.002, price=60000, price_kind="mark", stop=62000,
           signal_bar="x", reason="信号", venue="okx", leverage=10)
    b.open(symbol="ETHUSDT", market="perp", side="long", qty=0.05, price=2000, price_kind="mark", stop=1900,
           signal_bar="x", reason="信号", venue="okx", leverage=10)
    b.apply_funding("BTCUSDT", 0.0001, 60000, 10**13)
    b.close("ETHUSDT", 2050, "mark", "信号反转", "okx")
    b.mark("BTCUSDT", 59000, "t", "ws")
    r = b.reconcile()
    assert r["ok"] and abs(r["diff_usdt"]) < 1e-9
    assert r["funding_usdt"] != 0 and r["closed"] == 1 and r["open"] == 1


def test_api_keeps_shadow_out_of_main_trades():
    c = TestClient(__import__("qtw.app", fromlist=["app"]).app)
    main = c.get("/api/trades").json()
    assert all(not str(t.get("book", "")).startswith("影子") for t in main)
    sh = c.get("/api/shadow/trades")
    assert sh.status_code == 200 and isinstance(sh.json(), list)
    sm = c.get("/api/trades/summary").json()
    assert "main" in sm and "shadow" in sm and sm["main"]["ok"]
    dash = c.get("/api/dashboard").json()
    assert "shadow_books" in dash
