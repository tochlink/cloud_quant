"""止损锁解锁与回测一致：错过中间检查时，只要止损后有一根已收盘 K 线信号改变过就解锁。"""
from qtw import db, engine
from qtw.paper import PaperBook


def _book(tmp_path):
    b = PaperBook(1000, 4, conn=db.connect(tmp_path / "b.sqlite"))
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.01, price=3000, price_kind="mark",
           stop=3100, signal_bar="x", reason="t", venue="okx")
    b.blocks["ETHUSDT"] = -1
    b.close("ETHUSDT", 3100, "mark", "ATR止损", "okx")
    return b, b.last_stop_time("ETHUSDT")


def test_block_holds_while_signal_never_changed(tmp_path):
    b, t = _book(tmp_path)
    row = {"signal": -1, "prev_run_close": "2020-01-01T00:00:00Z"}  # 当前空头信号段在止损前就开始
    assert engine.block_active(b, "ETHUSDT", row)


def test_block_clears_after_missed_flip_and_back(tmp_path):
    b, t = _book(tmp_path)
    row = {"signal": -1, "prev_run_close": "2099-01-01T00:00:00Z"}  # 止损后出现过不同信号再回到空头
    assert not engine.block_active(b, "ETHUSDT", row)


def test_block_clears_on_different_signal_and_without_stop_fill(tmp_path):
    b, _ = _book(tmp_path)
    assert not engine.block_active(b, "ETHUSDT", {"signal": 0, "prev_run_close": ""})
    b.blocks["BTCUSDT"] = 1  # 旧版迁移来的锁没有止损成交记录：退回只看最新信号
    assert engine.block_active(b, "BTCUSDT", {"signal": 1, "prev_run_close": "2099-01-01T00:00:00Z"})
