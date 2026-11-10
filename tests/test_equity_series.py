"""Hero equity hover series: real ledger points only, events attached by time."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from qtw import db, engine, equity_series, settings as S
from qtw.app import app
from qtw.paper import PaperBook
from qtw.signal_log import record


def _cfg():
    return S._merge(S.DEFAULTS, {
        "venue": "okx",
        "live": {"mode": "paper", "live_enabled": False, "confirm_phrase": "", "okx_demo": True, "gate_testnet": True},
    })


def _book(tmp_path, monkeypatch):
    cfg = _cfg()
    b = PaperBook(
        1000, cfg["fees"].get("taker_bps", 4.0),
        conn=db.connect(tmp_path / "equity.sqlite"),
        fee_by_market={m: S.taker_rate(cfg, m) for m in ("spot", "perp")},
    )
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "export_paper_csv", lambda cfg: None)
    return cfg, b


def _kinds(series):
    return [e["kind"] for p in series["points"] for e in p["events"]]


def test_empty_book_has_no_invented_curve(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    series = equity_series.for_book(b)
    # No ledger rows: at most the current official book.equity() point, never a mock history.
    assert series["starting_equity"] == 1000
    assert abs(series["current_equity"] - 1000) < 1e-9
    assert len(series["points"]) <= 1
    if series["points"]:
        assert abs(series["points"][0]["equity"] - b.equity()) < 1e-9
        assert series["points"][0]["events"] == []
    # Equity values are exactly the official book value (or empty).
    led = b.ledger()
    assert len(led) == 0


def test_events_attach_to_real_ledger_points(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.snapshot("start")
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.01, price=100_000,
           price_kind="mark", stop=102_000, signal_bar="", reason="做空信号",
           venue="okx", data_source="okx_public_rest", price_time="2026-11-10T00:00:00+00:00")
    b.snapshot("after open")
    b.resize(symbol="BTCUSDT", new_qty=0.015, price=99_500, price_kind="mark",
             reason="调仓（目标 1.5%）", venue="okx", data_source="okx_public_rest",
             price_time="2026-11-10T00:01:00+00:00")
    b.snapshot("after resize")
    b.close(symbol="BTCUSDT", price=98_000, price_kind="mark", reason="止盈",
            venue="okx", data_source="okx_public_rest", price_time="2026-11-10T00:02:00+00:00")
    b.snapshot("after close")

    led = b.ledger()
    series = equity_series.for_book(b)
    # points come only from ledger (+ optional current official equity)
    assert len(series["points"]) in (len(led), len(led) + 1)
    led_eq = [float(r["equity_usdt"]) for r in led]
    for i, eq in enumerate(led_eq):
        assert abs(series["points"][i]["equity"] - eq) < 1e-9
        assert series["points"][i]["time"] == led[i]["time"]
    if len(series["points"]) == len(led) + 1:
        assert abs(series["points"][-1]["equity"] - b.equity()) < 1e-9

    kinds = _kinds(series)
    assert kinds.count("开仓") == 1
    assert kinds.count("调仓") == 1
    assert kinds.count("止盈") == 1
    assert "平仓" not in kinds  # 止盈 is a close, classified specifically

    # Each event is attached to a point whose time is >= the fill time (causal).
    fills = {f["reason"]: f for f in b.fills()}
    by_kind = {e["kind"]: (e, p) for p in series["points"] for e in p["events"]}
    for kind, reason in (("开仓", "做空信号"), ("调仓", "调仓（目标 1.5%）"), ("止盈", "止盈")):
        ev, pt = by_kind[kind]
        assert ev["time"] == fills[reason]["time"]
        assert ev["symbol"] == "BTCUSDT"
        assert ev["price"] is not None
        assert ev["time"] <= pt["time"]

    short_open = by_kind["开仓"][0]
    assert short_open["side"] == "short"
    assert short_open["side_cn"] == "空"
    assert by_kind["止盈"][0]["realized_pnl"] is not None


def test_stop_and_manual_close_kinds(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.snapshot("s0")
    b.open(symbol="ETHUSDT", market="perp", side="long", qty=1, price=3000,
           price_kind="mark", stop=2940, signal_bar="", reason="做多信号",
           venue="okx", data_source="okx_public_rest")
    b.close(symbol="ETHUSDT", price=2940, price_kind="mark", reason="ATR止损",
            venue="okx", data_source="okx_public_rest")
    b.snapshot("s1")
    b.open(symbol="ETHUSDT", market="perp", side="long", qty=1, price=3000,
           price_kind="mark", stop=2940, signal_bar="", reason="做多信号",
           venue="okx", data_source="okx_public_rest")
    b.close(symbol="ETHUSDT", price=3010, price_kind="mark", reason="手动平仓",
            venue="okx", data_source="okx_public_rest")
    b.snapshot("s2")
    kinds = _kinds(equity_series.for_book(b))
    assert kinds.count("开仓") == 2
    assert "止损" in kinds
    assert "手动平仓" in kinds


def test_signal_log_resize_deduped_against_fill(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.snapshot("s0")
    b.open(symbol="SOLUSDT", market="perp", side="short", qty=1, price=200,
           price_kind="mark", stop=210, signal_bar="", reason="做空信号",
           venue="okx", data_source="okx_public_rest")
    b.resize(symbol="SOLUSDT", new_qty=1.2, price=198, price_kind="mark",
             reason="调仓（目标 2%）", venue="okx", data_source="okx_public_rest")
    b.snapshot("s1")
    # A signal_log 调仓 row at the same second as the fill must not double-count.
    fill = [f for f in b.fills() if f["action"] == "add"][0]
    rows = [{"symbol": "SOLUSDT", "signal": -1, "as_of": fill["time"], "signal_since": fill["time"], "prev_signal": -1}]
    record(rows, {"SOLUSDT": "调仓（目标 2%）"}, "okx", conn=b.conn)
    series = equity_series.for_book(b)
    assert _kinds(series).count("调仓") == 1


def test_api_paper_equity_uses_book(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.snapshot("s0")
    b.open(symbol="BTCUSDT", market="perp", side="short", qty=0.01, price=80_000,
           price_kind="mark", stop=82_000, signal_bar="", reason="做空信号",
           venue="okx", data_source="okx_public_rest")
    b.snapshot("s1")
    client = TestClient(app)
    r = client.get("/api/paper/equity")
    assert r.status_code == 200
    body = r.json()
    assert body["starting_equity"] == 1000
    assert len(body["points"]) >= 2
    assert body["event_count"] >= 1
    assert any(e["kind"] == "开仓" and e["symbol"] == "BTCUSDT" for p in body["points"] for e in p["events"])
    # Every point equity is a real ledger or current official equity.
    led_eq = {float(x["equity_usdt"]) for x in b.ledger()}
    led_eq.add(float(b.equity()))
    for p in body["points"]:
        assert any(abs(p["equity"] - e) < 1e-9 for e in led_eq)


def test_classify_reasons():
    assert equity_series.classify("open", "做空信号") == "开仓"
    assert equity_series.classify("add", "调仓（目标 3%）") == "调仓"
    assert equity_series.classify("reduce", "调仓（目标 1%）") == "调仓"
    assert equity_series.classify("close", "ATR止损") == "止损"
    assert equity_series.classify("close", "止盈") == "止盈"
    assert equity_series.classify("close", "手动平仓") == "手动平仓"
    assert equity_series.classify("close", "一键清仓") == "一键清仓"
    assert equity_series.classify("close", "信号反转") == "平仓"
    assert equity_series.classify("halt", "停止") is None
