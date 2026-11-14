"""dual_ma_trend_4h_v1：SMA(快) vs SMA(慢)，只用已收盘 K 线，无前视。

第 t 根 K 线收盘后得到的信号，最早只能在第 t+1 根开盘（回测）或之后（纸面/实盘）执行。
  快线 > 慢线 → +1 做多 → 现货多头
  快线 < 慢线 → -1 做空 → USDT 永续空头（1 倍保证金）
  否则/数据不足 → 0 空仓
信号确认：原始方向需在最近 confirm_bars 根已收盘 K 线上保持一致才生效，否则视为 0（空仓），过滤刚交叉就回头的假信号。
趋势过滤（trend_ma>0，仅作用于入场）：做多需上一根收盘 > 该市场 SMA(trend_ma)，做空需 < SMA(trend_ma)；
  已有持仓不因趋势过滤平仓，离场仍只看信号反转/归零与 ATR 止损。
震荡指数闸门（chop_n>0，可选，默认关闭，仅作用于入场）：CHOP_n = 100·log10(ΣTR_n / (maxH_n − minL_n)) / log10(n)，
  上一根 CHOP > chop_max（震荡市）时不新开 / 反手开仓；已有持仓离场、止损、调仓不受影响。
Elder-Ray 空头闸门（elder_short_gate_n>0，可选，默认关闭，只拦新开 / 反手空单）：用现货 K 线，
  E = EMA_N(close)，ATR = Wilder ATR14，bull = (high − E) / ATR；上一根 bull < −X（整根 K 线低于 EMA 超过 X 个 ATR，
  空头已过度延伸）时不新开空；已有持仓、止损、离场、调仓不受影响；前 N+20 根数据不足时不拦。
止损：入场价 ∓ atr_stop_mult × ATR(入场前一根收盘)。止损后保持空仓，直到信号方向改变。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def chop_index(df: pd.DataFrame, n: int) -> pd.Series:
    """Choppiness Index（只用已收盘 K 线）：100·log10(ΣTR_n / (max(H,n) − min(L,n))) / log10(n)。
    取值约 0–100，越高越震荡；历史不足 n 根或区间为 0 时为 NaN。"""
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    prev = c.shift(1)
    tr = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    rng = (h.rolling(n).max() - l.rolling(n).min()).replace(0, np.nan)
    return 100 * np.log10(tr.rolling(n).sum() / rng) / np.log10(n)


def chop_ok(chop: float, chop_n: int, chop_max: float) -> bool:
    """震荡指数入场闸门：关闭（chop_n=0）时恒为 True；CHOP 未形成（NaN）时不允许新开仓；CHOP > chop_max 时不新开。"""
    if not chop_n:
        return True
    if not (chop == chop):
        return False
    return chop <= chop_max


def elder_bull_power(df: pd.DataFrame, n: int, atr_n: int = 14) -> pd.Series:
    """Elder-Ray 牛力（ATR 归一化，只用已收盘 K 线）：(high − EMA_n(close)) / WilderATR_atr_n。前 n+20 根为 NaN。"""
    h, l, c = df["high"].astype(float), df["low"].astype(float), df["close"].astype(float)
    e = c.ewm(span=int(n), adjust=False).mean()
    prev = c.shift(1)
    tr = pd.concat([h - l, (h - prev).abs(), (l - prev).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / atr_n, adjust=False).mean()
    out = (h - e) / atr.replace(0, np.nan)
    out.iloc[: int(n) + 20] = np.nan
    return out


def elder_short_ok(bull: float, n: int, x: float) -> bool:
    """Elder-Ray 空头入场闸门：关闭（n=0）或牛力未形成（NaN）时为 True；bull < −x 时不新开空。"""
    if not n or not (bull == bull):
        return True
    return not bull < -float(x)


def indicators(df: pd.DataFrame, fast: int, slow: int, atr_period: int, confirm_bars: int = 1, trend_ma: int = 0,
               chop_n: int = 0, elder_n: int = 0) -> pd.DataFrame:
    out = df.copy()
    c = out["close"]
    out["chop"] = chop_index(out, int(chop_n)) if chop_n else np.nan
    out["elder_bull"] = elder_bull_power(out, int(elder_n)) if elder_n else np.nan
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


def ls_parity_scales(sig: dict, nvm_long: dict, nvm_short: dict, cap: float) -> tuple[np.ndarray, np.ndarray]:
    """可选动态多空风险平价「up」（ls_parity_cap，0 / ≤1 = 关闭）。第 t 根收盘的合成信号 sig[s]（1 / −1 / 0）下，
    R_L = Σ_{sig=1} nvm_long[s]，R_S = Σ_{sig=−1} nvm_short[s]；两侧都非空时只把较小一侧放大到较大一侧：
    ls = clip(max(R_L, R_S) / R_L, 1/cap, cap)，ss 同理（较大一侧为 1）；否则 1。调用方第 t+1 根用 t 的乘数
    （与 name_vol_mult 同口径）乘单笔风险上限与单币权重上限，总敞口上限不变。研究：docs/STRATEGY_FORMULAS.md
    「动态多空风险平价」与 2026-11-13 新默认复核（scratch/drp2/drp2.py）。"""
    syms = list(sig)
    n = len(np.asarray(sig[syms[0]])) if syms else 0
    ls, ss = np.ones(n), np.ones(n)
    if not syms or not cap or float(cap) <= 1:
        return ls, ss
    rl, rs = np.zeros(n), np.zeros(n)
    for s in syms:
        g = np.asarray(sig[s])
        rl += np.where(g == 1, np.asarray(nvm_long[s], dtype=float), 0.0)
        rs += np.where(g == -1, np.asarray(nvm_short[s], dtype=float), 0.0)
    both = (rl > 1e-12) & (rs > 1e-12)
    tgt, c = np.maximum(rl, rs), float(cap)
    ls = np.where(both, np.clip(tgt / np.where(rl > 0, rl, 1.0), 1.0 / c, c), 1.0)
    ss = np.where(both, np.clip(tgt / np.where(rs > 0, rs, 1.0), 1.0 / c, c), 1.0)
    return ls, ss


def hedge_pair_mask(sig: dict, close: dict, window: int, corr_min: float) -> dict:
    """可选多空对冲对乘数（hedge_pair_w，0 = 关闭）的掩码。第 t 根收盘：若存在另一币 q，合成信号 sig[q][t] = −sig[s][t] ≠ 0，
    且两币最近 window 根永续对数收益的样本相关 ρ_{s,q}[t]（pandas rolling corr，含第 t 根）≥ corr_min，则 s（与 q）为「对冲腿」= True。
    调用方第 t+1 根把对冲腿的单笔风险 / 单币权重乘数 × hedge_pair_h（与 name_vol_mult、ls_parity_scales 同口径，总敞口上限不变）。
    close[s] 必须与 sig[s] 按同一时间轴对齐。研究：docs/STRATEGY_FORMULAS.md「对冲对乘数」（scratch/hpn、scratch/hpph）。"""
    syms = list(sig)
    n = len(np.asarray(sig[syms[0]])) if syms else 0
    out = {s: np.zeros(n, dtype=bool) for s in syms}
    w = int(window or 0)
    if w < 2 or len(syms) < 2:
        return out
    G = {s: np.asarray(sig[s]) for s in syms}
    R = {}
    for s in syms:
        c = np.asarray(close[s], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            R[s] = pd.Series(np.r_[np.nan, np.diff(np.log(c))])
    for i, a in enumerate(syms):
        for b in syms[i + 1:]:
            opp = G[a] * G[b] == -1
            if not opp.any():
                continue
            rho = R[a].rolling(w, min_periods=w).corr(R[b]).to_numpy()
            with np.errstate(invalid="ignore"):
                hit = opp & (rho >= float(corr_min))  # 历史不足（NaN）→ False
            out[a] |= hit
            out[b] |= hit
    return out


def name_vol_mult(close, target: float, lookback: int, bars_per_year: float = 2190) -> np.ndarray:
    """单币波动率封顶（可选，name_vol_target = 0 关闭）：σ_t = 最近 lookback 根对数收益的样本标准差 × √bars_per_year
    （含第 t 根收盘），返回逐根 m_t = min(1, target / σ_t)；调用方在第 t+1 根用 m_t 乘单笔风险上限与单币权重上限（只缩不放）。
    历史不足、σ 非有限或为 0 时 m = 1。研究：output/research_inverse_vol_sizing*.csv。"""
    c = np.asarray(close, dtype=float)
    if not target or lookback < 2 or len(c) == 0:
        return np.ones(len(c))
    with np.errstate(divide="ignore", invalid="ignore"):
        r = pd.Series(np.log(c)).diff()
    sd = r.rolling(int(lookback)).std().to_numpy() * np.sqrt(bars_per_year)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.minimum(1.0, float(target) / sd)
    m[~np.isfinite(m)] = 1.0
    return m


def bar_close_equity(ledger: list[dict], interval_ms: int) -> list[float]:
    """把账本权益快照按 K 线周期分桶，取每根内最后一条（≈该根收盘权益），时间升序。
    用于实盘/模拟引擎的组合波动率目标，与回测逐根收盘权益口径一致。时间无法解析的行丢弃。"""
    from datetime import datetime, timezone
    out: dict[int, float] = {}
    for r in ledger or []:
        try:
            t = datetime.fromisoformat(str(r.get("time")).replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            v = float(r.get("equity_usdt"))
        except (TypeError, ValueError):
            continue
        if not v > 0:
            continue
        out[int(t.timestamp() * 1000) // int(interval_ms)] = v
    keys = sorted(out)
    res: list[float] = []
    for i, k in enumerate(keys):
        if i and k - keys[i - 1] > 1:
            # 停机 / 暂停漏掉的周期：按几何插值补齐中间各根，把跨 n 根的收益均摊成 n 个单根收益。
            # 否则一个跨多根的收益被当成一根，组合波动率被高估、仓位被无故缩小（重启后仍持续 lookback 根）。
            a, b, n = res[-1], out[k], k - keys[i - 1]
            res.extend(a * (b / a) ** (j / n) for j in range(1, n))
        res.append(out[k])
    return res


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
