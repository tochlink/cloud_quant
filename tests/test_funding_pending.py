"""资金费：已平永续仓在持仓期内、平仓时尚未公布的结算点要补记；官方费率按推断的结算间隔及时补拉。"""
import pytest

from qtw import db, leverage as LV
from qtw.paper import PaperBook


def _book(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    return PaperBook(1000, 0, conn=conn), conn


def test_close_defers_unpublished_settlement_and_applies_later(tmp_path):
    b, conn = _book(tmp_path)
    b.open(symbol="BTCUSDT", market="perp", side="long", qty=0.01, price=50000, price_kind="mark", stop=45000,
           signal_bar="x", reason="t", venue="okx", leverage=10)
    p = b.positions["BTCUSDT"]
    b.mark("BTCUSDT", 50000, "t")
    t0 = p.funding_ms
    b.close("BTCUSDT", 50000, "mark", "t", "okx")
    assert len(b.funding_pending) == 1
    e = b.funding_pending[0]
    assert e["from_ms"] == t0 and e["qty"] == pytest.approx(0.01) and e["direction"] == 1
    # 持久化：重开账本后仍在
    b2 = PaperBook(1000, 0, conn=conn)
    assert len(b2.funding_pending) == 1
    t0 = b2.funding_pending[0]["from_ms"] = e["to_ms"] - 3600_000  # 测试里开平同一毫秒，人为拉开持仓区间
    before = b2.equity()
    st = e["to_ms"] - 1  # 平仓前一刻的结算点，平仓时还没公布
    amt = b2.apply_pending_funding({"BTCUSDT": [(t0 - 10, 0.01), (st, 0.0001)]}, now_ms=e["to_ms"] + 1000)
    assert amt == pytest.approx(-0.0001 * 0.01 * 50000)  # 正费率多头支付；入场前的结算点不计
    assert b2.equity() == pytest.approx(before + amt)
    assert len(b2.funding_pending) == 1  # 还没看到平仓之后的结算点，保留（防止区间内还有没公布的）
    assert b2.apply_pending_funding({"BTCUSDT": [(st, 0.0001)]}, now_ms=e["to_ms"] + 1000) == 0  # 不重复
    b2.apply_pending_funding({"BTCUSDT": [(st, 0.0001), (e["to_ms"] + 8 * 3600_000, 0.0001)]}, now_ms=e["to_ms"] + 9 * 3600_000)
    assert b2.funding_pending == []


def test_pending_short_receives_and_expires_after_24h(tmp_path):
    b, _ = _book(tmp_path)
    b.open(symbol="ETHUSDT", market="perp", side="short", qty=1, price=2000, price_kind="mark", stop=2200,
           signal_bar="x", reason="t", venue="gate", leverage=10)
    b.mark("ETHUSDT", 2000, "t")
    b.close("ETHUSDT", 2000, "mark", "t", "gate")
    e = b.funding_pending[0]
    e["from_ms"] = e["to_ms"] - 3600_000
    assert b.apply_pending_funding({"ETHUSDT": [(e["to_ms"], 0.0002)]}, now_ms=e["to_ms"] + 60_000) == pytest.approx(0.4)
    assert len(b.funding_pending) == 1
    assert b.apply_pending_funding({}, now_ms=e["to_ms"] + 25 * 3600_000) == 0
    assert b.funding_pending == []


def test_spot_close_does_not_defer(tmp_path):
    b, _ = _book(tmp_path)
    b.open(symbol="BTCUSDT", market="spot", side="long", qty=0.01, price=50000, price_kind="last", stop=45000,
           signal_bar="x", reason="t", venue="okx")
    b.close("BTCUSDT", 50000, "last", "t", "okx")
    assert b.funding_pending == []


def test_funding_due_uses_inferred_interval(monkeypatch):
    H = 3600_000
    store = {"rows": []}
    monkeypatch.setattr(db, "query", lambda sql, args=(), conn=None: [{"t_ms": t} for t in store["rows"]])
    LV._FUND_TRIED.clear()
    assert LV._funding_due("okx", "BTCUSDT", now_s=1000.0)  # 库里没有
    LV._FUND_TRIED.clear()
    store["rows"] = [16 * H, 8 * H]  # 8 小时间隔，最新 16:00
    assert not LV._funding_due("okx", "BTCUSDT", now_s=(23 * H) / 1000)
    assert LV._funding_due("okx", "BTCUSDT", now_s=(24 * H + 5000) / 1000)  # 00:00 已结算 → 立即补拉（旧规则要等到 01:00）
    store["rows"] = [16 * H, 12 * H]  # 4 小时间隔
    assert LV._funding_due("okx", "BTCUSDT", now_s=(20 * H + 1000) / 1000)
    LV._FUND_TRIED[("okx", "BTCUSDT")] = (20 * H + 1000) / 1000
    assert not LV._funding_due("okx", "BTCUSDT", now_s=(20 * H + 60_000) / 1000)  # 5 分钟内不重复请求
