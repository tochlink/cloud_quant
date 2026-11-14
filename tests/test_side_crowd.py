"""同侧拥挤上限（side_crowd_cap / side_crowd_mult，默认关闭）：纯函数口径、关闭时回测逐位一致、引擎与回测同口径。
synth() / book() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import numpy as np
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.engine import apply_side_crowd
from qtw.risk import size
from qtw.strategy import side_crowd_scales
from tests.test_backtest import book

RK = {"max_risk_per_trade": 0.05, "max_weight_per_name": 0.2}


def _cfg(**kw):
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=0, **kw)
    return c


def test_defaults_off_and_validation():
    st = S.DEFAULTS["strategy"]
    assert st["side_crowd_cap"] == 0 and st["side_crowd_mult"] == 1.25
    for k, v in (("side_crowd_cap", 0.5), ("side_crowd_cap", 60), ("side_crowd_mult", 0.1), ("side_crowd_mult", 4)):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"][k] = v
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(side_crowd_cap=5, side_crowd_mult=1.25)
    S.validate(c)


def test_scales_formula():
    rng = np.random.default_rng(5)
    n, N = 300, 8
    sig = {f"S{i}": rng.choice([-1, 0, 1], size=n) for i in range(N)}
    ls, ss = side_crowd_scales(sig, 5, 1.25)
    G = np.vstack(list(sig.values()))
    for t in range(n):
        for out, sgn in ((ls, 1), (ss, -1)):
            k = int((G[:, t] == sgn).sum())
            want = 1.25 * min(1.0, 5 / k) if k else 1.0
            assert abs(out[t] - want) < 1e-12
    a, b = side_crowd_scales(sig, 0, 1.25)
    assert (a == 1).all() and (b == 1).all()


def test_backtest_off_is_bit_identical_and_on_changes_sizing():
    d = book(4)
    r0 = run_backtest(d, _cfg())
    r1 = run_backtest(d, _cfg(side_crowd_cap=50, side_crowd_mult=1.0))  # C ≥ 币数且 m = 1 等价关闭
    assert r0["equity"]["equity"].tolist() == r1["equity"]["equity"].tolist()
    r2 = run_backtest(d, _cfg(side_crowd_cap=1, side_crowd_mult=1.25))
    assert r2["summary"]["side_crowd_cap"] == 1 and r2["summary"]["side_crowd_mult"] == 1.25
    assert r0["equity"]["equity"].tolist() != r2["equity"]["equity"].tolist()


def _rows(sig, nvm, held=()):
    return [{"symbol": s, "signal": int(g), "side": {1: "long", -1: "short", 0: "-"}[int(g)], "in_universe": True,
             "name_vol_mult": float(nvm[s]), "ref_price": 100.0, "atr": 2.0,
             "stop_source": "position" if s in held else "suggested", "target_notional_usdt": -1.0} for s, g in sig.items()]


def test_engine_matches_backtest_bar_by_bar():
    rng = np.random.default_rng(9)
    syms = [f"S{i}" for i in range(8)]
    n = 120
    sig = {s: rng.choice([-1, 0, 1], size=n) for s in syms}
    ls, ss = side_crowd_scales(sig, 4, 1.5)
    for t in range(n):
        rows = _rows({s: sig[s][t] for s in syms}, {s: 0.8 for s in syms})
        apply_side_crowd(rows, 4, 1.5, 1000.0, RK, 2.0)
        for r in rows:
            want = 0.8 * {1: ls[t], -1: ss[t], 0: 1.0}[r["signal"]]
            assert abs(r["name_vol_mult"] - want) < 1e-12


def test_engine_off_noop_and_resize():
    rows = _rows({"A": 1, "B": 1, "C": 1, "D": -1, "E": 0}, {s: 0.5 for s in "ABCDE"}, held=("C",))
    before = [dict(r) for r in rows]
    apply_side_crowd(rows, 0, 1.25, 1000.0, RK, 2.0)
    assert rows == before
    apply_side_crowd(rows, 2, 1.5, 1000.0, RK, 2.0)
    by = {r["symbol"]: r for r in rows}
    assert abs(by["A"]["name_vol_mult"] - 0.5) < 1e-12  # 1.5 · min(1, 2/3) = 1
    assert abs(by["D"]["name_vol_mult"] - 0.75) < 1e-12 and by["E"]["name_vol_mult"] == 0.5
    z = size(side="short", equity=1000.0, price=100.0, atr=2.0, max_risk=0.05 * 0.75, max_weight=0.2 * 0.75, atr_mult=2.0)
    assert abs(by["D"]["target_notional_usdt"] - z.notional) < 1e-9
    assert by["C"]["target_notional_usdt"] == -1.0
