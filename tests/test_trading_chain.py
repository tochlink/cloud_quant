"""手动平仓 / 停止(恢复) / 一键清仓：纸面默认、实盘闸门关闭、市价按分市场 taker 计费。"""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from qtw import db, engine, settings as S
from qtw.app import app
from qtw.market.base import Quote
from qtw.paper import PaperBook


def _quote(symbol, market, price, venue="okx"):
    return Quote(
        venue=venue, symbol=symbol, market=market, price=price,
        kind="mark" if market == "perp" else "last",
        ts=datetime.now(timezone.utc), data_source=f"{venue}_public_rest",
        source_host="www.okx.com",
    )


def _cfg():
    return S._merge(S.DEFAULTS, {
        "venue": "okx",
        "live": {"mode": "paper", "live_enabled": False, "confirm_phrase": "", "okx_demo": True, "gate_testnet": True},
    })


def _book(tmp_path, monkeypatch):
    cfg = _cfg()
    b = PaperBook(
        1000, cfg["fees"].get("taker_bps", 4.0),
        conn=db.connect(tmp_path / "chain.sqlite"),
        fee_by_market={m: S.taker_rate(cfg, m) for m in ("spot", "perp")},
    )
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "export_paper_csv", lambda cfg: None)
    return cfg, b


def test_defaults_keep_live_off():
    cfg = S._merge(S.DEFAULTS, {})
    assert cfg["live"]["mode"] == "paper"
    assert cfg["live"]["live_enabled"] is False
    assert not S.live_armed(cfg)


def test_manual_close_charges_spot_and_perp_taker(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    assert abs(S.taker_rate(cfg, "spot") - 0.001) < 1e-15
    assert abs(S.taker_rate(cfg, "perp") - 0.00051) < 1e-15
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark",
           stop=2200, signal_bar="x", reason="t", venue="okx")
    prices = {("BTCUSDT", "spot"): 51000, ("ETHUSDT", "perp"): 1900}

    def fake_quote(venue, sym, market):
        px = prices[(sym, market)]
        q = _quote(sym, market, px)
        return px, q.kind, q

    routed = []
    monkeypatch.setattr(engine, "_quote", fake_quote)
    monkeypatch.setattr(engine, "_route", lambda *a, **k: routed.append(a) or "paper_filled")

    out = engine.close_position("BTCUSDT", cfg)
    assert out["ok"] and out["route_status"] == "paper_filled" and out["live_armed"] is False
    assert out["fee_bps"] == pytest.approx(10.0)
    fill = [f for f in b.fills() if f["symbol"] == "BTCUSDT" and f["action"] == "close"][0]
    assert fill["fee_usdt"] == pytest.approx(0.002 * 51000 * 0.001)
    assert fill["reason"] == "手动平仓"
    assert "BTCUSDT" not in b.positions

    out = engine.close_position("ETHUSDT", cfg)
    assert out["ok"] and out["fee_bps"] == pytest.approx(5.1)
    fill = [f for f in b.fills() if f["symbol"] == "ETHUSDT" and f["action"] == "close"][0]
    assert fill["fee_usdt"] == pytest.approx(0.05 * 1900 * 0.00051)
    assert routed[0][3] == "close_long" and routed[1][3] == "close_short"


