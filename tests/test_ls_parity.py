"""动态多空风险平价 up（ls_parity_cap，默认关闭）的测试：纯函数口径、关闭时与原回测逐位一致、只放大较小一侧且不超过上限。
synth() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import numpy as np
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.strategy import ls_parity_scales
from tests.test_backtest import book


def _cfg(cap=0.0, mode=None):
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=0, ls_parity_cap=cap)
    if mode:
        c["strategy"]["trade_mode"] = mode
    return c


def test_default_off_and_validation():
    assert S.DEFAULTS["strategy"]["ls_parity_cap"] == 0
    for v in (-1, 0.5, 11):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"]["ls_parity_cap"] = v
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"]["ls_parity_cap"] = 3
    S.validate(c)


def test_scales_formula():
    sig = {"A": np.array([1, 1, 1, 0, -1]), "B": np.array([1, -1, -1, 0, -1]), "C": np.array([-1, -1, 1, 1, -1])}
    one = {s: np.ones(5) for s in sig}
    ls, ss = ls_parity_scales(sig, one, one, 3.0)
    # bar0: L=2,S=1 → 空放大 2；bar1: L=1,S=2 → 多放大 2；bar2: L=2,S=1；bar3: 只有多 → 1；bar4: 只有空 → 1
    assert ls.tolist() == [1, 2, 1, 1, 1] and ss.tolist() == [2, 1, 2, 1, 1]
    ls, ss = ls_parity_scales(sig, one, {s: np.full(5, 0.1) for s in sig}, 3.0)
    assert ss[0] == pytest.approx(3.0) and ls[0] == 1  # 封顶 cap
    ls, ss = ls_parity_scales(sig, one, one, 0)
    assert (ls == 1).all() and (ss == 1).all()
    assert (np.minimum(ls, ss) == 1).all()  # 只放大不缩小


@pytest.mark.parametrize("mode", [None, "perp_both"])
def test_off_identical_and_on_changes_book(mode):
    data = book(3, 800)
    base = run_backtest(data, _cfg(0, mode))
    one = run_backtest(data, _cfg(1.0, mode))
    assert base["summary"]["ending_equity_usdt"] == one["summary"]["ending_equity_usdt"]
    assert base["trades"].equals(one["trades"])
    on = run_backtest(data, _cfg(3.0, mode))
    assert on["summary"]["ending_equity_usdt"] != base["summary"]["ending_equity_usdt"]
