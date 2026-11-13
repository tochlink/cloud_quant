"""调仓（rebalance_band）：回测记账、纯函数计划、纸面账本 resize、引擎每根 K 线一次、反手与信号日志。"""
import sys
import types

import pytest

from qtw import settings as S
from qtw import rebalance as RB
from qtw.backtest import run_backtest
from qtw.paper import PaperBook
from qtw import db

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from test_backtest import book as synth_book  # noqa: E402  测试专用确定性序列


def _cfg(band=0.1, mode="stop"):
    c = S.load()
    return {**c, "strategy": {**c["strategy"], "rebalance_band": band, "rebalance_mode": mode}}


def test_default_band_is_on_and_validated():
    c = S.load()
    assert c["strategy"]["rebalance_band"] == pytest.approx(0.1)
    with pytest.raises(ValueError):
        S.validate({**c, "strategy": {**c["strategy"], "rebalance_band": 0.01}})
    with pytest.raises(ValueError):
        S.validate({**c, "strategy": {**c["strategy"], "rebalance_mode": "x"}})


def test_rebalance_backtest_accounting():
    data = synth_book(8)
    off = run_backtest(data, _cfg(0.0))
    on = run_backtest(data, _cfg(0.1))
    assert off["summary"]["resizes"] == 0 and on["summary"]["resizes"] > 0
    for r in (off, on):
        tr = r["trades"]
        end = float(r["summary"]["ending_equity_usdt"])
        start = float(r["summary"]["starting_equity_usdt"])
        # 每笔 pnl = 毛盈亏 + 调仓已实现 − 全部手续费 → 合计必须等于权益变化
        assert tr["pnl_usdt"].sum() == pytest.approx(end - start, rel=1e-9, abs=1e-6)
    assert on["summary"]["total_return"] != off["summary"]["total_return"]


def _pos(side, qty, entry, stop):
    return types.SimpleNamespace(side=side, qty=qty, entry_price=entry, stop_price=stop)


def test_plan_caps_and_band():
    c = _cfg(0.25)
    # 权益 1000：单币权重上限 200；两个持仓目标都被权重封顶
    pos = {"A": _pos("short", 1.0, 100, 104), "B": _pos("long", 3.0, 100, 96)}
    px = {"A": 80.0, "B": 100.0}  # A 名义 80（远低于目标 200）→ 加仓；B 名义 300 → 减仓
    plan = RB.plan(pos, px, {}, equity=1000, new_notional=0, cfg=c, gross_now=380, fee=0.0)
    d = {r["symbol"]: r for r in plan}
    assert d["B"]["delta_usdt"] < 0 and d["A"]["delta_usdt"] > 0
    assert plan[0]["symbol"] == "B"  # 先减后加
    for r in plan:
        assert r["current_usdt"] + r["delta_usdt"] <= 200 + 1e-9
    # 偏离未超过阈值不调
    pos2 = {"A": _pos("long", 2.2, 100, 96)}
    assert RB.plan(pos2, {"A": 100.0}, {}, equity=1000, new_notional=0, cfg=c, gross_now=220, fee=0.0) == []
    # 总敞口：新开仓占满额度 → 已有持仓目标按比例缩小，不能突破 1× 权益
    pos3 = {"A": _pos("long", 2.0, 100, 96)}
    p3 = RB.plan(pos3, {"A": 100.0}, {}, equity=1000, new_notional=900, cfg=c, gross_now=1100, fee=0.0)
    assert p3 and p3[0]["current_usdt"] + p3[0]["delta_usdt"] == pytest.approx(100)
    # 已越过止损：不调仓（交给止损）
    assert RB.plan({"A": _pos("long", 1.0, 100, 96)}, {"A": 95.0}, {}, equity=1000, new_notional=0,
                   cfg=c, gross_now=95, fee=0.0) == []
    # 风险上限：止损很近时目标 = 权益×5% / 止损距离%（而非权重）
    t = RB.target_notional(side="long", price=100, stop=60, atr=None, equity=1000, max_risk=0.05, max_weight=0.2, atr_mult=2)
    assert t == pytest.approx(1000 * 0.05 / 0.4)


def test_paper_resize_accounting(tmp_path):
    conn = db.connect(tmp_path / "t.sqlite")
    bk = PaperBook(1000, 0, conn=conn, fee_by_market={"spot": 0.001, "perp": 0.00051})
    bk.open(symbol="X", market="perp", side="short", qty=2.0, price=100, price_kind="mark", stop=110,
            signal_bar="b", reason="t", venue="okx")
    r1 = bk.resize("X", 1.0, 90, "mark", "调仓", "okx")  # 减 1 @ 90 → +10 毛盈亏
    assert r1["action"] == "reduce" and r1["fee"] == pytest.approx(90 * 0.00051)
    assert r1["pnl"] == pytest.approx(10 - 90 * 0.00051)
    r2 = bk.resize("X", 3.0, 80, "mark", "调仓", "okx")  # 加 2 @ 80 → 均价 (100+160)/3
    assert r2["action"] == "add"
    p = bk.positions["X"]
    assert p.entry_price == pytest.approx(260 / 3) and p.stop_price == 110 and p.qty == 3.0
    pnl_close = bk.close("X", 70, "mark", "信号反转", "okx")
    tr = [t for t in bk.trade_records() if t["symbol"] == "X"]
    assert len(tr) == 1 and tr[0]["resizes"] == 2 and tr[0]["status"] == "closed"
    # 往返记录的盈亏 = 所有腿已实现盈亏之和 = 权益变化
    assert tr[0]["pnl_usdt"] == pytest.approx(bk.realized - 1000)
    assert pnl_close == pytest.approx(3 * (260 / 3 - 70) - 3 * 70 * 0.00051)


def test_rebalance_new_qty_rounds_and_never_leaves_dust():
    from qtw.engine import rebalance_new_qty
    from qtw.lots import Lot, floor_qty
    lot = Lot("gate", "XUSDT", "spot", 0.01, 0.0, min_quote=3.0)
    f = lambda q: floor_qty(q, lot, 10.0)  # 价格 10：最小金额 3 U = 0.3 币
    assert rebalance_new_qty(1.0, 1.357, f) == 1.35          # 加仓差额按步长向下取整
    assert rebalance_new_qty(1.0, 0.6, f) == 0.6             # 正常减仓（差额 4 U ≥ 3 U）
    assert rebalance_new_qty(1.0, 0.98, f) is None           # 差额 0.2 币 = 2 U < 3 U：不动
    assert rebalance_new_qty(1.0, 0.25, f) is None           # 差额够但剩余 0.25 币 = 2.5 U < 3 U：不留尘埃仓
    assert rebalance_new_qty(1.0, 0.0, f) is None            # 目标 0 由信号 / 止损离场处理，调仓不清仓
