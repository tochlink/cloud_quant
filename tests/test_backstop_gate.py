"""美联储一级信贷周度闸门（可选，默认关）：13 周均线与研究同口径、周三 + 3 天无前视、失败开放、
both（flag=1 拦新开多、flag=0 拦新开空）、回测与引擎同一函数、设置校验、FRED CSV 解析。"""
import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw import backstop_gate as G

D = 86_400_000


def _weeks(n=120, start="2024-01-03", path=None):
    d = pd.date_range(start, periods=n, freq="7D", tz="UTC")  # 周三
    v = 5000 + 1000 * np.sin(np.arange(n) / 5.0) if path is None else path(n)
    return d.as_unit("ms").asi8, np.asarray(v, float)


def test_flag_matches_pandas_research_formula():
    ob, vs = _weeks(200)
    ma, f = G.flag_series(vs, 13)
    pm = pd.Series(vs).rolling(13, min_periods=13).mean()
    m = ~np.isnan(pm.to_numpy())
    assert np.array_equal(m, np.isfinite(f))
    assert np.allclose(ma[m], pm.to_numpy()[m])
    assert np.array_equal(f[m] > 0.5, (pd.Series(vs) > pm).to_numpy()[m])


def test_known_after_lag_no_lookahead():
    ob, vs = _weeks(80, path=lambda n: np.where(np.arange(n) < 60, 3000.0, 90000.0))  # 第 60 周借款暴增
    st = {"backstop_gate_enabled": True}
    known = ob[60] + 3 * D
    bl, bs, f = G.block_mask(st, [known - 1, known], ob, vs)
    assert f[0] == 0.0 and f[1] == 1.0  # 公布前 1 毫秒只看到上一周（等于均线 → 0）
    assert bs[0] and not bl[0] and bl[1] and not bs[1]


def test_fail_open_when_stale_short_empty_or_disabled():
    ob, vs = _weeks(80)
    st = {"backstop_gate_enabled": True, "backstop_gate_stale_days": 21}
    bl, bs, f = G.block_mask(st, [ob[-1] + 3 * D], ob, vs)
    assert np.isfinite(f[0]) and (bl[0] or bs[0])
    bl, bs, f = G.block_mask(st, [ob[-1] + 30 * D], ob, vs)  # known 之后 27 天 > 21 天 → 过旧
    assert not bl[0] and not bs[0] and np.isnan(f[0])
    bl, bs, f = G.block_mask(st, [ob[5] + 3 * D], ob, vs)  # 历史不足 13 周
    assert not bl[0] and not bs[0] and np.isnan(f[0])
    bl, bs, f = G.block_mask(st, [ob[0]], ob, vs)
    assert not bl[0] and not bs[0]
    bl, bs, f = G.block_mask(st, [ob[-1]], np.zeros(0, "int64"), np.zeros(0))
    assert not bl[0] and not bs[0]
    bl, bs, f = G.block_mask({}, [ob[-1] + 3 * D], ob, vs)
    assert not bl.any() and not bs.any() and np.isnan(f).all()


def test_state_fail_open_and_reports(monkeypatch):
    monkeypatch.setattr(G, "series", lambda force=False, fetch=True: (np.zeros(0, "int64"), np.zeros(0)))
    out = G.state({"backstop_gate_enabled": True}, int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000))
    assert out["block_long"] is False and out["block_short"] is False and out["fail_open"]
    ob, vs = _weeks(80, path=lambda n: 1000.0 + np.arange(n) * 100.0)  # 借款单调上升 → flag 1 → 拦多
    monkeypatch.setattr(G, "series", lambda force=False, fetch=True: (ob, vs))
    out = G.state({"backstop_gate_enabled": True}, int(ob[60] + 3 * D))
    assert out["block_long"] is True and out["block_short"] is False and out["flag"] == 1
    assert out["wed"] == str(pd.Timestamp(ob[60], unit="ms").date()) and out["x"] == float(vs[60])


def test_parse_fred_csv():
    txt = "observation_date,WLCFLPCL\n2026-11-04,9219\n2026-11-11,.\n2026-11-18,9055.5\n"
    assert G.parse_fred_csv(txt) == {int(pd.Timestamp("2026-11-04", tz="UTC").value // 1_000_000): 9219.0,
                                     int(pd.Timestamp("2026-11-18", tz="UTC").value // 1_000_000): 9055.5}


def test_settings_defaults_validation_and_env(monkeypatch):
    st = S.validate(S._merge(S.DEFAULTS, {}))["strategy"]
    assert st["backstop_gate_enabled"] is False and S.DEFAULTS["strategy"]["backstop_gate_enabled"] is False
    assert (st["backstop_gate_trend_n"], st["backstop_gate_stale_days"]) == (13, 21.0)
    for k, v in (("backstop_gate_trend_n", 1), ("backstop_gate_trend_n", 999), ("backstop_gate_stale_days", 2)):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": {k: v}}))
    monkeypatch.setenv("QTW_BACKSTOP_GATE", "1")
    assert S.load()["strategy"]["backstop_gate_enabled"] is True


def test_backtest_gate_both_and_matches_engine_function():
    from qtw.backtest import run_backtest
    n = 400
    t = pd.date_range("2024-03-01", periods=n, freq="4h", tz="UTC")
    c = 100 + np.sin(np.arange(n) / 7.0)
    df = pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + 0.3,
                       "low": c - 0.3, "close": c, "volume": 1.0})
    F = {"spot": {"ETHUSDT": df.copy()}, "perp": {"ETHUSDT": df.copy()}}

    def cfg(on):
        x = S._merge(S.DEFAULTS, {"symbols": ["ETHUSDT"]})
        x["strategy"].update(fast_ma=5, slow_ma=10, trend_ma=0, btc_regime_ma=0, port_vol_target=0, name_vol_target=0,
                             backstop_gate_enabled=on)
        x["strategy"]["atr_stop_mult"] = 50.0
        return x

    def sig(val):
        def f(ind, idx, syms):
            a = np.zeros(len(idx), dtype=int)
            a[200:] = val
            return {s: a for s in syms}
        return f

    ob, vs = _weeks(100, start="2023-01-04", path=lambda k: 1000.0 + np.arange(k) * 100.0)  # 借款上升 → flag 1 → 拦多
    bl, bs, _ = G.block_mask(cfg(True)["strategy"], t.as_unit("ms").asi8, ob, vs)
    assert bl[199:].all() and not bs.any()
    off = run_backtest(F, cfg(False), signals=sig(1))
    on = run_backtest(F, cfg(True), signals=sig(1), backstop_data=(ob, vs))
    assert len(off["trades"]) >= 1 and len(on["trades"]) == 0
    assert on["summary"]["backstop_gate"]["blocked_long_bars"] == int(bl.sum())
    s_off = run_backtest(F, cfg(False), signals=sig(-1))
    s_on = run_backtest(F, cfg(True), signals=sig(-1), backstop_data=(ob, vs))
    assert len(s_on["trades"]) == len(s_off["trades"]) >= 1
    ob2, vs2 = _weeks(100, start="2023-01-04", path=lambda k: 100000.0 - np.arange(k) * 100.0)  # 借款回落 → flag 0 → 拦空
    s_on2 = run_backtest(F, cfg(True), signals=sig(-1), backstop_data=(ob2, vs2))
    assert len(s_on2["trades"]) == 0
    d_on = run_backtest(F, cfg(False), signals=sig(1), backstop_data=(ob, vs))
    assert len(d_on["trades"]) == len(off["trades"])
