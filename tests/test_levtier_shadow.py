"""#20 binance_margin_tier_tight_short_1h 影子：档位表解析与研究 parse.py 一致、入场 / 离场逻辑（全部离线，不访问网络）。"""
import json

from qtw import levtier_shadow as L

H = 3600 * 1000
REL = 1_795_154_412_166

BODY = (
    "Updates to Leverage & Margin Tiers:2026-03-13 06:30 (UTC):  PEOPLEUSDT  (USDⓈ-M Perpetual Contract)\n"
    "Previous Leverage and Margin Tiers | New Leverage and Margin Tiers | \n"
    "Leverage Before Change | Position Before Change (Notional Value in USDT) | Maintenance Margin Rate Before Change | "
    "Leverage After Change | Position After Change (Notional Value in USDT) | Maintenance Margin Rate After Change | \n"
    "51 - 75x | 0 < Position ≤ 500 | 1.00% | NA | \n"
    "26 - 50x | 500 < Position ≤ 5,000 | 1.50% | 21 - 50x | 0 < Position ≤ 5,000 | 1.50% | \n"
    " 1x | 7,500,000 < Position ≤ 12,500,000 | 50.00% |  1x | 7,500,000 < Position ≤ 12,500,000 | 50.00% | \n"
    "2026-03-13 06:30 (UTC):  HUMAUSDT and LAUSDT  (USDⓈ-M Perpetual Contract)\n"
    "Leverage Before Change | Position Before Change (Notional Value in USDT) | x | Leverage After Change | y | z | \n"
    "20x | 0 < Position ≤ 5,000 | 2% | 20x | 0 < Position ≤ 5,000 | 2% | \n"
    "1x | 1,000,000 < Position ≤ 2,000,000 | 50% | 1x | 500,000 < Position ≤ 1,000,000 | 50% | \n"
    "DOGEUSDT (USDⓈ-M Perpetual Contract)\n"
    "50x | 0 < Position ≤ 5,000 | 1% | 75x | 0 < Position ≤ 10,000 | 1% | \n"
)


def test_parse_tiers_directions():
    r = {x["coin"]: x for x in L.parse_tiers(BODY)}
    assert r["PEOPLE"]["lev_before"] == 75 and r["PEOPLE"]["lev_after"] == 50 and r["PEOPLE"]["dir"] == "tight"
    assert r["HUMA"]["dir"] == "tight" and r["LA"]["dir"] == "tight"  # 1x 档上限 2,000,000 → 1,000,000
    assert r["DOGE"]["dir"] == "loose"
    assert L.tight_coins(BODY) == ["PEOPLE", "HUMA", "LA"]


def test_flat_body_json_and_html():
    tree = {"node": "root", "child": [{"node": "element", "tag": "tr", "child": [
        {"node": "element", "tag": "td", "child": [{"node": "text", "text": "51 - 75x"}]},
        {"node": "element", "tag": "td", "child": [{"node": "text", "text": "0 &lt; Position"}]}]}]}
    assert L.flat_body(json.dumps(tree)) == "51 - 75x | 0 < Position | \n"
    assert L.flat_body("<tr><td>5x</td><td>a</td></tr>") == "5x | a | \n"


def test_title_match():
    assert L.title_match("Update on the Margin Tiers of USDⓈ-M Perpetual Contracts (2026-10-30)")
    assert L.title_match("Binance Futures Will Update the Leverage & Margin Tiers of Multiple USDⓈ-M Perpetual Contracts")
    assert not L.title_match("Binance Futures Will Delist and Update the Leverage & Margin Tiers of USDⓈ-M ETCBUSD Perpetual Contract")
    assert not L.title_match("Binance Will Extend the Monitoring Tag to Include BICO & CVC on 2026-10-09")


def _resolve(c, rel):
    return None if c == "NOPERP" else ("okx", f"{c}USDT")


def _px(v, s):
    return {"AAAUSDT": 2.0, "BBBUSDT": 0.5}.get(s, 1.0)


def test_entry_exit_short_48h_with_fees():
    b = L.new_book()
    a = [{"id": 7, "title": "Update on the Margin Tiers of USDⓈ-M Perpetual Contracts", "releaseDate": REL,
          "coins": ["AAA", "BBB", "NOPERP"]}]
    out = L.step_entries(b, a, REL + 30_000, _resolve, _px)
    assert out["wait"] == ["7"] and not b["positions"]
    L.step_entries(b, a, REL + 90_000, _resolve, _px)
    assert sorted(b["positions"]) == ["AAAUSDT", "BBBUSDT"]
    p = b["positions"]["AAAUSDT"]
    assert p["side"] == "short" and abs(p["notional"] - 100.0) < 1e-9 and p["strategy"] == "binance_margin_tier_tight_short_1h"
    assert L.step_exits(b, REL + 90_000 + 47 * H, _px) == []
    rows = L.step_exits(b, REL + 90_000 + 48 * H, lambda v, s: _px(v, s) * 0.9)
    assert len(rows) == 2 and not b["positions"]
    t = b["trades"][0]
    assert abs(t["pnl_usdt"] - (10.0 - 90.0 * L.FEE_RATE - 100.0 * L.FEE_RATE)) < 1e-6
    assert t["exit_reason"] == "持有期满 48h"


def test_no_coins_marked_seen_and_default_off(monkeypatch):
    b = L.new_book()
    L.step_entries(b, [{"id": 9, "title": "x", "releaseDate": REL, "coins": []}], REL + 90_000, _resolve, _px)
    assert "9" in b["seen"] and not b["positions"]
    monkeypatch.setenv("QTW_SHADOW_LEVTIER", "1")
    monkeypatch.setenv("QTW_FORBID_LIVE", "1")
    assert L.enabled() is False and L.start() is False
