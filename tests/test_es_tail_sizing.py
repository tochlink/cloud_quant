"""ES NORM 尾部厚度单币乘子（name_es_w / k / alpha，默认关闭）：纯函数口径、关闭时回测逐位一致、引擎与回测逐根同口径。"""
from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.engine import apply_es_tail
from qtw.risk import size
from qtw.strategy import es_tail_fatness, es_tail_mult
from tests.test_backtest import book

RK = {"max_risk_per_trade": 0.05, "max_weight_per_name": 0.2}


def _cfg(**kw):
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=0, **kw)
    return c


def test_defaults_off_and_validation():
    st = S.DEFAULTS["strategy"]
    assert st["name_es_w"] == 0 and st["name_es_k"] == 2.0 and st["name_es_alpha"] == 0.05
    for k, v in (("name_es_w", 5), ("name_es_w", 2000), ("name_es_k", 0.1), ("name_es_k", 6), ("name_es_alpha", 0.5), ("name_es_alpha", 0.001)):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"][k] = v
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(name_es_w=120, name_es_k=2.0)
    S.validate(c)


def test_fatness_formula():
    rng = np.random.default_rng(5)
    n, W, a = 400, 120, 0.05
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    FL, FS = es_tail_fatness(close, W, a)
    assert np.isnan(FL[:W]).all() and np.isfinite(FL[W:]).all()
    r = np.diff(np.log(close), prepend=np.nan)
    t = 300
    x = r[t - W + 1:t + 1]
    en = NormalDist().pdf(NormalDist().inv_cdf(a)) / a
    assert abs(FL[t] - (-x[x <= np.quantile(x, a)].mean()) / (x.std() * en)) < 1e-12
    assert abs(FS[t] - (x[x >= np.quantile(x, 1 - a)].mean()) / (x.std() * en)) < 1e-12
    assert 0.6 < np.nanmedian(FL) < 1.4  # 正态 ≈ 1


def test_mult_normalised_over_active():
    rng = np.random.default_rng(9)
    n, W = 300, 60
    syms = ["A", "B", "C", "D"]
    close = {s: 100 * np.exp(np.cumsum(rng.standard_t(3 + i, n) * 0.01)) for i, s in enumerate(syms)}
    sig = {s: rng.choice([-1, 0, 1], size=n) for s in syms}
    M = es_tail_mult(sig, close, W, 2.0)
    for t in range(W, n):
        act = [s for s in syms if sig[s][t] != 0]
        if act:
            assert abs(np.mean([M[s][t] for s in act]) - 1.0) < 1e-12
        for s in syms:
            if sig[s][t] == 0 and act:
                assert M[s][t] > 0
    off = es_tail_mult(sig, close, 0, 2.0)
    assert all((off[s] == 1).all() for s in syms)


def test_backtest_off_is_bit_identical_and_on_changes_sizing():
    d = book(4)
    r0 = run_backtest(d, _cfg())
    r1 = run_backtest(d, _cfg(name_es_w=0, name_es_k=3.0))
    assert r0["equity"]["equity"].tolist() == r1["equity"]["equity"].tolist()
    r2 = run_backtest(d, _cfg(name_es_w=40, name_es_k=3.0))
    assert r2["summary"]["name_es_w"] == 40 and r2["summary"]["name_es_k"] == 3.0
    assert r0["equity"]["equity"].tolist() != r2["equity"]["equity"].tolist()


def _rows(sig, nvm, mkt, held=()):
    return [{"symbol": s, "signal": int(g), "side": {1: "long", -1: "short", 0: "-"}[int(g)], "in_universe": True, "market": mkt[s],
             "name_vol_mult": float(nvm[s]), "ref_price": 100.0, "atr": 2.0,
             "stop_source": "position" if s in held else "suggested", "target_notional_usdt": -1.0} for s, g in sig.items()]


def test_engine_matches_backtest_bar_by_bar():
    rng = np.random.default_rng(11)
    syms = [f"S{i}" for i in range(5)]
    n, W, k = 140, 40, 2.0
    cl = {m: {s: 100 * np.exp(np.cumsum(rng.standard_t(4, n) * 0.01)) for s in syms} for m in ("spot", "perp")}
    sig = {s: rng.choice([-1, 0, 1], size=n) for s in syms}
    M = {m: es_tail_mult(sig, cl[m], W, k) for m in cl}
    t_idx = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    seen = 0
    for t in range(W + 1, n):
        closes = {m: {s: pd.Series(cl[m][s][:t + 1], index=t_idx[:t + 1]) for s in syms} for m in cl}
        mkt = {s: "spot" if sig[s][t] > 0 else "perp" for s in syms}
        rows = _rows({s: sig[s][t] for s in syms}, {s: 0.8 for s in syms}, mkt)
        apply_es_tail(rows, closes, W, k, 0.05, 1000.0, RK, 2.0)
        for r in rows:
            want = 0.8 * M[mkt[r["symbol"]]][r["symbol"]][t] if r["signal"] != 0 else 0.8
            assert abs(r["name_vol_mult"] - want) < 1e-12
            seen += r["signal"] != 0
    assert seen > 0


def test_engine_off_noop_and_resize():
    rng = np.random.default_rng(2)
    idx = pd.date_range("2026-01-01", periods=80, freq="4h", tz="UTC")
    closes = {m: {s: pd.Series(100 * np.exp(np.cumsum(rng.standard_t(3, 80) * 0.01)), index=idx) for s in "ABD"} for m in ("spot", "perp")}
    rows = _rows({"A": 1, "B": -1, "D": 1}, {"A": 0.5, "B": 1.0, "D": 0.5}, {"A": "spot", "B": "perp", "D": "spot"}, held=("D",))
    before = [dict(r) for r in rows]
    apply_es_tail(rows, closes, 0, 2.0, 0.05, 1000.0, RK, 2.0)
    apply_es_tail(rows, closes, 100, 2.0, 0.05, 1000.0, RK, 2.0)  # 历史不足
    assert rows == before
    apply_es_tail(rows, closes, 40, 2.0, 0.05, 1000.0, RK, 2.0)
    by = {r["symbol"]: r for r in rows}
    f = by["A"]["es_tail_mult"]
    z = size(side="long", equity=1000.0, price=100.0, atr=2.0, max_risk=0.05 * 0.5 * f, max_weight=0.2 * 0.5 * f, atr_mult=2.0)
    assert abs(by["A"]["target_notional_usdt"] - z.notional) < 1e-9
    assert by["D"]["target_notional_usdt"] == -1.0 and abs(by["D"]["name_vol_mult"] - 0.5 * by["D"]["es_tail_mult"]) < 1e-12
