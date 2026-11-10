"""对账公式测试（手工构造的成交表，仅验证配对与滑点符号）。"""
import pandas as pd
import pytest

from qtw.reconcile import load_fills, reconcile, round_trips


def _bt():
    return pd.DataFrame([
        {"symbol": "BTCUSDT", "side": "long", "entry_time": "2026-11-01T04:00:00+00:00", "entry_price": 100.0,
         "exit_time": "2026-11-02T08:00:00+00:00", "exit_price": 110.0, "exit_reason": "均线离场", "return_pct": 0.1},
        {"symbol": "ETHUSDT", "side": "short", "entry_time": "2026-11-01T08:00:00+00:00", "entry_price": 50.0,
         "exit_time": "2026-11-01T20:00:00+00:00", "exit_price": 45.0, "exit_reason": "ATR止损", "return_pct": 0.1},
        {"symbol": "BTCUSDT", "side": "long", "entry_time": "2026-11-05T00:00:00+00:00", "entry_price": 120.0,
         "exit_time": "", "exit_price": float("nan"), "exit_reason": "", "return_pct": 0.0},
    ])


def _fills(tmp_path):
    p = tmp_path / "f.csv"
    p.write_text(
        "venue,mode,symbol,market,side,action,fill_time,fill_price,qty,fee_usdt,order_id,reason\n"
        "okx,live,BTC-USDT,spot,long,open,2026-11-01T04:00:30Z,100.5,1,0.04,a,\n"
        "okx,live,BTC-USDT,spot,long,open,2026-11-01T04:01:00Z,100.5,1,0.04,b,\n"
        "okx,live,BTC-USDT,spot,long,close,2026-11-02T08:00:40Z,109.0,2,0.09,c,\n"
        "okx,live,ETH-USDT-SWAP,perp,short,open,2026-11-01T08:00:20Z,49.9,1,0.02,d,\n"
        "okx,live,ETH-USDT-SWAP,perp,short,close,2026-11-01T20:00:10Z,45.1,1,0.02,e,\n")
    return load_fills(p)


def test_pairing_and_slippage_sign(tmp_path):
    f = _fills(tmp_path)
    ut = round_trips(f)
    assert len(ut) == 2 and set(ut["symbol"]) == {"BTCUSDT", "ETHUSDT"}
    per, summ, missed = reconcile(f, _bt())
    b = per[per.symbol == "BTCUSDT"].iloc[0]
    assert b.matched and b.entry_slip_bps == pytest.approx(50.0)          # 多单买贵 50bps = 更差
    assert b.exit_slip_bps == pytest.approx(1 / 110 * 1e4)                # 卖便宜 = 更差
    e = per[per.symbol == "ETHUSDT"].iloc[0]
    assert e.entry_slip_bps == pytest.approx(20.0)                         # 空单卖便宜 = 更差
    assert e.exit_slip_bps == pytest.approx(0.1 / 45 * 1e4)                # 空单回补贵 = 更差（正数）
    assert summ.iloc[0]["matched"] == 2


def test_missed_and_unmatched(tmp_path):
    f = _fills(tmp_path)
    far = f.iloc[[0]].copy(); far["fill_time"] = pd.Timestamp("2026-12-01", tz="UTC")
    per, summ, missed = reconcile(pd.concat([f, far]).reset_index(drop=True), _bt())
    assert summ.iloc[0]["unmatched_user"] == 1
    assert summ.iloc[0]["missed_backtest"] == 1   # 11-05 那笔回测交易你那边没有


def test_bad_rows(tmp_path):
    p = tmp_path / "b.csv"
    p.write_text("venue,symbol,side,action,fill_time,fill_price,qty\nokx,BTCUSDT,buy,open,2026-11-01T00:00:00Z,1,1\n")
    with pytest.raises(ValueError):
        load_fills(p)