def test_close_missing_and_no_invented_price(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    assert engine.close_position("NOSYM", cfg)["ok"] is False
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    # wipe last official mark so a failed quote cannot be substituted
    b.positions["BTCUSDT"].mark_price = 0
    b.positions["BTCUSDT"].mark_time = ""
    from qtw.market import MarketDataError
    monkeypatch.setattr(engine, "_quote", lambda *a, **k: (_ for _ in ()).throw(MarketDataError("down")))
    out = engine.close_position("BTCUSDT", cfg)
    assert out["ok"] is False and "无官方报价" in out["error"]
    assert "BTCUSDT" in b.positions


def test_close_falls_back_to_last_real_mark(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    b.mark("BTCUSDT", 50500, "2026-11-10T15:00:00Z", "okx_public_rest")
    from qtw.market import MarketDataError
    monkeypatch.setattr(engine, "_quote", lambda *a, **k: (_ for _ in ()).throw(MarketDataError("down")))
    out = engine.close_position("BTCUSDT", cfg)
    assert out["ok"] and out["price"] == pytest.approx(50500)
    assert out["price_kind"].startswith("last_real_mark@")


def test_flatten_all_closes_every_position(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark",
           stop=2200, signal_bar="x", reason="t", venue="okx")
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (51000 if s == "BTCUSDT" else 1900, "mark" if m == "perp" else "last", _quote(s, m, 51000 if s == "BTCUSDT" else 1900)))
    trader = []
    monkeypatch.setattr(engine, "_trader", lambda cfg: trader.append("called") or (_ for _ in ()).throw(AssertionError("no live")))
    out = engine.flatten_all(cfg)
    assert out["ok"] and len(out["closed"]) == 2 and not b.positions
    assert out["live_armed"] is False and not trader
    reasons = {f["reason"] for f in b.fills() if f["action"] == "close"}
    assert reasons == {"一键清仓"}
    # worker / live switches untouched
    assert cfg["live"]["mode"] == "paper" and cfg["live"]["live_enabled"] is False


def test_halt_skips_signal_exit_and_entry_atr_still_works(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    assert engine.set_halt("BTCUSDT", True, cfg)["halted"] is True
    b2 = PaperBook(1000, 4, conn=b.conn, fee_by_market={m: S.taker_rate(cfg, m) for m in ("spot", "perp")})
    assert "BTCUSDT" in b2.halts

    def signals(cfg, with_quotes=False):
        return {"rows": [{"symbol": "BTCUSDT", "side": "flat", "signal": 0, "error": None,
                          "market": "spot", "signal_market": "spot", "trend_ok": True, "state": "",
                          "as_of": "t", "atr": 100, "advice": "空仓"}], "errors": {}}

    monkeypatch.setattr(engine, "compute_signals", signals)
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (50000, "last", _quote(s, m, 50000)))
    monkeypatch.setattr(engine, "_route", lambda *a, **k: "paper_filled")
    engine.run_cycle(cfg)
    assert "BTCUSDT" in b.positions  # 信号转空仓被停止挡住

    # 入场也被挡住（halt 在平仓后仍保留）
    b.close("BTCUSDT", 50000, "last", "test", "okx")
    def long_sig(cfg, with_quotes=False):
        return {"rows": [{"symbol": "BTCUSDT", "side": "long", "signal": 1, "error": None,
                          "market": "spot", "signal_market": "spot", "trend_ok": True, "state": "",
                          "as_of": "t", "atr": 1000, "advice": "做多"}], "errors": {}}
    cfg = S._merge(cfg, {"symbols": ["BTCUSDT"]})
    monkeypatch.setattr(engine, "compute_signals", long_sig)
    engine.run_cycle(cfg)
    assert "BTCUSDT" not in b.positions

    engine.set_halt("ETHUSDT", False, cfg)  # no-op
    engine.set_halt("BTCUSDT", False, cfg)
    engine.run_cycle(cfg)
    assert "BTCUSDT" in b.positions

    # ATR 止损在停止期间仍然生效
    engine.set_halt("BTCUSDT", True, cfg)
    b.positions["BTCUSDT"].stop_price = 51000
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (40000, "last", _quote(s, m, 40000)))
    def hold_sig(cfg, with_quotes=False):
        return {"rows": [{"symbol": "BTCUSDT", "side": "long", "signal": 1, "error": None,
                          "market": "spot", "signal_market": "spot", "trend_ok": True, "state": "",
                          "as_of": "t", "atr": 100, "advice": "做多"}], "errors": {}}
    monkeypatch.setattr(engine, "compute_signals", hold_sig)
    ev = engine.run_cycle(cfg)
    assert "BTCUSDT" not in b.positions
    assert any("ATR止损" in x for x in ev["events"])


def test_route_stays_paper_when_not_armed(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (51000, "last", _quote(s, m, 51000)))
    called = []
    monkeypatch.setattr(engine, "_trader", lambda cfg: called.append("trader"))
    out = engine.close_position("BTCUSDT", cfg)
    assert out["route_status"] == "paper_filled" and not called
    assert b.orders()[-1]["status"] == "paper_filled" and b.orders()[-1]["mode"] == "paper"


def test_route_blocked_when_live_flags_set_but_gates_closed(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    # live_armed requires mode+enabled+phrase, but guard still needs env + keys
    cfg = S._merge(cfg, {"live": {"mode": "live", "live_enabled": True, "confirm_phrase": S.LIVE_CONFIRM_PHRASE}})
    assert S.live_armed(cfg) is True
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (51000, "last", _quote(s, m, 51000)))
    called = []
    monkeypatch.setattr(engine, "_trader", lambda cfg: called.append("trader"))
    out = engine.close_position("BTCUSDT", cfg)
    assert out["ok"] is True  # paper book still closes
    assert out["route_status"] == "blocked" and not called
    assert b.orders()[-1]["status"] == "blocked"


