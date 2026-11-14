"""BTC 体制线多周期投票（btc_regime_vote_k，默认 0 = 单线）：纯函数口径、关闭时与单线逐位一致、引擎取数长度与回测同口径。
synth() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import numpy as np
import pandas as pd
import pytest

from qtw import engine as E
from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.strategy import btc_regime_blocks_long, regime_vote_lengths
from tests.test_backtest import synth


def test_lengths_and_defaults():
    assert regime_vote_lengths(1200) == [600, 900, 1200, 1500, 1800]
    assert S.DEFAULTS["strategy"]["btc_regime_vote_k"] == 0
    for k, n in ((6, 1200), (-1, 1200), (3, 1400)):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"].update(btc_regime_vote_k=k, btc_regime_ma=n)
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"]["btc_regime_vote_k"] = 3
    S.validate(c)


def test_vote_formula_and_off_identity():
    c = synth(900, seed=3)["close"]
    n = 200
    assert btc_regime_blocks_long(c, n, 0).equals(btc_regime_blocks_long(c, n))
    x = pd.Series(c, dtype=float)
    votes = sum((x < x.rolling(m).mean()).fillna(False).astype(int) for m in (100, 150, 200, 250, 300))
    for k in range(1, 6):
        got = btc_regime_blocks_long(c, n, k)
        assert got.equals(votes >= k)
    # k1 ⊇ k3 ⊇ k5；未形成的 SMA 不计票（前 99 根全不拦）
    assert (btc_regime_blocks_long(c, n, 1) >= btc_regime_blocks_long(c, n, 3)).all()
    assert not btc_regime_blocks_long(c, n, 1).iloc[:99].any()
    assert not btc_regime_blocks_long(c, 0, 3).any()


def _data():
    spot = {"BTCUSDT": synth(900, seed=11), "S1USDT": synth(900, seed=1)}
    perp = {"BTCUSDT": synth(900, seed=11, scale=1.01), "S1USDT": synth(900, seed=1, scale=1.01)}
    return {"spot": spot, "perp": perp}


def test_backtest_off_bit_identical_and_vote_runs():
    d = _data()
    base = S._merge(S.DEFAULTS, {"symbols": ["BTCUSDT", "S1USDT"]})
    base["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=200)
    a = run_backtest(d, base)
    c0 = S._merge(base, {}); c0["strategy"]["btc_regime_vote_k"] = 0
    b = run_backtest(d, c0)
    assert a["equity"]["equity"].tolist() == b["equity"]["equity"].tolist()
    for k in (1, 3, 5):
        ck = S._merge(base, {}); ck["strategy"]["btc_regime_vote_k"] = k
        r = run_backtest(d, ck)
        assert np.isfinite(r["equity"]["equity"]).all()


def test_engine_fetches_longest_vote_sma(monkeypatch):
    df = synth(2000, seed=7)
    seen = []

    def fake(venue, sym, interval, limit, market):
        seen.append(limit)
        return df.tail(limit).reset_index(drop=True)
    monkeypatch.setattr(E.mcache, "candles", fake)
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"]["btc_regime_vote_k"] = 3
    r = E._btc_regime_state(cfg)
    assert seen[-1] == 1805 and r["vote_k"] == 3
    assert r["blocked"] == bool(btc_regime_blocks_long(df.tail(1805)["close"].reset_index(drop=True), 1200, 3).iloc[-1])
    cfg["strategy"]["btc_regime_vote_k"] = 0
    r = E._btc_regime_state(cfg)
    assert seen[-1] == 1205 and r["vote_k"] == 0


def test_strategy11_overrides_only_regime_vote():
    from qtw import shadow
    from qtw import strategies as R
    cfg = S.load()
    c = R.strategy_cfg(cfg, "ma_trend_regime_vote")
    assert R.BY_ID["ma_trend_regime_vote"]["no"] == 11 and R.BY_ID["ma_trend_regime_vote"]["signal"] is None
    st = c["strategy"]
    assert st["btc_regime_vote_k"] == 3
    for k in ("fast_ma", "slow_ma", "trend_ma", "btc_regime_ma", "confirm_bars", "atr_stop_mult", "port_vol_target", "side_crowd_cap"):
        assert st[k] == cfg["strategy"][k]
    assert c["risk"] == cfg["risk"]
    S.validate(c)
    assert "ma_trend_regime_vote" not in shadow.active_ids()
    assert R.VERDICTS["ma_trend_regime_vote"]["status"] == "观察"
