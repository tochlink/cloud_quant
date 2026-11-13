"""事件驱动（tick / K 线收盘）、短线层闸门、开始交易选币、反手标签。"""
import copy
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from qtw import db, engine, realtime, settings as S, stream, worker
from qtw.market.base import Quote
from qtw.paper import PaperBook, label_actions


def _q(sym, mkt, px):
    return Quote(venue="OKX", symbol=sym, market=mkt, price=px, kind="mark" if mkt == "perp" else "last",
                 ts=datetime.now(timezone.utc), data_source="okx_public_ws", source_host="ws.okx.com", recv_at=time.time())


def _cfg():
    c = copy.deepcopy(S.DEFAULTS); c["venue"] = "okx"
    return c


def test_bar_close_events_derive_from_1m():
    ms = int(datetime(2026, 11, 13, 4, 0, tzinfo=timezone.utc).timestamp() * 1000)
    evs = stream.bar_close_events("okx", "spot", "BTCUSDT", "1m", ms - 60_000, 1.0)
    assert [e["tf"] for e in evs] == ["1m", "5m", "10m", "1h"]
    assert all(e["close_ms"] == ms for e in evs)
    day = int(datetime(2026, 11, 14, tzinfo=timezone.utc).timestamp() * 1000)
    assert "1d" in [e["tf"] for e in stream.bar_close_events("okx", "spot", "BTCUSDT", "1m", day - 60_000, 1.0)]
    assert [e["tf"] for e in stream.bar_close_events("okx", "spot", "BTCUSDT", "1m", ms - 120_000, 1.0)] == ["1m"]
    four = stream.bar_close_events("okx", "perp", "BTCUSDT", "4h", ms - 14_400_000, 1.0)
    assert [e["tf"] for e in four] == ["4h"] and four[0]["close_ms"] == ms


def test_fallback_wait_is_next_bar_close_plus_grace():
    t = datetime(2026, 11, 13, 4, 0, 2, tzinfo=timezone.utc).timestamp()
    w = worker.fallback_wait("4h", now=t)
    assert w == pytest.approx(4 * 3600 - 2 + worker.BAR_FALLBACK_SEC)


def test_tick_triggers_stop_and_records_latency(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "rt.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="ETHUSDT", market="spot", side="long", qty=0.1, price=3000, price_kind="last", stop=2900,
           signal_bar="x", reason="t", venue="okx", data_source="okx_public_ws", price_time="2026-11-13T00:00:00Z")
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "_route", lambda *a, **k: None)
    monkeypatch.setattr(engine, "export_paper_csv", lambda *a, **k: None)
    monkeypatch.setitem(realtime._CFG, "cfg", _cfg()); monkeypatch.setitem(realtime._CFG, "at", time.time() + 999)
    realtime.on_tick(_q("ETHUSDT", "spot", 2950))
    assert "ETHUSDT" in b.positions  # 未触及
    realtime.on_tick(_q("ETHUSDT", "perp", 2800))
    assert "ETHUSDT" in b.positions  # 不同市场的报价不计入现货多单
    realtime.on_tick(_q("ETHUSDT", "spot", 2890))
    assert "ETHUSDT" not in b.positions
    st = realtime.status()
    assert st["mode"] == "event_driven" and st["tick"]["n"] >= 2 and st["tick"]["p50_ms"] is not None
    assert st["tick_exits"] and "ATR止损" in st["tick_exits"][-1]["events"][0]


def test_bar_close_kicks_core_only(monkeypatch):
    seen = []
    monkeypatch.setattr(worker, "kick_bar", lambda ev: seen.append(ev["tf"]) or True)
    monkeypatch.setitem(realtime._CFG, "cfg", _cfg()); monkeypatch.setitem(realtime._CFG, "at", time.time() + 999)
    for tf in ("1m", "5m", "10m", "1h", "4h", "1d"):
        realtime.on_bar_close({"venue": "okx", "market": "spot", "symbol": "BTCUSDT", "tf": tf, "close_ms": 0, "recv_at": time.time()})
    assert seen == ["4h", "1d"]
    last = realtime.status()["bar"]["last_by_tf"]
    assert "短线层关闭" in last["5m"]["decision"] and "长线" in last["4h"]["decision"]


