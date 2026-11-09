import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.strategy import indicators


def synth(n=600, seed=0, start="2025-01-01"):
    rng = np.random.default_rng(seed)
    t = pd.date_range(start, periods=n, freq="4h", tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)) + np.sin(np.arange(n) / 40) * 0.3)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, n))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, n))
    return pd.DataFrame({"open_time": t, "open": o, "high": h, "low": lo, "close": c, "volume": 1.0,
                         "close_time": t + pd.Timedelta(hours=4)})


def cfg():
    return S.load()


def test_signal_uses_only_past_data():
    df = synth()
    full = indicators(df, 20, 60, 14)
    k = 400
    part = indicators(df.iloc[: k + 1], 20, 60, 14)
    pd.testing.assert_series_equal(full["signal"].iloc[: k + 1], part["signal"], check_names=False)


def test_backtest_no_lookahead():
    """篡改第 k 根之后的数据，不得改变第 k 根之前的任何成交或权益。"""
    a = {"AAAUSDT": synth(seed=1), "BBBUSDT": synth(seed=2)}
    k = 450
    b = {s: d.copy() for s, d in a.items()}
    for d in b.values():
        d.loc[k:, ["open", "high", "low", "close"]] *= 3.0  # 未来暴涨
    ra, rb = run_backtest(a, cfg()), run_backtest(b, cfg())
    cut = a["AAAUSDT"]["close_time"].iloc[k - 1].isoformat()
    ea = ra["equity"][ra["equity"]["time"] <= cut]["equity"].to_numpy()
    eb = rb["equity"][rb["equity"]["time"] <= cut]["equity"].to_numpy()
    assert len(ea) > 50
    np.testing.assert_allclose(ea, eb)
    ta = ra["trades"][ra["trades"]["entry_time"] < cut][["symbol", "entry_time", "entry_price", "qty"]]
    tb = rb["trades"][rb["trades"]["entry_time"] < cut][["symbol", "entry_time", "entry_price", "qty"]]
    pd.testing.assert_frame_equal(ta.reset_index(drop=True), tb.reset_index(drop=True))


def test_entries_execute_at_next_open_and_caps_hold():
    data = {f"S{i}USDT": synth(seed=i) for i in range(8)}
    r = run_backtest(data, cfg())
    tr = r["trades"]
    assert len(tr) > 0
    d0 = data["S0USDT"].set_index("open_time")
    for _, t in tr[tr.symbol == "S0USDT"].iterrows():
        assert t.entry_price == pytest.approx(d0.loc[pd.Timestamp(t.entry_time), "open"])
    eq = r["equity"]
    assert (eq["gross_exposure"] <= eq["equity"] * 1.0 * 1.25).all()  # 入场按开盘价封顶，收盘波动可略超
    s = r["summary"]
    assert -1 <= s["max_drawdown"] <= 0
    assert 0 <= s["win_rate"] <= 1
    # 每笔入场名义 ≤ 20% 当时权益（用起始资金的上界检验）
    assert (tr["notional_usdt"] <= 0.2 * eq["equity"].max() + 1e-6).all()
