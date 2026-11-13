import numpy as np

from qtw import settings as S
from qtw.strategy import port_vol_factor


def test_port_vol_factor_basic():
    assert port_vol_factor([100, 101, 102], 0, 2) == 1.0  # 关闭
    assert port_vol_factor([100, 101], 0.3, 5) == 1.0  # 历史不足
    assert port_vol_factor([100.0] * 10, 0.3, 5) == 1.0  # σ = 0
    rng = np.random.default_rng(0)
    eq = 100 * np.cumprod(1 + rng.normal(0, 0.02, 400))  # 年化约 0.02×√2190 ≈ 94%
    k = port_vol_factor(eq, 0.3, 180)
    assert 0.2 < k < 0.5
    assert port_vol_factor(eq, 5.0, 180) == 1.0  # 只缩不放


def test_port_vol_settings_validation():
    c = S._merge(S.DEFAULTS, {})
    assert c["strategy"]["port_vol_target"] == 0.30
    for bad in ({"port_vol_target": 0.01}, {"port_vol_target": 3}, {"port_vol_lookback": 10}):
        cfg = S._merge(S.DEFAULTS, {"strategy": bad})
        try:
            S.validate(cfg)
        except ValueError:
            continue
        raise AssertionError(bad)


def test_bar_close_equity_buckets_last_per_bar():
    from qtw.strategy import bar_close_equity
    H = 4 * 3600 * 1000
    led = [{"time": "2026-01-01T00:10:00+00:00", "equity_usdt": 100}, {"time": "2026-01-01T03:50:00Z", "equity_usdt": 101},
           {"time": "2026-01-01T04:00:00Z", "equity_usdt": 102}, {"time": "bad", "equity_usdt": 5}, {"time": "2026-01-01T09:00:00Z", "equity_usdt": None}]
    assert bar_close_equity(led, H) == [101.0, 102.0]


def test_bar_close_equity_fills_missed_bars_geometrically():
    """停机漏掉的 K 线按几何插值补齐：桶数 = 跨越的根数，跨多根的收益均摊，不被当成一根收益抬高波动率。"""
    from qtw.strategy import bar_close_equity
    H = 4 * 3600 * 1000
    led = [{"time": "2026-01-01T03:00:00Z", "equity_usdt": 100}, {"time": "2026-01-01T15:00:00Z", "equity_usdt": 133.1},
           {"time": "2026-01-01T19:00:00Z", "equity_usdt": 140}]
    out = bar_close_equity(led, H)
    assert len(out) == 5
    assert [round(x, 6) for x in out[:4]] == [100.0, 110.0, 121.0, 133.1] and out[4] == 140.0


def test_vol_scaled_cfg_scales_caps_only_when_enabled():
    from qtw import engine as E

    class BK:
        def __init__(self, led): self._led = led
        def ledger(self): return self._led
    rng = np.random.default_rng(1)
    eq = 1000 * np.cumprod(1 + rng.normal(0, 0.02, 300))
    led = [{"time": f"2026-01-{1 + i // 6:02d}T{(i % 6) * 4:02d}:00:00Z", "equity_usdt": float(v)} for i, v in enumerate(eq[:186])]
    c = S._merge(S.DEFAULTS, {})
    c["strategy"]["port_vol_target"] = 0.0
    off = E.vol_scaled_cfg(c, BK(led))
    assert off["_pv_k"] == 1.0 and off["risk"] == c["risk"]
    c["strategy"]["port_vol_target"] = 0.3
    on = E.vol_scaled_cfg(c, BK(led))
    assert 0 < on["_pv_k"] < 1
    assert abs(on["risk"]["max_risk_per_trade"] - c["risk"]["max_risk_per_trade"] * on["_pv_k"]) < 1e-12
    assert on["risk"]["max_gross_exposure"] == c["risk"]["max_gross_exposure"]
    assert E.vol_scaled_cfg(on, BK(led)) is on  # 不重复缩放
    assert E.vol_scaled_cfg(c, BK(led[:50]))["_pv_k"] == 1.0  # 历史不足
