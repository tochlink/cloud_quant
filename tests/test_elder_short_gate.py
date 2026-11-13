import math

import numpy as np
import pandas as pd

from qtw import settings as S
from qtw.strategy import elder_bull_power, elder_short_ok, indicators


def _df(closes, spread=1.0):
    n = len(closes)
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + spread,
                         "low": c - spread, "close": c, "volume": 1.0})


def test_elder_short_ok_gate():
    assert elder_short_ok(-9.0, 0, 0.0)  # 关闭
    assert elder_short_ok(float("nan"), 26, 0.0)  # 未形成不拦（与研究口径一致）
    assert elder_short_ok(0.0, 26, 0.0) and elder_short_ok(-0.5, 26, 0.5)
    assert not elder_short_ok(-0.01, 26, 0.0) and not elder_short_ok(-0.51, 26, 0.5)


def test_bull_power_falling_market_negative_and_no_lookahead():
    down = elder_bull_power(_df(list(np.linspace(200, 100, 120)), 0.2), 26)
    up = elder_bull_power(_df(list(np.linspace(100, 200, 120)), 0.2), 26)
    assert math.isnan(down.iloc[45]) and not math.isnan(down.iloc[46])
    assert down.iloc[-1] < -1 and up.iloc[-1] > 1
    d = _df(list(np.sin(np.arange(150) / 5) * 5 + 50))
    full, part = elder_bull_power(d, 26), elder_bull_power(d.iloc[:100], 26)
    assert np.allclose(full.iloc[:100].dropna(), part.dropna())


def test_indicators_elder_column_default_nan():
    d = indicators(_df(list(range(1, 101))), 2, 3, 2, 1)
    assert d["elder_bull"].isna().all()
    d = indicators(_df(list(range(1, 101))), 2, 3, 2, 1, elder_n=26)
    assert d["elder_bull"].notna().sum() == 100 - 46


def test_elder_default_off_and_validation():
    assert S.DEFAULTS["strategy"]["elder_short_gate_n"] == 0
    for k, v in (("elder_short_gate_n", 3), ("elder_short_gate_x", -1), ("elder_short_gate_x", 9)):
        cfg = S._merge(S.DEFAULTS, {})
        cfg["strategy"][k] = v
        try:
            S.validate(cfg)
            assert False
        except ValueError:
            pass
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"].update(elder_short_gate_n=26, elder_short_gate_x=0.5)
    S.validate(cfg)
