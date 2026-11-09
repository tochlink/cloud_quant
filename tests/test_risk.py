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


def test_cap_at_entry_marks_gross_when_scaled_below_per_name_cap():
    from qtw.risk import cap_at_entry
    # 8 names each wanted the 20% weight cap (200 U on 1000) but got ~125 U after 1x gross scale
    assert cap_at_entry(entry_notional=124.95, entry_price=74760.6, stop_price=76050.58571428573,
                        entry_equity=1000.0) == "gross"


def test_cap_at_entry_keeps_weight_or_risk_when_filled_at_standalone():
    from qtw.risk import cap_at_entry
    # stop 20% → raw = 50/0.2 = 250 > 200 cap → weight, filled at 200
    assert cap_at_entry(entry_notional=200, entry_price=100, stop_price=80, entry_equity=1000) == "weight"
    # stop 40% → raw = 125 → risk, filled at 125
    assert cap_at_entry(entry_notional=125, entry_price=100, stop_price=60, entry_equity=1000) == "risk"


def test_cap_at_entry_uses_entry_notional_not_later_mark():
    from qtw.risk import cap_at_entry
    # A single 20% weight-capped name stays "weight" even if we only have entry fields
    # (later mark-to-market must not flip the label to gross).
    assert cap_at_entry(entry_notional=200, entry_price=100, stop_price=80, entry_equity=1000) == "weight"
    assert cap_at_entry(entry_notional=0, entry_price=100, stop_price=80, entry_equity=1000) == "none"


def test_equity_near_picks_snapshot_at_or_before_entry():
    from qtw.engine import _equity_near
    led = [
        {"time": "2026-11-09T15:00:00Z", "equity_usdt": 1000.0},
        {"time": "2026-11-09T15:06:00Z", "equity_usdt": 999.6},
        {"time": "2026-11-09T16:00:00Z", "equity_usdt": 1010.0},
    ]
    assert _equity_near(led, "2026-11-09T15:06:00Z", 1000.0) == 999.6
    assert _equity_near(led, "2026-11-09T15:03:00Z", 1000.0) == 1000.0
    assert _equity_near([], "2026-11-09T15:06:00Z", 1000.0) == 1000.0
    assert _equity_near(led, "2026-11-09T14:00:00Z", 1000.0) == 1000.0