def test_kick_bar_dedupes_same_close(monkeypatch):
    class T:
        def is_alive(self):
            return True
    monkeypatch.setattr(worker, "_thread", T()); worker._stop.clear(); worker._kick.clear()
    worker._state.pop("_trig_key", None)
    assert worker.kick_bar({"tf": "4h", "close_ms": 123, "symbol": "BTCUSDT"})
    worker._kick.clear()
    assert worker.kick_bar({"tf": "1d", "close_ms": 123, "symbol": "ETHUSDT"})
    assert not worker._kick.is_set()  # 同一收盘时刻只唤醒一次
    worker._state.pop("pending_trigger", None); worker._state.pop("_trig_key", None)


def test_short_layer_cannot_be_enabled():
    c = _cfg(); c["short_layer"]["enabled"] = True
    with pytest.raises(ValueError, match="短线层未通过验证"):
        S.validate(c)
    assert S.SHORT_LAYER_VALIDATED is False and S.DEFAULTS["short_layer"]["enabled"] is False


def test_short_layer_api_reports_failed_validation():
    from qtw.app import app
    d = TestClient(app).get("/api/short_layer").json()
    assert d["validated"] is False and d["enabled"] is False and d["research"]["passed"] is False
    unseen = [r for r in d["research"]["rows"] if r["stage"].startswith("test_") and not r["stress"]]
    assert unseen and all(r["expectancy_u"] < 0 for r in unseen)
    assert {"win_rate", "payoff", "profit_factor", "expectancy_u", "fee_drag_pct"} <= set(unseen[0])


def test_start_with_coin_selection_and_flatten(monkeypatch):
    from qtw import app as A
    closed = []
    monkeypatch.setattr(A.worker, "start", lambda: None)

    class P:
        side, market, qty = "short", "perp", 1.0

    class B:
        positions = {"AVAXUSDT": P(), "BTCUSDT": P()}
    monkeypatch.setattr(A.engine, "book", lambda *a, **k: B())
    monkeypatch.setattr(A.engine, "close_position", lambda s: closed.append(s) or {"ok": True})
    c = TestClient(A.app)
    u = c.get("/api/universe").json()
    assert set(S.SUPPORTED_SYMBOLS) <= set(u["supported"]) and "AVAXUSDT" in u["held"]
    r = c.post("/api/worker/start", json={"symbols": ["BTCUSDT", "ETHUSDT"], "deselect_policy": "flatten"}).json()
    assert r["selection"]["flattened"] == ["AVAXUSDT"] and closed == ["AVAXUSDT"]
    cfg = S.load()
    assert cfg["symbols"] == ["BTCUSDT", "ETHUSDT"] and cfg["worker"]["deselect_policy"] == "flatten"
    r = c.post("/api/worker/start", json={"symbols": ["BTCUSDT"], "deselect_policy": "keep"}).json()
    assert r["selection"]["kept"] == ["AVAXUSDT"] and closed == ["AVAXUSDT"]
    assert c.post("/api/worker/start", json={"symbols": ["FAKEUSDT"]}).status_code == 400
    assert c.post("/api/worker/start", json={"symbols": []}).status_code == 400
    S.update({"symbols": list(S.DEFAULTS["symbols"]), "worker": {"deselect_policy": "keep", "enabled": True}})


