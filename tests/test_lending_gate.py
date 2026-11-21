"""OKX USDT 借贷利率体制闸门（可选，默认关）：z 计算、无前视、失败开放、只拦新开多、回测与引擎同一函数。"""
import math

import numpy as np
import pandas as pd

from qtw import lending as L
from qtw import settings as S
from qtw.backtest import run_backtest

H = 3_600_000
T0 = 1_767_225_600_000  # 2026-01-01 00:00 UTC


def _rates(n, base=0.05, spike_at=None, spike=0.5):
    ts = T0 + np.arange(n, dtype="int64") * H
    rv = base + 0.001 * np.sin(np.arange(n) / 3.0)
    if spike_at is not None:
        rv = rv.copy()
        rv[spike_at:] = spike
    return ts, rv


def test_zscore_matches_manual_rolling():
    ts, rv = _rates(24 * 5)
    z = L.zscore_at(ts, ts, rv, window_days=1, stale_hours=6)
    i = 100
    w = rv[i - 23:i + 1]
    assert math.isclose(z[i], (rv[i] - w.mean()) / w.std(ddof=1), rel_tol=1e-9)
    # 不足 W·12 = 12 个点 → NaN
    assert np.isnan(z[:11]).all() and not np.isnan(z[11])


def test_zscore_matches_pandas_research_formula():
    ts, rv = _rates(24 * 70)
    rv = rv + np.linspace(0, 0.02, len(rv))
    s = pd.Series(rv, index=pd.to_datetime(ts, unit="ms", utc=True))
    ref = ((s - s.rolling(720, min_periods=360).mean()) / s.rolling(720, min_periods=360).std()).to_numpy()
    z = L.zscore_at(ts, ts, rv, 30, 6)
    m = ~np.isnan(ref)
    assert (np.isnan(z) == np.isnan(ref)).all()
    assert np.allclose(z[m], ref[m], atol=1e-6)


def test_no_lookahead():
    ts, rv = _rates(24 * 3)
    t = int(ts[50])
    z0 = L.zscore_at([t], ts[:51], rv[:51], 1, 6)[0]
    # 之后（ts > t）出现巨大利率尖峰不影响 z(t)
    rv2 = rv.copy()
    rv2[51:] = 9.9
    z1 = L.zscore_at([t], ts, rv2, 1, 6)[0]
    assert z0 == z1
    # t 落在两条之间（t + 30 分钟）：只用 ts ≤ t 的那条
    z2 = L.zscore_at([t + H // 2], ts, rv2, 1, 6)[0]
    assert z2 == z0
    # 尖峰那一小时开始才看得到
    assert L.zscore_at([int(ts[51])], ts, rv2, 1, 6)[0] > 3


def test_fail_open_empty_stale_and_fetch_error(monkeypatch, tmp_path):
    assert not L.blocks_long(L.zscore_at([T0], [], [], 30, 6), 1.0).any()
    ts, rv = _rates(24 * 3, spike_at=60)
    # 最新一条早于 t − 6h → NaN → 不拦
    late = int(ts[-1]) + 7 * H
    assert np.isnan(L.zscore_at([late], ts, rv, 1, 6)[0])
    assert L.zscore_at([int(ts[-1]) + 5 * H], ts, rv, 1, 6)[0] == L.zscore_at([int(ts[-1])], ts, rv, 1, 6)[0]
    assert not L.blocks_long([np.nan, np.nan], 1.0).any()
    assert L.blocks_long([1.01, 0.99, np.nan], 1.0).tolist() == [True, False, False]
    # 拉取失败：不抛异常、返回已有缓存（这里为空）、状态失败开放
    monkeypatch.setattr(L, "DATA_DIR", tmp_path)
    monkeypatch.setattr(L, "_MEM", {"t": 0.0, "rows": None, "err": "", "no_older": False})

    def boom(after):
        raise RuntimeError("offline")
    monkeypatch.setattr(L, "_get_page", boom)
    k, v = L.series()
    assert k.size == 0 and "offline" in L.last_error()
    st = {"lending_gate_enabled": True}
    s = L.state(st, T0)
    assert s["enabled"] and s["blocked"] is False and s["fail_open"]


def test_series_pagination_and_cache(monkeypatch, tmp_path):
    now = 1_795_287_600_000
    full = {now - k * H: 0.05 + 0.0001 * (k % 7) for k in range(24 * 50)}
    keys = sorted(full, reverse=True)

    def page(after):
        ks = [t for t in keys if after is None or t < after][:100]
        return [(t, full[t]) for t in ks]
    monkeypatch.setattr(L, "DATA_DIR", tmp_path)
    monkeypatch.setattr(L, "_MEM", {"t": 0.0, "rows": None, "err": "", "no_older": False})
    monkeypatch.setattr(L, "_get_page", page)
    monkeypatch.setattr(L.time, "sleep", lambda s: None)
    monkeypatch.setattr(L.time, "time", lambda: now / 1000 + 60)
    k, v = L.series()
    assert k[-1] == now and k[0] <= now - 30 * 24 * H  # ≥ 30 天
    assert np.all(np.diff(k) == H)
    assert (tmp_path / L.PATH_NAME).exists()
    # 再次读取（缓存）结果一致
    monkeypatch.setattr(L, "_MEM", {"t": now / 1000 + 60, "rows": None, "err": "", "no_older": False})
    k2, v2 = L.series()
    assert (k2 == k).all() and np.allclose(v2, v)


def test_default_off_validation_and_env(monkeypatch):
    st = S.DEFAULTS["strategy"]
    assert st["lending_gate_enabled"] is False
    assert (st["lending_gate_window_days"], st["lending_gate_z"], st["lending_gate_side"]) == (30, 1.0, "long")
    off, z = L.block_mask(st, [T0])
    assert not off.any()
    for k, v in (("lending_gate_window_days", 3), ("lending_gate_z", 0), ("lending_gate_side", "short")):
        cfg = S._merge(S.DEFAULTS, {})
        cfg["strategy"][k] = v
        try:
            S.validate(cfg)
            assert False, k
        except ValueError:
            pass
    assert S.load()["strategy"]["lending_gate_enabled"] is False
    monkeypatch.setenv("QTW_LENDING_GATE", "1")
    assert S.load()["strategy"]["lending_gate_enabled"] is True


def _frames(n=400):
    t = pd.date_range("2026-01-01", periods=n, freq="4h", tz="UTC")
    c = pd.Series(100 + np.sin(np.arange(n) / 9.0) * 0.5, dtype=float)
    df = pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(hours=4), "open": c, "high": c + 0.3,
                       "low": c - 0.3, "close": c, "volume": 1.0})
    return {"spot": {"ETHUSDT": df.copy()}, "perp": {"ETHUSDT": df.copy()}}, t


