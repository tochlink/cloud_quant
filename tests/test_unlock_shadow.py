"""#17 token_unlock_short_1h 影子：日历、入场 / 离场、对冲腿盈亏（全部离线，不访问网络）。"""
from datetime import datetime, timezone

import pytest

from qtw import unlock_shadow as U

H = 3600 * 1000


def ms(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp() * 1000)


def test_calendar_matches_research_rules():
    cal = U.calendar()
    keys = {(c, U._iso_ms(t)[:10]) for c, t in cal}
    assert ("ARB", "2024-03-16") in keys and ("ARB", "2026-12-16") in keys and ("ARB", "2027-03-16") in keys
    assert ("STRK", "2024-04-15") in keys and ("JTO", "2024-12-07") in keys and ("JTO", "2027-01-07") not in keys
    assert ("ZK", "2025-06-17") in keys and ("ZRO", "2025-06-20") in keys and ("PYTH", "2026-05-20") in keys
    assert ("APT", "2026-10-12") in keys and ("APT", "2026-11-12") not in keys
    research = sum(1 for c, t in cal if t <= ms("2026-11-20T00:00:00"))
    assert research == 164  # 与 scratch/tokenunlock1h/unlock_events_official.csv 同一事件数


def _px_a(v, s):
    return {"JTOUSDT": 2.0, "BTCUSDT": 100000.0}[s]


def test_entry_window_and_hedge_leg():
    b = U.new_book()
    t0 = ms("2026-12-07T00:00:00")
    out = U.step_entries(b, t0 - 73 * H, lambda c: "okx", _px_a)
    assert not out["open"] and not b["positions"]
    out = U.step_entries(b, t0 - 72 * H + 30_000, lambda c: "okx", _px_a)
    p = b["positions"]["JTO@2026-12-07"]
    assert p["side"] == "short" and p["hedge_side"] == "long" and p["venue"] == "okx"
    assert p["notional"] == pytest.approx(250.0) and p["qty"] == pytest.approx(125.0)
    assert p["hedge_qty"] == pytest.approx(250.0 / 100000.0)
    assert b["fees"] == pytest.approx(2 * 250 * 0.00051)
    assert len(out["open"]) == 2
    # 同一事件不重复开
    U.step_entries(b, t0 - 60 * H, lambda c: "okx", _px_a)
    assert len(b["positions"]) == 1


def test_stale_entry_not_opened():
    b = U.new_book()
    t0 = ms("2026-12-07T00:00:00")
    out = U.step_entries(b, t0 - 60 * H, lambda c: "okx", _px_a)
    assert not b["positions"] and out["stale"] and "JTO@2026-12-07" in b["seen"]


def test_exit_at_t0_pnl_both_legs():
    b = U.new_book()
    t0 = ms("2026-12-07T00:00:00")
    U.step_entries(b, t0 - 72 * H, lambda c: "okx", _px_a)
    assert U.step_exits(b, t0 - H, lambda v, s: 1.0) == []
    rows = U.step_exits(b, t0 + 60_000, lambda v, s: {"JTOUSDT": 1.8, "BTCUSDT": 101000.0}[s])
    assert len(rows) == 2 and not b["positions"]
    t = b["trades"][-1]
    g1 = 125 * 0.2          # 空 125 JTO，2.0 → 1.8
    g2 = 0.0025 * 1000.0    # 多 0.0025 BTC，+1000
    fees_in = 2 * 250 * 0.00051
    fees_out = (125 * 1.8 + 0.0025 * 101000) * 0.00051
    assert t["pnl_usdt"] == pytest.approx(g1 + g2 - fees_in - fees_out)
    assert b["realized"] == pytest.approx(1000 + g1 + g2 - fees_in - fees_out)
    assert U.equity(b) == pytest.approx(b["realized"])


def test_gross_cap_and_no_venue():
    b = U.new_book()
    t0 = ms("2026-12-16T00:00:00")
    out = U.step_entries(b, t0 - 72 * H, lambda c: None, _px_a)
    assert ["ARB", "OKX / Gate 无 live 的 USDT 永续"] in out["skip"] and not b["positions"]


def test_disabled_by_default_and_in_tests(monkeypatch):
    monkeypatch.delenv("QTW_SHADOW_UNLOCK", raising=False)
    assert not U.enabled()
    monkeypatch.setenv("QTW_SHADOW_UNLOCK", "1")
    assert not U.enabled()  # conftest 设置了 QTW_FORBID_LIVE=1
    assert U.start() is False


def test_log_text_open_table_format():
    out = {"open": [["JTOUSDT", "开空·永续", "250.0", "2", "okx", 30]], "skip": [], "stale": []}
    txt = U.log_text(out, [])
    assert "token_unlock_short_1h（#17" in txt and "开仓" in txt and "JTOUSDT" in txt and "金额(U)" in txt
