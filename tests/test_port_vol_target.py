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
    assert c["strategy"]["port_vol_target"] == 0.0
    for bad in ({"port_vol_target": 0.01}, {"port_vol_target": 3}, {"port_vol_lookback": 10}):
        cfg = S._merge(S.DEFAULTS, {"strategy": bad})
        try:
            S.validate(cfg)
        except ValueError:
            continue
        raise AssertionError(bad)
