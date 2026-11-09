"""dual_ma_trend_4h_v1：SMA(快) vs SMA(慢)，只用已收盘 K 线，无前视。

第 t 根 K 线收盘后得到的信号，最早只能在第 t+1 根开盘（回测）或之后（纸面/实盘）执行。
  快线 > 慢线 → +1 做多 → 现货多头
  快线 < 慢线 → -1 做空 → USDT 永续空头（1 倍保证金）
  否则/数据不足 → 0 空仓
止损：入场价 ∓ atr_stop_mult × ATR(入场前一根收盘)。止损后保持空仓，直到信号方向改变。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def indicators(df: pd.DataFrame, fast: int, slow: int, atr_period: int) -> pd.DataFrame:
    out = df.copy()
    c = out["close"]
    out["sma_fast"] = c.rolling(fast, min_periods=fast).mean()
    out["sma_slow"] = c.rolling(slow, min_periods=slow).mean()
    prev = c.shift(1)
    tr = pd.concat([(out["high"] - out["low"]).abs(), (out["high"] - prev).abs(), (out["low"] - prev).abs()], axis=1).max(axis=1)
    out["atr"] = tr.rolling(atr_period, min_periods=atr_period).mean()
    sig = np.where(out["sma_fast"] > out["sma_slow"], 1, np.where(out["sma_fast"] < out["sma_slow"], -1, 0))
    sig = np.where(out["sma_fast"].isna() | out["sma_slow"].isna(), 0, sig)
    out["signal"] = sig.astype(int)
    return out


def side_of(sig: int) -> str:
    return {1: "long", -1: "short"}.get(int(sig), "flat")


def market_of(sig: int) -> str:
    return {1: "spot", -1: "perp"}.get(int(sig), "-")


def last_cross(ind: pd.DataFrame) -> pd.Timestamp | None:
    s = ind["signal"]
    ch = s.ne(s.shift(1)) & s.shift(1).notna()
    idx = ch[ch].index
    return ind.loc[idx[-1], "close_time"] if len(idx) else None
