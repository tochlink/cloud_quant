"""t69u：多空都用 USDT 永续 + 逐仓杠杆（默认 10 倍，1–100）+ 强平 + 资金费。"""
import copy
import math
from datetime import datetime, timezone

import numpy as np
import pytest

from qtw import db, engine, leverage as LV, margin as M, settings as S
from qtw.market.base import Quote
from qtw.paper import PaperBook


def test_defaults_perp_both_10x_risk_sized():
    rk = S.DEFAULTS["risk"]
    assert rk["trade_mode"] == "perp_both" and rk["perp_leverage"] == 10 and rk["leverage_scales_exposure"] is False
    assert LV.exposure_mult(S.DEFAULTS) == 1.0
    c = copy.deepcopy(S.DEFAULTS); c["risk"]["leverage_scales_exposure"] = True
    assert LV.exposure_mult(c) == 10.0
    c["risk"]["trade_mode"] = "spot_perp"
    assert LV.exposure_mult(c) == 1.0  # 现货不能加杠杆：放大敞口只在多空都用永续时生效


@pytest.mark.parametrize("lev,ok", [(1, True), (10, True), (100, True), (0, False), (101, False), (2.5, False)])
def test_settings_leverage_range(lev, ok):
    s = S.load()
    s["risk"]["perp_leverage"] = lev
    if ok:
        assert S.validate(s)["risk"]["perp_leverage"] == lev
    else:
        with pytest.raises(ValueError):
            S.validate(s)


def test_market_for_modes():
    c = copy.deepcopy(S.DEFAULTS)
    assert LV.market_for(1, c) == "perp" and LV.market_for(-1, c) == "perp" and LV.market_for(0, c) == "-"
    c["risk"]["trade_mode"] = "spot_perp"
    assert LV.market_for(1, c) == "spot" and LV.market_for("short", c) == "perp"


def test_pick_caps_by_venue_and_keeps_stop_before_liquidation():
    # OKX ADA 公开上限 50 倍
    lv = LV.pick("long", 1.0, 0.995, 100, "okx", "ADAUSDT", fee=0.00051)
    assert lv["lev"] <= 50 and "最高 50" in lv["reason"]
    # 止损 15%：10 倍强平只有约 9% → 必须降杠杆，且降完后止损先于强平
    for side, stop in (("long", 85.0), ("short", 115.0)):
        lv = LV.pick(side, 100.0, stop, 10, "okx", "BTCUSDT", fee=0.00051)
        assert lv["lev"] < 10 and "降到" in lv["reason"]
        assert M.stop_precedes_liquidation(side, 100.0, stop, lv["lev"], lv["mmr"] + 0.00051, 0.005)
    # 止损 3%：10 倍安全，不降
    lv = LV.pick("short", 100.0, 103.0, 10, "okx", "BTCUSDT", fee=0.00051)
    assert lv["lev"] == 10 and lv["reason"] == ""
    assert lv["liq"] == pytest.approx(100 * (1 + 0.1 - 0.004 - 0.00051))


def test_funding_by_bar_bins_settlements_into_next_bar():
    h = 3600_000
    times = np.array([0, 4 * h, 8 * h, 12 * h], dtype="int64") * 1_000_000
    acc = LV.funding_by_bar(times, [(0, 9.0), (4 * h, 0.001), (5 * h, 0.002), (8 * h, -0.003)])
    assert acc[0] == 0 and acc[1] == pytest.approx(0.001) and acc[2] == pytest.approx(-0.001) and acc[3] == 0



def test_funding_by_bar_treats_settlement_a_few_seconds_late_as_at_bar_open():
    # 官方结算记录常比整点晚 1 ~ 2 秒：仍归到该整点开盘那根，而不是晚一根
    h = 3600_000
    times = np.array([0, 4 * h, 8 * h, 12 * h], dtype="int64") * 1_000_000
    acc = LV.funding_by_bar(times, [(4 * h + 1000, 0.001), (8 * h + 2000, 0.002), (8 * h + 61_000, 0.004)])
    assert acc[1] == pytest.approx(0.001) and acc[2] == pytest.approx(0.002) and acc[3] == pytest.approx(0.004)
    old = LV.funding_by_bar(times, [(4 * h + 1000, 0.001)], grace_ms=0)
    assert old[1] == 0 and old[2] == pytest.approx(0.001)


def _q(sym, px):
    return Quote(venue="okx", symbol=sym, market="perp", price=px, kind="mark", ts=datetime.now(timezone.utc),
                 data_source="okx_public_ws", source_host="ws.okx.com")


