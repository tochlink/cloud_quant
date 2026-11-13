"""指标页（qtw.ta）：无前视、数值口径、投票 / 证据分范围、卡片文字、合约数据缺失时跳过、接口参数校验、不接入下单。"""
import re

import numpy as np
import pandas as pd
import pytest

from qtw import ta


def _df(n=400, drift=0.002, seed=1, start="2026-01-01", freq="4h"):
    rng = np.random.default_rng(seed)
    r = drift + rng.normal(0, 0.01, n)
    c = 100 * np.exp(np.cumsum(r))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.004, n))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, 0.004, n))
    v = rng.uniform(50, 150, n)
    t = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"open_time": t, "open": o, "high": h, "low": lo, "close": c, "volume": v})


def test_no_lookahead_every_column_and_score():
    df = _df(360, drift=0.0, seed=7)
    full = ta.compute(df, "4h")
    full_sc = ta.score_series(full)
    for k in (200, 260, 359):
        part = ta.compute(df.iloc[:k].copy(), "4h")
        for col in ta.SERIES_COLS:
            if col == "score":
                continue
            a, b = part[col].to_numpy(dtype=float), full[col].iloc[:k].to_numpy(dtype=float)
            assert np.allclose(a, b, equal_nan=True, rtol=1e-9, atol=1e-9), col
        assert np.allclose(ta.score_series(part).to_numpy(), full_sc.iloc[:k].to_numpy(), atol=1e-12)


def test_basic_values():
    df = _df(300)
    ind = ta.compute(df, "4h")
    assert ind["sma50"].iloc[-1] == pytest.approx(df["close"].tail(50).mean())
    assert ind["sma50"].iloc[:49].isna().all() and ind["sma150"].iloc[:149].isna().all()
    up = df.copy()
    up["close"] = np.linspace(100, 200, len(up)); up["open"] = up["close"] - 0.1
    up["high"] = up["close"] + 0.2; up["low"] = up["open"] - 0.2
    iu = ta.compute(up, "4h")
    assert iu["rsi14"].iloc[-1] == pytest.approx(100.0)
    assert iu["st_dir"].iloc[-1] == 1
    # 唐奇安用之前 n 根：单调上涨时收盘始终高于「前 20 根最高」
    assert (iu["close"].iloc[30:] > iu["dc20_hi"].iloc[30:]).all()
    assert ((ind["bb_up"] >= ind["bb_lo"]) | ind["bb_up"].isna()).all()
    assert ind["kdj_k"].dropna().between(0, 100).all()
    assert ind["mfi14"].dropna().between(0, 100).all() and ind["wr14"].dropna().between(-100, 0).all()


def test_vwap_resets_each_utc_day_and_skipped_on_daily():
    df = _df(48, freq="1h", start="2026-03-01")
    ind = ta.compute(df, "1h")
    tp = (df["high"] + df["low"] + df["close"]) / 3
    assert ind["vwap"].iloc[24] == pytest.approx(tp.iloc[24])  # 新的一天第一根 = 该根典型价
    assert ta.compute(_df(200, freq="1D"), "1d")["vwap"].isna().all()


def test_ichimoku_cloud_is_shifted_forward_not_back():
    df = _df(200)
    ind = ta.compute(df, "4h")
    h, lo = df["high"], df["low"]
    tk = (h.rolling(9).max() + lo.rolling(9).min()) / 2
    kj = (h.rolling(26).max() + lo.rolling(26).min()) / 2
    assert ind["ich_span_a"].iloc[150] == pytest.approx(((tk + kj) / 2).iloc[124])


def test_votes_and_score_ranges_and_trend_direction():
    upi = ta.compute(_df(400, drift=0.004, seed=3), "4h")
    dni = ta.compute(_df(400, drift=-0.004, seed=3), "4h")
    for ind in (upi, dni):
        V = ta.votes(ind)
        assert set(np.unique(V.to_numpy())) <= {-1, 0, 1}
        sc = ta.score_series(ind, V)
        assert sc.between(-1, 1).all()
    assert ta.score_series(upi).iloc[-1] >= ta.BULL_TH
    assert ta.score_series(dni).iloc[-1] <= -ta.BULL_TH
    assert ta.label(0.3) == "偏多" and ta.label(-0.3) == "偏空" and ta.label(0.1) == "中性"