def _cfg(on):
    c = S._merge(S.DEFAULTS, {"symbols": ["ETHUSDT"]})
    c["strategy"].update(fast_ma=5, slow_ma=10, trend_ma=0, btc_regime_ma=0, port_vol_target=0, name_vol_target=0,
                         lending_gate_enabled=on, lending_gate_window_days=7)
    c["strategy"]["atr_stop_mult"] = 50.0  # 宽止损，避免止损干扰
    return c


def _sig(val, start):
    def f(ind, idx, syms):
        a = np.zeros(len(idx), dtype=int)
        a[start:] = val
        return {s: a for s in syms}
    return f


def _rates_on(t, spike_from=None, spike_to=None):
    n = int((t[-1] - t[0]) / pd.Timedelta(hours=1)) + 24 * 10
    ts = int(t[0].value // 1_000_000) - 24 * 10 * H + np.arange(n + 24 * 10, dtype="int64") * H
    rv = 0.05 + 0.001 * np.sin(np.arange(len(ts)) / 5.0)
    if spike_from is not None:
        a = int(t[spike_from].value // 1_000_000)
        b = int(t[spike_to].value // 1_000_000)
        rv = np.where((ts >= a) & (ts < b), 0.30, rv)
    return ts, rv


def test_backtest_gate_blocks_new_long_only():
    F, t = _frames()
    first_long = 200
    # ① 尖峰覆盖入场前后 → 新开多推迟到尖峰之后（z 回落）
    lr = _rates_on(t, 190, 220)
    off = run_backtest(F, _cfg(False), signals=_sig(1, first_long))
    on = run_backtest(F, _cfg(True), signals=_sig(1, first_long), lending_rates=lr)
    e_off = pd.Timestamp(off["trades"][0]["entry_time"]) if isinstance(off["trades"], list) else pd.Timestamp(off["trades"].iloc[0]["entry_time"])
    e_on = pd.Timestamp(on["trades"][0]["entry_time"]) if isinstance(on["trades"], list) else pd.Timestamp(on["trades"].iloc[0]["entry_time"])
    assert e_off == t[first_long + 1]
    assert e_on > t[first_long + 1]
    assert on["summary"]["lending_gate"]["blocked_bars"] > 0
    # ② 尖峰只出现在已持多之后 → 已有多单不被平掉，与关闭时逐笔相同
    lr2 = _rates_on(t, 260, 300)
    on2 = run_backtest(F, _cfg(True), signals=_sig(1, first_long), lending_rates=lr2)
    assert on2["summary"]["lending_gate"]["blocked_bars"] > 0
    assert len(on2["trades"]) == len(off["trades"])
    assert np.allclose(on2["equity"]["equity"].to_numpy(), off["equity"]["equity"].to_numpy())
    # ③ 空单不受影响
    s_off = run_backtest(F, _cfg(False), signals=_sig(-1, first_long))
    s_on = run_backtest(F, _cfg(True), signals=_sig(-1, first_long), lending_rates=lr)
    assert np.allclose(s_on["equity"]["equity"].to_numpy(), s_off["equity"]["equity"].to_numpy())
    # ④ 数据缺失（失败开放）→ 与关闭相同
    empty = (np.array([], dtype="int64"), np.array([], dtype=float))
    on3 = run_backtest(F, _cfg(True), signals=_sig(1, first_long), lending_rates=empty)
    assert np.allclose(on3["equity"]["equity"].to_numpy(), off["equity"]["equity"].to_numpy())


def test_engine_and_backtest_share_block_mask(monkeypatch):
    from qtw import engine
    ts, rv = _rates(24 * 10, spike_at=24 * 9)
    monkeypatch.setattr(L, "series", lambda start_ms=None, force=False, fetch=True: (ts, rv))
    st = {**S.DEFAULTS["strategy"], "lending_gate_enabled": True, "lending_gate_window_days": 7}
    t_open = int(ts[24 * 9 + 2])
    df = pd.DataFrame({"open_time": [pd.Timestamp(t_open, unit="ms", tz="UTC")]})
    g = engine._lending_gate_state({"strategy": st}, {"perp": {"ETHUSDT": df}})
    bl, z = L.block_mask(st, [t_open], ts, rv)
    assert g["blocked"] is True and bool(bl[0]) is True and math.isclose(g["z"], float(z[0]))
    assert g["rate"] == rv[24 * 9 + 2] and g["eval_open_ms"] == t_open
    off = engine._lending_gate_state({"strategy": S.DEFAULTS["strategy"]}, {})
    assert off == {"enabled": False, "blocked": False}
