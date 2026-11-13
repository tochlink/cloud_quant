"""模拟盘引擎侧动态多空风险平价 up（ls_parity_cap）：与回测 ls_parity_scales 逐根一致、关闭时不改行、只重算未持仓行的建议仓位。"""
import numpy as np

from qtw.engine import apply_ls_parity
from qtw.risk import size
from qtw.strategy import ls_parity_scales

RK = {"max_risk_per_trade": 0.05, "max_weight_per_name": 0.2}


def _rows(sig, nvm, held=()):
    out = []
    for s in sig:
        g = int(sig[s])
        out.append({"symbol": s, "signal": g, "side": {1: "long", -1: "short", 0: "-"}[g], "in_universe": True,
                    "name_vol_mult": float(nvm[s]), "ref_price": 100.0, "atr": 2.0,
                    "stop_source": "position" if s in held else "suggested", "target_notional_usdt": -1.0})
    return out


def test_off_is_noop():
    rows = _rows({"A": 1, "B": -1}, {"A": 0.5, "B": 1.0})
    before = [dict(r) for r in rows]
    for c in (0, 1, 0.5):
        apply_ls_parity(rows, c, 1000.0, RK, 2.0)
        assert rows == before


def test_matches_backtest_scales_bar_by_bar():
    rng = np.random.default_rng(7)
    syms = [f"S{i}" for i in range(8)]
    n = 300
    sig = {s: rng.choice([-1, 0, 1], size=n) for s in syms}
    nvm = {s: rng.uniform(0.2, 1.0, size=n) for s in syms}
    for cap in (1.5, 3.0, 5.0):
        ls, ss = ls_parity_scales(sig, nvm, nvm, cap)
        for t in range(n):
            rows = _rows({s: sig[s][t] for s in syms}, {s: nvm[s][t] for s in syms})
            apply_ls_parity(rows, cap, 1000.0, RK, 2.0)
            for r in rows:
                if r["signal"] == 0:
                    assert r["name_vol_mult"] == nvm[r["symbol"]][t]
                    continue
                k = ls[t] if r["signal"] == 1 else ss[t]
                assert abs(r["name_vol_mult"] - nvm[r["symbol"]][t] * k) < 1e-12


def test_only_smaller_side_scaled_and_resized():
    rows = _rows({"A": 1, "B": -1, "C": -1, "D": 1}, {"A": 0.3, "B": 1.0, "C": 1.0, "D": 0.2}, held=("D",))
    apply_ls_parity(rows, 3.0, 1000.0, RK, 2.0)
    by = {r["symbol"]: r for r in rows}
    assert by["B"]["name_vol_mult"] == 1.0 and by["C"]["name_vol_mult"] == 1.0  # 较大一侧不动
    assert abs(by["A"]["ls_parity_scale"] - 3.0) < 1e-12  # 2.0 / 0.5 = 4 → 封顶 3
    assert abs(by["A"]["name_vol_mult"] - 0.9) < 1e-12
    z = size(side="long", equity=1000.0, price=100.0, atr=2.0, max_risk=0.05 * 0.9, max_weight=0.2 * 0.9, atr_mult=2.0)
    assert abs(by["A"]["target_notional_usdt"] - z.notional) < 1e-9
    assert by["D"]["target_notional_usdt"] == -1.0  # 已持仓行不重算建议仓位（compute_signals 之后会用实际持仓覆盖）
    assert abs(by["D"]["name_vol_mult"] - 0.6) < 1e-12  # 但调仓乘数同样放大


def test_out_of_universe_and_one_sided_ignored():
    rows = _rows({"A": 1, "B": -1}, {"A": 0.5, "B": 1.0})
    rows[1]["in_universe"] = False
    apply_ls_parity(rows, 3.0, 1000.0, RK, 2.0)
    assert rows[0]["name_vol_mult"] == 0.5 and rows[1]["name_vol_mult"] == 1.0
