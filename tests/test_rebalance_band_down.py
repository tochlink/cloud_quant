"""可选 rebalance_band_down（非对称调仓带：减仓用单独阈值，加仓仍用 rebalance_band）。"""
import types

import pytest

from qtw import settings as S
from qtw import rebalance as RB


def _cfg(band=0.1, down=0.0):
    c = S.load()
    return {**c, "strategy": {**c["strategy"], "rebalance_band": band, "rebalance_band_down": down, "rebalance_mode": "stop"},
            "risk": {**c["risk"], "max_risk_per_trade": 0.01, "max_weight_per_name": 1.0, "max_gross_exposure": 10.0}}


def _plan(cur_usdt, down):
    # 价格 100、止损 90 → 止损距离 10% → 目标 = 1000 × 1% / 10% = 100 USDT
    pos = {"X": types.SimpleNamespace(side="long", qty=cur_usdt / 100.0, stop_price=90.0)}
    return RB.plan(pos, {"X": 100.0}, {"X": 1.0}, equity=1000.0, new_notional=0.0, cfg=_cfg(0.1, down), gross_now=cur_usdt, fee=0.0)


def test_default_off_and_validated():
    c = S.load()
    assert c["strategy"]["rebalance_band_down"] == 0.0
    with pytest.raises(ValueError):
        S.validate({**c, "strategy": {**c["strategy"], "rebalance_band_down": 0.01}})


def test_down_band_only_affects_reductions():
    # 超出目标 20%：默认（同 0.1）会减仓；down=0.3 时不减
    assert len(_plan(120.0, 0.0)) == 1 and _plan(120.0, 0.0)[0]["delta_usdt"] < 0
    assert _plan(120.0, 0.3) == []
    # 超出 40%：两者都减
    assert _plan(140.0, 0.3)[0]["delta_usdt"] == pytest.approx(-40.0)
    # 低于目标 20%：加仓阈值不受 down 影响
    assert _plan(80.0, 0.3)[0]["delta_usdt"] == pytest.approx(20.0)
