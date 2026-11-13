"""多策略注册表 / 影子子账本 / 资金费率套利模拟（v7）。synth() 仅测试用。"""
import json

import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw import strategies as R
from qtw.backtest import run_backtest
from tests.test_backtest import book, synth


def test_registry_shape():
    ids = [s["id"] for s in R.STRATEGIES]
    assert len(ids) == len(set(ids)) and ids[0] == "ma_trend"
    assert 5 <= len(ids) - 1 <= 7
    for s in R.STRATEGIES:
        assert s["name"] and s["desc"] and isinstance(s["params"], dict)
        assert any("\u4e00" <= ch <= "\u9fff" for ch in s["name"])  # 中文名
        assert s["interval"] in ("1h", "4h", "8h")


def test_default_strategy_is_byte_identical():
    data, cfg = book(3, 700), S.load()
    a, b = run_backtest(data, cfg), R.run("ma_trend", data, cfg)
    pd.testing.assert_frame_equal(a["equity"], b["equity"])
    pd.testing.assert_frame_equal(a["trades"], b["trades"])


def test_signals_none_keeps_default():
    data, cfg = book(2, 600), S.load()
    a, b = run_backtest(data, cfg), run_backtest(data, cfg, signals=None)
    assert a["summary"]["total_return"] == b["summary"]["total_return"]


@pytest.mark.parametrize("sid", [s["id"] for s in R.STRATEGIES if s["signal"] is not None and s["interval"] == "4h"])
def test_candidate_signals_have_no_lookahead(sid):
    """截断未来 K 线不改变任何已收盘根的信号（因果）。"""
    data, cfg = book(4, 900), S.load()
    fn = R.signal_fn(sid)
    def sig(d):
        syms = sorted(d["spot"])
        ind = {m: {s: d[m][s].set_index("open_time", drop=False) for s in syms} for m in d}
        idx = ind["spot"][syms[0]].index
        return fn(ind, idx, syms)
    full = sig(data)
    cut = {m: {s: df.iloc[:700].reset_index(drop=True) for s, df in v.items()} for m, v in data.items()}
    part = sig(cut)
    for s in part:
        assert np.array_equal(full[s][:700], part[s]), (sid, s)
        assert set(np.unique(full[s])) <= {-1, 0, 1}


@pytest.mark.parametrize("sid", [s["id"] for s in R.STRATEGIES if s["signal"] is not None and s["interval"] == "4h"])
def test_candidate_runs_through_same_engine(sid):
    data, cfg = book(4, 900), S.load()
    r = R.run(sid, data, cfg)
    sm = r["summary"]
    assert sm["strategy_id"] == sid and sm["rule_id"] == sid
    e = r["equity"]["equity"]
    assert np.isfinite(e).all() and (e > 0).all()
    if len(r["trades"]):
        assert set(r["trades"]["market"]) <= {"spot", "perp"}
        t = r["trades"]
        long_mkt = "perp" if cfg["risk"].get("trade_mode") == "perp_both" else "spot"
        assert (t[t.side == "long"].market == long_mkt).all() and (t[t.side == "short"].market == "perp").all()


def test_meanrev_runs_on_1h():
    t = pd.date_range("2025-01-01", periods=800, freq="1h", tz="UTC")
    def one(seed, scale=1.0):
        d = synth(800, seed=seed, scale=scale)
        d["open_time"], d["close_time"] = t, t + pd.Timedelta(hours=1)
        return d
    data = {"spot": {"S0USDT": one(0), "S1USDT": one(1)}, "perp": {"S0USDT": one(0, 1.01), "S1USDT": one(1, 1.01)}}
    cfg = S.load(); cfg["strategy"]["interval"] = "1h"
    r = R.run("meanrev_1h", data, cfg)
    assert len(r["equity"]) > 0


def test_xsmom_long_top_short_bottom():
    data, cfg = book(6, 900), S.load()
    sig = R.latest_signals("xsmom", data, cfg)
    assert sum(v == 1 for v in sig.values()) == 2 and sum(v == -1 for v in sig.values()) == 2


