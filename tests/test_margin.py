import math

import pytest

from qtw import margin as M


def test_liq_price_short_and_long():
    assert M.isolated_liq_price("short", 100.0, 10, 0.005) == pytest.approx(109.5)
    assert M.isolated_liq_price("long", 100.0, 10, 0.005) == pytest.approx(90.5)
    assert M.isolated_liq_price("空", 100.0, 1, 0.0) == pytest.approx(200.0)


def test_adverse_distance_sign():
    assert M.adverse_stop_distance("short", 100.0, 104.0) == pytest.approx(0.04)
    assert M.adverse_stop_distance("long", 100.0, 96.0) == pytest.approx(0.04)
    # 止损已锁利：负距离
    assert M.adverse_stop_distance("short", 100.0, 98.0) == pytest.approx(-0.02)


def test_max_safe_leverage_formula():
    # d=3.9%（研究中位数）: floor(1/(0.039+0.005+0.005)) = 20
    assert M.max_safe_isolated_leverage("short", 100.0, 103.9) == 20
    # d=20.6%（加仓后 p90）: floor(1/0.216) = 4
    assert M.max_safe_isolated_leverage("short", 100.0, 120.6) == 4
    # d=72%（加仓后最大）: 1
    assert M.max_safe_isolated_leverage("short", 100.0, 172.0) == 1
    # 锁利止损 → 上限
    assert M.max_safe_isolated_leverage("short", 100.0, 95.0, cap=100) == 100


def test_effective_leverage_caps_request():
    assert M.effective_isolated_leverage(10, "short", 100.0, 103.9) == 10
    assert M.effective_isolated_leverage(100, "short", 100.0, 103.9) == 20
    assert M.effective_isolated_leverage(10, "short", 100.0, 120.6) == 4
    assert M.effective_isolated_leverage(0.5, "long", 100.0, 96.0) == 1
    assert M.effective_isolated_leverage(500, "long", 100.0, 99.9) == 90
    assert M.effective_isolated_leverage(500, "long", 100.0, 101.0) == 100


@pytest.mark.parametrize("side,stop", [("short", 103.9), ("short", 112.0), ("long", 93.0), ("long", 81.0)])
def test_capped_leverage_always_puts_stop_first(side, stop):
    for req in (1, 3, 5, 10, 20, 50, 100):
        lev = M.effective_isolated_leverage(req, side, 100.0, stop)
        assert M.stop_precedes_liquidation(side, 100.0, stop, lev, buffer=M.DEFAULT_BUFFER)


def test_uncapped_10x_fails_for_wide_stop():
    # 研究里的典型失败：均价下移后止损距离 20%，10 倍逐仓强平价 109.5 < 止损 120
    assert not M.stop_precedes_liquidation("short", 100.0, 120.0, 10)
    assert M.stop_precedes_liquidation("short", 100.0, 120.0, 4)


def test_rebalance_add_lowers_avg_entry_and_cap():
    # 首次 100 开空，止损 108 → 上限 11；盈利后在 80 加同等名义，均价约 88.9，止损不动 → 上限降到 4
    first = M.max_safe_isolated_leverage("short", 100.0, 108.0)
    avg = 2.0 / (1 / 100.0 + 1 / 80.0)  # 等名义加仓后的数量加权均价
    after = M.max_safe_isolated_leverage("short", avg, 108.0)
    assert first == 11 and after == 4


def test_margin_and_validation():
    assert M.isolated_margin(-1000.0, 10) == pytest.approx(100.0)
    with pytest.raises(ValueError):
        M.isolated_liq_price("short", 100.0, 0.5)
    with pytest.raises(ValueError):
        M.adverse_stop_distance("flat", 100.0, 101.0)
    with pytest.raises(ValueError):
        M.adverse_stop_distance("long", float("nan"), 101.0)
