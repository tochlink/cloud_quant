import math

import numpy as np
import pandas as pd

from qtw import settings as S
from qtw.strategy import chop_index, chop_ok, indicators


def _df(closes, spread=1.0):
    n = len(closes)
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + spread,
                         "low": c - spread, "close": c, "volume": 1.0})


def test_chop_ok_gate():
    assert chop_ok(float("nan"), 0, 50) and chop_ok(90, 0, 50)  # 关闭
    assert not chop_ok(float("nan"), 14, 50)  # 未形成不开仓
    assert chop_ok(50, 14, 50) and chop_ok(30, 14, 50) and not chop_ok(50.1, 14, 50)


def test_chop_trend_low_range_high_and_no_lookahead():
    trend = chop_index(_df(list(range(1, 61)), 0.5), 14)
    zig = chop_index(_df([10, 12] * 30, 0.5), 14)
    assert math.isnan(trend.iloc[12]) and not math.isnan(trend.iloc[13])
    assert trend.iloc[-1] < 40 and zig.iloc[-1] > 70
    d = _df(list(np.sin(np.arange(80) / 3) * 5 + 50))
    full = chop_index(d, 14)
    part = chop_index(d.iloc[:50], 14)
    assert np.allclose(full.iloc[:50].dropna(), part.dropna())


def test_indicators_chop_column():
    d = indicators(_df(list(range(1, 41))), 2, 3, 2, 1)
    assert d["chop"].isna().all()
    d = indicators(_df(list(range(1, 41))), 2, 3, 2, 1, chop_n=10)
    assert d["chop"].notna().sum() == 31


def test_chop_default_off_and_validation():
    assert S.DEFAULTS["strategy"]["chop_n"] == 0
    for k, v in (("chop_n", 3), ("chop_max", 10)):
        cfg = S._merge(S.DEFAULTS, {})
        cfg["strategy"][k] = v
        try:
            S.validate(cfg)
            assert False
        except ValueError:
            pass
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"].update(chop_n=56, chop_max=50)
    S.validate(cfg)
