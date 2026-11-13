import copy

import pytest

from qtw import settings as S


def _cfg(**live):
    c = copy.deepcopy(S.DEFAULTS)
    c["live"].update(live)
    return c


@pytest.mark.parametrize("v,want", [("false", False), ("0", False), ("", False), ("False", False), (0, False),
                                    ("true", True), ("1", True), (True, True), (1, True)])
def test_live_enabled_strict_bool(v, want):
    assert S.validate(_cfg(live_enabled=v))["live"]["live_enabled"] is want


def test_string_false_does_not_arm_live():
    c = S.validate(_cfg(mode="live", live_enabled="false", confirm_phrase=S.LIVE_CONFIRM_PHRASE))
    assert S.live_armed(c) is False


def test_demo_flags_strict_bool():
    c = S.validate(_cfg(okx_demo="true", gate_testnet="0"))
    assert c["live"]["okx_demo"] is True and c["live"]["gate_testnet"] is False


def test_bad_mode_rejected():
    with pytest.raises(ValueError):
        S.validate(_cfg(mode="foo"))
