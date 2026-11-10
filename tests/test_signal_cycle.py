"""引擎每根新 K 线：信号重算、反手（同周期平旧开新、分市场 taker）、调仓每根一次、信号变化日志。"""
import copy
from datetime import datetime, timezone

import pandas as pd
import pytest

from qtw import db, engine, signal_log, settings as S
from qtw.market.base import Quote
from qtw.paper import PaperBook
from qtw.rebalance import last_bar
from tests.test_backtest import synth  # 测试专用确定性序列


def _cfg(band=0.1):
    c = copy.deepcopy(S.DEFAULTS)
    c["symbols"] = ["XUSDT"]
    c["strategy"].update(trend_ma=0, short_breaker_bars=0, rebalance_band=band)
    return c


@pytest.fixture
def bk(tmp_path, monkeypatch):
    c = _cfg()
    b = PaperBook(1000, 4.0, conn=db.connect(tmp_path / "cyc.sqlite"),
                  fee_by_market={m: S.taker_rate(c, m) for m in ("spot", "perp")})
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "export_paper_csv", lambda cfg: None)
    return b


def _row(sig, bar, atr=2.0, px=100.0):
    side = {1: "long", -1: "short", 0: "flat"}[sig]
    mkt = {1: "spot", -1: "perp", 0: "-"}[sig]
    return {"symbol": "XUSDT", "signal": sig, "side": side, "market": mkt, "signal_market": mkt if mkt != "-" else "spot",
            "advice": engine.ADVICE[sig], "atr": atr, "as_of": bar, "signal_since": bar, "prev_signal": None,
            "prev_run_close": "", "trend_ok": True, "state": "entry_pending" if sig else "flat", "bar_close": px}


def _drive(monkeypatch, state):
    def fake_signals(cfg, with_quotes=True):
        return {"rows": [state["row"]], "errors": {}}

    def fake_quote(venue, sym, market):
        px = state["px"]
        q = Quote(venue=venue, symbol=sym, market=market, price=px, kind="mark" if market == "perp" else "last",
                  ts=datetime.now(timezone.utc), data_source="okx_public_rest", source_host="www.okx.com")
        return px, q.kind, q

    routed = []
    monkeypatch.setattr(engine, "compute_signals", fake_signals)
    monkeypatch.setattr(engine, "_quote", fake_quote)
    monkeypatch.setattr(engine, "_route", lambda cfg, s, m, a, q, p: routed.append((s, m, a, q)) or "paper_filled")
    return routed


def test_flip_closes_and_opens_opposite_same_cycle(bk, monkeypatch):
    c = _cfg(band=0)
    st = {"row": _row(-1, "2026-11-10T12:00:00Z"), "px": 100.0}
    routed = _drive(monkeypatch, st)
    engine.run_cycle(c)
    assert bk.positions["XUSDT"].side == "short" and bk.positions["XUSDT"].market == "perp"
    st.update(row=_row(1, "2026-11-10T16:00:00Z"), px=95.0)
    out = engine.run_cycle(c)
    p = bk.positions["XUSDT"]
    assert p.side == "long" and p.market == "spot"
    assert [a for _, _, a, _ in routed] == ["open_short", "close_short", "open_long"]
    f = bk.fills()
    close, opn = f[-2], f[-1]
    assert close["action"] == "close" and close["reason"] == "信号反转"
    assert close["fee_usdt"] == pytest.approx(close["notional_usdt"] * 0.00051)  # 永续 taker 5.1 bps
    assert opn["action"] == "open" and opn["fee_usdt"] == pytest.approx(opn["notional_usdt"] * 0.001)  # 现货 taker 10 bps
    assert any("平空" in e for e in out["events"]) and any("开多" in e for e in out["events"])
    log = signal_log.recent(10, bk.conn)
    assert log[0]["old_signal"] == -1 and log[0]["new_signal"] == 1 and "开多" in log[0]["action"]
    # 信号转空仓 → 平仓，不开新仓
    st.update(row=_row(0, "2026-11-10T20:00:00Z"))
    engine.run_cycle(c)
    assert "XUSDT" not in bk.positions
    assert signal_log.recent(1, bk.conn)[0]["new_signal"] == 0


