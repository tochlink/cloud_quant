"""#15 binance_delist_short_1h 影子：标题解析、入场 / 离场逻辑（全部离线，不访问网络）。"""
import pytest

from qtw import delist_shadow as D

H = 3600 * 1000
REL = 1_790_000_000_000


def art(i, title, rel=REL):
    return {"id": i, "title": title, "releaseDate": rel}


def test_parse_title_matches_research_regex():
    assert D.parse_title("Binance Will Delist DEGO, DENT, TRU on 2026-04-28") == ["DEGO", "DENT", "TRU"]
    assert D.parse_title("Binance Will Delist ALCX, ARDR, NFP, POND on 2026-07-10") == ["ALCX", "ARDR", "NFP", "POND"]
    assert D.parse_title("Binance Will Delist EPIC and QUICK on 2026-10-28") == ["EPIC", "QUICK"]
    assert D.parse_title("Binance Will Delist 1000SATS & USDP on 2026-09-24") == ["SATS", "USDP"]
    # 单字母 D 与 STOP 词被过滤（与 parse.py 相同）
    assert D.parse_title("Binance Will Delist COS, D, HIGH, MBOX on 2026-06-19") == ["COS", "HIGH", "MBOX"]
    assert D.parse_title("Binance Will Delist BUSD on 2023-12-15") == []


@pytest.mark.parametrize("t", [
    "Binance Will Delist XYZ Margin Pairs on 2026-01-01",
    "Binance Futures Will Delist PTBUSDT and MITOUSDT USDⓈ-M Perpetual Contracts (2026-10-23)",
    "Notice of Removal of Spot Trading Pairs - 2026-11-20",
    "Binance Will List Foo (FOO)",
])
def test_parse_title_ignores_other_announcements(t):
    assert D.parse_title(t) == []


def _resolve_all(c, rel):
    return None if c == "NOPERP" else ("okx", f"{c}USDT")


def _px(v, s):
    return {"AAAUSDT": 2.0, "BBBUSDT": 0.5}.get(s, 1.0)


def test_entry_waits_until_release_plus_60s_then_equal_weight_short():
    b = D.new_book()
    a = [art(1, "Binance Will Delist AAA, BBB and NOPERP on 2026-12-01")]
    out = D.step_entries(b, a, REL + 30_000, _resolve_all, _px)
    assert out["wait"] == ["1"] and not b["positions"] and "1" not in b["seen"]
    out = D.step_entries(b, a, REL + 90_000, _resolve_all, _px)
    assert sorted(b["positions"]) == ["AAAUSDT", "BBBUSDT"]
    assert ["NOPERP", "OKX / Gate 无上线 ≥24h 的 USDT 永续"] in out["skip"]
    p = b["positions"]["AAAUSDT"]
    assert p["side"] == "short" and p["market"] == "perp" and p["venue"] == "okx"
    assert p["notional"] == pytest.approx(100.0)  # 0.2 × 1000U / 2 币
    assert p["qty"] == pytest.approx(50.0) and p["entry_delay_sec"] == pytest.approx(90.0)
    assert b["fees"] == pytest.approx(200 * 0.00051)
    assert b["events"][-1]["delay_sec"] == pytest.approx(90.0)
    # 同一公告再次轮询不重复开
    D.step_entries(b, a, REL + 400_000, _resolve_all, _px)
    assert len(b["positions"]) == 2


def test_no_duplicate_when_coin_already_open():
    b = D.new_book()
    D.step_entries(b, [art(1, "Binance Will Delist AAA on 2026-12-01")], REL + 61_000, _resolve_all, _px)
    out = D.step_entries(b, [art(2, "Binance Will Delist AAA and BBB on 2026-12-02", REL + H)], REL + H + 61_000, _resolve_all, _px)
    assert ["AAA", "同币已有持仓，不重复开"] in out["skip"]
    assert b["positions"]["BBBUSDT"]["notional"] == pytest.approx(0.2 * D.equity(b), rel=1e-3)


def test_stale_announcement_not_traded():
    b = D.new_book()
    out = D.step_entries(b, [art(1, "Binance Will Delist AAA on 2026-12-01")], REL + 3 * H, _resolve_all, _px)
    assert not b["positions"] and out["stale"] and "1" in b["seen"]


def test_exit_after_24h_pnl_and_fees():
    b = D.new_book()
    D.step_entries(b, [art(1, "Binance Will Delist AAA on 2026-12-01")], REL + 60_000, _resolve_all, _px)
    t0 = REL + 60_000
    assert D.step_exits(b, t0 + 23 * H, lambda v, s: 1.0) == []
    rows = D.step_exits(b, t0 + 24 * H, lambda v, s: 1.8)  # 2.0 → 1.8，空单赚 10%
    assert rows and not b["positions"]
    t = b["trades"][-1]
    gross = 200 * 0.10  # 单币公告：整条预算 200U
    fees = 200 * 0.00051 + 180 * 0.00051
    assert t["pnl_usdt"] == pytest.approx(gross - fees)
    assert b["realized"] == pytest.approx(1000 + gross - fees)
    assert D.equity(b) == pytest.approx(b["realized"])


def test_exit_price_failure_retries_later():
    b = D.new_book()
    D.step_entries(b, [art(1, "Binance Will Delist AAA on 2026-12-01")], REL + 60_000, _resolve_all, _px)

    def boom(v, s):
        raise RuntimeError("net")
    assert D.step_exits(b, REL + 25 * H, boom) == [] and "AAAUSDT" in b["positions"]


def test_disabled_by_default_and_in_tests(monkeypatch):
    monkeypatch.delenv("QTW_SHADOW_DELIST", raising=False)
    assert not D.enabled()
    monkeypatch.setenv("QTW_SHADOW_DELIST", "1")
    assert not D.enabled()  # conftest 设置了 QTW_FORBID_LIVE=1
    assert D.start() is False


def test_log_text_open_table_format():
    out = {"open": [["AAAUSDT", "开空·永续", "100.0", "2", "okx", 90]], "skip": [], "stale": []}
    txt = D.log_text(out, [])
    assert "binance_delist_short_1h（#15" in txt and "开仓" in txt and "AAAUSDT" in txt and "金额(U)" in txt
