import copy

import pytest

from qtw import settings as S


def _cfg(ap):
    c = copy.deepcopy(S.DEFAULTS)
    c["strategy"]["atr_period"] = ap
    return c


@pytest.mark.parametrize("ap", [0, 1, -5, 201, 1000])
def test_atr_period_out_of_range_rejected(ap):
    with pytest.raises(ValueError, match="ATR 周期"):
        S.validate(_cfg(ap))


@pytest.mark.parametrize("ap", [2, 14, 60, 200, "21"])
def test_atr_period_in_range_accepted(ap):
    out = S.validate(_cfg(ap))
    assert out["strategy"]["atr_period"] == int(ap)