def test_cards_have_chinese_tags_and_reasons():
    ind = ta.compute(_df(400), "4h")
    cs = ta.cards(ind)
    assert [c["key"] for c in cs] == [k for k, *_ in ta.SPECS]
    for c in cs:
        assert c["tag"] in ("偏多", "偏空", "中性") and c["reason"]
        if c["context_only"]:
            assert c["tag"] == "中性" and c["weight"] == 0
    sm = ta.summarize(cs)
    assert sm["bull"] + sm["bear"] + sm["neutral"] == sm["n"]
    assert -1 <= sm["score"] <= 1
    # 数据不足：只给「算不出来」，不编值
    short = ta.cards(ta.compute(_df(30), "4h"))
    assert next(c for c in short if c["key"] == "ma_cross")["available"] is False


def test_deriv_cards_skip_gracefully_and_thresholds():
    miss = ta.deriv_cards({"error": "HTTP 451"}, None)
    assert all(not c["available"] and c["vote"] == 0 for c in miss)
    hot = ta.deriv_cards({"funding_rate": 0.001, "oi_usd": 110.0, "oi_usd_24h_ago": 100.0}, -0.02)
    f, oi = hot
    assert f["tag"] == "偏空" and oi["tag"] == "偏空"
    calm = ta.deriv_cards({"funding_rate": 0.0001, "oi_usd": 101.0, "oi_usd_24h_ago": 100.0}, 0.05)
    assert calm[0]["tag"] == "中性" and calm[1]["tag"] == "中性"


def test_derivatives_error_is_reported_not_faked(monkeypatch):
    ta._DERIV_CACHE.clear()
    monkeypatch.setattr(ta, "_gate_deriv", lambda s: (_ for _ in ()).throw(RuntimeError("blocked")))
    d = ta.derivatives("gate", "BTCUSDT")
    assert "error" in d and "funding_rate" not in d
    ta._DERIV_CACHE.clear()


def test_btc_regime_card():
    assert ta.btc_regime_card(None)["available"] is False
    b = _df(1300, drift=0.001)
    assert ta.btc_regime_card(b)["tag"] == "偏多"


def test_trading_code_never_imports_ta():
    """证据分只作参考：engine / backtest / paper / worker / strategy 不得引用 qtw.ta。"""
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1] / "qtw"
    for name in ("engine.py", "backtest.py", "paper.py", "worker.py", "strategy.py", "realtime.py", "risk.py", "rebalance.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert not re.search(r"from \.\s+import[^\n]*\bta\b|from \.ta\b|qtw\.ta\b|from qtw import[^\n]*\bta\b", src), name


def test_api_indicators_payload_and_validation(monkeypatch):
    from fastapi.testclient import TestClient
    from qtw import app as qapp
    df = _df(560)
    df["close_time"] = df["open_time"] + pd.Timedelta(hours=4)
    monkeypatch.setattr(qapp, "_ind_frame", lambda v, sym, iv, bars, market: df.tail(bars).reset_index(drop=True).assign(partial=False))
    monkeypatch.setattr(qapp.mcache, "candles", lambda *a, **k: df.tail(30).reset_index(drop=True))
    monkeypatch.setattr("qtw.ta.derivatives", lambda v, s: {"error": "offline"})
    c = TestClient(qapp.app)
    r = c.get("/api/indicators?symbol=BTCUSDT&venue=gate&market=perp&interval=4h&bars=300")
    assert r.status_code == 200
    d = r.json()
    assert len(d["candles"]) == 300 and len(d["times"]) == 300
    assert all(len(v) == 300 for v in d["series"].values())
    keys = [x["key"] for x in d["cards"]]
    assert "funding" in keys and "oi" in keys and "btc_regime" in keys
    assert d["summary"]["label"] in ("偏多", "偏空", "中性") and "参考证据" in d["note"]
    assert c.get("/api/indicators?symbol=FOOUSDT").status_code == 400
    assert c.get("/api/indicators?symbol=BTCUSDT&interval=15m").status_code == 400
    assert c.get("/api/indicators?symbol=BTCUSDT&venue=binance").status_code == 400
    m = c.get("/api/indicators/matrix?symbol=ETHUSDT&venue=okx&market=spot").json()
    assert [x["interval"] for x in m["rows"]] == ["1m", "5m", "10m", "1h", "4h", "1d"]
    assert {x["book"] for x in m["rows"]} == {"短线", "长线"}


def test_sse_payload_has_other_venue_forming(monkeypatch):
    from qtw import app as qapp
    monkeypatch.setattr(qapp.stream, "status", lambda venue=None: {"connections": []})
    monkeypatch.setattr(qapp.stream, "snapshot", lambda venue: {"prices": {}, "forming": {f"1m:BTCUSDT:spot": {"venue": venue}}})
    p = qapp._live_payload()
    assert p["forming_alt"]["venue"] in ("gate", "okx") and p["forming_alt"]["venue"] != p["venue"]
    assert p["forming_alt"]["forming"]["1m:BTCUSDT:spot"]["venue"] == p["forming_alt"]["venue"]
