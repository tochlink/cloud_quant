import numpy as np
import pandas as pd

from qtw import settings as S
from qtw.strategy import btc_regime_blocks_long


def test_regime_mask_basic():
    c = pd.Series([10, 10, 10, 10, 5, 20], dtype=float)
    m = btc_regime_blocks_long(c, 3)
    # 前 2 根 SMA 未形成 → 不拦；第 5 根 5 < SMA(10,10,5) → 拦；第 6 根 20 > SMA → 不拦
    assert m.tolist() == [False, False, False, False, True, False]
    assert not btc_regime_blocks_long(c, 0).any()


def test_regime_setting_validation():
    c = S._merge(S.DEFAULTS, {})
    assert c["strategy"]["btc_regime_ma"] == 1200
    for bad in (10, 5000):
        cfg = S._merge(S.DEFAULTS, {"strategy": {"btc_regime_ma": bad}})
        try:
            S.validate(cfg)
        except ValueError:
            continue
        raise AssertionError(bad)
