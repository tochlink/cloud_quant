"""运行时自适应（qtw/adaptive.py）与热加载（qtw/hotreload.py）。
synth() 为测试专用确定性序列（见 test_backtest.py 说明）；研究结论只用官方 OKX / Gate 数据（docs/STRATEGY_FORMULAS.md）。"""
import importlib
import sys
import time

import numpy as np
import pandas as pd
import pytest

from qtw import adaptive as A
from qtw import hotreload as H
from qtw import settings as S
from qtw.backtest import run_backtest
from qtw.strategy import indicators
from tests.test_backtest import synth


def _data(n=900):
    spot = {"BTCUSDT": synth(n, seed=11), "S1USDT": synth(n, seed=1)}
    perp = {"BTCUSDT": synth(n, seed=11, scale=1.01), "S1USDT": synth(n, seed=1, scale=1.01)}
    return {"spot": spot, "perp": perp}


def _cfg(**st):
    c = S._merge(S.DEFAULTS, {"symbols": ["BTCUSDT", "S1USDT"]})
    c["strategy"].update({"fast_ma": 10, "slow_ma": 30, "trend_ma": 0, "btc_regime_ma": 200, **st})
    return c


def test_defaults_and_validation():
    d = S.DEFAULTS["strategy"]
    assert d["hot_reload"] is True
    S.validate(S._merge(S.DEFAULTS, {}))
    for bad in ({"adaptive_size_mode": "x"}, {"adaptive_size_lo": 1.5, "adaptive_size_hi": 1.0}, {"retune_every_days": 1},
                {"retune_lookback_days": 10}, {"direction_bias_band": 3}):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": bad}))
    s = S.validate(S._merge(S.DEFAULTS, {"strategy": {"auto_retune": "false", "direction_bias": "1"}}))
    assert s["strategy"]["auto_retune"] is False and s["strategy"]["direction_bias"] is True


def test_trend_mult_bounds_and_caps():
    ind = indicators(synth(1500, seed=4), 10, 30, 14)
    for mode, lo, hi in (("spread", 0.5, 1.5), ("adx", 0.25, 1.25)):
        m = A.trend_size_mult(ind, mode, lo, hi)
        assert len(m) == len(ind) and np.isfinite(m).all()
        assert m.min() >= lo - 1e-12 and m.max() <= hi + 1e-12
    assert (A.trend_size_mult(ind, "off") == 1).all()
    base = np.array([0.3, 0.8, 1.0, 1.4])
    out = A.combine_mult(base, np.array([2.0, 2.0, 2.0, 2.0]))
    assert (out <= np.maximum(base, 1.0) + 1e-12).all()  # 5% / 20% 上限永不突破
    assert out.tolist() == [0.6, 1.0, 1.0, 1.4]


def test_trend_mult_causal():
    """第 t 根的乘子只依赖 ≤ t 的 K 线：截断未来数据不改变过去的值。"""
    df = synth(1400, seed=9)
    full = A.trend_size_mult(indicators(df, 10, 30, 14), "adx", 0.25, 1.25)
    part = A.trend_size_mult(indicators(df.iloc[:1000], 10, 30, 14), "adx", 0.25, 1.25)
    assert np.allclose(full[:1000], part)
    fs = A.trend_size_mult(indicators(df, 10, 30, 14), "spread", 0.5, 1.5)
    ps = A.trend_size_mult(indicators(df.iloc[:1000], 10, 30, 14), "spread", 0.5, 1.5)
    assert np.allclose(fs[:1000], ps)


def test_backtest_off_identity_and_features_run():
    d = _data()
    a = run_backtest(d, _cfg())
    b = run_backtest(d, _cfg(adaptive_size_mode="off", direction_bias=False))
    assert a["equity"]["equity"].tolist() == b["equity"]["equity"].tolist()
    for st in ({"adaptive_size_mode": "adx"}, {"adaptive_size_mode": "spread", "adaptive_size_hi": 1.5},
               {"direction_bias": True, "direction_bias_band": 0.0}):
        r = run_backtest(d, _cfg(**st))
        assert np.isfinite(r["equity"]["equity"]).all()
        tr = r["trades"]
        if len(tr):  # 单笔风险仍 ≤ 5%：|入场 − 止损| × 数量 ≤ 5% × 起始资金量级（含盈利放大，宽松检查）
            assert (tr["notional_usdt"] <= 0.2 * r["equity"]["equity"].max() * 1.01).all()


