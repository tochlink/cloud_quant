"""信号起点不能落在慢均线预热结束处：当前信号段早于取数窗口时，prev_run_close 为空，止损锁保持（与回测一致），
不会因为窗口滑动在若干根之后「自动解锁」并同向再入场。"""
import numpy as np
import pandas as pd

from qtw import db, engine, settings as S
from qtw.paper import PaperBook


def _frame(close, start="2026-01-01"):
    t = pd.date_range(start, periods=len(close), freq="4h", tz="UTC")
    c = np.asarray(close, dtype=float)
    return pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4) - pd.Timedelta(milliseconds=1),
                         "open": c, "high": c * 1.001, "low": c * 0.999, "close": c, "volume": 1.0})


def _run(monkeypatch, tmp_path, close):
    cfg = S._merge(S.DEFAULTS, {})
    cfg["symbols"] = ["ETHUSDT"]
    cfg["strategy"].update(btc_regime_ma=0, short_breaker_bars=0)
    b = PaperBook(1000, 4, conn=db.connect(tmp_path / "w.sqlite"))
    seen = {}

    def many(venue, syms, interval, limit, markets=("spot", "perp")):
        seen["limit"] = limit
        f = _frame(close)
        return {m: {"ETHUSDT": f.tail(limit).reset_index(drop=True)} for m in markets}, {}

    monkeypatch.setattr(engine.mcache, "many", many)
    monkeypatch.setattr(engine, "book", lambda *a, **k: b)
    row = engine.compute_signals(cfg, with_quotes=False)["rows"][0]
    return row, seen["limit"], cfg


def test_no_fake_cross_when_segment_predates_window(monkeypatch, tmp_path):
    close = np.linspace(3000, 1500, 1200)  # 整段下跌：空头信号段远早于取数窗口
    row, limit, cfg = _run(monkeypatch, tmp_path, close)
    assert row["signal"] == -1
    assert row["signal_since"] == "" and row["prev_run_close"] == ""
    b = PaperBook(1000, 4, conn=db.connect(tmp_path / "b.sqlite"))
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.01, price=1600, price_kind="mark",
           stop=1700, signal_bar="x", reason="t", venue="okx")
    b.blocks["ETHUSDT"] = -1
    b.close("ETHUSDT", 1700, "mark", "ATR止损", "okx")
    assert engine.block_active(b, "ETHUSDT", row)  # 信号从未变化 → 止损锁不解除


def test_real_cross_inside_window_is_kept(monkeypatch, tmp_path):
    close = np.r_[np.linspace(1500, 3000, 1150), np.linspace(3000, 2000, 50)]  # 窗口内真实死叉
    row, limit, cfg = _run(monkeypatch, tmp_path, close)
    assert row["signal"] == -1
    assert row["signal_since"] and row["prev_run_close"]
    assert pd.Timestamp(row["prev_run_close"]) < pd.Timestamp(row["as_of"])
