"""止损反手（sar_hold_bars，默认关闭）的回测测试：只在 ATR 止损后的下一根开盘反手、不连环反手、无前视。
synth() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import pandas as pd
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from tests.test_backtest import book


def _cfg(h=0, k=1.0, m=2.0):
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=0, sar_hold_bars=h, sar_risk_mult=k, sar_atr_mult=m)
    return c


def test_default_off_and_validation():
    assert S.DEFAULTS["strategy"]["sar_hold_bars"] == 0
    for k, v in (("sar_hold_bars", -1), ("sar_hold_bars", 101), ("sar_risk_mult", 5), ("sar_atr_mult", 0.2)):
        c = S._merge(S.DEFAULTS, {})
        c["strategy"][k] = v
        with pytest.raises(ValueError):
            S.validate(c)
    c = S._merge(S.DEFAULTS, {})
    c["strategy"].update(sar_hold_bars=12, sar_risk_mult=1.0, sar_atr_mult=2.0)
    S.validate(c)


def test_off_has_no_reverse_exits():
    tr = run_backtest(book(3), _cfg(0))["trades"]
    assert not (tr["exit_reason"] == "反手时间").any()


def test_reverse_only_next_bar_after_stop_and_not_chained():
    data = book(3, 800)
    tr = run_backtest(data, _cfg(6))["trades"]
    sar = tr[tr["exit_reason"] == "反手时间"]
    assert len(sar) > 0
    stops = tr[tr["exit_reason"] == "ATR止损"]
    for _, t in sar.iterrows():
        assert t["bars_held"] == 6
        e = pd.Timestamp(t["entry_time"])
        prev = stops[(stops["symbol"] == t["symbol"]) & (stops["side"] != t["side"])
                     & (stops["exit_time"].map(pd.Timestamp) == e - pd.Timedelta(hours=4))]
        assert len(prev) == 1  # 反手仓必须在反向 ATR 止损的下一根开盘开出
        # 不连环反手：触发本反手的止损单本身不能是反手仓（即它不能紧跟在另一笔反向止损之后开出）
        p = prev.iloc[0]
        pe = pd.Timestamp(p["entry_time"])
        chained = stops[(stops["symbol"] == t["symbol"]) & (stops["side"] == t["side"])
                        & (stops["exit_time"].map(pd.Timestamp) == pe - pd.Timedelta(hours=4))]
        assert len(chained) == 0


def test_reverse_no_lookahead():
    data = book(3, 800)
    cut = {m: {s: d.iloc[:700] for s, d in v.items()} for m, v in data.items()}
    a = run_backtest(data, _cfg(6))["trades"]
    b = run_backtest(cut, _cfg(6))["trades"]
    last = pd.Timestamp(cut["spot"]["S0USDT"]["open_time"].iloc[-1])
    ka = a[(a["status"] == "closed") & (a["exit_time"].map(pd.Timestamp) < last)].reset_index(drop=True)
    kb = b[(b["status"] == "closed") & (b["exit_time"].map(pd.Timestamp) < last)].reset_index(drop=True)
    pd.testing.assert_frame_equal(ka[["symbol", "side", "entry_time", "exit_time", "exit_reason"]],
                                  kb[["symbol", "side", "entry_time", "exit_time", "exit_reason"]])
