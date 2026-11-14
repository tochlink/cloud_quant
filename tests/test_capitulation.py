import numpy as np
import pandas as pd

from qtw import settings as S
from qtw import strategies as R


def _ind(paths):
    idx = pd.RangeIndex(len(next(iter(paths.values()))))
    d = {s: pd.DataFrame({"close": c, "high": c, "low": c, "open": c}, index=idx) for s, c in paths.items()}
    return {"spot": d, "perp": d}, idx


def test_capitulation_event_hold_and_no_retrigger():
    n, syms = 120, [f"S{i}" for i in range(8)]
    base = np.full(n, 100.0)
    paths = {}
    for k, s in enumerate(syms):
        c = base.copy()
        c[50:] = 85.0 if k < 7 else 101.0  # 7/8 下跌 15%，篮子均值约 −14%
        c[80:] = 70.0 if k < 7 else 101.0  # 持仓期内（50..73）之后再跌，应在 80 重新触发
        paths[s] = c
    ind, idx = _ind(paths)
    p = dict(R.BY_ID["capitulation_1h"]["params"])
    sig = R.sig_capitulation(ind, idx, syms, p)["S0"]
    assert sig[:50].sum() == 0
    assert sig[50:74].all() and sig[74:80].sum() == 0  # 持有 24 根后归零；50..73 期间的后续事件不重复触发
    assert sig[80] == 1


def test_capitulation_breadth_required():
    n, syms = 80, [f"S{i}" for i in range(8)]
    paths = {}
    for k, s in enumerate(syms):
        c = np.full(n, 100.0)
        c[40:] = 60.0 if k < 6 else 110.0  # 只有 6/8 下跌（篮子仍 < −10%），不满足 7/8
        paths[s] = c
    ind, idx = _ind(paths)
    sig = R.sig_capitulation(ind, idx, syms, R.BY_ID["capitulation_1h"]["params"])["S0"]
    assert sig.sum() == 0


def test_capitulation_cfg_overrides():
    spec = R.BY_ID["capitulation_1h"]
    assert spec["no"] == 13 and spec["interval"] == "1h"
    c = R.strategy_cfg(S.DEFAULTS, "capitulation_1h")
    assert c["risk"]["max_weight_per_name"] == 0.0625 and c["strategy"]["atr_stop_mult"] == 50.0
    assert c["strategy"]["btc_regime_ma"] == 0 and c["strategy"]["name_vol_target"] == 0.0
    assert S.DEFAULTS["risk"]["max_weight_per_name"] == 0.2  # 默认不变
    assert R.VERDICTS["capitulation_1h"]["status"] == "观察"
