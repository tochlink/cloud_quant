"""1000U 纸面账户端到端：信号 → 风控定仓 → 纸面下单 → 成交扣 taker 费 → 持仓计价 →
ATR 止损 / 信号离场 → 平仓 → 账本（权益、已实现 / 未实现盈亏、往返交易、订单日志）。实盘闸门始终关闭。"""
import copy
from datetime import datetime, timezone

import pytest

from qtw import db, engine, settings as S
from qtw.market.base import Quote
from qtw.paper import PaperBook


def _cfg():
    c = copy.deepcopy(S.DEFAULTS)
    c["symbols"] = ["BTCUSDT", "ETHUSDT"]
    return c


def _row(sym, sig, atr, bar, px):
    side = {1: "long", -1: "short", 0: "flat"}[sig]
    mkt = {1: "spot", -1: "perp", 0: "-"}[sig]
    return {"symbol": sym, "signal": sig, "side": side, "market": mkt,
            "signal_market": mkt if mkt != "-" else "spot", "advice": engine.ADVICE[sig], "atr": atr,
            "as_of": bar, "signal_since": bar, "prev_signal": None, "prev_run_close": "", "trend_ok": True,
            "state": "entry_pending" if sig else "flat", "bar_close": px, "name_vol_mult": 1.0}


@pytest.fixture
def env(tmp_path, monkeypatch):
    cfg = _cfg()
    b = PaperBook(1000, 4.0, conn=db.connect(tmp_path / "e2e.sqlite"),
                  fee_by_market={m: S.taker_rate(cfg, m) for m in ("spot", "perp")})
    monkeypatch.setattr(engine, "_BOOK", b)
    monkeypatch.setattr(engine, "export_paper_csv", lambda cfg: None)
    monkeypatch.setattr(engine, "_trader", lambda cfg: (_ for _ in ()).throw(AssertionError("live trader must not be used")))
    st = {"prices": {}, "rows": []}

    def fake_quote(venue, sym, market):
        px = st["prices"][(sym, market)]
        q = Quote(venue=venue, symbol=sym, market=market, price=px, kind="mark" if market == "perp" else "last",
                  ts=datetime.now(timezone.utc), data_source="okx_public_rest", source_host="www.okx.com")
        return px, q.kind, q

    monkeypatch.setattr(engine, "_quote", fake_quote)
    monkeypatch.setattr(engine, "compute_signals", lambda cfg, with_quotes=False: {"rows": st["rows"], "errors": {}})
    return cfg, b, st


def test_full_chain_on_1000u_paper_account(env):
    cfg, b, st = env
    assert not S.live_armed(cfg)
    bar1 = "2026-11-11T00:00:00Z"
    # 1) 信号：BTC 做多（现货）、ETH 做空（永续）
    st["rows"] = [_row("BTCUSDT", 1, 1000.0, bar1, 50000.0), _row("ETHUSDT", -1, 50.0, bar1, 2000.0)]
    st["prices"] = {("BTCUSDT", "spot"): 50000.0, ("ETHUSDT", "perp"): 2000.0}
    r1 = engine.run_cycle(cfg)
    assert len([e for e in r1["events"] if "开" in e]) == 2
    btc, eth = b.positions["BTCUSDT"], b.positions["ETHUSDT"]
    # 风控：2×ATR 止损距离 4%/5%，5% 风险 → 远超 20% 权重上限 → 各 200 USDT；总敞口 400 ≤ 1000 不缩放
    assert btc.notional_entry == pytest.approx(200.0) and eth.notional_entry == pytest.approx(200.0)
    assert btc.stop_price == pytest.approx(48000.0) and eth.stop_price == pytest.approx(2100.0)
    assert (btc.market, btc.side, eth.market, eth.side) == ("spot", "long", "perp", "short")
    fee_open = 200 * 0.001 + 200 * 0.00051
    assert b.realized == pytest.approx(1000 - fee_open)
    opens = [f for f in b.fills() if f["action"] == "open"]
    assert sorted(f["fee_usdt"] for f in opens) == pytest.approx([0.102, 0.2])

    # 2) 价格变动、信号不变：只计价，不交易；未实现盈亏进入权益
    st["prices"] = {("BTCUSDT", "spot"): 51000.0, ("ETHUSDT", "perp"): 1950.0}
    r2 = engine.run_cycle(cfg)
    assert not [e for e in r2["events"] if "开" in e or "平" in e]
    upnl = 0.004 * 1000 + 0.1 * 50
    assert b.equity() == pytest.approx(1000 - fee_open + upnl)
    assert r2["snapshot"]["unrealized_usdt"] == pytest.approx(upnl)

    # 3) ETH 触及 ATR 止损 → 平空，扣永续 taker，锁定同向再入场
    st["prices"][("ETHUSDT", "perp")] = 2100.0
    r3 = engine.run_cycle(cfg)
    assert any("ETHUSDT 平空" in e and "ATR止损" in e for e in r3["events"])
    assert "ETHUSDT" not in b.positions and b.blocks.get("ETHUSDT") == -1
    eth_close = [f for f in b.fills() if f["symbol"] == "ETHUSDT" and f["action"] == "close"][0]
    assert eth_close["fee_usdt"] == pytest.approx(0.1 * 2100 * 0.00051)
    assert eth_close["realized_pnl_usdt"] == pytest.approx(-0.1 * 100 - 0.1 * 2100 * 0.00051)
    # 信号仍为空 → 止损锁生效，不立即反复开空
    engine.run_cycle(cfg)
    assert "ETHUSDT" not in b.positions

    # 4) BTC 信号转空仓 → 按现货 taker 平多
    st["rows"][0] = _row("BTCUSDT", 0, 1000.0, "2026-11-11T04:00:00Z", 52000.0)
    st["prices"][("BTCUSDT", "spot")] = 52000.0
    r4 = engine.run_cycle(cfg)
    assert any("BTCUSDT 平多" in e and "信号转空仓" in e for e in r4["events"])
    assert not b.positions

    # 5) 账本：已实现 = 1000 + 毛盈亏 − 全部手续费；往返交易与订单日志齐全，全部为纸面成交
    fees = sum(f["fee_usdt"] for f in b.fills())
    gross = 0.004 * 2000 - 0.1 * 100
    assert b.realized == pytest.approx(1000 + gross - fees)
    assert b.equity() == pytest.approx(b.realized)
    trades = [t for t in b.trade_records() if t["status"] == "closed"]
    assert len(trades) == 2
    assert sum(t["pnl_usdt"] for t in trades) == pytest.approx(gross - fees)
    assert {t["exit_reason"] for t in trades} == {"ATR止损", "信号转空仓"}
    orders = b.orders()
    assert len(orders) == 4 and {o["status"] for o in orders} == {"paper_filled"} and {o["mode"] for o in orders} == {"paper"}
    assert {o["action"] for o in orders} == {"open_long", "open_short", "close_long", "close_short"}
    assert b.ledger()[-1]["equity_usdt"] == pytest.approx(b.realized)


def test_candle_keep_covers_btc_regime_lookback():
    """prune 不能删掉 BTC 熊市过滤要读的历史（btc_regime_ma + 5，校验上限 2000）。"""
    from qtw import db as _db, settings as _S
    assert _db.CANDLE_KEEP_BARS >= int(_S.DEFAULTS["strategy"]["btc_regime_ma"]) + 5
    assert _db.CANDLE_KEEP_BARS >= 2000 + 5
