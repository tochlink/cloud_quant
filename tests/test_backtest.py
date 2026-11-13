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
    # 入场字段（第一笔成交）不受未来数据影响；已在 cut 前平仓的交易，包括调仓后的数量，也必须完全一致
    cols = ["symbol", "entry_time"]
    # 交易表按平仓顺序追加；篡改后的数据可能让同一批持仓在不同时刻平仓，所以先按入场排序再比
    ent = lambda t: t[t["entry_time"] < cut][cols].sort_values(cols).reset_index(drop=True)
    ta, tb = ent(ra["trades"]), ent(rb["trades"])
    pd.testing.assert_frame_equal(ta, tb)
    cols = ["symbol", "entry_time", "entry_price", "qty", "exit_price", "pnl_usdt"]
    done = lambda t: t[(t["status"] == "closed") & (t["exit_time"] < cut)][cols].sort_values(["entry_time", "symbol"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(done(ra["trades"]), done(rb["trades"]))


def nobal():
    c = cfg()
    return {**c, "strategy": {**c["strategy"], "rebalance_band": 0.0}}


def test_longs_use_spot_and_shorts_use_perp_prices():
    data = book(4)
    c = nobal()
    c = {**c, "risk": {**c["risk"], "trade_mode": "spot_perp"}}  # 旧口径：现货做多 + 永续做空
    r = run_backtest(data, c)  # 关闭调仓：调仓加仓会把入场价变成加权均价
    tr = r["trades"]
    assert (tr.side == "long").any() and (tr.side == "short").any()
    for _, t in tr.iterrows():
        src = data["spot" if t.side == "long" else "perp"][t.symbol].set_index("open_time")
        assert t.market == ("spot" if t.side == "long" else "perp")
        assert t.entry_price == pytest.approx(src.loc[pd.Timestamp(t.entry_time), "open"])


def test_perp_both_mode_trades_longs_on_perp_with_leverage_margin():
    data = book(4)
    c = nobal()
    c = {**c, "risk": {**c["risk"], "trade_mode": "perp_both", "perp_leverage": 10}}
    r = run_backtest(data, c)
    tr = r["trades"]
    assert (tr.side == "long").any() and (tr.side == "short").any()
    for _, t in tr.iterrows():
        src = data["perp"][t.symbol].set_index("open_time")
        assert t.market == "perp"
        assert t.entry_price == pytest.approx(src.loc[pd.Timestamp(t.entry_time), "open"])
        assert 1 <= t.leverage <= 10
        # 止损必须先于强平
        assert (t.init_stop > t.liq_price) if t.side == "long" else (t.init_stop < t.liq_price)
    assert r["summary"]["liquidations"] == 0
    # 杠杆只决定保证金，不放大风险：1 倍与 10 倍收益相同
    c1 = {**c, "risk": {**c["risk"], "perp_leverage": 1}}
    assert run_backtest(data, c1)["summary"]["ending_equity_usdt"] == pytest.approx(r["summary"]["ending_equity_usdt"])


def test_caps_hold():
    r = run_backtest(book(8), nobal())  # 入场名义上限；调仓后的上限见 test_rebalance_backtest_accounting
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


def test_pyramid_off_by_default_and_bounded():
    c = nobal()
    assert c["strategy"]["pyramid_r"] == 0.0
    data = book()
    base = run_backtest(data, c)
    c2 = {**c, "strategy": {**c["strategy"], "pyramid_r": 1.0, "pyramid_frac": 0.5}}
    r = run_backtest(data, c2)
    eq0 = float(c["risk"]["starting_equity_usdt"])
    # 加仓后单币名义不超过权重上限（按入场根权益，留出价格波动余量）
    peak = r["equity"]["equity"].max()
    for _, t in r["trades"].iterrows():
        assert t["notional_usdt"] <= float(c["risk"]["max_weight_per_name"]) * max(peak, eq0) * 1.05
    # 关闭时与原逻辑一致；打开后结果确实改变（有加仓发生）
    c3 = {**c, "strategy": {**c["strategy"], "pyramid_r": 0.0}}
    assert run_backtest(data, c3)["summary"]["total_return"] == base["summary"]["total_return"]
    assert r["summary"]["total_return"] != base["summary"]["total_return"]
    with pytest.raises(ValueError):
        S.validate({**c, "strategy": {**c["strategy"], "pyramid_r": 0.2}})