def test_resize_once_per_new_bar(bk, monkeypatch):
    c = _cfg(band=0.1)
    st = {"row": _row(-1, "2026-11-10T12:00:00Z", atr=2.0), "px": 100.0}
    routed = _drive(monkeypatch, st)
    engine.run_cycle(c)
    q0 = bk.positions["XUSDT"].qty
    n0 = q0 * 100
    assert n0 == pytest.approx(200, rel=0.01)  # 权重上限 20%
    # 同一根 K 线内价格大跌：不调仓（每根 K 线只评估一次）
    st["px"] = 85.0
    engine.run_cycle(c)
    assert bk.positions["XUSDT"].qty == q0
    # 新收盘 K 线：名义 ≈ 0.85×200 = 170，比目标（20% 权重）低 >10% → 加仓到目标；止损不变
    st["row"] = _row(-1, "2026-11-10T16:00:00Z", atr=2.0)
    out = engine.run_cycle(c)
    p = bk.positions["XUSDT"]
    assert p.qty > q0 and p.stop_price == pytest.approx(104.0)
    assert any("加仓" in e for e in out["events"]) and routed[-1][2] == "open_short"
    assert abs(p.qty * 85 - 0.2 * bk.equity()) / (0.2 * bk.equity()) < 0.02
    assert last_bar(bk.conn) == "2026-11-10T16:00:00Z"
    q1 = p.qty
    engine.run_cycle(c)  # 同一根再跑：不重复调仓
    assert bk.positions["XUSDT"].qty == q1
    add = [f for f in bk.fills() if f["action"] == "add"]
    assert len(add) == 1 and add[0]["fee_usdt"] == pytest.approx(add[0]["notional_usdt"] * 0.00051)
    tr = bk.trade_records()
    assert tr[-1]["status"] == "open" and tr[-1]["resizes"] == 1
    lg = signal_log.recent(1, bk.conn)[0]
    assert lg["old_signal"] == lg["new_signal"] == -1 and "加仓" in lg["action"]
    # 再下一根：价格继续跌到 70，止损 104 离现价 48.6% → 风险目标 = 权益×5%/48.6% ≈ 110 → 减仓（锁定部分利润）
    st.update(row=_row(-1, "2026-11-10T20:00:00Z", atr=2.0), px=70.0)
    out = engine.run_cycle(c)
    p = bk.positions["XUSDT"]
    assert any("减仓" in e for e in out["events"]) and routed[-1][2] == "close_short"
    assert p.qty * 70 == pytest.approx(bk.equity() * 0.05 / ((104 - 70) / 70), rel=0.02)
    red = [f for f in bk.fills() if f["action"] == "reduce"]
    assert len(red) == 1 and red[0]["realized_pnl_usdt"] > 0


def test_compute_signals_recomputes_on_new_closed_bar(bk, monkeypatch):
    c = _cfg(band=0)
    df = synth(400, seed=3)
    df["close_time"] = df["open_time"] + pd.Timedelta(hours=4)
    view = {"n": 300}

    def fake_many(venue, syms, interval, need):
        d = df.iloc[: view["n"]].reset_index(drop=True)
        return {"spot": {"XUSDT": d}, "perp": {"XUSDT": d}}, {}

    monkeypatch.setattr(engine.mcache, "many", fake_many)
    a = engine.compute_signals(c, with_quotes=False)["rows"][0]
    view["n"] = 301
    b = engine.compute_signals(c, with_quotes=False)["rows"][0]
    assert pd.Timestamp(b["as_of"]) - pd.Timestamp(a["as_of"]) == pd.Timedelta(hours=4)
    assert pd.Timestamp(b["next_check"]) == pd.Timestamp(b["as_of"]) + pd.Timedelta(hours=4)
    # 走完整段：信号确实随新 K 线变化（不是一直一个）
    seen = set()
    for n in range(200, 400, 5):
        view["n"] = n
        seen.add(engine.compute_signals(c, with_quotes=False)["rows"][0]["signal"])
    assert len(seen) >= 2
    r = engine.compute_signals(c, with_quotes=False)["rows"][0]
    assert r["prev_signal"] in (-1, 0, 1, None) and r["prev_signal"] != r["signal"]
