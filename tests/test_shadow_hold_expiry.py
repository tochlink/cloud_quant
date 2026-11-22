"""事件型影子子账本（#13 / #14）持有期：固定在原始入场 + H 根到期，重算信号 / 新触发不延长，重启不重置。

回归：2026-11-14 #13 入场后进程停机 6 天，重启后新触发（2026-11-21）让无状态重算信号重新变 1，
旧单被当成新事件的持有段一直拿到 11-22（约 177h，设计 24h）；#14 旧单同理一直不平。"""
import numpy as np
import pandas as pd
import pytest

from qtw import db, shadow
from qtw import settings as S

SYMS = ["ADAUSDT", "AVAXUSDT", "BNBUSDT", "BTCUSDT", "DOGEUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
T0 = pd.Timestamp("2026-11-01", tz="UTC")


def _data(n, drops):
    """1h K 线；每个 drops 下标处 8 个币一起再跌 15%（#13 投降事件出现在那根）。"""
    t = pd.date_range(T0, periods=n, freq="h")
    fr = {}
    for k, s in enumerate(SYMS):
        c = np.full(n, 100.0) * (1 + 0.001 * np.sin(np.arange(n) + k))
        for d in drops:
            if d < n:
                c[d:] *= 0.85
        fr[s] = pd.DataFrame({"open_time": t, "open": c, "high": c * 1.001, "low": c * 0.999, "close": c, "volume": 1.0})
    return {"spot": fr, "perp": {s: d.copy() for s, d in fr.items()}}


def _at(i):  # 第 i 根收盘后几秒的决策时刻
    return (T0 + pd.Timedelta(hours=i + 1, seconds=5)).isoformat().replace("+00:00", "Z")


@pytest.fixture()
def fresh(monkeypatch):
    monkeypatch.setattr(shadow, "_px", lambda venue, sym, market, fb: (float(fb), "bar_close"))
    for sid in ("capitulation_1h", "capitulation_dvol_1h"):
        shadow._BOOKS.pop(sid, None)
        shadow._ensure()
        db.execute("DELETE FROM shadow_books WHERE sid=?", (sid,))
    yield
    for sid in ("capitulation_1h", "capitulation_dvol_1h"):
        shadow._BOOKS.pop(sid, None)


def test_entry_records_persistent_expiry(fresh):
    shadow.decide("capitulation_1h", _data(120, [119]), S.load(), _at(119))
    p = shadow.book("capitulation_1h")["positions"]["BTCUSDT"]
    # 触发 K 线开盘 11-05 23:00，准时入场 11-06 00:00，持有 24 根 → 11-07 00:00 到期
    assert p["expires_at"] == "2026-11-07T00:00:00Z"
    shadow._BOOKS.pop("capitulation_1h")  # 模拟重启：从 SQLite 重新载入
    b = shadow.book("capitulation_1h")
    assert b["positions"]["BTCUSDT"]["expires_at"] == "2026-11-07T00:00:00Z"
    assert shadow.overdue("capitulation_1h", b, pd.Timestamp("2026-11-06T23:59:59Z")) == []
    assert len(shadow.overdue("capitulation_1h", b, pd.Timestamp("2026-11-07T00:00:00Z"))) == 8


def test_holds_until_expiry_then_exits_exactly_at_entry_plus_h(fresh):
    shadow.decide("capitulation_1h", _data(120, [119]), S.load(), _at(119))
    shadow.decide("capitulation_1h", _data(143, [119]), S.load(), _at(142))
    assert len(shadow.book("capitulation_1h")["positions"]) == 8  # 入场后第 23 根收盘（11-06 23:00）：未到期
    rows = {}
    shadow.decide("capitulation_1h", _data(144, [119]), S.load(), _at(143), rows=rows)  # 第 24 根收盘 = 11-07 00:00
    b = shadow.book("capitulation_1h")
    assert not b["positions"] and len(rows["close"]) == 8
    assert all(t["exit_reason"] == "持有期满" for t in b["trades"])


def test_retrigger_after_restart_does_not_extend_old_hold(fresh):
    """#13 实际情形：入场后停机，重启时已过期且又有新触发（已过宽限），旧单必须立即按到期平掉，不补开新触发。"""
    shadow.decide("capitulation_1h", _data(120, [119]), S.load(), _at(119))
    shadow._BOOKS.pop("capitulation_1h")  # 停机 / 重启
    rows = {}
    # 第 160 根收盘：新触发在第 150 根（重算信号 = 1，持有段 150..173），旧单 11-07 00:00 早已到期
    ev = shadow.decide("capitulation_1h", _data(161, [119, 150]), S.load(), _at(160), rows=rows)
    b = shadow.book("capitulation_1h")
    assert b["last_decision"]["signals"]["BTCUSDT"] == 1  # 旧代码会因为这个继续持有
    assert not b["positions"] and len(rows["close"]) == 8 and not rows["open"]
    assert all(t["exit_reason"].startswith("持有期满（到期 2026-11-07T00:00:00Z") for t in b["trades"])
    assert any("不补开" in e for e in ev)


def test_legacy_position_without_expiry_uses_entry_plus_h(fresh):
    """#14 旧单（开仓时还没有 signal_bar / expires_at）：按 entry_time + H(48) 根到期。"""
    shadow.decide("capitulation_dvol_1h", _data(120, [119]), S.load(), _at(119))
    b = shadow.book("capitulation_dvol_1h")
    assert len(b["positions"]) == 8
    for p in b["positions"].values():
        for k in ("expires_at", "signal_bar", "late_bars"):
            p.pop(k, None)
        p["entry_time"] = "2026-11-06T00:00:05Z"
    b.pop("last_trigger", None)
    assert shadow.event_expiry("capitulation_dvol_1h", b["positions"]["BTCUSDT"]) == pd.Timestamp("2026-11-08T00:00:05Z")
    shadow.decide("capitulation_dvol_1h", _data(168, [119]), S.load(), _at(167))  # 收盘 11-08 00:00 < 到期
    assert len(b["positions"]) == 8
    rows = {}
    # 重算信号因新触发（第 175 根）仍为 1，但旧单已到期 → 平仓，新触发已过宽限不补开
    shadow.decide("capitulation_dvol_1h", _data(178, [119, 175]), S.load(), _at(177), rows=rows)
    assert not b["positions"] and len(rows["close"]) == 8 and not rows["open"]


def test_chained_new_trigger_is_a_new_trade_with_its_own_expiry(fresh):
    """到期那根正好出现新触发（回测里是新的一段）：旧单按期平仓、新单另起，到期 = 新触发 + H+1 根；持有期内的触发不加仓。"""
    shadow.decide("capitulation_1h", _data(120, [119]), S.load(), _at(119))
    shadow.decide("capitulation_1h", _data(131, [119, 130]), S.load(), _at(130))  # 持有期内再跌：不加仓、不延长
    b = shadow.book("capitulation_1h")
    assert len(b["positions"]) == 8 and b["positions"]["BTCUSDT"]["expires_at"] == "2026-11-07T00:00:00Z"
    rows = {}
    shadow.decide("capitulation_1h", _data(144, [119, 143]), S.load(), _at(143), rows=rows)
    assert len(rows["close"]) == 8 and len(rows["open"]) == 8
    assert b["positions"]["BTCUSDT"]["expires_at"] == "2026-11-08T00:00:00Z"
