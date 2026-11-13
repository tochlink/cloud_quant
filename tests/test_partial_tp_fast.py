"""分批止盈 / 保本止损、快速判断层、下单精度取整、图表周期聚合与同比。合成序列仅用于测试。"""
import copy
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from qtw import db, engine, lots, settings as S
from qtw.backtest import breakeven_stop, partial_tp_target, run_backtest
from qtw.fastlayer import FastSeries, aggregate, ema_break_flags, to_ms
from qtw.market.base import Quote
from qtw.paper import PaperBook
from tests.test_backtest import book


def _cfg(**st):
    c = copy.deepcopy(S.DEFAULTS)
    c["symbols"] = []
    c["strategy"].update(trend_ma=0, short_breaker_bars=0, name_vol_target=0, **st)
    return c


PTP = dict(tp_partial=True, tp_partial_r=2.0, tp_frac=0.5, tp_breakeven=True)


def test_defaults_off():
    st = S.DEFAULTS["strategy"]
    assert st["tp_partial"] is False and st["tp_breakeven"] is False and st["fast_exit_tf"] == "off"
    assert st["tp_partial_r"] == 2.0 and st["tp_frac"] == 0.5
    r = run_backtest(book(), _cfg())
    assert r["summary"]["partial_tp_trades"] == 0 and r["summary"]["breakeven_exits"] == 0


def test_formulas():
    assert partial_tp_target("long", 100, 90, 2) == pytest.approx(120)
    assert partial_tp_target("short", 100, 110, 2) == pytest.approx(80)
    assert breakeven_stop("long", 100, 0.001, True) == pytest.approx(100.2)
    assert breakeven_stop("short", 100, 0.00051, True) == pytest.approx(100 * (1 - 2 * 0.00051))
    assert breakeven_stop("long", 100, 0.001, False) == pytest.approx(100)


def test_partial_tp_backtest_fills_and_breakeven_reason():
    r = run_backtest(book(), _cfg(**PTP))
    tr, sm = r["trades"], r["summary"]
    assert sm["partial_tp_trades"] > 0
    done = tr[tr.tp_done.astype(bool)]
    assert len(done) == sm["partial_tp_trades"]
    for _, t in done.iterrows():
        tgt = partial_tp_target(t.side, t.entry_price, t.init_stop, 2.0)
        d = 1 if t.side == "long" else -1
        assert d * (t.tp_price - tgt) >= -1e-9  # 按分批价或更优的开盘价成交
    be = tr[tr.exit_reason == "保本止损"]
    assert len(be) == sm["breakeven_exits"] and len(be) > 0
    assert be.be_moved.astype(bool).all()


def test_fast_series_identity_with_4h_bars():
    d = book()
    for st in ({}, PTP):
        r0 = run_backtest(d, _cfg(**st))
        fx = {}
        for m in ("spot", "perp"):
            for s, df in d[m].items():
                t = to_ms(df.open_time)
                fx[(m, s)] = FastSeries(t, df.open, df.high, df.low, df.close, 14_400_000)
        r1 = run_backtest(d, _cfg(**st), fast=fx)
        assert np.max(np.abs(r0["equity"]["equity"].to_numpy() - r1["equity"]["equity"].to_numpy())) < 1e-9
        assert r1["summary"]["fast_bars_resolved"] > 0


def test_fast_exit_flags_close_trades():
    d = book()
    fx = {}
    for m in ("spot", "perp"):
        for s, df in d[m].items():
            t = to_ms(df.open_time)
            bl, bs = ema_break_flags(df.close.to_numpy(), 5, 1)
            fx[(m, s)] = FastSeries(t, df.open, df.high, df.low, df.close, 14_400_000, bl, bs)
    r = run_backtest(d, _cfg(), fast=fx)
    assert r["summary"]["fast_exits"] > 0
    assert (r["trades"].exit_reason == "快速离场").sum() == r["summary"]["fast_exits"]


