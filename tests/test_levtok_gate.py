"""Gate BTC 杠杆代币多空成交额比闸门（可选，默认关）：7 日求和 + 90 日均线与研究同口径、日 + 28h 无前视、失败开放、
contra_both（flag=1 拦新开空、flag=0 拦新开多）、回测与引擎同一函数、设置校验、Gate K 线解析（只用已收盘日）。"""
import numpy as np
import pandas as pd
import pytest

from qtw import settings as S
from qtw import levtok_gate as G

D = 86_400_000
H = 3_600_000


def _days(n=300, start="2025-01-01", lpath=None, spath=None):
    d = pd.date_range(start, periods=n, freq="1D", tz="UTC").as_unit("ms").asi8
    i = np.arange(n)
    lv = 1e6 * (1.5 + np.sin(i / 9.0)) if lpath is None else lpath(i)
    sv = 1e6 * (1.5 + np.cos(i / 13.0)) if spath is None else spath(i)
    return d, np.asarray(lv, float), np.asarray(sv, float)


def test_flag_matches_pandas_research_formula():
    ks, lv, sv = _days(400)
    lv[50] = 0.0  # 零成交日 → 缺失（研究 df.replace(0, NaN)）
    grid, x, ma, f = G.flag_series(ks, lv, sv, 7, 90)
    L = pd.Series(lv).replace(0, np.nan)
    Sx = pd.Series(sv).replace(0, np.nan)
    px = np.log(L.rolling(7, min_periods=7).sum() / Sx.rolling(7, min_periods=7).sum())
    pm = px.rolling(90, min_periods=90).mean()
    pf = (px > pm).astype(float)
    pf[pm.isna() | px.isna()] = np.nan
    assert np.array_equal(grid, ks)
    assert np.array_equal(np.isfinite(x), px.notna().to_numpy())
    assert np.allclose(x[np.isfinite(x)], px.dropna().to_numpy())
    m = pf.notna().to_numpy()
    assert np.array_equal(m, np.isfinite(f))
    assert np.allclose(ma[m], pm.to_numpy()[m])
    assert np.array_equal(f[m], pf.to_numpy()[m])


def test_missing_calendar_day_is_not_skipped():
    ks, lv, sv = _days(200)
    keep = np.ones(ks.size, bool); keep[150] = False  # 缺一天：按日历展开，窗口含缺日 → NaN
    grid, x, ma, f = G.flag_series(ks[keep], lv[keep], sv[keep], 7, 90)
    assert grid.size == 200 and np.isnan(x[150:157]).all() and np.isfinite(x[157])
    assert np.isnan(f[150:157 + 89]).all()


def test_known_after_lag_no_lookahead():
    # 前 200 天 3L 与 3S 相同（x=0，flag 0），第 200 天起 3L 成交额暴增 → x 上升 > 均线 → flag 1
    ks, lv, sv = _days(230, lpath=lambda i: np.where(i < 200, 1e6, 5e6), spath=lambda i: np.full(i.shape, 1e6))
    st = {"levtok_gate_enabled": True}
    known = ks[200] + 28 * H
    bl, bs, f = G.block_mask(st, [known - 1, known], ks, lv, sv)
    assert f[0] == 0.0 and f[1] == 1.0  # 公布前 1 毫秒只看到前一日（等于均线 → 0）
    assert bl[0] and not bs[0] and bs[1] and not bl[1]  # flag 0 拦多、flag 1 拦空


def test_fail_open_when_stale_short_empty_or_disabled():
    ks, lv, sv = _days(300)
    st = {"levtok_gate_enabled": True, "levtok_gate_stale_days": 3}
    bl, bs, f = G.block_mask(st, [ks[-1] + 28 * H], ks, lv, sv)
    assert np.isfinite(f[0]) and (bl[0] or bs[0])
    bl, bs, f = G.block_mask(st, [ks[-1] + 28 * H + 4 * D], ks, lv, sv)  # 过旧 > 3 天
    assert not bl[0] and not bs[0] and np.isnan(f[0])
    bl, bs, f = G.block_mask(st, [ks[50] + 28 * H], ks, lv, sv)  # 历史不足 7 + 90 天
    assert not bl[0] and not bs[0] and np.isnan(f[0])
    bl, bs, f = G.block_mask(st, [ks[0]], ks, lv, sv)
    assert not bl[0] and not bs[0]
    bl, bs, f = G.block_mask(st, [ks[-1]], np.zeros(0, "int64"), np.zeros(0), np.zeros(0))
    assert not bl[0] and not bs[0]
    bl, bs, f = G.block_mask({}, [ks[-1] + 28 * H], ks, lv, sv)
    assert not bl.any() and not bs.any() and np.isnan(f).all()


def test_state_fail_open_and_reports(monkeypatch):
    e = np.zeros(0)
    monkeypatch.setattr(G, "series", lambda force=False, fetch=True: (np.zeros(0, "int64"), e, e))
    out = G.state({"levtok_gate_enabled": True}, int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000))
    assert out["block_long"] is False and out["block_short"] is False and out["fail_open"]
    ks, lv, sv = _days(300, lpath=lambda i: 1e6 * (1 + i / 50.0), spath=lambda i: np.full(i.shape, 1e6))  # 3L 单调上升 → flag 1 → 拦空
    monkeypatch.setattr(G, "series", lambda force=False, fetch=True: (ks, lv, sv))
    out = G.state({"levtok_gate_enabled": True}, int(ks[250] + 28 * H))
    assert out["block_short"] is True and out["block_long"] is False and out["flag"] == 1
    assert out["day"] == str(pd.Timestamp(ks[250], unit="ms").date()) and out["x"] is not None and out["x"] > out["ma"]


def test_parse_candles_only_closed_days():
    now = int(pd.Timestamp("2026-11-28 01:00", tz="UTC").value // 1_000_000)
    rows = [["1795651200", "1000.5", "1", "1", "1", "1", "5", "true"],   # 2026-11-26
            ["1795737600", "2000", "1", "1", "1", "1", "5", "true"],     # 2026-11-27（00:00 已收盘）
            ["1795824000", "30", "1", "1", "1", "1", "5", "false"],      # 2026-11-28 未收盘
            ["bad"]]
    d = G.parse_candles(rows, now_ms=now)
    assert d == {1795651200000: 1000.5, 1795737600000: 2000.0}


def test_settings_defaults_validation_and_env(monkeypatch):
    st = S.validate(S._merge(S.DEFAULTS, {}))["strategy"]
    assert st["levtok_gate_enabled"] is False and S.DEFAULTS["strategy"]["levtok_gate_enabled"] is False
    assert (st["levtok_gate_sum_n"], st["levtok_gate_trend_n"], st["levtok_gate_stale_days"]) == (7, 90, 3.0)
    for k, v in (("levtok_gate_trend_n", 1), ("levtok_gate_trend_n", 999), ("levtok_gate_sum_n", 99), ("levtok_gate_stale_days", 1)):
        with pytest.raises(ValueError):
            S.validate(S._merge(S.DEFAULTS, {"strategy": {k: v}}))
    monkeypatch.setenv("QTW_LEVTOK_GATE", "1")
    assert S.load()["strategy"]["levtok_gate_enabled"] is True
