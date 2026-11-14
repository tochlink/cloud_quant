"""可选体制线来源币种（btc_regime_symbol，默认 BTCUSDT）：默认逐位不变、ETH 来源等价于把 ETH 序列当作体制序列、引擎 / 取数用同一币种。
synth() 为测试专用确定性序列（见 test_backtest.py 说明）。"""
import pandas as pd
import pytest

from qtw import backtest as B
from qtw import engine as E
from qtw import settings as S
from tests.test_backtest import synth


def _data():
    spot = {"BTCUSDT": synth(900, seed=11), "ETHUSDT": synth(900, seed=5), "S1USDT": synth(900, seed=1)}
    perp = {k: synth(900, seed={"BTCUSDT": 11, "ETHUSDT": 5, "S1USDT": 1}[k], scale=1.01) for k in spot}
    return {"spot": spot, "perp": perp}


def _cfg(**kw):
    c = S._merge(S.DEFAULTS, {"symbols": ["BTCUSDT", "ETHUSDT", "S1USDT"]})
    c["strategy"].update(fast_ma=10, slow_ma=30, trend_ma=0, btc_regime_ma=200, **kw)
    return c


def test_defaults_and_validation():
    assert S.DEFAULTS["strategy"]["btc_regime_symbol"] == "BTCUSDT"
    c = _cfg(btc_regime_symbol="ethusdt"); S.validate(c)
    assert c["strategy"]["btc_regime_symbol"] == "ETHUSDT"
    with pytest.raises(ValueError):
        S.validate(_cfg(btc_regime_symbol="DOGEUSDT"))


def test_default_bit_identical_and_eth_uses_eth_series():
    d = _data()
    a = B.run_backtest(d, _cfg())
    b = B.run_backtest(d, _cfg(btc_regime_symbol="BTCUSDT"))
    assert a["equity"]["equity"].tolist() == b["equity"]["equity"].tolist()
    assert a["summary"]["btc_regime_symbol"] == "BTCUSDT"
    e = B.run_backtest(d, _cfg(btc_regime_symbol="ETHUSDT"))
    assert e["summary"]["btc_regime_symbol"] == "ETHUSDT" and e["summary"]["btc_regime_source"] == "symbols"
    # 等价性：把 ETH 现货放进 btc_spot、币池里去掉 BTC 现货影响（体制只看 btc_spot）→ 体制序列相同
    seen = []
    orig = B.btc_regime_blocks_long
    def spy(close, n, vote_k=0):
        seen.append(close.to_numpy().copy()); return orig(close, n, vote_k)
    B.btc_regime_blocks_long = spy
    try:
        B.run_backtest(d, _cfg(btc_regime_symbol="ETHUSDT"))
    finally:
        B.btc_regime_blocks_long = orig
    assert (seen[-1] == d["spot"]["ETHUSDT"].sort_values("open_time")["close"].to_numpy()).all()


def test_btc_spot_for_regime_and_engine_fetch_symbol(monkeypatch):
    df = synth(1400, seed=7)
    seen = []

    def fake(venue, sym, interval, limit, market):
        seen.append(sym)
        return df.tail(limit).reset_index(drop=True)
    from qtw.market import cache as mcache
    monkeypatch.setattr(mcache, "candles", fake)
    monkeypatch.setattr(E.mcache, "candles", fake)
    c = S._merge(S.DEFAULTS, {}); c["strategy"]["btc_regime_symbol"] = "ETHUSDT"
    data = {"spot": {"S1USDT": df}, "perp": {"S1USDT": df}}
    got, err = B.btc_spot_for_regime(c, data, 1300)
    assert err == "" and got is not None and seen[-1] == "ETHUSDT"
    # 币池里已有 ETH 现货时不另取
    assert B.btc_spot_for_regime(c, {"spot": {"ETHUSDT": df}}, 1300) == (None, "")
    r = E._btc_regime_state(c)
    assert seen[-1] == "ETHUSDT" and r["symbol"] == "ETHUSDT"
    c["strategy"]["btc_regime_symbol"] = "BTCUSDT"
    assert E._btc_regime_state(c)["symbol"] == "BTCUSDT" and seen[-1] == "BTCUSDT"


def test_strategy12_overrides_only_regime_symbol():
    from qtw import shadow
    from qtw import strategies as R
    cfg = S.load()
    c = R.strategy_cfg(cfg, "ma_trend_regime_eth")
    assert R.BY_ID["ma_trend_regime_eth"]["no"] == 12 and R.BY_ID["ma_trend_regime_eth"]["signal"] is None
    st = c["strategy"]
    assert st["btc_regime_symbol"] == "ETHUSDT"
    for k in ("fast_ma", "slow_ma", "trend_ma", "btc_regime_ma", "btc_regime_vote_k", "confirm_bars", "atr_stop_mult", "port_vol_target"):
        assert st[k] == cfg["strategy"][k]
    assert c["risk"] == cfg["risk"]
    S.validate(c)
    assert "ma_trend_regime_eth" not in shadow.active_ids()
    assert R.VERDICTS["ma_trend_regime_eth"]["status"] == "观察"
