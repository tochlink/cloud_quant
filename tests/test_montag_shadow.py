"""#19 binance_montag_short_1h 影子：监控标签标题解析与研究 parse.py 一致、入场 / 离场逻辑（全部离线，不访问网络）。"""
import os

from qtw import montag_shadow as M

H = 3600 * 1000
REL = 1_795_154_412_166


def art(i, title, rel=REL):
    return {"id": i, "title": title, "releaseDate": rel}


def test_parse_title_matches_research_mt_add():
    assert M.parse_title("Binance Will Extend the Monitoring Tag to Include BANK, INIT, MITO, ONE, THE & ZIL, "
                         "Remove the Seed Tag for MORPHO & HYPE on 2026-11-20") == ["BANK", "INIT", "MITO", "ONE", "THE", "ZIL"]
    assert M.parse_title("Binance Will Extend the Monitoring Tag to Include BICO & CVC on 2026-10-09") == ["BICO", "CVC"]
    assert M.parse_title("Binance Will Extend the Monitoring Tag to GPS on 2025-03-07") == ["GPS"]
    assert M.parse_title("Binance Will Extend the Monitoring Tag to Include BAL, CTXC and SUN and Remove the Monitoring Tag "
                         "for MLN & ZEN on 2024-07-01") == ["BAL", "CTXC", "SUN"]
    assert M.parse_title("Binance Will Change the Monitoring Tag Inclusion Frequency to Monthly and Extend the Monitoring Tag "
                         "to Include AERGO, ALPACA & VIDT on 2025-03-04") == ["AERGO", "ALPACA", "VIDT"]
    # 单字母 D 被过滤（与 delist_shadow 同一 STOP / 长度规则）
    assert M.parse_title("Binance Will Extend the Monitoring Tag to Include ACA, D, DATA & FLOW on 2026-01-02") == ["ACA", "DATA", "FLOW"]


def test_parse_title_ignores_remove_only_and_other():
    for t in ("Binance Will Remove the Monitoring Tag for ZEC and the Seed Tag for ENA, PYTH, TAO & W on 2025-07-09",
              "Binance Will Remove the Seed Tag for BONK, EIGEN, ETHFI, PENGU & PEPE on 2025-07-21",
              "Introducing Seed Tags & Monitoring Tags for Tokens with High Volatility and Risks",
              "Binance Will Delist COS, HIGH on 2026-06-19"):
        assert M.parse_title(t) == []


def test_research_parse_agrees_on_official_titles():
    fn = "/workspace/scratch/bnbmontag1h/events_parsed.csv"
    src = "/workspace/scratch/bnbmontag1h/binance_announcements_official.csv"
    if not (os.path.exists(fn) and os.path.exists(src)):
        return
    import csv
    want = {}
    for r in csv.DictReader(open(fn)):
        if r["event_type"] == "mt_add" and len(r["coin"]) >= 2:
            want.setdefault(r["ann_id"], []).append(r["coin"])
    got = {}
    for r in csv.DictReader(open(src)):
        c = M.parse_title(r["title"])
        if c:
            got[r["id"]] = c
    assert got == want


def _resolve(c, rel):
    return None if c == "NOPERP" else ("okx", f"{c}USDT")


def _px(v, s):
    return {"AAAUSDT": 2.0, "BBBUSDT": 0.5}.get(s, 1.0)


def test_entry_exit_short_24h_with_fees():
    b = M.new_book()
    a = [art(7, "Binance Will Extend the Monitoring Tag to Include AAA, BBB & NOPERP on 2026-12-01")]
    out = M.step_entries(b, a, REL + 30_000, _resolve, _px)
    assert out["wait"] == ["7"] and not b["positions"]
    out = M.step_entries(b, a, REL + 90_000, _resolve, _px)
    assert sorted(b["positions"]) == ["AAAUSDT", "BBBUSDT"]
    p = b["positions"]["AAAUSDT"]
    assert p["side"] == "short" and abs(p["notional"] - 100.0) < 1e-9 and p["strategy"] == "binance_montag_short_1h"
    assert M.step_exits(b, REL + 90_000 + 23 * H, _px) == []
    rows = M.step_exits(b, REL + 90_000 + 24 * H, lambda v, s: _px(v, s) * 0.9)
    assert len(rows) == 2 and not b["positions"]
    t = b["trades"][0]
    assert abs(t["pnl_usdt"] - (10.0 - 90.0 * M.FEE_RATE - 100.0 * M.FEE_RATE)) < 1e-6
    txt = M.log_text(out, rows)
    assert "binance_montag_short_1h（#19" in txt and "金额(U)" in txt


def test_stale_not_opened_and_default_off(monkeypatch):
    b = M.new_book()
    out = M.step_entries(b, [art(8, "Binance Will Extend the Monitoring Tag to AAA on 2026-12-01")], REL + 3 * H, _resolve, _px)
    assert out["stale"] and not b["positions"]
    monkeypatch.setenv("QTW_SHADOW_MONTAG", "1")
    monkeypatch.setenv("QTW_FORBID_LIVE", "1")
    assert M.enabled() is False and M.start() is False
