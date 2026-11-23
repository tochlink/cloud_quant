"""MoF 周度居民外债净买闸门（可选，默认关）：13 周和 / 26 周均线与研究同口径、周末 + 6 天无前视、失败开放、
contra_both（flag=1 拦新开空、flag=0 拦新开多）、回测与引擎同一函数、设置校验、官方 week.csv 解析。"""
import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw import mof_gate as M

D = 86_400_000


def _weeks(n=120, start="2024-01-06", path=None):
    d = pd.date_range(start, periods=n, freq="7D", tz="UTC")  # 周六
    v = 1000 * np.sin(np.arange(n) / 5.0) if path is None else path(n)
    return d.as_unit("ms").asi8, np.asarray(v, float)


def test_flag_matches_pandas_research_formula():
    ob, vs = _weeks(200)
    s, ma, f = M.flag_series(vs, 13, 26)
    ps = pd.Series(vs).rolling(13).sum()
    pm = ps.rolling(26).mean()
    m = ~np.isnan(pm.to_numpy())
    assert np.array_equal(m, np.isfinite(f))
    assert np.allclose(s[m], ps.to_numpy()[m]) and np.allclose(ma[m], pm.to_numpy()[m])
    assert np.array_equal(f[m] > 0.5, (ps > pm).to_numpy()[m])


def test_known_after_lag_no_lookahead():
    ob, vs = _weeks(80, path=lambda n: np.where(np.arange(n) < 60, -100.0 + np.arange(n) * 0.0, 5000.0))  # 第 60 周起外流暴增
    st = {"mof_gate_enabled": True}
    known = ob[60] + 6 * D
    bl, bs, f = M.block_mask(st, [known - 1, known], ob, vs)
    assert f[0] == 0.0 and f[1] == 1.0  # 公布前 1 毫秒只看到上一周
    assert bl[0] and not bs[0] and bs[1] and not bl[1]


def test_fail_open_when_stale_short_empty_or_disabled():
    ob, vs = _weeks(80)
    st = {"mof_gate_enabled": True, "mof_gate_stale_days": 21}
    bl, bs, f = M.block_mask(st, [ob[-1] + 6 * D], ob, vs)
    assert np.isfinite(f[0]) and (bl[0] or bs[0])
    bl, bs, f = M.block_mask(st, [ob[-1] + 30 * D], ob, vs)  # known 之后 24 天 > 21 天 → 过旧
    assert not bl[0] and not bs[0] and np.isnan(f[0])
    bl, bs, f = M.block_mask(st, [ob[20] + 6 * D], ob, vs)  # 历史不足 13 + 26 − 1 周
    assert not bl[0] and not bs[0] and np.isnan(f[0])
    bl, bs, f = M.block_mask(st, [ob[0]], ob, vs)
    assert not bl[0] and not bs[0]
    bl, bs, f = M.block_mask(st, [ob[-1]], np.zeros(0, "int64"), np.zeros(0))
    assert not bl[0] and not bs[0]
    bl, bs, f = M.block_mask({}, [ob[-1] + 6 * D], ob, vs)
    assert not bl.any() and not bs.any() and np.isnan(f).all()


def test_state_fail_open_and_reports(monkeypatch):
    monkeypatch.setattr(M, "series", lambda force=False, fetch=True: (np.zeros(0, "int64"), np.zeros(0)))
    out = M.state({"mof_gate_enabled": True}, int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000))
    assert out["block_long"] is False and out["block_short"] is False and out["fail_open"]
    ob, vs = _weeks(80, path=lambda n: np.arange(n) * 100.0)  # 外流单调加速 → flag 1 → 拦空
    monkeypatch.setattr(M, "series", lambda force=False, fetch=True: (ob, vs))
    out = M.state({"mof_gate_enabled": True}, int(ob[60] + 6 * D))
    assert out["block_short"] is True and out["block_long"] is False and out["flag"] == 1
    assert out["week_end"] == str(pd.Timestamp(ob[60], unit="ms").date())


def test_parse_official_week_csv_layout():
    hdr = "\n".join([",x"] * 14)
    row = lambda p, v: f'{p},"1,689 ","1,419 ",270 ,"23,929 ","15,051 ","{v}","9,149 ",1,1,1,1,1,1,1,1,1,1,1,1,1,1,1'
    txt = hdr + "\n" + row("2025．12．21～ 12．27", "8,878 ") + "\n" + row("2026．12．27～1．2", "-2,729 ") + "\n,（備考）\n"
    d = M.parse_week_csv(txt)
    assert d == {int(pd.Timestamp("2025-12-27", tz="UTC").value // 1_000_000): 8878.0,
                 int(pd.Timestamp("2027-01-02", tz="UTC").value // 1_000_000): -2729.0}


def test_settings_defaults_validation_and_env(monkeypatch):
    st = S.validate(S._merge(S.DEFAULTS, {}))["strategy"]
    assert st["mof_gate_enabled"] is False and S.DEFAULTS["strategy"]["mof_gate_enabled"] is False
    assert (st["mof_gate_sum_n"], st["mof_gate_trend_n"], st["mof_gate_stale_days"]) == (13, 26, 21.0)
    for k, v in (("mof_gate_sum_n", 99), ("mof_gate_trend_n", 1), ("mof_gate_stale_days", 2)):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": {k: v}}))
    monkeypatch.setenv("QTW_MOF_GATE", "1")
    assert S.load()["strategy"]["mof_gate_enabled"] is True


def test_backtest_gate_contra_both_and_matches_engine_function():
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
                             mof_gate_enabled=on)
        x["strategy"]["atr_stop_mult"] = 50.0
        return x

    def sig(val):
        def f(ind, idx, syms):
            a = np.zeros(len(idx), dtype=int)
            a[200:] = val
            return {s: a for s in syms}
        return f

    ob, vs = _weeks(100, start="2023-01-07", path=lambda k: np.arange(k) * 100.0)  # 外流持续加速 → flag 1
    bl, bs, _ = M.block_mask(cfg(True)["strategy"], t.as_unit("ms").asi8, ob, vs)
    assert bs[199:].all() and not bl.any()
    off = run_backtest(F, cfg(False), signals=sig(-1))
    on = run_backtest(F, cfg(True), signals=sig(-1), mof_data=(ob, vs))
    assert len(off["trades"]) >= 1 and len(on["trades"]) == 0
    assert on["summary"]["mof_gate"]["blocked_short_bars"] == int(bs.sum())
    l_off = run_backtest(F, cfg(False), signals=sig(1))
    l_on = run_backtest(F, cfg(True), signals=sig(1), mof_data=(ob, vs))
    assert len(l_on["trades"]) == len(l_off["trades"]) >= 1
    ob2, vs2 = _weeks(100, start="2023-01-07", path=lambda k: -np.arange(k) * 100.0)  # 资金回流 → flag 0 → 拦多
    l_on2 = run_backtest(F, cfg(True), signals=sig(1), mof_data=(ob2, vs2))
    assert len(l_on2["trades"]) == 0
    d_on = run_backtest(F, cfg(False), signals=sig(-1), mof_data=(ob, vs))
    assert len(d_on["trades"]) == len(off["trades"])