def test_run_cycle_manages_deselected_positions_without_new_entries(monkeypatch, tmp_path):
    conn = db.connect(tmp_path / "sel.sqlite")
    b = PaperBook(1000, 4, conn=conn)
    b.open(symbol="AVAXUSDT", market="perp", side="short", qty=1, price=20, price_kind="mark", stop=22,
           signal_bar="x", reason="t", venue="okx", data_source="okx_public_ws", price_time="2026-11-13T00:00:00Z")
    seen = {}
    rows = [{"symbol": "AVAXUSDT", "side": "long", "signal": 1, "market": "spot", "signal_market": "spot", "atr": 1.0}]

    def fake_sig(cfg, with_quotes=False):
        seen["symbols"] = list(cfg["symbols"])
        return {"rows": rows, "errors": {}}
    monkeypatch.setattr(engine, "compute_signals", fake_sig)
    monkeypatch.setattr(engine, "book", lambda *a, **k: b)
    monkeypatch.setattr(engine, "vol_scaled_cfg", lambda c, bk: c)
    monkeypatch.setattr(engine, "_route", lambda *a, **k: None)
    monkeypatch.setattr(engine, "export_paper_csv", lambda *a, **k: None)
    monkeypatch.setattr(engine, "_quote", lambda v, s, m: (21.0, "mark" if m == "perp" else "last", _q(s, m, 21.0)))
    cfg = _cfg(); cfg["symbols"] = ["BTCUSDT"]
    try:
        engine.run_cycle(cfg)
    except Exception:  # noqa: BLE001  后续步骤依赖真实信号字段，这里只看离场 / 入场
        pass
    assert seen["symbols"] == ["BTCUSDT", "AVAXUSDT"]
    assert "AVAXUSDT" not in b.positions  # 信号反转 → 平仓
    assert not any(t["symbol"] == "AVAXUSDT" and t["side"] == "long" for t in b.trade_records())  # 未选中 → 不反手开多


def test_label_actions_reversal_and_blocked():
    rows = [
        {"symbol": "BTCUSDT", "side": "short", "status": "closed", "entry_time": "2026-11-10T00:00:00Z",
         "exit_time": "2026-11-12T04:00:05Z", "exit_reason": "信号反转"},
        {"symbol": "BTCUSDT", "side": "long", "status": "open", "entry_time": "2026-11-12T04:00:06Z"},
        {"symbol": "AVAXUSDT", "side": "short", "status": "closed", "entry_time": "2026-11-10T00:00:00Z",
         "exit_time": "2026-11-12T04:00:05Z", "exit_reason": "信号反转"},
        {"symbol": "ETHUSDT", "side": "long", "status": "closed", "entry_time": "2026-11-10T00:00:00Z",
         "exit_time": "2026-11-11T00:00:00Z", "exit_reason": "ATR止损（实时）"},
    ]
    label_actions(rows)
    assert rows[0]["exit_action"] == "反手" and rows[1]["entry_action"] == "反手开多"
    assert rows[2]["exit_action"] == "平仓" and "拦截" in rows[2]["exit_note"]
    assert rows[3]["exit_action"] == "止损" and rows[3]["entry_action"] == "开多"


def test_backtest_summary_has_quality_metrics():
    from qtw.backtest import _trade_quality

    class T:
        def __init__(self, p):
            self.pnl_usdt = p
    q = _trade_quality([T(10), T(-2), T(-2), T(-2), T(30)])
    assert q["payoff_ratio"] == pytest.approx(20 / 2) and q["expectancy_usdt"] == pytest.approx(34 / 5)
    assert q["top10_pnl_share"] == pytest.approx(30 / 34)


def test_hover_fields_and_chinese_intervals_in_frontend():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "static"
    ch = (root / "charts.js").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    k_bar = ch[ch.index('bar.className = "k-ohlc"'):ch.index("c._ohlcShow")]
    for f in ("时间", "开盘", "最高", "最低", "收盘", "涨跌额", "涨跌幅", "振幅"):
        assert f"<em>{f}</em>" in k_bar
    yoy_head = ch[ch.index("<th>年份</th>"):ch.index("<th>年内</th>")]
    assert "<th>涨跌额</th>" in yoy_head and "<th>振幅</th>" in yoy_head
    for lab in ("1分", "5分", "10分", "15分", "1时", "4时", "日线", "周线", "月线", "年线"):
        assert f'"{lab}"' in app
    assert "TradingView" in app and "pickCoins" in app and "bookTag" in app