def test_api_close_halt_flatten(tmp_path, monkeypatch):
    # Isolate from other tests that swap engine._BOOK; use the app data dir.
    monkeypatch.setattr(engine, "_BOOK", None)
    cfg = S.load()
    b = engine.book(cfg)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.002, price=50000, price_kind="last",
           stop=45000, signal_bar="x", reason="t", venue="okx")
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=0.05, price=2000, price_kind="mark",
           stop=2200, signal_bar="x", reason="t", venue="okx")
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (51000 if s == "BTCUSDT" else 1900, "last" if m == "spot" else "mark", _quote(s, m, 51000 if s == "BTCUSDT" else 1900)))
    monkeypatch.setattr(engine, "export_paper_csv", lambda cfg: None)
    client = TestClient(app)
    st = client.get("/api/status").json()
    assert st["mode"] == "paper" and st["settings"]["live"]["live_enabled"] is False
    r = client.post("/api/positions/BTCUSDT/halt")
    assert r.status_code == 200 and r.json()["halted"] is True
    d = client.get("/api/positions").json()
    row = next(p for p in d["positions"] if p["symbol"] == "BTCUSDT")
    assert row["halted"] is True
    r = client.post("/api/positions/BTCUSDT/resume")
    assert r.json()["halted"] is False
    r = client.post("/api/positions/NOSYM/close")
    assert r.status_code == 404
    r = client.post("/api/positions/BTCUSDT/close")
    assert r.status_code == 200 and r.json()["ok"] and r.json()["route_status"] == "paper_filled"
    r = client.post("/api/paper/flatten")
    assert r.status_code == 200 and r.json()["ok"]
    assert r.json()["live_armed"] is False
    assert client.get("/api/positions").json()["positions"] == []


def test_listed_symbols_unions_positions(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="ADAUSDT", market="perp", side="short", qty=10, price=0.18, price_kind="mark",
           stop=0.19, signal_bar="x", reason="t", venue="okx")
    cfg = S._merge(cfg, {"symbols": ["BTCUSDT", "ETHUSDT"]})
    assert engine.listed_symbols(cfg, b) == ["BTCUSDT", "ETHUSDT", "ADAUSDT"]


def test_compute_signals_keeps_held_outside_universe(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="ADAUSDT", market="perp", side="short", qty=10, price=0.18, price_kind="mark",
           stop=0.19, signal_bar="x", reason="t", venue="okx")
    b.mark("ADAUSDT", 0.17, "2026-11-10T15:00:00Z", "okx_public_rest")
    cfg = S._merge(cfg, {"symbols": ["BTCUSDT"]})
    monkeypatch.setattr(engine.mcache, "many", lambda *a, **k: ({}, {}))
    monkeypatch.setattr(engine, "_short_breaker_state", lambda *a, **k: {"blocked_now": False, "trailing_pnl": 0, "bars": 0, "error": ""})
    out = engine.compute_signals(cfg, with_quotes=False)
    by = {r["symbol"]: r for r in out["rows"]}
    assert "ADAUSDT" in by
    r = by["ADAUSDT"]
    assert r["in_universe"] is False
    assert r["stop_source"] == "position"
    assert r["stop_price"] == pytest.approx(0.19)
    assert r["position_entry"] == pytest.approx(0.18)
    assert r["state"] == "held_outside"
    assert r["side"] == "short"


def test_run_cycle_atr_exits_orphan_without_signal_row(tmp_path, monkeypatch):
    cfg, b = _book(tmp_path, monkeypatch)
    b.open(symbol="ADAUSDT", market="perp", side="short", qty=10, price=0.18, price_kind="mark",
           stop=0.19, signal_bar="x", reason="t", venue="okx")
    cfg = S._merge(cfg, {"symbols": ["BTCUSDT"]})
    monkeypatch.setattr(engine, "compute_signals", lambda cfg, with_quotes=False: {"rows": [], "errors": {}})
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (0.20, "mark", _quote(s, m, 0.20)))
    monkeypatch.setattr(engine, "_route", lambda *a, **k: "paper_filled")
    ev = engine.run_cycle(cfg)
    assert "ADAUSDT" not in b.positions
    assert any("ATR止损" in x for x in ev["events"])