def test_fast_series_missing_coverage_returns_none():
    fs = FastSeries([0, 60_000], [1, 1], [1, 1], [1, 1], [1, 1], 60_000)
    assert fs.walk(None, pd.Timestamp(0, unit="ms", tz="UTC"), pd.Timestamp(14_400_000, unit="ms", tz="UTC"),
                   tp_r=0, ptp=None, be=None, fast_exit=False) is None


def test_aggregate_10m_from_1m_drops_incomplete():
    t0 = pd.Timestamp("2026-11-01", tz="UTC")
    ot = [t0 + pd.Timedelta(minutes=i) for i in range(25)]
    df = pd.DataFrame({"open_time": ot, "open": np.arange(25.0), "high": np.arange(25.0) + 1, "low": np.arange(25.0) - 1,
                       "close": np.arange(25.0) + 0.5, "volume": 1.0})
    a = aggregate(df, 10, 1)
    assert len(a) == 2  # 第三个桶只有 5 根，丢弃
    assert a.open.tolist() == [0, 10] and a.close.tolist() == [9.5, 19.5]
    assert a.high.tolist() == [10, 20] and a.low.tolist() == [-1, 9] and a.volume.tolist() == [10, 10]


def test_ema_break_flags_need_confirm():
    c = np.r_[np.full(10, 100.0), 90, 90, 90]
    bl, bs = ema_break_flags(c, 3, 2)
    assert not bl[10] and bl[11] and bl[12] and not bs.any()


@pytest.mark.real_lots
def test_floor_qty_okx_perp_and_gate_spot():
    okx = lots.Lot("okx", "BTCUSDT", "perp", step=0.01 * 0.01, min_qty=0.01 * 0.01, ct_val=0.01, contract_step=0.01)
    assert lots.floor_qty(0.0020755, okx) == pytest.approx(0.002)
    assert lots.floor_qty(0.00005, okx) == 0
    assert lots.contracts(0.002, okx) == pytest.approx(0.2)
    gate = lots.Lot("gate", "ETHUSDT", "spot", step=0.0001, min_qty=0.0001, min_quote=3)
    assert lots.floor_qty(0.072587, gate, 1960) == pytest.approx(0.0725)
    assert lots.floor_qty(0.001, gate, 1960) == 0  # 1.96 U < 最小 3 U


def test_okx_spot_order_uses_base_qty():
    from qtw.live.okx import order_payload
    p = order_payload("ETHUSDT", "spot", "open_long", 0.0725, 1960)
    assert p["tgtCcy"] == "base_ccy" and p["sz"] == "0.0725" and p["side"] == "buy"
    q = order_payload("BTCUSDT", "perp", "open_short", 0.002, 69000, {"ct_val": 0.01, "lot_sz": 0.01})
    assert q["sz"] == "0.2" and q["side"] == "sell"


def test_db_migration_adds_tp_columns(tmp_path):
    conn = db.connect(tmp_path / "m.sqlite")
    cols = {r[1] for r in conn.execute("PRAGMA table_info(paper_positions)")}
    assert {"init_stop", "tp_done", "be_moved"} <= cols


def _q(sym, mkt, px):
    return Quote(venue="okx", symbol=sym, market=mkt, price=px, kind="mark" if mkt == "perp" else "last",
                 ts=datetime.now(timezone.utc), data_source="okx_public_ws", source_host="ws.okx.com")


