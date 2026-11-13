"""跨根分批入场（staged_entry_f1，默认关闭）的回测测试：默认关闭、参数校验、首笔按 f1、下一根补满、无前视。
synth() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import pandas as pd
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from tests.test_backtest import book


def _cfg(f1=0.0):
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=0, staged_entry_f1=f1, rebalance_band=0)
    return c


def test_default_off_and_validation():
    assert S.DEFAULTS["strategy"]["staged_entry_f1"] == 0
    for v in (0.01, 0.99, 1.5, -0.2):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"]["staged_entry_f1"] = v
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"]["staged_entry_f1"] = 0.25
    S.validate(c)


def test_off_has_no_topups():
    r = run_backtest(book(3), _cfg(0))
    assert r["summary"]["staged_topups"] == 0


def test_first_fill_fraction_then_topup_next_bar():
    data = book(3, 800)
    off = run_backtest(data, _cfg(0))
    on = run_backtest(data, _cfg(0.25))
    assert on["summary"]["staged_topups"] > 0
    t_on = on["trades"]
    # 只持有 1 根就离场的仓位没有机会补仓：名义应约为 f1 × 计划名义，明显小于补满后的仓位
    one = t_on[t_on["bars_held"] == 1]
    more = t_on[t_on["bars_held"] >= 2]
    if len(one) and len(more):
        assert one["notional_usdt"].median() < more["notional_usdt"].median()
    # 止损价保持首笔的 ATR 止损（补仓不移动止损）
    assert (t_on["stop_price"] == t_on["init_stop"]).all()
    # 同样的信号 → 同一批入场时间（分批只改规模，不改时机）
    k_off = set(zip(off["trades"]["symbol"], off["trades"]["entry_time"]))
    k_on = set(zip(t_on["symbol"], t_on["entry_time"]))
    assert len(k_off & k_on) >= 0.9 * len(k_off)


def test_staged_no_lookahead():
    data = book(3, 800)
    cut = {m: {s: d.iloc[:700] for s, d in v.items()} for m, v in data.items()}
    a = run_backtest(data, _cfg(0.25))["trades"]
    b = run_backtest(cut, _cfg(0.25))["trades"]
    last = pd.Timestamp(cut["spot"]["S0USDT"]["open_time"].iloc[-1])
    ka = a[(a["status"] == "closed") & (a["exit_time"].map(pd.Timestamp) < last)].reset_index(drop=True)
    kb = b[(b["status"] == "closed") & (b["exit_time"].map(pd.Timestamp) < last)].reset_index(drop=True)
    cols = ["symbol", "side", "entry_time", "exit_time", "qty", "pnl_usdt"]
    pd.testing.assert_frame_equal(ka[cols], kb[cols])
