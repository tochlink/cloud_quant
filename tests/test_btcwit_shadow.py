"""#18 btc_witness_mom_1h 影子：见证字节公式、z 与研究口径一致、入场 / 不重叠 / 离场（全部离线，不访问网络）。"""
import math
import random

import numpy as np
import pandas as pd

from qtw import btcwit_shadow as S

H = S.HOUR_MS
T0 = 1_790_000_000_000 // H * H


def _blocks(n_hours, share_fn, start_ms=T0):
    rows, h = [], 900_000
    for i in range(n_hours):
        for j in range(6):
            size = 1_500_000
            wit = share_fn(i) * size
            weight = 4 * size - 3 * wit          # 反解：witness = (4·size − weight)/3
            rows.append([h, (start_ms + i * H) // 1000 + j * 500, size, weight])
            h += 1
    return rows


def test_witness_bytes_matches_bip141():
    stripped, total = 1_000_000, 1_600_000
    weight = 3 * stripped + total
    assert S.witness_bytes(total, weight) == total - stripped


def test_burst_z_matches_research_pandas():
    rnd = random.Random(7)
    vals = [0.5 + 0.05 * rnd.random() for _ in range(400)]
    share = {T0 + i * H: v for i, v in enumerate(vals)}
    del share[T0 + 250 * H]                      # 无出块小时 = NaN（不补）
    idx = np.array([T0 + i * H for i in range(400)], dtype=np.int64)
    x = pd.Series([share.get(int(t), np.nan) for t in idx], index=idx)
    mu = x.rolling(S.W, min_periods=S.MIN_W).mean().shift(1)
    sd = x.rolling(S.W, min_periods=S.MIN_W).std().shift(1)
    ref = (x.rolling(S.L, min_periods=S.L).sum() - S.L * mu) / (sd * np.sqrt(S.L))
    for i in (200, 249, 254, 300, 399):
        z = S.burst_z(share, int(idx[i]))
        r = ref.iloc[i]
        if not np.isfinite(r):
            assert z is None
        else:
            assert math.isclose(z, r, rel_tol=1e-9, abs_tol=1e-9)


def _px(sym):
    return {"BTCUSDT": 100_000.0}.get(sym, 10.0)


def test_spike_opens_long_basket_then_exits_after_48h():
    b = S.new_book()
    n = 200
    b["blocks"] = _blocks(n, lambda i: 0.5 + (0.0005 * (i % 3)) + (0.2 if i >= n - 4 else 0.0))
    last_hour = T0 + (n - 1) * H
    now = last_hour + H + 150_000
    out = S.step_decide(b, now, _px)
    assert out["z"] is not None and out["z"] >= S.K
    assert sorted(b["positions"]) == sorted(S.COINS)
    assert all(p["side"] == "long" for p in b["positions"].values())
    gross = sum(p["notional"] for p in b["positions"].values())
    assert math.isclose(gross, S.START_EQ * S.GROSS, rel_tol=1e-9)
    # 同一小时不重复判定；持仓中再触发不加仓
    assert S.step_decide(b, now + 60_000, _px)["hour"] is None
    out2 = S.step_decide(b, now + H, _px)
    assert len(b["positions"]) == 8 and not out2["open"]
    assert S.step_exits(b, now + S.HOLD_MS - 1000, _px) == []
    rows = S.step_exits(b, now + S.HOLD_MS + 1000, lambda s: _px(s) * 1.01)
    assert len(rows) == 8 and not b["positions"]
    pnl = sum(t["pnl_usdt"] for t in b["trades"])
    exp = S.START_EQ * 0.01 - S.START_EQ * S.FEE_RATE * (1 + 1.01)
    assert math.isclose(pnl, exp, rel_tol=1e-6)
    assert math.isclose(S.equity(b), S.START_EQ + exp, rel_tol=1e-9)


def test_drop_opens_short_and_quiet_hour_does_nothing():
    b = S.new_book()
    n = 200
    b["blocks"] = _blocks(n, lambda i: 0.5 + 0.0005 * (i % 3) - (0.2 if i >= n - 4 else 0.0))
    S.step_decide(b, T0 + n * H + 150_000, _px)
    assert b["positions"] and all(p["side"] == "short" for p in b["positions"].values())
    q = S.new_book()
    q["blocks"] = _blocks(n, lambda i: 0.5 + 0.0005 * (i % 3))
    out = S.step_decide(q, T0 + n * H + 150_000, _px)
    assert out["z"] is not None and abs(out["z"]) < S.K and not q["positions"]


def test_late_or_early_decision_and_missing_data():
    b = S.new_book()
    b["blocks"] = _blocks(200, lambda i: 0.5)
    assert S.step_decide(b, T0 + 200 * H + 30_000, _px)["hour"] is None        # 整点后 2 分钟前不判定
    out = S.step_decide(b, T0 + 200 * H + (S.MAX_LATE_SEC + 60) * 1000, _px)  # 过晚：跳过、不补
    assert out["skip"] and not b["positions"]
    e = S.new_book()
    out = S.step_decide(e, T0 + 200 * H + 150_000, _px)
    assert out["z"] is None and not e["positions"]


def test_merge_blocks_trims_old_and_dedups():
    b = S.new_book()
    now = T0 + 500 * H
    old = [[1, (now - (S.KEEP_HOURS + 5) * H) // 1000, 1, 1]]
    S.merge_blocks(b, old + [[2, now // 1000 - 60, 10, 30], [2, now // 1000 - 60, 10, 30]], now)
    assert [r[0] for r in b["blocks"]] == [2]


def test_disabled_in_test_mode(monkeypatch):
    monkeypatch.setenv("QTW_SHADOW_BTCWIT", "1")
    assert S.enabled() is False and S.start() is False
