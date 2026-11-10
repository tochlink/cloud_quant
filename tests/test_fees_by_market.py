from qtw import settings as S
from qtw.paper import PaperBook


def test_taker_rate_defaults_and_fallback():
    cfg = S._merge(S.DEFAULTS, {})
    assert S.taker_rate(cfg, "spot") == 10.0 / 10_000
    assert abs(S.taker_rate(cfg, "perp") - 5.1 / 10_000) < 1e-15
    assert S.taker_rate({"fees": {"taker_bps": 4}}, "perp") == 4 / 10_000


def test_validate_rejects_bad_fee():
    cfg = S._merge(S.DEFAULTS, {"fees": {"perp_taker_bps": -1}})
    try:
        S.validate(cfg)
    except ValueError:
        return
    raise AssertionError("negative fee accepted")


def test_paper_book_charges_market_fee(tmp_path):
    from qtw import db
    b = PaperBook(1000, 4, conn=db.connect(tmp_path / "t.sqlite"), fee_by_market={"spot": 0.001, "perp": 0.00051})
    assert b.fee == 0.001 and b.fee_for("perp") == 0.00051 and b.fee_for("x") == 0.0004
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last", stop=45000,
           signal_bar="x", reason="t", venue="okx")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark", stop=2200,
           signal_bar="x", reason="t", venue="okx")
    assert abs(b.realized - (1000 - 100 * 0.001 - 100 * 0.00051)) < 1e-9
