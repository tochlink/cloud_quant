"""多空对冲对乘数（hedge_pair_w / c / h，默认关闭）：纯函数口径、关闭时回测逐位一致、引擎与回测同口径、#9 只改仓位。
synth() / book() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw import strategies as R
from qtw.backtest import run_backtest
from qtw.engine import apply_hedge_pair
from qtw.risk import size
from qtw.strategy import hedge_pair_mask
from tests.test_backtest import book

RK = {"max_risk_per_trade": 0.05, "max_weight_per_name": 0.2}


def _cfg(**kw):
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=0, **kw)
    return c


def test_defaults_off_and_validation():
    st = S.DEFAULTS["strategy"]
    assert st["hedge_pair_w"] == 0 and st["hedge_pair_c"] == 0.5 and st["hedge_pair_h"] == 1.5
    for k, v in (("hedge_pair_w", 5), ("hedge_pair_w", 2000), ("hedge_pair_c", 1.5), ("hedge_pair_h", 0.1), ("hedge_pair_h", 4)):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"][k] = v
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(hedge_pair_w=180, hedge_pair_c=0.0, hedge_pair_h=1.5)
    S.validate(c)
    assert c["strategy"]["hedge_pair_c"] == 0.0


def test_mask_formula():
    rng = np.random.default_rng(3)
    n, W = 200, 30
    base = rng.normal(0, 0.01, n)
    close = {"A": 100 * np.exp(np.cumsum(base)), "B": 50 * np.exp(np.cumsum(base + rng.normal(0, 0.002, n))),
             "C": 10 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))}
    sig = {"A": np.ones(n, dtype=int), "B": -np.ones(n, dtype=int), "C": np.ones(n, dtype=int)}
    sig["B"][150:] = 1  # 150 根后 A/B 同向，不再是对冲对
    m = hedge_pair_mask(sig, close, W, 0.5)
    assert not m["A"][:W].any()  # 历史不足
    assert m["A"][W:150].all() and m["B"][W:150].all()  # 高相关 + 反向
    assert not m["A"][150:].any()
    r = {s: pd.Series(np.r_[np.nan, np.diff(np.log(close[s]))]) for s in close}
    rho_bc = r["B"].rolling(W).corr(r["C"]).to_numpy()
    want_c = (np.arange(n) < 150) & (rho_bc >= 0.5)
    assert (m["C"] == want_c).all()
    assert not any(v.any() for v in hedge_pair_mask(sig, close, 0, 0.5).values())


def test_backtest_off_is_bit_identical_and_on_changes_sizing():
    d = book(4)
    r0 = run_backtest(d, _cfg())
    r1 = run_backtest(d, _cfg(hedge_pair_w=40, hedge_pair_c=0.5, hedge_pair_h=1.0))  # h=1 等价关闭
    assert r0["equity"]["equity"].tolist() == r1["equity"]["equity"].tolist()
    r2 = run_backtest(d, _cfg(hedge_pair_w=40, hedge_pair_c=-1.0, hedge_pair_h=1.5))
    assert r2["summary"]["hedge_pair_w"] == 40 and r2["summary"]["hedge_pair_h"] == 1.5
    assert r0["equity"]["equity"].tolist() != r2["equity"]["equity"].tolist()  # c=−1：任何反向信号都放大


def _rows(sig, nvm, held=()):
    return [{"symbol": s, "signal": int(g), "side": {1: "long", -1: "short", 0: "-"}[int(g)], "in_universe": True,
             "name_vol_mult": float(nvm[s]), "ref_price": 100.0, "atr": 2.0,
             "stop_source": "position" if s in held else "suggested", "target_notional_usdt": -1.0} for s, g in sig.items()]


def test_engine_matches_backtest_mask_bar_by_bar():
    rng = np.random.default_rng(11)
    syms = [f"S{i}" for i in range(5)]
    n, W, c, h = 160, 40, 0.3, 1.5
    f = rng.normal(0, 0.01, n)
    close = {s: 100 * np.exp(np.cumsum(f * rng.uniform(0, 1.5) + rng.normal(0, 0.008, n))) for s in syms}
    sig = {s: rng.choice([-1, 0, 1], size=n) for s in syms}
    m = hedge_pair_mask(sig, close, W, c)
    t_idx = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    hits = 0
    for t in range(W + 1, n):
        pc = {s: pd.Series(close[s][:t + 1], index=t_idx[:t + 1]) for s in syms}
        rows = _rows({s: sig[s][t] for s in syms}, {s: 0.8 for s in syms})
        apply_hedge_pair(rows, pc, W, c, h, 1000.0, RK, 2.0)
        for r in rows:
            want = 0.8 * h if (r["signal"] != 0 and m[r["symbol"]][t]) else 0.8
            assert abs(r["name_vol_mult"] - want) < 1e-12
            hits += r.get("hedge_pair", False)
    assert hits > 0


def test_engine_off_noop_and_resize():
    rows = _rows({"A": 1, "B": -1, "D": 1}, {"A": 0.5, "B": 1.0, "D": 0.5}, held=("D",))
    idx = pd.date_range("2026-01-01", periods=60, freq="4h", tz="UTC")
    x = np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, 60)))
    pc = {"A": pd.Series(x, index=idx), "B": pd.Series(2 * x, index=idx), "D": pd.Series(3 * x, index=idx)}
    before = [dict(r) for r in rows]
    apply_hedge_pair(rows, pc, 0, 0.5, 1.5, 1000.0, RK, 2.0)
    apply_hedge_pair(rows, pc, 30, 0.5, 1.0, 1000.0, RK, 2.0)
    assert rows == before
    apply_hedge_pair(rows, pc, 30, 0.5, 1.5, 1000.0, RK, 2.0)
    by = {r["symbol"]: r for r in rows}
    assert abs(by["A"]["name_vol_mult"] - 0.75) < 1e-12 and abs(by["B"]["name_vol_mult"] - 1.5) < 1e-12
    z = size(side="long", equity=1000.0, price=100.0, atr=2.0, max_risk=0.05 * 0.75, max_weight=0.2 * 0.75, atr_mult=2.0)
    assert abs(by["A"]["target_notional_usdt"] - z.notional) < 1e-9
    assert by["D"]["target_notional_usdt"] == -1.0 and abs(by["D"]["name_vol_mult"] - 0.75) < 1e-12


def test_strategy9_overrides_only_sizing():
    cfg = S.load()
    c = R.strategy_cfg(cfg, "ma_trend_lsp_hp")
    assert R.BY_ID["ma_trend_lsp_hp"]["signal"] is None
    st = c["strategy"]
    assert (st["hedge_pair_w"], st["hedge_pair_c"], st["hedge_pair_h"], st["ls_parity_cap"]) == (180, 0.5, 1.5, 3.0)
    assert c["risk"]["max_risk_per_trade"] == 0.03 and st["port_vol_target"] == 0.5
    for k in ("fast_ma", "slow_ma", "trend_ma", "btc_regime_ma", "confirm_bars", "atr_stop_mult"):
        assert st[k] == cfg["strategy"][k]
    S.validate(c)
    from qtw import shadow
    assert "ma_trend_lsp_hp" not in shadow.active_ids()
    assert R.VERDICTS["ma_trend_lsp_hp"]["status"] == "观察"