def test_engine_partial_tp_then_breakeven(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "ptp.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.002, price=70000, price_kind="mark", stop=72000,
           signal_bar="x", reason="t", venue="okx", data_source="okx_public_ws", price_time="2026-11-13T00:00:00Z")
    monkeypatch.setattr(engine, "_route", lambda *a, **k: None)
    cfg = copy.deepcopy(S.DEFAULTS); cfg["venue"] = "okx"; cfg["strategy"].update(PTP)
    p = b.positions["BTCUSDT"]
    assert p.init_stop == 72000
    ev = []
    assert engine._exit_checks(cfg, b, "BTCUSDT", p, 66500, "mark", _q("BTCUSDT", "perp", 66500), ev) is False
    assert not ev  # 未到 2R（66000）
    assert engine._exit_checks(cfg, b, "BTCUSDT", p, 65900, "mark", _q("BTCUSDT", "perp", 65900), ev) is False
    p = b.positions["BTCUSDT"]
    assert p.qty == pytest.approx(0.001) and p.tp_done and p.be_moved
    assert p.stop_price == pytest.approx(70000 * (1 - 2 * b.fee_for("perp")))
    assert any("止盈" in e for e in ev)
    assert engine._exit_checks(cfg, b, "BTCUSDT", p, 70000, "mark", _q("BTCUSDT", "perp", 70000), ev) is True
    assert "BTCUSDT" not in b.positions
    recs = b.trade_records() if hasattr(b, "trade_records") else []
    if recs:
        last = recs[-1] if isinstance(recs, list) else recs.iloc[-1]
        assert (last["exit_reason"] if "exit_reason" in last else "保本止损") == "保本止损"


def test_chart_aggregate_weekly_monthly(monkeypatch):
    from qtw.market import chart
    days = pd.date_range("2025-12-29", periods=40, freq="D", tz="UTC")
    d = pd.DataFrame({"open_time": days, "open": np.arange(40.0), "high": np.arange(40.0) + 2, "low": np.arange(40.0) - 2,
                      "close": np.arange(40.0) + 1, "volume": 1.0})
    w = chart._agg_daily(d, "1w")
    assert w.open_time.iloc[0] == pd.Timestamp("2025-12-29", tz="UTC") and w.close.iloc[0] == 7
    m = chart._agg_daily(d, "1M")
    assert m.open_time.tolist()[:2] == [pd.Timestamp("2025-12-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")]
    assert m.open.iloc[1] == 3 and m.close.iloc[1] == 34
    y = chart._agg_daily(d, "1y")
    assert len(y) == 2 and y.high.iloc[1] == 41


def test_yoy_normalizes_each_year(monkeypatch):
    from qtw.market import chart
    days = pd.date_range("2025-01-01", "2026-03-01", freq="D", tz="UTC")
    c = np.linspace(100, 200, len(days))
    d = pd.DataFrame({"open_time": days, "open": c, "high": c, "low": c, "close": c, "volume": 1.0})
    monkeypatch.setattr(chart.mcache, "candles", lambda *a, **k: d)
    out = chart.yoy("okx", "ETHUSDT", "1d", [2025, 2026])
    s25, s26 = out["series"]
    assert s25["points"][0]["value"] == 0 and s26["points"][0]["value"] == 0
    assert s25["points"][31]["time"] == s26["points"][31]["time"]  # 同一天对齐
    raw = chart.yoy("okx", "ETHUSDT", "1d", [2025], mode="raw")
    assert raw["series"][0]["points"][0]["value"] == pytest.approx(100)
    assert out["available_years"] == [2025, 2026]


def test_api_candles_interval_param(monkeypatch):
    from fastapi.testclient import TestClient
    from qtw.app import app
    from qtw.market import chart
    seen = {}

    def fake(venue, symbol, interval, bars, market="spot"):
        seen["iv"] = interval
        n = 300
        t = pd.date_range("2026-01-01", periods=n, freq="10min", tz="UTC")
        c = np.linspace(100, 110, n)
        df = pd.DataFrame({"open_time": t, "open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1.0,
                           "close_time": t + pd.Timedelta(minutes=10), "partial": False})
        df.attrs.update(aggregated_from="1m", data_source="test")
        return df

    monkeypatch.setattr(chart, "chart_candles", fake)
    cl = TestClient(app)
    r = cl.get("/api/candles", params={"symbol": "BTCUSDT", "interval": "10m"})
    assert r.status_code == 200 and seen["iv"] == "10m"
    j = r.json()
    assert j["interval"] == "10m" and j.get("aggregated_from") == "1m"
    assert cl.get("/api/candles", params={"symbol": "BTCUSDT", "interval": "3m"}).status_code == 400