def test_verdicts_follow_rule_and_json():
    res = R.load_research()
    assert res and res["verdicts"]["ma_trend"]["status"] == "采用"
    for sid, v in res["verdicts"].items():
        assert v["status"] in ("采用", "观察", "淘汰") and sid in R.BY_ID
        if sid == "ma_trend":
            continue
        m = res["metrics"][sid]
        passes = all(m[f"{ven}_{f}"]["full_ret"] > 0 and (m[f"{ven}_{f}"]["post_ret"] or 0) > 0.005
                     for ven in ("gate", "okx") for f in ("real", "stress"))
        assert (v["status"] != "淘汰") == passes, sid
    g = res["metrics"]["ma_trend"]["gate_real"]
    assert g["full_ret"] == pytest.approx(160.67) and g["sharpe"] == pytest.approx(1.68) and g["post_ret"] == pytest.approx(59.72)
    o = res["metrics"]["ma_trend"]["okx_real"]
    assert o["full_ret"] == pytest.approx(163.32) and o["sharpe"] == pytest.approx(1.69) and o["post_ret"] == pytest.approx(59.54)


def test_carry_simulation_accounting():
    from qtw import carry
    data = book(2, 300)
    for m in data:
        for s in data[m]:
            data[m][s] = data["spot"][s].copy() if m == "perp" else data[m][s]  # 期现同价 → 基差盈亏为 0
    t0 = int(data["spot"]["S0USDT"]["open_time"].iloc[0].value // 1_000_000)
    f = pd.DataFrame({"time_ms": [t0 + k * 8 * 3_600_000 for k in range(100)], "rate": [0.0003] * 100})
    cfg = S.load()
    r = carry.simulate(data, {"S0USDT": f, "S1USDT": f}, cfg, window=3, enter_rate=1e-4, exit_rate=0.0)
    sm = r["summary"]
    assert sm["funding_usdt"] > 0 and sm["fees_usdt"] > 0
    end = float(r["equity"]["equity"].iloc[-1])
    assert end == pytest.approx(1000.0 + sm["funding_usdt"] - sm["fees_usdt"], rel=1e-9)


def test_shadow_book_isolated(monkeypatch):
    from qtw import db, engine, shadow
    db.connect()
    monkeypatch.setattr(shadow, "_px", lambda venue, sym, market, fb: (float(fb), "bar_close"))
    monkeypatch.setitem(R.VERDICTS, "tsmom", {"status": "观察"})
    shadow._BOOKS.pop("tsmom", None)
    cfg = S.load(); cfg["venue"] = "gate"
    data = book(3, 900)
    before = engine._BOOK
    ev = shadow.decide("tsmom", data, cfg, "2026-11-13T20:00:00+00:00")
    assert engine._BOOK is before  # 默认账本没被创建 / 改动
    st = {b["sid"]: b for b in shadow.status()}["tsmom"]
    assert ev and st["positions"] and st["equity"] < 1000.0 + 1e-9  # 只付了开仓手续费
    p = st["positions"][0]
    long_mkt = "perp" if cfg["risk"].get("trade_mode") == "perp_both" else "spot"
    assert p["market"] == (long_mkt if p["side"] == "long" else "perp")

    class Q:  # 价格穿过止损 → 平仓 + 锁定
        symbol, market, venue, data_source, ts = p["symbol"], p["market"], "gate", "test", None
        price = p["stop"] * (0.99 if p["side"] == "long" else 1.01)
    shadow.on_tick(Q)
    b = shadow.book("tsmom")
    assert p["symbol"] not in b["positions"] and p["symbol"] in b["blocked"]
    assert b["trades"][-1]["exit_reason"] == "ATR止损"
    row = db.query("SELECT state FROM shadow_books WHERE sid='tsmom'")
    assert json.loads(row[0]["state"])["blocked"]


def test_shadow_only_observe_or_adopt():
    from qtw import shadow
    for sid in shadow.active_ids():
        assert R.VERDICTS[sid]["status"] in ("采用", "观察") and R.BY_ID[sid]["signal"] is not None
