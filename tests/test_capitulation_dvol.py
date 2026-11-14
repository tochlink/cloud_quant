import numpy as np
import pandas as pd

from qtw import dvol
from qtw import settings as S
from qtw import strategies as R


def _ind(paths):
    idx = pd.RangeIndex(len(next(iter(paths.values()))))
    d = {s: pd.DataFrame({"close": c, "high": c, "low": c, "open": c}, index=idx) for s, c in paths.items()}
    return {"spot": d, "perp": d}, idx


def _p(**kw):
    p = dict(R.BY_ID["capitulation_dvol_1h"]["params"])
    p.update(kw)
    return p


def test_dvol_spike_triggers_48h_hold_without_price_event():
    n, syms = 400, [f"S{i}" for i in range(8)]
    ind, idx = _ind({s: np.full(n, 100.0) for s in syms})
    dv = 60 + 0.5 * np.sin(np.arange(n))  # 有界噪声，z 不会到 3
    dv[250] = 90.0  # 168h z 远大于 3
    sig = R.sig_capitulation_dvol(ind, idx, syms, _p(_dvol_values=dv))["S0"]
    assert sig[:250].sum() == 0
    assert sig[250:298].all() and sig[298:].sum() == 0  # 持有 48 根，不重复触发


def test_capitulation_event_still_triggers_without_dvol():
    n, syms = 120, [f"S{i}" for i in range(8)]
    paths = {}
    for k, s in enumerate(syms):
        c = np.full(n, 100.0)
        c[50:] = 85.0 if k < 7 else 101.0
        paths[s] = c
    ind, idx = _ind(paths)  # RangeIndex：取不到 DVOL，只剩投降规则
    sig = R.sig_capitulation_dvol(ind, idx, syms, _p())["S0"]
    assert sig[:50].sum() == 0 and sig[50:98].all() and sig[98:].sum() == 0


def test_no_dvol_data_means_no_dvol_trigger():
    n, syms = 300, [f"S{i}" for i in range(8)]
    ind, idx = _ind({s: np.full(n, 100.0) for s in syms})
    sig = R.sig_capitulation_dvol(ind, idx, syms, _p(_dvol_values=np.full(n, np.nan)))["S0"]
    assert sig.sum() == 0


def test_zscore_alignment_uses_open_time_and_gaps_stay_nan():
    s = pd.Series({0: 1.0, 3_600_000: 2.0})
    z = dvol.zscore_on(np.array([0, 3_600_000, 2 * 3_600_000 * 10]), s, window=2)
    assert np.isnan(z[0]) and np.isfinite(z[1]) and np.isnan(z[2])
    assert dvol.idx_to_ms(pd.RangeIndex(3)) is None
    i = pd.date_range("2026-11-01", periods=2, freq="h", tz="UTC")
    assert list(dvol.idx_to_ms(i)) == [1793491200000, 1793494800000]


def test_cfg_overrides_and_default_unchanged():
    spec = R.BY_ID["capitulation_dvol_1h"]
    assert spec["no"] == 14 and spec["interval"] == "1h" and spec["params"]["hold"] == 48
    c = R.strategy_cfg(S.DEFAULTS, "capitulation_dvol_1h")
    assert c["risk"]["max_weight_per_name"] == 0.0625 and c["strategy"]["atr_stop_mult"] == 50.0
    assert S.DEFAULTS["risk"]["max_weight_per_name"] == 0.2
    assert R.VERDICTS["capitulation_dvol_1h"]["status"] == "观察"
