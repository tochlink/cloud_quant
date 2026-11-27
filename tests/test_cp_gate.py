"""H.15 商业票据融资利差闸门（可选，默认关）：公式与研究同口径、known 无前视、失败开放、只拦新开多、回测与引擎同一函数、设置校验、FRED 解析。"""
import numpy as np
import pandas as pd
import pytest

from qtw import cp_gate as C
from qtw import settings as S

D = 86_400_000


def _obs(n=200, start="2024-01-01", path=None):
    d = pd.bdate_range(start, periods=n, tz="UTC")
    v = 0.15 + 0.05 * np.sin(np.arange(n) / 7.0) if path is None else path(n)
    return d.as_unit("ms").asi8, np.asarray(v, float)


def test_diff_matches_pandas_research_flag():
    ob, vs = _obs(300)
    x, ma, df = C.x_diff(vs, 60, 5)
    s = pd.Series(vs)
    xr = s.rolling(5).mean()
    v = xr.dropna()
    mr = v.rolling(60).mean().reindex(xr.index)
    m = ~np.isnan(mr.to_numpy())
    assert np.array_equal(m, ~np.isnan(ma)) and np.allclose(ma[m], mr.to_numpy()[m], atol=1e-10)
    assert np.array_equal(df[m] > 0, (xr > mr).to_numpy()[m])


def test_known_is_next_business_day_plus_one():
    fri = int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000)
    wed = int(pd.Timestamp("2026-11-18", tz="UTC").value // 1_000_000)
    k = C.known_ms([wed, fri])
    assert k[0] == int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000)  # 周三 → 周四发布 → 周五 00:00
    assert k[1] == int(pd.Timestamp("2026-11-24", tz="UTC").value // 1_000_000)  # 周五 → 周一发布 → 周二 00:00


def test_no_lookahead_and_blocks_long_when_stress_rises():
    ob, vs = _obs(160, path=lambda n: np.where(np.arange(n) < 100, 0.10, 0.40))  # 第 100 个观测起利差跳升
    st = {"cp_gate_enabled": True}
    known = int(C.known_ms([ob[100]])[0])
    bl, d = C.block_mask(st, [known - 1, known + 3 * D], ob, vs)
    assert not bl[0]  # 公布前 1 毫秒看不到
    assert bl[1] and d[1] > 0


def test_fail_open_when_stale_short_empty_or_disabled():
    ob, vs = _obs(200, path=lambda n: 0.1 + 0.002 * np.arange(n))  # 单调上升 → 应拦多
    st = {"cp_gate_enabled": True, "cp_gate_stale_days": 10}
    k = int(C.known_ms([ob[-1]])[0])
    bl, d = C.block_mask(st, [k], ob, vs)
    assert bl[0] and d[0] > 0
    bl, d = C.block_mask(st, [k + 30 * D], ob, vs)
    assert not bl[0] and np.isnan(d[0])
    bl, d = C.block_mask(st, [int(C.known_ms([ob[10]])[0])], ob, vs)  # 历史不足
    assert not bl[0] and np.isnan(d[0])
    bl, d = C.block_mask(st, [k], np.zeros(0, "int64"), np.zeros(0))
    assert not bl[0]
    bl, d = C.block_mask({}, [k], ob, vs)
    assert not bl.any() and np.isnan(d).all()


def test_state_fail_open_without_data(monkeypatch):
    monkeypatch.setattr(C, "series", lambda force=False, fetch=True: (np.zeros(0, "int64"), np.zeros(0)))
    out = C.state({"cp_gate_enabled": True}, int(pd.Timestamp("2026-11-20", tz="UTC").value // 1_000_000))
    assert out["blocked"] is False and out["fail_open"]


def test_state_reports_latest_known_observation(monkeypatch):
    ob, vs = _obs(200, path=lambda n: 0.1 + 0.002 * np.arange(n))
    monkeypatch.setattr(C, "series", lambda force=False, fetch=True: (ob, vs))
    out = C.state({"cp_gate_enabled": True}, int(C.known_ms([ob[150]])[0]))
    assert out["blocked"] is True and out["spread"] == vs[150] and out["diff"] > 0
    assert out["obs_date"] == str(pd.Timestamp(ob[150], unit="ms").date())


def test_parse_fred_and_spread_drop_missing():
    a = C.parse_fred("observation_date,DCPF3M\n2026-11-20,4.41\n2026-11-21,\n2026-11-23,4.37\n")
    b = C.parse_fred("observation_date,DTB3\n2026-11-20,4.20\n2026-11-23,.\n2026-11-24,4.18\n")
    assert len(a) == 2 and len(b) == 2
    sp = C.spread_from(a, b)
    assert list(sp.values()) == [0.21]


def test_settings_defaults_off_and_validation():
    c = S.validate(S._merge(S.DEFAULTS, {}))
    assert c["strategy"]["cp_gate_enabled"] is False and c["strategy"]["cp_gate_n"] == 60
    with pytest.raises(ValueError):
        S.validate(S._merge(S.DEFAULTS, {"strategy": {"cp_gate_n": 3}}))
    with pytest.raises(ValueError):
        S.validate(S._merge(S.DEFAULTS, {"strategy": {"cp_gate_stale_days": 1}}))
