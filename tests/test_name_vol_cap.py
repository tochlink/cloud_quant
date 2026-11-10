import numpy as np

from qtw import rebalance as RB
from qtw import settings as S
from qtw.strategy import name_vol_mult


def test_name_vol_mult_basic():
    assert (name_vol_mult([1, 2, 3], 0, 2) == 1).all()  # 关闭
    m = name_vol_mult([100.0] * 10, 0.6, 5)
    assert (m == 1).all()  # σ = 0 → 不缩
    rng = np.random.default_rng(1)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 400)))  # 年化约 0.03×√2190 ≈ 140%
    m = name_vol_mult(c, 0.6, 120)
    assert (m[:120] == 1).all()  # 历史不足
    assert 0.3 < m[-1] < 0.6
    assert (m <= 1).all()
    assert (name_vol_mult(c, 5.0, 120) == 1).all()  # 只缩不放


def test_name_vol_settings_default_and_validation():
    c = S._merge(S.DEFAULTS, {})
    assert c["strategy"]["name_vol_target"] == 0.60 and c["strategy"]["name_vol_lookback"] == 120
    for bad in ({"name_vol_target": 0.05}, {"name_vol_target": 9}, {"name_vol_lookback": 5}):
        cfg = S._merge(S.DEFAULTS, {"strategy": bad})
        try:
            S.validate(cfg)
        except ValueError:
            continue
        raise AssertionError(bad)


class _P:
    def __init__(self, side, qty, stop):
        self.side, self.qty, self.stop_price = side, qty, stop


def test_rebalance_plan_name_mult_scales_target():
    cfg = S._merge(S.DEFAULTS, {})
    pos = {"A": _P("long", 2.0, 90.0)}
    base = RB.plan(pos, {"A": 100.0}, {"A": 1.0}, equity=1000, new_notional=0, cfg=cfg, gross_now=200, fee=0.001)
    half = RB.plan(pos, {"A": 100.0}, {"A": 1.0}, equity=1000, new_notional=0, cfg=cfg, gross_now=200, fee=0.001, name_mult={"A": 0.5})
    assert not base  # 已在目标 200 USDT
    assert half and abs(half[0]["target_usdt"] - 100.0) < 1e-6
