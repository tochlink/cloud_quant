"""整段回测因果性回归：所有可选参数同时打开时，篡改第 k 根之后的数据不得改变第 k 根之前的权益与已平仓交易。

synth() 只是测试专用的确定性序列（见 tests/test_backtest.py），不是行情数据。
"""
import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from tests.test_backtest import synth

ALL_ON = dict(ls_parity_cap=3.0, hedge_pair_w=60, hedge_pair_c=0.0, hedge_pair_h=1.5, staged_entry_f1=0.5,
              tp_r=2.0, tp_frac=0.5, sar_hold_bars=6, chop_n=30, elder_short_gate_n=13, elder_short_gate_x=1.0)


def _book(n_sym=4, n=700):
    spot = {f"S{i}USDT": synth(n, seed=10 + i) for i in range(n_sym)}
    perp = {f"S{i}USDT": synth(n, seed=10 + i, scale=1.01) for i in range(n_sym)}
    return {"spot": spot, "perp": perp}


@pytest.mark.parametrize("opts", [{}, ALL_ON], ids=["default", "all_options"])
def test_no_lookahead_with_all_options(opts):
    c = S.load()
    c = {**c, "strategy": {**c["strategy"], **opts}}
    a = _book()
    k = 520
    b = {m: {s: d.copy() for s, d in v.items()} for m, v in a.items()}
    for v in b.values():
        for d in v.values():
            d.loc[k:, ["open", "high", "low", "close"]] *= 0.4
    ra, rb = run_backtest(a, c), run_backtest(b, c)
    cut = a["spot"]["S0USDT"]["close_time"].iloc[k - 1].isoformat()
    ea = ra["equity"][ra["equity"]["time"] <= cut]["equity"].to_numpy()
    eb = rb["equity"][rb["equity"]["time"] <= cut]["equity"].to_numpy()
    assert len(ea) > 50
    np.testing.assert_allclose(ea, eb)
    cols = ["symbol", "entry_time", "entry_price", "qty", "exit_price", "pnl_usdt"]
    done = lambda t: t[(t["status"] == "closed") & (t["exit_time"] < cut)][cols].sort_values(["entry_time", "symbol"]).reset_index(drop=True)
    da = done(ra["trades"])
    assert len(da) > 0
    pd.testing.assert_frame_equal(da, done(rb["trades"]))
