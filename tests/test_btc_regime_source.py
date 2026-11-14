"""BTC 体制过滤的数据来源：标的里没有 BTCUSDT 时，回测用单独传入的 BTC 现货（btc_spot），与引擎 _btc_regime_state 同口径。"""
import numpy as np
import pandas as pd

from qtw import settings as S
from qtw.backtest import btc_spot_for_regime, run_backtest


def _frame(close, start="2024-01-01"):
    t = pd.date_range(start, periods=len(close), freq="4h", tz="UTC")
    c = np.asarray(close, dtype=float)
    return pd.DataFrame({"open_time": t, "open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                         "volume": 1.0, "close_time": t + pd.Timedelta(hours=4)})


def _cfg(**st):
    c = S._merge(S.DEFAULTS, {"strategy": {"fast_ma": 5, "slow_ma": 15, "trend_ma": 0, "confirm_bars": 1, "btc_regime_ma": 30,
                                           "port_vol_target": 0, "name_vol_target": 0, **st}})
    c["symbols"] = ["ETHUSDT"]
    return c


def _data():
    n = 400
    i = np.arange(n)
    eth = 100 + 10 * np.sin(i / 12.0) + i * 0.02          # 反复多空交叉
    btc = np.where(i < 200, 30000 - i * 20, 26000 + (i - 200) * 30)  # 前半段持续下跌（熊市体制）
    return {"spot": {"ETHUSDT": _frame(eth)}, "perp": {"ETHUSDT": _frame(eth)}}, _frame(btc)


def test_btc_spot_param_matches_btc_in_spot_data():
    data, btc = _data()
    cfg = _cfg()
    with_param = run_backtest(data, cfg, btc_spot=btc)
    in_spot = run_backtest({"spot": {**data["spot"], "BTCUSDT": btc}, "perp": data["perp"]}, cfg)
    assert with_param["summary"]["btc_regime_source"] == "btc_spot"
    assert in_spot["summary"]["btc_regime_source"] == "symbols"
    a, b = with_param["trades"], in_spot["trades"]
    assert len(a) == len(b) and (a["entry_time"].astype(str).tolist() == b["entry_time"].astype(str).tolist())
    assert np.allclose(with_param["equity"]["equity"].to_numpy(), in_spot["equity"]["equity"].to_numpy())


def test_regime_actually_blocks_longs_with_btc_spot():
    data, btc = _data()
    cfg = _cfg()
    off = run_backtest(data, cfg)  # 无 BTC 数据：体制过滤不生效（summary 注明 missing）
    on = run_backtest(data, cfg, btc_spot=btc)
    assert off["summary"]["btc_regime_source"] == "missing"
    lo = lambda r: int((r["trades"]["side"] == "long").sum()) if len(r["trades"]) else 0
    assert lo(on) < lo(off)


def test_btc_spot_ignored_when_btc_in_symbols_and_helper_noop():
    data, btc = _data()
    cfg = _cfg()
    d2 = {"spot": {**data["spot"], "BTCUSDT": btc}, "perp": data["perp"]}
    assert btc_spot_for_regime(cfg, d2, 500) == (None, "")
    cfg0 = _cfg(btc_regime_ma=0)
    assert btc_spot_for_regime(cfg0, data, 500) == (None, "")
    r = run_backtest(data, cfg0, btc_spot=btc)
    assert r["summary"]["btc_regime_source"] == "off"
