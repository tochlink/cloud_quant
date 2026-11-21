"""H.4.1 外国官方托管美债闸门（可选，默认关）：z 公式、W+3 天无前视、失败开放、只拦新开多、回测与引擎同一函数、设置校验。"""
import numpy as np
import pandas as pd
import pytest

from qtw import custody as C
from qtw import settings as S

D = 86_400_000
W0 = int(pd.Timestamp("2020-01-01", tz="UTC").value // 1_000_000)  # 周三


def _weekly(n=120, drop_at=None):
    ob = W0 + np.arange(n, dtype="int64") * 7 * D
    v = 1e6 * np.exp(0.001 * np.arange(n) + 0.002 * np.sin(np.arange(n)))
    if drop_at is not None:
        v = v.copy()
        v[drop_at:] *= 0.9  # 外国官方突然抛售 10%
    return ob, v


def test_weekly_z_matches_pandas_research_formula():
    ob, v = _weekly(150)
    s = pd.Series(np.log(v))
    d = s - s.shift(4)
    ref = ((d - d.rolling(52, min_periods=52).mean()) / d.rolling(52, min_periods=52).std()).to_numpy()
    z = C.weekly_z(v, 52, 4)
    m = ~np.isnan(ref)
    assert np.array_equal(m, ~np.isnan(z))
    assert np.allclose(z[m], ref[m], atol=1e-9)


def test_known_from_is_wednesday_plus_3_days_no_lookahead():
    ob, v = _weekly(120, drop_at=100)
    st = {"custody_gate_enabled": True}
    known = ob[100] + 3 * D
    bl, z = C.block_mask(st, [known - 1, known], ob, v)
    zw = C.weekly_z(v, 52, 4)
    assert z[0] == zw[99] and z[1] == zw[100]  # 公布前（W+3 之前 1 毫秒）只看到上一周
    assert bl[1] and z[1] < -1 and bl[0] == (zw[99] < -1)


def test_fail_open_when_stale_or_short_history_or_empty():
    ob, v = _weekly(120, drop_at=100)
    st = {"custody_gate_enabled": True, "custody_gate_stale_days": 21}
    late = ob[-1] + 3 * D + 30 * D
    bl, z = C.block_mask(st, [late], ob, v)
    assert not bl[0] and np.isnan(z[0])
    bl, z = C.block_mask(st, [ob[10] + 3 * D], ob, v)  # 不足 N + h 周
    assert not bl[0] and np.isnan(z[0])
    bl, z = C.block_mask(st, [ob[-1]], np.array([], dtype="int64"), np.array([]))
    assert not bl[0]


def test_disabled_never_blocks():
    ob, v = _weekly(120, drop_at=100)
    bl, z = C.block_mask({}, [ob[110]], ob, v)
    assert not bl.any() and np.isnan(z).all()


def test_parse_drops_fred_zero_placeholders():
    d = C._parse("observation_date,WMTSECL1\n2002-12-18,0\n2007-07-04,1209781\n2007-07-11,.\n")
    assert list(d.values()) == [1209781.0]


def test_settings_defaults_validation_and_env(monkeypatch):
    st = S.validate(S._merge(S.DEFAULTS, {}))["strategy"] if hasattr(S, "validate") else S.DEFAULTS["strategy"]
    assert st["custody_gate_enabled"] is False
    assert (st["custody_gate_series"], st["custody_gate_n"], st["custody_gate_h"], st["custody_gate_k"]) == ("tsy", 52, 4, 1.0)
    for k, v in (("custody_gate_n", 5), ("custody_gate_k", 0), ("custody_gate_series", "xyz"), ("custody_gate_h", 20)):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": {k: v}}))


def test_backtest_gate_blocks_only_new_longs_and_matches_engine_function():
    from qtw.backtest import run_backtest
    n = 400
    t = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    c = 100 + np.sin(np.arange(n) / 7.0)
    df = pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + 0.3,
                       "low": c - 0.3, "close": c, "volume": 1.0})
    F = {"spot": {"ETHUSDT": df.copy()}, "perp": {"ETHUSDT": df.copy()}}

    def cfg(on):
        x = S._merge(S.DEFAULTS, {"symbols": ["ETHUSDT"]})
        x["strategy"].update(fast_ma=5, slow_ma=10, trend_ma=0, btc_regime_ma=0, port_vol_target=0, name_vol_target=0,
                             custody_gate_enabled=on)
        x["strategy"]["atr_stop_mult"] = 50.0
        return x

    def sig(val):
        def f(ind, idx, syms):
            a = np.zeros(len(idx), dtype=int)
            a[200:] = val
            return {s: a for s in syms}
        return f

    # 托管序列：回测期间（2024-01 → 2024-03）处于「抛售」周 → z 很负
    ob = int(pd.Timestamp("2022-02-16", tz="UTC").value // 1_000_000) + np.arange(120, dtype="int64") * 7 * D
    v = 1e6 * np.exp(0.001 * np.arange(120) + 0.0005 * np.sin(np.arange(120) * 1.3))
    v[100:] *= 0.97 ** np.arange(1, 21)
    om = t.as_unit("ms").asi8
    bl, _ = C.block_mask(cfg(True)["strategy"], om, ob, v)
    assert bl[199:].all()
    off = run_backtest(F, cfg(False), signals=sig(1))
    on = run_backtest(F, cfg(True), signals=sig(1), custody_data=(ob, v))
    assert len(off["trades"]) >= 1 and len(on["trades"]) == 0  # 新开多被拦
    assert on["summary"]["custody_gate"]["blocked_bars"] == int(bl.sum())
    s_off = run_backtest(F, cfg(False), signals=sig(-1))
    s_on = run_backtest(F, cfg(True), signals=sig(-1), custody_data=(ob, v))
    assert len(s_on["trades"]) == len(s_off["trades"]) >= 1  # 空单不受影响


def test_parse_fed_ddp_xml_stream_picks_named_series_only():
    import io
    xml = (b'<x><kf:Series SERIES_NAME="RESH4F_N.WW"><frb:Obs OBS_STATUS="A" OBS_VALUE="5" TIME_PERIOD="2007-07-04" /></kf:Series>'
           b'<kf:Series SERIES_NAME="RESH4FG_N.WW"><frb:Obs OBS_STATUS="A" OBS_VALUE="0" TIME_PERIOD="2002-12-18" />'
           b'<frb:Obs OBS_STATUS="A" OBS_VALUE="1209781" TIME_PERIOD="2007-07-04" /></kf:Series></x>')
    d = C._parse_fed_xml(io.BytesIO(xml), "RESH4FG_N.WW")
    assert list(d.values()) == [1209781.0]
    assert next(iter(d)) == int(pd.Timestamp("2007-07-04", tz="UTC").value // 1_000_000)
