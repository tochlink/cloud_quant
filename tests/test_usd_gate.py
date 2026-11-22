"""美元广义指数做空闸门（可选，默认关）：均线公式与研究同口径、+lag 天无前视、失败开放、只拦新开空、回测与引擎同一函数、设置校验、FRED 解析。"""
import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw import usd_gate as U

D = 86_400_000


def _obs(n=120, start="2024-01-01", path=None):
    d = pd.bdate_range(start, periods=n, tz="UTC")
    v = 110 + np.sin(np.arange(n) / 6.0) if path is None else path(n)
    return d.as_unit("ms").asi8, np.asarray(v, float)


def test_ma_matches_pandas_rolling_and_research_flag():
    ob, vs = _obs(200)
    ma, df = U.ma_diff(vs, 20)
    s = pd.Series(vs)
    ref = s.rolling(20).mean().to_numpy()
    m = ~np.isnan(ref)
    assert np.array_equal(m, ~np.isnan(ma)) and np.allclose(ma[m], ref[m], atol=1e-10)
    # 研究：off = v > ma（美元强）；short_on 拦空 = not off
    off = (s > s.rolling(20).mean()).to_numpy()
    assert np.array_equal((df[m] <= 0), ~off[m])


def test_known_after_lag_no_lookahead():
    ob, vs = _obs(80, path=lambda n: np.where(np.arange(n) < 50, 100 + 0.1 * np.arange(n), 90.0))  # 第 50 个观测起美元急跌
    st = {"usd_gate_enabled": True}
    known = ob[50] + 10 * D
    bl, d = U.block_mask(st, [known - 1, known], ob, vs)
    _, df = U.ma_diff(vs, 20)
    assert d[0] == df[49] and d[1] == df[50]  # 公布前 1 毫秒只看到上一观测
    assert not bl[0] and d[0] > 0 and bl[1] and d[1] <= 0
    bl2, _ = U.block_mask({**st, "usd_gate_lag_days": 14}, [known], ob, vs)
    assert not bl2[0]


def test_fail_open_when_stale_short_empty_or_disabled():
    ob, vs = _obs(80, path=lambda n: 100 - 0.1 * np.arange(n))  # 单调走弱 → 本应拦空
    st = {"usd_gate_enabled": True, "usd_gate_stale_days": 14}
    bl, d = U.block_mask(st, [ob[-1] + 10 * D], ob, vs)
    assert bl[0] and d[0] < 0
    bl, d = U.block_mask(st, [ob[-1] + 30 * D], ob, vs)  # known 之后 20 天 > 14 天 → 过旧
    assert not bl[0] and np.isnan(d[0])
    bl, d = U.block_mask(st, [ob[5] + 10 * D], ob, vs)  # 不足 20 个观测
    assert not bl[0] and np.isnan(d[0])
    bl, d = U.block_mask(st, [ob[0]], ob, vs)  # 还没有任何已知观测
    assert not bl[0] and np.isnan(d[0])
    bl, d = U.block_mask(st, [ob[-1]], np.zeros(0, "int64"), np.zeros(0))
    assert not bl[0]
    bl, d = U.block_mask({}, [ob[-1] + 10 * D], ob, vs)
    assert not bl.any() and np.isnan(d).all()


def test_state_fail_open_without_data(monkeypatch):
    monkeypatch.setattr(U, "series", lambda force=False, fetch=True: (np.zeros(0, "int64"), np.zeros(0)))
    out = U.state({"usd_gate_enabled": True}, int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000))
    assert out["blocked"] is False and out["fail_open"]


def test_state_reports_latest_known_observation(monkeypatch):
    ob, vs = _obs(80, path=lambda n: 100 - 0.1 * np.arange(n))
    monkeypatch.setattr(U, "series", lambda force=False, fetch=True: (ob, vs))
    out = U.state({"usd_gate_enabled": True}, int(ob[60] + 10 * D))
    assert out["blocked"] is True and out["value"] == vs[60] and out["diff"] < 0
    assert out["obs_date"] == str(pd.Timestamp(ob[60], unit="ms").date())


def test_parse_fred_csv_drops_blank_rows():
    txt = "observation_date,DTWEXBGS\n2026-11-10,122.1143\n2026-11-11,\n2026-11-12,.\n2026-11-13,122.6503\n"
    d = U.parse_fred(txt)
    assert len(d) == 2 and d[int(pd.Timestamp("2026-11-13", tz="UTC").value // 1_000_000)] == 122.6503


def test_settings_defaults_validation_and_env(monkeypatch, tmp_path):
    st = S.validate(S._merge(S.DEFAULTS, {}))["strategy"]
    assert st["usd_gate_enabled"] is False
    assert (st["usd_gate_n"], st["usd_gate_lag_days"], st["usd_gate_stale_days"]) == (20, 10, 14.0)
    for k, v in (("usd_gate_n", 2), ("usd_gate_lag_days", 1), ("usd_gate_stale_days", 1)):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": {k: v}}))
    assert S.DEFAULTS["strategy"]["usd_gate_enabled"] is False


def test_backtest_gate_blocks_only_new_shorts_and_matches_engine_function():
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
                             usd_gate_enabled=on)
        x["strategy"]["atr_stop_mult"] = 50.0
        return x

    def sig(val):
        def f(ind, idx, syms):
            a = np.zeros(len(idx), dtype=int)
            a[200:] = val
            return {s: a for s in syms}
        return f

    ob, vs = _obs(150, start="2024-01-01", path=lambda k: 120 - 0.05 * np.arange(k))  # 美元持续走弱
    bl, _ = U.block_mask(cfg(True)["strategy"], t.as_unit("ms").asi8, ob, vs)
    assert bl[199:].all()
    off = run_backtest(F, cfg(False), signals=sig(-1))
    on = run_backtest(F, cfg(True), signals=sig(-1), usd_data=(ob, vs))
    assert len(off["trades"]) >= 1 and len(on["trades"]) == 0
    assert on["summary"]["usd_gate"]["blocked_bars"] == int(bl.sum())
    l_off = run_backtest(F, cfg(False), signals=sig(1))
    l_on = run_backtest(F, cfg(True), signals=sig(1), usd_data=(ob, vs))
    assert len(l_on["trades"]) == len(l_off["trades"]) >= 1
    # 默认关闭时逐笔不变
    d_on = run_backtest(F, cfg(False), signals=sig(-1), usd_data=(ob, vs))
    assert len(d_on["trades"]) == len(off["trades"])


def test_env_forces_on(monkeypatch, tmp_path):
    monkeypatch.setenv("QTW_USD_GATE", "1")
    assert S.load()["strategy"]["usd_gate_enabled"] is True