def test_direction_bias_blocks_only_new_shorts():
    d = _data()
    r0 = run_backtest(d, _cfg())
    r1 = run_backtest(d, _cfg(direction_bias=True, direction_bias_band=0.0))
    s0 = (r0["trades"]["side"] == "short").sum()
    s1 = (r1["trades"]["side"] == "short").sum()
    assert s1 <= s0


def test_schedule_identity_and_switch():
    d = _data()
    base = _cfg()
    a = run_backtest(d, base)
    p0 = {"fast_ma": 10, "slow_ma": 30, "atr_stop_mult": base["strategy"]["atr_stop_mult"], "btc_regime_ma": 200}
    b = run_backtest(d, base, schedule=[(pd.Timestamp("2000-01-01", tz="UTC"), p0)])
    assert a["equity"]["equity"].tolist() == b["equity"]["equity"].tolist()
    # 整段换成另一组参数 = 静态跑另一组参数
    p1 = {"fast_ma": 12, "slow_ma": 40, "atr_stop_mult": 2.5, "btc_regime_ma": 150}
    c = run_backtest(d, base, schedule=[(pd.Timestamp("2000-01-01", tz="UTC"), p1)])
    st = _cfg(fast_ma=12, slow_ma=40, atr_stop_mult=2.5, btc_regime_ma=150)
    e = run_backtest(d, st)
    assert c["equity"]["equity"].tolist()[-200:] == e["equity"]["equity"].tolist()[-200:]
    # 中途换参数：换参前的权益与不换完全一致（只用过去数据，不前视）
    t_sw = pd.Timestamp(d["spot"]["S1USDT"]["open_time"].iloc[600])
    m = run_backtest(d, base, schedule=[(pd.Timestamp("2000-01-01", tz="UTC"), p0), (t_sw, p1)])
    ea, em = a["equity"].set_index("time")["equity"], m["equity"].set_index("time")["equity"]
    before = [k for k in ea.index if pd.Timestamp(k) < t_sw]
    assert len(before) > 100 and ea.loc[before].tolist() == em.loc[before].tolist()


def test_choose_hysteresis():
    inc = {"fast_ma": 50, "slow_ma": 150, "atr_stop_mult": 2.0, "btc_regime_ma": 1200}
    ch = {"fast_ma": 30, "slow_ma": 100, "atr_stop_mult": 2.0, "btc_regime_ma": 1200}
    sc = {A.pkey(inc): 1.0, A.pkey(ch): 1.2}
    assert A.choose(sc, inc, 0.3)[0] == inc
    assert A.choose(sc, inc, 0.1)[0] == ch
    assert A.choose({A.pkey(ch): 1.2}, inc, 0.3)[0] == ch  # 现任无分数 → 取最优
    assert A.choose({A.pkey(ch): float("nan")}, inc, 0.3)[0] == inc


def test_score_window_uses_only_past():
    d = _data(1400)
    c = _cfg()
    t = pd.Timestamp(d["spot"]["S1USDT"]["open_time"].iloc[1000])
    p = {"fast_ma": 10, "slow_ma": 30, "atr_stop_mult": 2.0, "btc_regime_ma": 200}
    s_full = A.score_window(d, c, p, t, 90)
    cut = {m: {s: df.iloc[:1000] for s, df in v.items()} for m, v in d.items()}
    s_cut = A.score_window(cut, c, p, t, 90)
    assert s_full == pytest.approx(s_cut)


