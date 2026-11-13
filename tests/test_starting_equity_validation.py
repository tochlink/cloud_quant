import copy

import pytest

from qtw import settings as S


def _cfg(v):
    c = copy.deepcopy(S.DEFAULTS)
    c["risk"]["starting_equity_usdt"] = v
    return c


@pytest.mark.parametrize("v", [0, -100, 5, 2e9])
def test_starting_equity_out_of_range_rejected(v):
    with pytest.raises(ValueError, match="起始纸面资金"):
        S.validate(_cfg(v))


@pytest.mark.parametrize("v", [10, 1000, "500", 1e6])
def test_starting_equity_in_range_accepted(v):
    assert S.validate(_cfg(v))["risk"]["starting_equity_usdt"] == float(v)
