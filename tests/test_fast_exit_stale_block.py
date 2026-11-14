"""旧版「快速离场」平仓留下的锁不再阻止同向再入场（快速离场在模拟盘 / 实盘已停用）；其他离场原因的锁不变。"""
from qtw import db, engine
from qtw.paper import PaperBook


def _book(tmp_path, reason):
    b = PaperBook(1000, 4, conn=db.connect(tmp_path / "b.sqlite"))
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.001, price=70000, price_kind="mark",
           stop=73000, signal_bar="x", reason="t", venue="okx")
    b.blocks["BTCUSDT"] = -1
    b.close("BTCUSDT", 70500, "mark", reason, "okx")
    b.save()
    return b


ROW = {"signal": -1, "prev_run_close": "2020-01-01T00:00:00Z"}  # 空头信号段在平仓前就开始、从未改变


def test_fast_exit_lock_is_ignored(tmp_path):
    b = _book(tmp_path, "快速离场")
    assert b.last_close_reason("BTCUSDT") == "快速离场"
    assert not engine.block_active(b, "BTCUSDT", ROW)
    # 重启后从 SQLite 读回同样不锁
    b2 = PaperBook(1000, 4, conn=db.connect(tmp_path / "b.sqlite"))
    assert b2.blocks.get("BTCUSDT") == -1
    assert not engine.block_active(b2, "BTCUSDT", ROW)


def test_fast_exit_lock_kept_in_research_mode(tmp_path):
    b = _book(tmp_path, "快速离场")
    assert engine.block_active(b, "BTCUSDT", ROW, fast_exit_research=True)


def test_other_exit_locks_unchanged(tmp_path):
    for i, why in enumerate(("ATR止损", "手动平仓", "一键清仓", "紧急停止(Kill Switch)")):
        d = tmp_path / str(i)
        d.mkdir()
        assert engine.block_active(_book(d, why), "BTCUSDT", ROW), why
