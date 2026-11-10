"""空头熔断的影子账本与账户仓位上限无关（固定标准仓位口径）。"""
import copy
import math

import pandas as pd

from qtw import backtest as B
from qtw import settings as S


def _df(closes):
    n = len(closes)
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c * 1.01,
                         "low": c * 0.99, "close": c, "volume": 1.0})


def _data():
    out = {"spot": {}, "perp": {}}
    for k, (amp, per) in enumerate(((20, 37), (15, 53), (25, 29))):
        closes = [100 + amp * math.sin(i / per * 2 * math.pi) - i * 0.02 for i in range(700)]
        out["spot"][f"S{k}USDT"] = _df(closes)
        out["perp"][f"S{k}USDT"] = _df([x * 1.0005 for x in closes])
    return out


def test_shadow_book_ignores_account_sizing():
    data = _data()
    base = S._merge(S.DEFAULTS, {"symbols": list(data["spot"])})
    masks = []
    for w, r, eq in ((0.20, 0.05, 1000.0), (0.14, 0.035, 1000.0), (0.30, 0.08, 5000.0)):
        c = copy.deepcopy(base)
        c["risk"].update(max_weight_per_name=w, max_risk_per_trade=r, starting_equity_usdt=eq)
        res = B.short_breaker(data, c)
        assert res["bars"] == c["strategy"]["short_breaker_bars"]
        masks.append(res["mask"])
    assert masks[0] == masks[1] == masks[2]


def test_shadow_sizing_matches_default_risk():
    for k, v in B.SHADOW_SIZING.items():
        assert S.DEFAULTS["risk"][k] == v
