import pytest

from qtw.paper import PaperBook


def test_paper_book_persists_and_accounts(tmp_path):
    b = PaperBook(1000, 4, directory=tmp_path)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last", stop=45000,
           signal_bar="x", reason="t", venue="okx")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark", stop=2200,
           signal_bar="x", reason="t", venue="okx")
    fees = (100 + 100) * 0.0004
    assert b.equity() == pytest.approx(1000 - fees)
    b.mark("BTCUSDT", 55000, "t"); b.mark("ETHUSDT", 1900, "t")
    assert b.equity() == pytest.approx(1000 - fees + 10 + 5)
    b.save()
    b2 = PaperBook(1000, 4, directory=tmp_path)  # 重新加载
    assert set(b2.positions) == {"BTCUSDT", "ETHUSDT"}
    assert b2.equity() == pytest.approx(b.equity())
    pnl = b2.close("ETHUSDT", 1900, "mark", "t", "okx")
    assert pnl == pytest.approx(5 - 0.05 * 1900 * 0.0004)
    assert len(b2.fills()) == 3
