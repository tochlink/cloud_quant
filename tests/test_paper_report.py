"""qtw.paper_report：只读账本报告与 CSV 快照（不联网、不编造价格）。"""
import csv

import pytest

from qtw import db, paper_report, settings as S
from qtw.paper import PaperBook


def test_report_reads_book_and_writes_csv(tmp_path):
    cfg = S.DEFAULTS
    path = tmp_path / "qtw.sqlite"
    b = PaperBook(1000, 4.0, conn=db.connect(path), fee_by_market={m: S.taker_rate(cfg, m) for m in ("spot", "perp")})
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.004, price=50000, price_kind="last", stop=48000,
           signal_bar="x", reason="做多信号", venue="okx")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.1, price=2000, price_kind="mark", stop=2100,
           signal_bar="x", reason="做空信号", venue="okx")
    b.log_order(mode="paper", venue="okx", symbol="BTCUSDT", market="spot", action="open_long", qty=0.004,
                ref_price=50000, status="paper_filled", detail="纸面成交")
    b.close("ETHUSDT", 2100, "mark", "ATR止损", "okx")
    b.mark("BTCUSDT", 51000, "2026-11-11T02:00:00Z", "okx_public_ws")
    b.save()
    rep = paper_report.build(path)
    s = rep["summary"]
    assert s["starting_equity_usdt"] == 1000 and s["open_positions"] == 1 and s["closed_trades"] == 1
    assert s["unrealized_usdt"] == pytest.approx(4.0)
    assert s["equity_usdt"] == pytest.approx(b.equity())
    assert rep["trades"][0]["exit_reason"] == "ATR止损"
    assert rep["positions"][0]["current_price"] == 51000 and rep["positions"][0]["stop_price"] == 48000
    out = tmp_path / "snap.csv"
    paper_report.write_csv(rep, out)
    kinds = [r["record"] for r in csv.DictReader(out.open(encoding="utf-8"))]
    assert kinds == ["summary", "position", "trade", "order"]
    assert "权益" in paper_report.render(rep)


def test_report_shows_dash_without_real_price(tmp_path):
    path = tmp_path / "qtw.sqlite"
    b = PaperBook(1000, 4.0, conn=db.connect(path))
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.004, price=50000, price_kind="last", stop=48000,
           signal_bar="x", reason="t", venue="okx")
    b.positions["BTCUSDT"].mark_price = 0
    b.save()
    rep = paper_report.build(path)
    p = rep["positions"][0]
    assert p["current_price"] is None and p["unrealized_pnl_usdt"] is None
    assert rep["summary"]["unpriced_positions"] == "BTCUSDT"
    assert "—" in paper_report.render(rep)