def test_effective_cfg_overlay_and_record():
    cfg = S._merge(S.DEFAULTS, {})
    assert A.effective_cfg(cfg) is cfg  # 关闭时原样
    res = {"params": {"fast_ma": 30, "slow_ma": 100, "atr_stop_mult": 2.5, "btc_regime_ma": 900}, "reason": "test", "scores": {}}
    A.record(cfg["venue"], res, 365, 0.3)
    on = S._merge(cfg, {"strategy": {"auto_retune": True}})
    eff = A.effective_cfg(on)
    assert eff["strategy"]["fast_ma"] == 30 and eff["strategy"]["btc_regime_ma"] == 900 and eff["_adaptive"]["params"]
    assert on["strategy"]["fast_ma"] == cfg["strategy"]["fast_ma"]  # 不污染已保存设置
    assert A.effective_cfg(eff) is eff
    st = A.status(on)
    assert st["active_params"]["fast_ma"] == 30 and st["last_adaptation"]["time"]
    assert not A.due(on)  # 刚调过参，未到期


def test_hot_reload_param_change_logged_and_positions_kept():
    from qtw import engine as E
    H._snap.update(params=None, mtimes={})
    H.check_once(kick=False)  # 基线快照
    bk = E.book(S.load())
    bk.open(symbol="BTCUSDT", market="perp", side="long", qty=0.01, price=50000.0, price_kind="mark", stop=48000.0,
            signal_bar="2026-11-20T00:00:00+00:00", reason="test", venue="okx")
    S.update({"strategy": {"fast_ma": 40, "atr_stop_mult": 2.5}})
    out = H.check_once(kick=False)
    keys = {r[0] for r in out["param_changes"]}
    assert {"strategy.fast_ma", "strategy.atr_stop_mult"} <= keys
    assert any(c["source"] == "settings" for c in A.recent_changes(5))
    p = E.book().positions.get("BTCUSDT")
    assert p is not None and p.stop_price == 48000.0  # 持仓与原止损保留
    assert H.check_once(kick=False)["param_changes"] == []  # 无变化不重复记录
    bk.close("BTCUSDT", 50000.0, "mark", "test", "okx")
    S.update({"strategy": {"fast_ma": S.DEFAULTS["strategy"]["fast_ma"], "atr_stop_mult": S.DEFAULTS["strategy"]["atr_stop_mult"]}})


def test_reload_module_success_rebind_and_fallback(tmp_path, monkeypatch):
    pkg = tmp_path / "qtwtmp_mods"
    pkg.mkdir()
    a = pkg / "qtwtmp_a.py"
    a.write_text("def f():\n    return 1\n", encoding="utf-8")
    (pkg / "qtwtmp_b.py").write_text("from qtwtmp_a import f\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(pkg))
    ma = importlib.import_module("qtwtmp_a")
    mb = importlib.import_module("qtwtmp_b")
    assert mb.f() == 1
    time.sleep(0.01)
    a.write_text("def f():\n    return 2\n", encoding="utf-8")
    r = H.reload_module("qtwtmp_a")
    assert r["ok"] and ma.f() == 2 and mb.f() == 2 and r["rebound"] >= 1  # 依赖模块里的旧绑定也换成新函数
    a.write_text("def f(:\n    return 3\n", encoding="utf-8")
    r = H.reload_module("qtwtmp_a")
    assert not r["ok"] and "语法错误" in r["error"] and ma.f() == 2  # 语法错误：继续用上一版
    a.write_text("def f():\n    return 4\nraise RuntimeError('boom')\n", encoding="utf-8")
    r = H.reload_module("qtwtmp_a")
    assert not r["ok"] and ma.f() == 2 and sys.modules["qtwtmp_a"] is ma  # 执行出错：回退上一版
    for m in ("qtwtmp_a", "qtwtmp_b"):
        sys.modules.pop(m, None)


def test_reload_strategy_module_keeps_working():
    from qtw import engine as E
    from qtw import strategy
    old = E.indicators
    r = H.reload_module("qtw.strategy")
    assert r["ok"]
    assert E.indicators is strategy.indicators and E.indicators is not old  # 引擎拿到新函数
    ind = E.indicators(synth(300, seed=2), 10, 30, 14)
    assert "signal" in ind


def test_api_adaptive_endpoint():
    from fastapi.testclient import TestClient
    from qtw.app import app
    with TestClient(app) as c:
        r = c.get("/api/adaptive")
        assert r.status_code == 200
        j = r.json()
        body = j.get("data", j)
        assert "active_params" in body and "hot_reload" in body and "last_adaptation" in body
        assert c.post("/api/adaptive/retune").status_code in (200, 400)
