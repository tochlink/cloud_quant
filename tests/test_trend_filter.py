import math

import pandas as pd

from qtw import settings as S
from qtw.strategy import indicators, trend_ok


def _df(closes):
    n = len(closes)
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + 1,
                         "low": c - 1, "close": c, "volume": 1.0})


def test_trend_ok_gate():
    assert trend_ok(1, 10, float("nan"), 0) and trend_ok(-1, 10, 20, 0)  # 关闭
    assert trend_ok(0, 10, 20, 100)
    assert trend_ok(1, 11, 10, 100) and not trend_ok(1, 9, 10, 100)
    assert trend_ok(-1, 9, 10, 100) and not trend_ok(-1, 11, 10, 100)
    assert not trend_ok(1, 11, float("nan"), 100)  # 趋势线未形成不开仓


def test_indicators_trend_ma_column_no_lookahead():
    closes = list(range(1, 31))
    d = indicators(_df(closes), 2, 3, 2, 1, trend_ma=5)
    assert math.isnan(d["trend_ma"].iloc[3])
    assert d["trend_ma"].iloc[4] == sum(closes[:5]) / 5
    assert d["trend_ma"].iloc[-1] == sum(closes[-5:]) / 5


def test_trend_default_and_validation():
    assert S.DEFAULTS["strategy"]["trend_ma"] == 100
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"]["trend_ma"] = 5
    try:
        S.validate(cfg)
        assert False
    except ValueError:
        pass
    cfg["strategy"]["trend_ma"] = 0
    assert S.validate(cfg)["strategy"]["trend_ma"] == 0


def test_short_breaker_default_and_validation():
    assert S.DEFAULTS["strategy"]["short_breaker_bars"] == 0
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"]["short_breaker_bars"] = 3
    try:
        S.validate(cfg)
        assert False
    except ValueError:
        pass
    cfg["strategy"]["short_breaker_bars"] = 0
    assert S.validate(cfg)["strategy"]["short_breaker_bars"] == 0


def test_short_breaker_off_and_causal_mask():
    from qtw.backtest import short_breaker
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"]["short_breaker_bars"] = 0
    assert short_breaker({}, cfg)["blocked_now"] is False