def test_paper_perp_long_margin_funding_and_liquidation(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "lev.sqlite")
    b = PaperBook(1000, 4, conn=conn, fee_by_market={"spot": 0.001, "perp": 0.00051})
    b.open(symbol="BTCUSDT", market="perp", side="long", qty=0.002, price=50000, price_kind="mark", stop=48000,
           signal_bar="x", reason="t", venue="okx", leverage=10, liq_price=45500)
    p = b.positions["BTCUSDT"]
    assert p.margin_usdt == pytest.approx(10.0) and b.margin_used() == pytest.approx(10.0)
    eq0 = b.equity()
    # 正费率：多头付费
    amt = b.apply_funding("BTCUSDT", 0.0001, 50000, p.funding_ms + 1)
    assert amt == pytest.approx(-0.01) and b.equity() == pytest.approx(eq0 - 0.01)
    assert b.apply_funding("BTCUSDT", 0.0001, 50000, p.funding_ms) == 0  # 同一结算点不重复
    b.save()
    b2 = PaperBook(1000, 4, conn=conn, fee_by_market={"spot": 0.001, "perp": 0.00051})
    p2 = b2.positions["BTCUSDT"]
    assert p2.leverage == 10 and p2.liq_price == 45500 and p2.funding_usdt == pytest.approx(-0.01)
    # 跳空穿过强平价：引擎按强平处理，损失 = 全部逐仓保证金
    monkeypatch.setattr(engine, "_route", lambda *a, **k: None)
    cfg = copy.deepcopy(S.DEFAULTS); cfg["venue"] = "okx"
    ev = []
    before = b2.realized
    assert engine._exit_checks(cfg, b2, "BTCUSDT", p2, 45000, "mark", _q("BTCUSDT", 45000), ev) is True
    assert "BTCUSDT" not in b2.positions and "强制平仓" in ev[0]
    assert b2.realized == pytest.approx(before - 10.0)
    assert b2.fills()[-1]["reason"] == "强制平仓"


def test_relever_after_add_lowers_leverage_when_avg_entry_moves(tmp_path, monkeypatch):
    conn = db.connect(tmp_path / "rl.sqlite")
    b = PaperBook(1000, 4, conn=conn, fee_by_market={"spot": 0.001, "perp": 0.00051})
    lv = LV.pick("short", 100.0, 106.0, 10, "okx", "SOLUSDT", fee=0.00051)
    assert lv["lev"] == 10
    b.open(symbol="SOLUSDT", market="perp", side="short", qty=1.0, price=100.0, price_kind="mark", stop=106.0,
           signal_bar="x", reason="t", venue="okx", leverage=lv["lev"], liq_price=lv["liq"])
    # 盈利后在 90 加仓：均价下移到 95，止损仍在 106（距均价 11.6%）→ 10 倍会先强平
    b.resize("SOLUSDT", 2.0, 90.0, "mark", "调仓", "okx")
    cfg = copy.deepcopy(S.DEFAULTS); cfg["venue"] = "okx"
    engine.relever(cfg, b, "SOLUSDT")
    p = b.positions["SOLUSDT"]
    assert p.leverage < 10 and p.lev_reason
    assert p.liq_price > p.stop_price  # 空单：强平价在止损之上
    assert p.margin_usdt == pytest.approx(p.qty * p.entry_price / p.leverage)


def test_live_payloads_perp_long_and_leverage(monkeypatch):
    from qtw.live import gate as gate_live, okx as okx_live
    spec = {"ct_val": 0.01, "lot_sz": 0.01}
    o = okx_live.order_payload("BTCUSDT", "perp", "open_long", 0.002, 69000, spec, "long_short_mode")
    assert o["side"] == "buy" and o["posSide"] == "long"
    c = okx_live.order_payload("BTCUSDT", "perp", "close_long", 0.002, 69000, spec)
    assert c["side"] == "sell" and c["reduceOnly"] is True
    _, g = gate_live.order_request("BTCUSDT", "perp", "close_long", 0.002, 69000, {"ct_val": 0.0001})
    assert g["size"] == -20 and g["reduce_only"] is True
    _, g = gate_live.order_request("BTCUSDT", "perp", "open_long", 0.002, 69000, {"ct_val": 0.0001})
    assert g["size"] == 20 and "reduce_only" not in g
    sent = []
    monkeypatch.setattr("qtw.live.guard.require", lambda cfg, ex: None)
    monkeypatch.setattr(okx_live, "_send", lambda req: sent.append(req) or {"code": "0", "data": [{"posMode": "net_mode"}]})
    okx_live.OkxTrader({"api_key": "k", "secret": "s", "passphrase": "p"}).place_order(
        {"risk": {"perp_leverage": 10}}, "BTCUSDT", "perp", "open_long", 0.002, 69000, spec, leverage=7)
    lev = [r for r in sent if "set-leverage" in str(r.get("url", r))]
    assert lev and '"lever":"7"' in lev[0]["body"]


def test_backtest_exposure_scaling_simulates_liquidation_and_ruin():
    from tests.test_backtest import book, nobal
    from qtw.backtest import run_backtest
    c = nobal()
    base = {**c, "risk": {**c["risk"], "trade_mode": "perp_both", "perp_leverage": 50, "leverage_scales_exposure": True,
                          "leverage_protect": False}}
    r = run_backtest(book(4), base)
    sm = r["summary"]
    assert sm["exposure_mult"] == 50 and sm["min_equity_usdt"] >= 0
    assert sm["liquidations"] > 0 or sm["ruined"]
    assert not math.isnan(sm["max_margin_used_pct"])


def test_legacy_saved_settings_upgrade_to_new_leverage_default(monkeypatch):
    legacy = copy.deepcopy(S.DEFAULTS)
    legacy["risk"].pop("trade_mode"); legacy["risk"].pop("leverage_scales_exposure"); legacy["risk"]["perp_leverage"] = 1
    monkeypatch.setattr(S, "_read_db", lambda: legacy)
    s = S.load()
    assert s["risk"]["trade_mode"] == "perp_both" and s["risk"]["perp_leverage"] == 10
    newer = copy.deepcopy(S.DEFAULTS); newer["risk"]["perp_leverage"] = 3
    monkeypatch.setattr(S, "_read_db", lambda: newer)
    assert S.load()["risk"]["perp_leverage"] == 3  # 新版存档里用户自己选的倍数保留
