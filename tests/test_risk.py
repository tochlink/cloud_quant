import pytest

from qtw import settings as S
from qtw.risk import size


def test_risk_budget_respected_when_not_capped():
    z = size(side="long", equity=1000, price=100, atr=10, max_risk=0.05, max_weight=0.2, atr_mult=2)
    # stop 20% → raw = 50/0.2 = 250 > 200 cap → capped
    assert z.capped_by == "weight" and z.notional == pytest.approx(200)
    z = size(side="long", equity=1000, price=100, atr=20, max_risk=0.05, max_weight=0.2, atr_mult=2)
    # stop 40% → raw = 125 → risk exactly 50
    assert z.capped_by == "risk" and z.notional == pytest.approx(125)
    assert z.risk_usdt == pytest.approx(50)


@pytest.mark.parametrize("atr", [0.01, 0.5, 1, 3, 8, 30])
@pytest.mark.parametrize("side", ["long", "short"])
def test_caps_never_exceeded(atr, side):
    z = size(side=side, equity=1000, price=100, atr=atr, max_risk=0.05, max_weight=0.2, atr_mult=2)
    assert z.weight <= 0.2 + 1e-12
    assert z.risk_usdt <= 50 + 1e-9


def test_stop_direction_and_gross_room():
    lo = size(side="long", equity=1000, price=100, atr=5, atr_mult=2)
    sh = size(side="short", equity=1000, price=100, atr=5, atr_mult=2)
    assert lo.stop_price == pytest.approx(90) and sh.stop_price == pytest.approx(110)
    z = size(side="long", equity=1000, price=100, atr=1, gross_room=30)
    assert z.notional == pytest.approx(30) and z.capped_by == "gross"


def test_flat_and_invalid_inputs():
    assert size(side="flat", equity=1000, price=100, atr=1).notional == 0
    assert size(side="long", equity=1000, price=100, atr=0).notional == 0


def test_settings_reject_looser_risk():
    s = S.load()
    s["risk"]["max_weight_per_name"] = 0.3
    with pytest.raises(ValueError):
        S.validate(s)
    s = S.load()
    s["risk"]["max_risk_per_trade"] = 0.06
    with pytest.raises(ValueError):
        S.validate(s)
    s = S.load()
    s["risk"]["perp_leverage"] = 3
    with pytest.raises(ValueError):
        S.validate(s)


def test_scale_to_room_proportional_and_fee_aware():
    from qtw.risk import scale_to_room
    out = scale_to_room({f"S{i}": 200.0 for i in range(8)}, 1000.0, 0.0004)
    assert len(set(round(v, 9) for v in out.values())) == 1
    assert sum(out.values()) * 1.0004 <= 1000 + 1e-9
    assert scale_to_room({"A": 100.0}, 1000, 0.0004) == {"A": 100.0}
    assert scale_to_room({"A": 100.0}, -5, 0.0004) == {"A": 0.0}
