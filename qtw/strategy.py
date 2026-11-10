"""dual_ma_trend_4h_v1：SMA(快) vs SMA(慢)，只用已收盘 K 线，无前视。

第 t 根 K 线收盘后得到的信号，最早只能在第 t+1 根开盘（回测）或之后（纸面/实盘）执行。
  快线 > 慢线 → +1 做多 → 现货多头
  快线 < 慢线 → -1 做空 → USDT 永续空头（1 倍保证金）
  否则/数据不足 → 0 空仓
信号确认：原始方向需在最近 confirm_bars 根已收盘 K 线上保持一致才生效，否则视为 0（空仓），过滤刚交叉就回头的假信号。
趋势过滤（trend_ma>0，仅作用于入场）：做多需上一根收盘 > 该市场 SMA(trend_ma)，做空需 < SMA(trend_ma)；
  已有持仓不因趋势过滤平仓，离场仍只看信号反转/归零与 ATR 止损。
止损：入场价 ∓ atr_stop_mult × ATR(入场前一根收盘)。止损后保持空仓，直到信号方向改变。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def indicators(df: pd.DataFrame, fast: int, slow: int, atr_period: int, confirm_bars: int = 1, trend_ma: int = 0) -> pd.DataFrame:
    out = df.copy()
    c = out["close"]
    out["trend_ma"] = c.rolling(int(trend_ma), min_periods=int(trend_ma)).mean() if trend_ma else np.nan
    out["sma_fast"] = c.rolling(fast, min_periods=fast).mean()
    out["sma_slow"] = c.rolling(slow, min_periods=slow).mean()
    prev = c.shift(1)
    tr = pd.concat([(out["high"] - out["low"]).abs(), (out["high"] - prev).abs(), (out["low"] - prev).abs()], axis=1).max(axis=1)
    out["atr"] = tr.rolling(atr_period, min_periods=atr_period).mean()
    sig = np.where(out["sma_fast"] > out["sma_slow"], 1, np.where(out["sma_fast"] < out["sma_slow"], -1, 0))
    sig = np.where(out["sma_fast"].isna() | out["sma_slow"].isna(), 0, sig)
    sig = pd.Series(sig, index=out.index).astype(int)
    raw = sig
    for j in range(1, max(1, int(confirm_bars))):
        sig = sig.where(raw.eq(raw.shift(j)), 0)
    out["signal"] = sig.astype(int)
    return out


def trend_ok(sig: int, close: float, tma: float, trend_ma: int) -> bool:
    """入场趋势闸门：关闭时恒为 True；趋势线尚未形成（NaN）时不允许新开仓。"""
    if not trend_ma or sig == 0:
        return True
    if not (tma == tma):
        return False
    return close > tma if sig > 0 else close < tma


def btc_regime_blocks_long(close, n: int):
    """BTC 熊市体制过滤（仅拦新开多单）：BTC 现货收盘 < SMA_n 时为 True。
    n = 0 关闭；SMA 尚未形成（历史不足 n 根）时为 False（不拦），与研究口径一致。
    调用方用「上一根已收盘 K 线」的值决定本根是否允许开多（因果）。"""
    c = pd.Series(close, dtype=float)
    if not n:
        return pd.Series(False, index=c.index)
    return (c < c.rolling(int(n)).mean()).fillna(False)


def port_vol_factor(equity, target: float, lookback: int, bars_per_year: float = 2190) -> float:
    """组合波动率目标（可选，默认关闭）：用最近 lookback 根已收盘权益的逐根收益算年化波动 σ，
    返回 k = min(1, target / σ)，调用方把单笔风险上限与单币权重上限都乘以 k（只缩不放）。
    target = 0 关闭；权益历史不足 lookback + 1 根、或 σ = 0 时返回 1（不缩）。"""
    if not target or lookback < 2:
        return 1.0
    q = np.asarray(equity, dtype=float)
    if len(q) < lookback + 1:
        return 1.0
    q = q[-(lookback + 1):]
    if (q <= 0).any():
        return 1.0
    sd = float(np.std(np.diff(q) / q[:-1]) * np.sqrt(bars_per_year))
    return min(1.0, float(target) / sd) if sd > 0 else 1.0


def side_of(sig: int) -> str:
    return {1: "long", -1: "short"}.get(int(sig), "flat")


def market_of(sig: int) -> str:
    return {1: "spot", -1: "perp"}.get(int(sig), "-")


def last_cross(ind: pd.DataFrame) -> pd.Timestamp | None:
    s = ind["signal"]
    ch = s.ne(s.shift(1)) & s.shift(1).notna()
    idx = ch[ch].index
    return ind.loc[idx[-1], "close_time"] if len(idx) else None


def combine(spot_sig, perp_sig):
    """现货与永续各自在自己的已收盘 K 线上算 dual-MA，再合成：
      现货 = +1 且永续 ≠ -1 → +1（现货做多）
      永续 = -1 且现货 ≠ +1 → -1（永续做空）
      其余（含冲突：现货多 / 永续空）→ 0 空仓
    """
    s = np.asarray(spot_sig, dtype=int)
    p = np.asarray(perp_sig, dtype=int)
    return np.where((s == 1) & (p != -1), 1, np.where((p == -1) & (s != 1), -1, 0)).astype(int)
