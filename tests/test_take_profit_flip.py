"""固定止盈（tp_r）与信号反转翻仓的一致性测试。synth() 仅为测试专用确定性序列。"""
import copy
import types

import pandas as pd
import pytest

from qtw import engine, settings as S
from qtw.backtest import run_backtest
from tests.test_backtest import book


def _cfg(**st):
    c = copy.deepcopy(S.DEFAULTS)
    c["symbols"] = []
    c["risk"]["trade_mode"] = "spot_perp"  # 本文件的价格构造按「现货做多 + 永续做空」口径
    c["strategy"].update(trend_ma=0, short_breaker_bars=0, name_vol_target=0, **st)  # 单币封顶会引发调仓加仓、改写加权入场价，这里只测止盈机制
    return c


def test_take_profit_off_by_default():
    assert S.DEFAULTS["strategy"]["tp_r"] == 0 and S.DEFAULTS["strategy"]["tp_reentry"] is False
    r = run_backtest(book(), _cfg())
    assert r["summary"]["take_profit_exits"] == 0
    assert (r["trades"]["exit_reason"] != "止盈").all()


def test_take_profit_fills_at_target_or_better_open():
    d = book()
    r = run_backtest(d, _cfg(tp_r=1.0))
    tr = r["trades"]
    tp = tr[tr.exit_reason == "止盈"]
    assert len(tp) > 0 and r["summary"]["take_profit_exits"] == len(tp)
    for _, t in tp.iterrows():
        assert t.target_price == pytest.approx(t.entry_price + (1 if t.side == "long" else -1) * abs(t.entry_price - t.stop_price))
        mk = "spot" if t.side == "long" else "perp"
        bar = d[mk][t.symbol].set_index("open_time").loc[pd.Timestamp(t.exit_time)]
        if t.side == "long":
            assert t.exit_price == pytest.approx(max(bar.open, t.target_price)) and bar.high >= t.target_price
        else:
            assert t.exit_price == pytest.approx(min(bar.open, t.target_price)) and bar.low <= t.target_price
        assert t.pnl_usdt > 0


def test_take_profit_lock_blocks_same_direction_reentry():
    r = run_backtest(book(), _cfg(tp_r=1.0, tp_reentry=False))
    tr = r["trades"].sort_values("entry_time")
    for _, t in tr[tr.exit_reason == "止盈"].iterrows():
        nxt = tr[(tr.symbol == t.symbol) & (tr.entry_time > t.exit_time)].head(1)
        if len(nxt) and nxt.iloc[0].side == t.side:
            # 同向再入场之前，信号必须先改变过（锁定解除至少隔一根）
            assert pd.Timestamp(nxt.iloc[0].entry_time) > pd.Timestamp(t.exit_time) + pd.Timedelta(hours=4)


def test_reversal_flip_opens_opposite_on_same_bar():
    # confirm_bars=1 时信号可直接 ±1 翻转（默认 2 根确认时中间会先出现 1 根 0：先平仓，下一根再开反向）
    r = run_backtest(book(n_sym=3), _cfg(confirm_bars=1))
    tr = r["trades"]
    flips = tr[tr.exit_reason == "信号反转"]
    assert len(flips) > 0
    for _, t in flips.iterrows():
        nxt = tr[(tr.symbol == t.symbol) & (tr.entry_time == t.exit_time)]
        # 平旧仓与开反向仓在同一根开盘，且只有一条新腿（不缺腿、不重复）
        assert len(nxt) <= 1
        if len(nxt):
            n = nxt.iloc[0]
            assert n.side != t.side and n.market == ("perp" if t.side == "long" else "spot")
            # 两条腿各自按所在市场收手续费
            assert n.fees_usdt > 0 and t.fees_usdt > 0
    opened_same_bar = sum(len(tr[(tr.symbol == t.symbol) & (tr.entry_time == t.exit_time)]) for _, t in flips.iterrows())
    assert opened_same_bar >= 0.5 * len(flips)


def test_engine_take_profit_formula_matches_backtest():
    p = types.SimpleNamespace(entry_price=100.0, stop_price=96.0, direction=1)
    st = {"tp_r": 2.0}
    assert not engine.take_profit_hit(p, 107.9, st) and engine.take_profit_hit(p, 108.0, st)
    q = types.SimpleNamespace(entry_price=100.0, stop_price=104.0, direction=-1)
    assert not engine.take_profit_hit(q, 92.1, st) and engine.take_profit_hit(q, 92.0, st)
    assert not engine.take_profit_hit(p, 1e9, {"tp_r": 0})


def test_take_profit_validation():
    s = copy.deepcopy(S.DEFAULTS)
    s["strategy"]["tp_r"] = 50
    with pytest.raises(ValueError):
        S.validate(s)
