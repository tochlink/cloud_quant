"""加密股相对强弱闸门（可选，默认关）：rs 公式、D+1 无前视、失败开放、只拦新开多、回测与引擎同一函数、设置校验、Nasdaq 解析。"""
import json

import numpy as np
import pandas as pd
import pytest

from qtw import cryptoeq as C
from qtw import settings as S

D = 86_400_000


def _btc4h(days=200, start="2024-01-01", drift=0.0):
    t = pd.date_range(start, periods=days * 6, freq="4h", tz="UTC")
    c = 40000 * np.exp(drift * np.arange(len(t)) / 6 + 0.01 * np.sin(np.arange(len(t)) / 9))
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c, "low": c, "close": c, "volume": 1.0})


def _stock(days=200, start="2024-01-01", path=None):
    d = pd.bdate_range(start, periods=days, tz="UTC")
    v = 300 * np.exp(0.002 * np.arange(len(d))) if path is None else path(len(d))
    return d.as_unit("ms").asi8, np.asarray(v, float)


def test_rs_change_matches_research_pandas_formula():
    btc = _btc4h(260)
    sk, sv = _stock(180, path=lambda n: 200 * np.exp(0.01 * np.cos(np.arange(n) / 5)))
    bk, bv = C.btc20(btc)
    days, chg = C.rs_change(sk, sv, bk, bv, 20)
    b20 = btc[btc.close_time.dt.hour == 20].set_index(btc[btc.close_time.dt.hour == 20].close_time.dt.normalize())["close"]
    px = pd.Series(sv, index=pd.to_datetime(sk, unit="ms", utc=True))
    rs = np.log(px / b20.reindex(px.index)).dropna()
    ref = (rs - rs.shift(20)).to_numpy()
    assert np.array_equal(days, rs.index.as_unit("ms").asi8)
    m = ~np.isnan(ref)
    assert np.array_equal(m, ~np.isnan(chg)) and np.allclose(chg[m], ref[m], atol=1e-12)


def test_btc20_takes_bar_closing_at_20utc():
    btc = _btc4h(3)
    bk, bv = C.btc20(btc)
    assert len(bk) == 3
    row = btc[btc.close_time == pd.Timestamp("2024-01-02 20:00", tz="UTC")]
    assert bv[1] == float(row.close.iloc[0]) and bk[1] == int(pd.Timestamp("2024-01-02", tz="UTC").value // 1_000_000)


def test_known_from_next_day_no_lookahead_and_blocks_on_falling_rs():
    btc = _btc4h(120)
    # 股票先涨后在第 60 个交易日起相对 BTC 暴跌
    sk, sv = _stock(80, path=lambda n: np.where(np.arange(n) < 60, 300 * np.exp(0.01 * np.arange(n)), 100.0))
    st = {"cryptoeq_gate_enabled": True}
    known = sk[60] + D
    bl, c = C.block_mask(st, [known - 1, known], btc, (sk, sv))
    days, chg = C.rs_change(sk, sv, *C.btc20(btc), 20)
    j = int(np.searchsorted(days, sk[60]))
    assert c[0] == chg[j - 1] and c[1] == chg[j]  # 公布前 1 毫秒只看到上一交易日
    assert not bl[0] and c[0] > 0 and bl[1] and c[1] <= 0


def test_fail_open_when_stale_short_or_empty_and_disabled():
    btc = _btc4h(120)
    sk, sv = _stock(80)
    st = {"cryptoeq_gate_enabled": True, "cryptoeq_gate_stale_days": 7}
    bl, c = C.block_mask(st, [sk[-1] + 20 * D], btc, (sk, sv))
    assert not bl[0] and np.isnan(c[0])
    bl, c = C.block_mask(st, [sk[5] + D], btc, (sk, sv))  # 不足 n 个交易日
    assert not bl[0] and np.isnan(c[0])
    bl, c = C.block_mask(st, [sk[-1]], None, (sk, sv))  # 没有 BTC
    assert not bl[0]
    bl, c = C.block_mask({}, [sk[-1]], btc, (sk, sv))
    assert not bl.any() and np.isnan(c).all()


def test_parse_nasdaq_json():
    txt = json.dumps({"data": {"tradesTable": {"rows": [
        {"date": "11/20/2026", "close": "$1,234.50"}, {"date": "11/19/2026", "close": "N/A"}, {"date": "08/07/2024", "close": "$124.685"}]}}})
    d = C.parse_nasdaq(txt)
    assert d[int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000)] == 1234.5 and len(d) == 2


def test_settings_defaults_validation_and_env(monkeypatch):
    st = S.validate(S._merge(S.DEFAULTS, {}))["strategy"]
    assert st["cryptoeq_gate_enabled"] is False
    assert (st["cryptoeq_gate_symbol"], st["cryptoeq_gate_n"], st["cryptoeq_gate_stale_days"]) == ("MSTR", 20, 7.0)
    for k, v in (("cryptoeq_gate_n", 2), ("cryptoeq_gate_symbol", "TSLA"), ("cryptoeq_gate_stale_days", 1)):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": {k: v}}))


def test_backtest_gate_blocks_only_new_longs_and_matches_engine_function():
    from qtw.backtest import run_backtest
    n = 400
    t = pd.date_range("2024-03-01", periods=n, freq="4h", tz="UTC")
    c = 100 + np.sin(np.arange(n) / 7.0)
    df = pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + 0.3,
                       "low": c - 0.3, "close": c, "volume": 1.0})
    btc = _btc4h(200, start="2024-01-01")
    F = {"spot": {"ETHUSDT": df.copy()}, "perp": {"ETHUSDT": df.copy()}}

    def cfg(on):
        x = S._merge(S.DEFAULTS, {"symbols": ["ETHUSDT"]})
        x["strategy"].update(fast_ma=5, slow_ma=10, trend_ma=0, btc_regime_ma=0, port_vol_target=0, name_vol_target=0,
                             cryptoeq_gate_enabled=on)
        x["strategy"]["atr_stop_mult"] = 50.0
        return x

    def sig(val):
        def f(ind, idx, syms):
            a = np.zeros(len(idx), dtype=int)
            a[200:] = val
            return {s: a for s in syms}
        return f

    sk, sv = _stock(150, start="2024-01-01", path=lambda k: 300 * np.exp(-0.01 * np.arange(k)))  # 相对 BTC 持续走弱
    bl, _ = C.block_mask(cfg(True)["strategy"], t.as_unit("ms").asi8, btc, (sk, sv))
    assert bl[199:].all()
    off = run_backtest(F, cfg(False), signals=sig(1), btc_spot=btc)
    on = run_backtest(F, cfg(True), signals=sig(1), btc_spot=btc, cryptoeq_data=(sk, sv))
    assert len(off["trades"]) >= 1 and len(on["trades"]) == 0
    assert on["summary"]["cryptoeq_gate"]["blocked_bars"] == int(bl.sum())
    s_off = run_backtest(F, cfg(False), signals=sig(-1), btc_spot=btc)
    s_on = run_backtest(F, cfg(True), signals=sig(-1), btc_spot=btc, cryptoeq_data=(sk, sv))
    assert len(s_on["trades"]) == len(s_off["trades"]) >= 1
