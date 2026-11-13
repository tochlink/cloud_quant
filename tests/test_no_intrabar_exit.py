"""kean 11-14 本地账本回归：长线单不能在 4h 收盘之间被 5m 快速离场平掉；手动平仓 / 一键清仓后不能按同一旧信号立刻开回去。
合成数据仅用于测试。"""
import numpy as np
import pandas as pd
import pytest

from qtw import engine, settings as S
from tests.test_signal_cycle import _cfg, _drive, _row, bk  # noqa: F401  (fixture)


def test_saved_fast_exit_is_ignored():
    S.update({"strategy": {"fast_exit_tf": "5m"}})
    assert S.load()["strategy"]["fast_exit_tf"] == "off"
    raw = S.load()
    raw["strategy"]["fast_exit_tf"] = "5m"
    S._write_db(raw)  # 旧版页面直接存进库的值
    assert S.load()["strategy"]["fast_exit_tf"] == "off"


def test_engine_never_fast_exits_even_if_cfg_says_5m(bk, monkeypatch):  # noqa: F811
    c = _cfg(band=0)
    st = {"row": _row(-1, "2026-11-13T12:00:00Z"), "px": 100.0}
    routed = _drive(monkeypatch, st)
    engine.run_cycle(c)
    assert bk.positions["XUSDT"].side == "short"
    # 5m 收盘价一路在 EMA 上方（逆空头）：旧逻辑会在下一轮「快速离场」
    n = 300
    t = pd.date_range("2026-11-13T00:00Z", periods=n, freq="5min")
    df = pd.DataFrame({"open_time": t, "close_time": t + pd.Timedelta(minutes=5) + pd.Timedelta(days=30),
                       "open": 100.0, "high": 101.0, "low": 99.0, "close": np.linspace(90, 101, n), "volume": 1.0})
    monkeypatch.setattr(engine, "fast_frame", lambda *a, **k: df)
    c["strategy"].update(fast_exit_tf="5m", fast_exit_n=50, fast_exit_confirm=2)
    st["px"] = 100.8  # 逆向但远没到 2×ATR 止损（100 + 2×2 = 104）
    engine.run_cycle(c)
    assert "XUSDT" in bk.positions
    assert [a for _, _, a, _ in routed] == ["open_short"]
    assert not any(f["reason"] == "快速离场" for f in bk.fills())


def test_intrabar_only_genuine_stop_closes(bk, monkeypatch):  # noqa: F811
    c = _cfg(band=0)
    st = {"row": _row(-1, "2026-11-13T12:00:00Z"), "px": 100.0}
    _drive(monkeypatch, st)
    engine.run_cycle(c)
    stop = bk.positions["XUSDT"].stop_price
    assert stop == pytest.approx(104.0)
    for px in (101.0, 103.9):
        st["px"] = px
        engine.run_cycle(c)
        assert "XUSDT" in bk.positions
    st["px"] = 104.2
    engine.run_cycle(c)
    assert "XUSDT" not in bk.positions and bk.fills()[-1]["reason"] == "ATR止损"


@pytest.mark.parametrize("how", ["flatten", "close"])
def test_manual_close_does_not_reopen_on_same_signal(bk, monkeypatch, how):  # noqa: F811
    c = _cfg(band=0)
    st = {"row": _row(-1, "2026-11-13T12:00:00Z"), "px": 100.0}
    routed = _drive(monkeypatch, st)
    engine.run_cycle(c)
    st["row"] = {**_row(-1, "2026-11-13T12:00:00Z"), "prev_run_close": "2026-11-01T00:00:00Z"}
    out = engine.flatten_all(c) if how == "flatten" else engine.close_position("XUSDT", c)
    assert out["ok"] and "XUSDT" not in bk.positions
    reason = bk.fills()[-1]["reason"]
    assert reason == ("一键清仓" if how == "flatten" else "手动平仓")
    engine.run_cycle(c)  # 同一旧信号：不再同一分钟按市价开回去
    assert "XUSDT" not in bk.positions
    assert [a for _, _, a, _ in routed] == ["open_short", "close_short"]
    # 信号改变（转空仓）→ 解锁；之后新的做空信号才会入场
    st["row"] = _row(0, "2026-11-13T16:00:00Z")
    engine.run_cycle(c)
    st["row"] = {**_row(-1, "2026-11-13T20:00:00Z"), "prev_run_close": "2026-11-13T20:00:00Z"}
    engine.run_cycle(c)
    assert bk.positions["XUSDT"].side == "short"
