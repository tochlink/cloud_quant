"""回测数学测试。

注意：synth() 只是**测试专用**的确定性序列，用来验证无前视与记账逻辑；
应用 / 回测 / 引擎 / 行情代码绝不导入它（见 test_no_synthetic_data_in_app_code）。
"""
import pathlib

import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.strategy import combine, indicators


def synth(n=600, seed=0, start="2025-01-01", scale=1.0):
    rng = np.random.default_rng(seed)
    t = pd.date_range(start, periods=n, freq="4h", tz="UTC")
    c = scale * 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)) + np.sin(np.arange(n) / 40) * 0.3)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, n))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, n))
    return pd.DataFrame({"open_time": t, "open": o, "high": h, "low": lo, "close": c, "volume": 1.0,
                         "close_time": t + pd.Timedelta(hours=4)})


def book(n_sym=2, n=600):
    spot = {f"S{i}USDT": synth(n, seed=i) for i in range(n_sym)}
    # 永续用不同价位的独立序列，便于检验做空确实用永续价格
    perp = {f"S{i}USDT": synth(n, seed=i, scale=1.01) for i in range(n_sym)}
    return {"spot": spot, "perp": perp}


def cfg():
    return S.load()


def test_combine_rule():
    s = [1, 1, 1, -1, -1, 0, 0, 0, -1]
    p = [1, 0, -1, -1, 0, -1, 1, 0, 1]
    assert list(combine(s, p)) == [1, 1, 0, -1, 0, -1, 0, 0, 0]


def test_signal_uses_only_past_data():
    df = synth()
    full = indicators(df, 20, 60, 14)
    k = 400
    part = indicators(df.iloc[: k + 1], 20, 60, 14)
    pd.testing.assert_series_equal(full["signal"].iloc[: k + 1], part["signal"], check_names=False)


def test_backtest_no_lookahead():
    """篡改第 k 根之后的现货与永续数据，不得改变第 k 根之前的任何成交或权益。"""
    a = book()
    k = 450
    b = {m: {s: d.copy() for s, d in v.items()} for m, v in a.items()}
    for v in b.values():
        for d in v.values():
            d.loc[k:, ["open", "high", "low", "close"]] *= 3.0
    ra, rb = run_backtest(a, cfg()), run_backtest(b, cfg())
    cut = a["spot"]["S0USDT"]["close_time"].iloc[k - 1].isoformat()
    ea = ra["equity"][ra["equity"]["time"] <= cut]["equity"].to_numpy()
    eb = rb["equity"][rb["equity"]["time"] <= cut]["equity"].to_numpy()
    assert len(ea) > 50
    np.testing.assert_allclose(ea, eb)
    cols = ["symbol", "entry_time", "entry_price", "qty"]
    ta = ra["trades"][ra["trades"]["entry_time"] < cut][cols].reset_index(drop=True)
    tb = rb["trades"][rb["trades"]["entry_time"] < cut][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(ta, tb)


def test_longs_use_spot_and_shorts_use_perp_prices():
    data = book(4)
    r = run_backtest(data, cfg())
    tr = r["trades"]
    assert (tr.side == "long").any() and (tr.side == "short").any()
    for _, t in tr.iterrows():
        src = data["spot" if t.side == "long" else "perp"][t.symbol].set_index("open_time")
        assert t.market == ("spot" if t.side == "long" else "perp")
        assert t.entry_price == pytest.approx(src.loc[pd.Timestamp(t.entry_time), "open"])


def test_caps_hold():
    r = run_backtest(book(8), cfg())
    tr, eq = r["trades"], r["equity"]
    assert (tr["notional_usdt"] <= 0.2 * eq["equity"].max() + 1e-6).all()
    s = r["summary"]
    assert -1 <= s["max_drawdown"] <= 0 and 0 <= s["win_rate"] <= 1
    assert s["short_prices"].startswith("perp")


def test_missing_perp_is_excluded_not_substituted():
    data = book(2)
    del data["perp"]["S1USDT"]
    r = run_backtest(data, cfg())
    assert "S1USDT" in r["summary"]["excluded_symbols"]
    assert set(r["trades"]["symbol"]) <= {"S0USDT"}


def test_no_synthetic_data_in_app_code():
    root = pathlib.Path(__file__).resolve().parent.parent / "qtw"
    for f in root.rglob("*.py"):
        txt = f.read_text(encoding="utf-8")
        assert "synth(" not in txt and "np.random" not in txt and "random." not in txt, f
