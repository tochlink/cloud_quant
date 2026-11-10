import pandas as pd

from qtw import settings as S
from qtw.strategy import indicators


def _df(closes):
    n = len(closes)
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    c = pd.Series(closes, dtype=float)
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + 1,
                         "low": c - 1, "close": c, "volume": 1.0})


def test_confirm_bars_delays_and_filters_flip():
    closes = [10] * 5 + [20, 5, 20, 20, 20]  # 单根上穿后立刻回头 → 假信号
    raw = indicators(_df(closes), 2, 3, 2, 1)["signal"].tolist()
    conf = indicators(_df(closes), 2, 3, 2, 2)["signal"].tolist()
    for i in range(len(closes)):
        want = raw[i] if i >= 1 and raw[i] == raw[i - 1] else 0
        assert conf[i] == want
    assert conf != raw


def test_confirm_bars_default_and_validation():
    assert S.DEFAULTS["strategy"]["confirm_bars"] == 2
    cfg = S._merge(S.DEFAULTS, {})
    cfg["strategy"]["confirm_bars"] = 9
    try:
        S.validate(cfg)
        assert False
    except Exception:
        pass
