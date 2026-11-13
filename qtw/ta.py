"""指标页：常用技术指标 + 多空证据分（只作参考证据，不参与下单）。

约定（无前视）：
* 输入只含交易所官方**已收盘** K 线（market.base.finalize 已剔除未收盘根）；
* 所有指标只用当根及更早的数据（rolling / ewm / cumsum，均为因果）；
* 唐奇安通道用「之前 n 根」的最高 / 最低（shift 1），所以「突破」是用已收盘价对比过去区间；
* 一目均衡表的先行带 A / B 画在「计算时刻 + 26 根」处：第 t 根看到的云 = 26 根前算好的值（因果）；
  不画迟行线（它要往回挪 26 根，会造成视觉前视），信号里用「收盘 vs 26 根前收盘」代替；
* 证据分 = 各指标投票（+1 偏多 / -1 偏空 / 0 中性）按权重加权平均，范围 -1 ~ +1。

研究结论（docs/STRATEGY_FORMULAS.md）：用证据分做入场一致性闸门没有通过两个交易所 + 未参与选参数历史的检验，
所以它只展示，不接入 engine / backtest 的任何决策。
"""
from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
import pandas as pd

INTRADAY = {"1m", "5m", "10m", "15m", "1h", "4h"}
TF_LIST = ["1m", "5m", "10m", "1h", "4h", "1d"]
TF_CN = {"1m": "1分钟", "5m": "5分钟", "10m": "10分钟", "15m": "15分钟", "1h": "1小时", "4h": "4小时", "1d": "日线"}
BULL_TH = 0.25  # 证据分 ≥ +0.25 记「偏多」，≤ -0.25 记「偏空」，其余「中性」


# ---------------------------------------------------------------- 基础算子
def rma(x: pd.Series, n: int) -> pd.Series:
    """Wilder 平滑（RMA），前 n 根不足时为 NaN。"""
    return x.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def true_range(h, l, c) -> pd.Series:
    pc = c.shift(1)
    return pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def supertrend(h, l, c, n: int = 10, mult: float = 3.0):
    atr = rma(true_range(h, l, c), n).to_numpy()
    hl2 = ((h + l) / 2).to_numpy()
    cc = c.to_numpy()
    N = len(cc)
    line = np.full(N, np.nan)
    dirn = np.zeros(N)
    fu = fl = np.nan
    d = 1
    for i in range(N):
        if not np.isfinite(atr[i]):
            continue
        bu, bl = hl2[i] + mult * atr[i], hl2[i] - mult * atr[i]
        if np.isnan(fu):
            fu, fl, d = bu, bl, 1 if cc[i] >= hl2[i] else -1
        else:
            fu = bu if (bu < fu or cc[i - 1] > fu) else fu
            fl = bl if (bl > fl or cc[i - 1] < fl) else fl
            if d == -1 and cc[i] > fu:
                d = 1
            elif d == 1 and cc[i] < fl:
                d = -1
        line[i] = fl if d == 1 else fu
        dirn[i] = d
    return pd.Series(line, index=c.index), pd.Series(dirn, index=c.index)


def _mad(x: np.ndarray) -> float:
    return float(np.mean(np.abs(x - x.mean())))


# ---------------------------------------------------------------- 指标计算
def compute(df: pd.DataFrame, interval: str = "4h") -> pd.DataFrame:
    """输入已收盘 OHLCV（open_time 为 UTC 时间），返回附加了全部指标列的副本。"""
    out = df.copy().reset_index(drop=True)
    o, h, l, c = (out[k].astype(float) for k in ("open", "high", "low", "close"))
    v = out["volume"].astype(float) if "volume" in out else pd.Series(0.0, index=out.index)
    out["sma50"] = c.rolling(50, min_periods=50).mean()
    out["sma150"] = c.rolling(150, min_periods=150).mean()
    out["ma100"] = c.rolling(100, min_periods=100).mean()
    out["ema12"] = c.ewm(span=12, adjust=False, min_periods=12).mean()
    out["ema26"] = c.ewm(span=26, adjust=False, min_periods=26).mean()
    out["macd"] = out["ema12"] - out["ema26"]
    out["macd_sig"] = out["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    out["macd_hist"] = out["macd"] - out["macd_sig"]
    d = c.diff()
    ag, al = rma(d.clip(lower=0), 14), rma((-d).clip(lower=0), 14)
    rs = ag / al.replace(0, np.nan)
    out["rsi14"] = np.where(al.eq(0) & ag.gt(0), 100.0, 100 - 100 / (1 + rs))
    out.loc[ag.isna(), "rsi14"] = np.nan
    ll9, hh9 = l.rolling(9, min_periods=9).min(), h.rolling(9, min_periods=9).max()
    rsv = ((c - ll9) / (hh9 - ll9).replace(0, np.nan) * 100).fillna(50).where(ll9.notna())
    out["kdj_k"] = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    out["kdj_d"] = out["kdj_k"].ewm(alpha=1 / 3, adjust=False).mean()
    out["kdj_j"] = 3 * out["kdj_k"] - 2 * out["kdj_d"]
    mid, sd = c.rolling(20, min_periods=20).mean(), c.rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid"], out["bb_up"], out["bb_lo"] = mid, mid + 2 * sd, mid - 2 * sd
    out["bb_pctb"] = (c - out["bb_lo"]) / (out["bb_up"] - out["bb_lo"]).replace(0, np.nan)
    out["bb_bw"] = (out["bb_up"] - out["bb_lo"]) / mid * 100
    tr = true_range(h, l, c)
    out["atr14"] = tr.rolling(14, min_periods=14).mean()  # 与策略止损同口径：TR 的 14 根简单平均
    out["atr_pct"] = out["atr14"] / c * 100
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=c.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=c.index)
    atr_w = rma(tr, 14)
    out["pdi"] = 100 * rma(pdm, 14) / atr_w
    out["mdi"] = 100 * rma(mdm, 14) / atr_w
    dx = 100 * (out["pdi"] - out["mdi"]).abs() / (out["pdi"] + out["mdi"]).replace(0, np.nan)
    out["adx"] = rma(dx, 14)
    tp = (h + l + c) / 3
    out["cci20"] = (tp - tp.rolling(20, min_periods=20).mean()) / (0.015 * tp.rolling(20, min_periods=20).apply(_mad, raw=True))
    hh14, ll14 = h.rolling(14, min_periods=14).max(), l.rolling(14, min_periods=14).min()
    out["wr14"] = (hh14 - c) / (hh14 - ll14).replace(0, np.nan) * -100
    out["obv"] = (np.sign(d.fillna(0)) * v).cumsum()
    out["obv_ma20"] = out["obv"].rolling(20, min_periods=20).mean()
    mf = tp * v
    tpd = tp.diff()
    pos = mf.where(tpd > 0, 0.0).rolling(14, min_periods=14).sum()
    neg = mf.where(tpd < 0, 0.0).rolling(14, min_periods=14).sum()
    out["mfi14"] = np.where(neg.eq(0) & pos.gt(0), 100.0, 100 - 100 / (1 + pos / neg.replace(0, np.nan)))
    out.loc[pos.isna(), "mfi14"] = np.nan
    if interval in INTRADAY and "open_time" in out:
        day = pd.to_datetime(out["open_time"], utc=True).dt.floor("D")
        pv = (tp * v).groupby(day).cumsum()
        vv = v.groupby(day).cumsum()
        out["vwap"] = pv / vv.replace(0, np.nan)
    else:
        out["vwap"] = np.nan
    for n in (20, 55):
        out[f"dc{n}_hi"] = h.rolling(n, min_periods=n).max().shift(1)
        out[f"dc{n}_lo"] = l.rolling(n, min_periods=n).min().shift(1)
    out["st_line"], out["st_dir"] = supertrend(h, l, c, 10, 3.0)
    tenkan = (h.rolling(9, min_periods=9).max() + l.rolling(9, min_periods=9).min()) / 2
    kijun = (h.rolling(26, min_periods=26).max() + l.rolling(26, min_periods=26).min()) / 2
    out["ich_tenkan"], out["ich_kijun"] = tenkan, kijun
    out["ich_span_a"] = ((tenkan + kijun) / 2).shift(26)
    out["ich_span_b"] = ((h.rolling(52, min_periods=52).max() + l.rolling(52, min_periods=52).min()) / 2).shift(26)
    out["ich_mom26"] = c - c.shift(26)
    vm, vs = v.rolling(20, min_periods=20).mean(), v.rolling(20, min_periods=20).std(ddof=0)
    out["vol_z"] = (v - vm) / vs.replace(0, np.nan)
    out["bar_dir"] = np.sign(c - o)
    return out


# ---------------------------------------------------------------- 投票（向量化，研究与页面同一口径）
# key, 名称, 分组, 权重；权重 0 = 只作背景参考，不计入证据分
SPECS: list[tuple[str, str, str, float]] = [
    ("ma_cross", "SMA 50 / 150", "趋势", 1.0),
    ("trend100", "趋势线 MA100", "趋势", 1.0),
    ("ema", "EMA 12 / 26", "趋势", 1.0),
    ("macd", "MACD (12,26,9)", "动量", 1.0),
    ("rsi", "RSI 14", "动量", 1.0),
    ("kdj", "KDJ (9,3,3)", "动量", 1.0),
    ("boll", "布林带 (20,2) %B", "波动", 1.0),
    ("bbw", "布林带宽", "波动", 0.0),
    ("atr", "ATR 14 / ATR%", "波动", 0.0),
    ("adx", "ADX / DI (14)", "趋势", 1.0),
    ("cci", "CCI 20", "动量", 1.0),
    ("wr", "威廉 %R 14", "动量", 1.0),
    ("obv", "OBV 能量潮", "量能", 0.5),
    ("mfi", "MFI 14 资金流", "量能", 0.5),
    ("vwap", "VWAP 当日均价", "量能", 0.5),
    ("dc20", "唐奇安 20", "趋势", 1.0),
    ("dc55", "唐奇安 55", "趋势", 1.0),
    ("supertrend", "超级趋势 (10,3)", "趋势", 1.0),
    ("ichimoku", "一目均衡表", "趋势", 1.0),
    ("volz", "成交量 Z 分数", "量能", 0.5),
]
EXTRA_SPECS = {"funding": ("资金费率", "合约", 0.5), "oi": ("持仓量 24h 变化", "合约", 0.5), "btc_regime": ("BTC 体制 (MA1200)", "大盘", 0.5)}
WEIGHTS = {k: w for k, _, _, w in SPECS}


def _sgn(x: pd.Series) -> pd.Series:
    return np.sign(x).fillna(0)


def _band(x: pd.Series, hi: float, lo: float) -> pd.Series:
    return pd.Series(np.where(x > hi, 1, np.where(x < lo, -1, 0)), index=x.index).where(x.notna(), 0)


def votes(ind: pd.DataFrame) -> pd.DataFrame:
    """每根 K 线每个指标的投票：+1 偏多 / -1 偏空 / 0 中性（数据不足也是 0）。只用当根已收盘值。"""
    c = ind["close"].astype(float)
    V = pd.DataFrame(index=ind.index)
    V["ma_cross"] = _sgn(ind["sma50"] - ind["sma150"])
    V["trend100"] = _sgn(c - ind["ma100"])
    V["ema"] = _sgn(ind["ema12"] - ind["ema26"])
    m, hst = ind["macd"], ind["macd_hist"]
    V["macd"] = np.where((m > 0) & (hst > 0), 1, np.where((m < 0) & (hst < 0), -1, 0))
    V["rsi"] = _band(ind["rsi14"], 55, 45)
    V["kdj"] = _sgn(ind["kdj_k"] - ind["kdj_d"]).where(ind["kdj_k"].notna(), 0)
    V["boll"] = _band(ind["bb_pctb"], 0.6, 0.4)
    V["bbw"] = 0
    V["atr"] = 0
    V["adx"] = np.where(ind["adx"] >= 20, np.sign(ind["pdi"] - ind["mdi"]), 0)
    V["cci"] = _band(ind["cci20"], 100, -100)
    V["wr"] = _band(ind["wr14"], -40, -60)
    V["obv"] = _sgn(ind["obv"] - ind["obv_ma20"])
    V["mfi"] = _band(ind["mfi14"], 60, 40)
    V["vwap"] = _sgn(c - ind["vwap"])
    for n in (20, 55):
        hi, lo = ind[f"dc{n}_hi"], ind[f"dc{n}_lo"]
        p = (c - lo) / (hi - lo).replace(0, np.nan)
        V[f"dc{n}"] = _band(p, 0.7, 0.3)
    V["supertrend"] = ind["st_dir"].fillna(0)
    top = ind[["ich_span_a", "ich_span_b"]].max(axis=1)
    bot = ind[["ich_span_a", "ich_span_b"]].min(axis=1)
    tk = ind["ich_tenkan"] - ind["ich_kijun"]
    V["ichimoku"] = np.where((c > top) & (tk > 0) & (ind["ich_mom26"] > 0), 1,
                             np.where((c < bot) & (tk < 0) & (ind["ich_mom26"] < 0), -1, 0))
    V["volz"] = np.where(ind["vol_z"] >= 2, ind["bar_dir"], 0)
    return V.fillna(0).astype(int)


def score_series(ind: pd.DataFrame, V: pd.DataFrame | None = None) -> pd.Series:
    """技术面证据分（-1 ~ +1）：Σ 权重 × 投票 / Σ 权重（只算有数据的指标）。研究闸门用的就是这条序列。"""
    V = votes(ind) if V is None else V
    avail = pd.DataFrame({k: _available(ind, k) for k in V.columns}, index=ind.index)
    w = pd.Series(WEIGHTS)
    num = (V[w.index] * w).where(avail[w.index], 0).sum(axis=1)
    den = (avail[w.index] * w).sum(axis=1)
    return (num / den.replace(0, np.nan)).fillna(0.0)


_AVAIL_COL = {"ma_cross": "sma150", "trend100": "ma100", "ema": "ema26", "macd": "macd_sig", "rsi": "rsi14", "kdj": "kdj_k",
              "boll": "bb_pctb", "bbw": "bb_bw", "atr": "atr14", "adx": "adx", "cci": "cci20", "wr": "wr14", "obv": "obv_ma20",
              "mfi": "mfi14", "vwap": "vwap", "dc20": "dc20_hi", "dc55": "dc55_hi", "supertrend": "st_line",
              "ichimoku": "ich_span_b", "volz": "vol_z"}


def _available(ind: pd.DataFrame, key: str) -> pd.Series:
    return ind[_AVAIL_COL[key]].notna()


def label(score: float) -> str:
    return "偏多" if score >= BULL_TH else "偏空" if score <= -BULL_TH else "中性"


# ---------------------------------------------------------------- 卡片文字（最后一根已收盘 K 线）
def _f(x, d=2):
    if x is None or not np.isfinite(x):
        return "—"
    a = abs(x)
    if a >= 1000:
        return f"{x:,.{min(d, 2)}f}"
    if a >= 1:
        return f"{x:.{d}f}"
    return f"{x:.4g}"


def _px(x):
    if x is None or not np.isfinite(x):
        return "—"
    a = abs(x)
    return f"{x:,.2f}" if a >= 1000 else f"{x:.4f}".rstrip("0").rstrip(".") if a >= 1 else f"{x:.5g}"


def _card(key: str, r: pd.Series, vote: int, avail: bool) -> dict:
    name, group, w = next((n, g, ww) for k, n, g, ww in SPECS if k == key)
    c = float(r["close"])
    val, why = "—", ""
    if key == "ma_cross":
        val = f"{_px(r.sma50)} / {_px(r.sma150)}"
        why = (f"快线 SMA50 在慢线 SMA150 {'之上' if vote > 0 else '之下'}，" if vote else "两线持平，") + "这就是当前策略判断多空方向用的那一对均线（4 小时周期）。"
    elif key == "trend100":
        val = _px(r.ma100)
        why = f"收盘 {_px(c)} {'高于' if vote > 0 else '低于' if vote < 0 else '等于'} 100 根均线，{'中期趋势向上' if vote > 0 else '中期趋势向下' if vote < 0 else '方向不明'}。策略用它拦截逆势新开仓。"
    elif key == "ema":
        val = f"{_px(r.ema12)} / {_px(r.ema26)}"
        why = f"短期 EMA12 {'高于' if vote > 0 else '低于'} EMA26，短期动能{'向上' if vote > 0 else '向下'}。" if vote else "两条 EMA 几乎重合。"
    elif key == "macd":
        val = f"DIF {_f(r.macd, 4)} · 柱 {_f(r.macd_hist, 4)}"
        why = ("DIF 在零轴上方且柱体为正：多头动能在增强。" if vote > 0 else "DIF 在零轴下方且柱体为负：空头动能在增强。" if vote < 0
               else "DIF 与柱体方向不一致（如零轴下方金叉 / 上方死叉），动能在切换，记中性。")
    elif key == "rsi":
        x = float(r.rsi14)
        val = _f(x, 1)
        ext = "，已进入超买区（>70），追多要小心回落" if x > 70 else "，已进入超卖区（<30），追空要小心反弹" if x < 30 else ""
        why = f"RSI {_f(x, 1)}：{'> 55 偏多' if vote > 0 else '< 45 偏空' if vote < 0 else '45~55 之间，多空均衡'}{ext}。"
    elif key == "kdj":
        val = f"K {_f(r.kdj_k, 1)} · D {_f(r.kdj_d, 1)} · J {_f(r.kdj_j, 1)}"
        j = float(r.kdj_j)
        ext = "；J > 100 过热" if j > 100 else "；J < 0 过冷" if j < 0 else ""
        why = f"K 线{'在 D 线上方（金叉区）' if vote > 0 else '在 D 线下方（死叉区）' if vote < 0 else '与 D 线重合'}{ext}。KDJ 很灵敏，短周期上来回翻转很常见。"
    elif key == "boll":
        b = float(r.bb_pctb)
        val = f"%B {b:.2f}"
        why = f"收盘位于布林带 {b * 100:.0f}% 位置（0% = 下轨，100% = 上轨）：{'贴上半区运行偏多' if vote > 0 else '贴下半区运行偏空' if vote < 0 else '在中轨附近'}。"
    elif key == "bbw":
        val = f"{_f(r.bb_bw, 2)}%"
        why = "上下轨之间的宽度占中轨的百分比。只看波动大小，不分多空：收窄说明在蓄势，放宽说明行情正在展开。"
    elif key == "atr":
        val = f"{_px(r.atr14)} · {_f(r.atr_pct, 2)}%"
        why = f"最近 14 根平均真实波幅约为价格的 {_f(r.atr_pct, 2)}%。策略止损放在 2 × ATR 外，所以它决定止损宽度和仓位大小，不分多空。"
    elif key == "adx":
        val = f"ADX {_f(r.adx, 1)} · +DI {_f(r.pdi, 1)} · −DI {_f(r.mdi, 1)}"
        why = (f"ADX ≥ 20 说明有趋势，{'+DI 大于 −DI，上涨方向占优' if vote > 0 else '−DI 大于 +DI，下跌方向占优'}。" if vote
               else "ADX < 20，市场没有明显趋势（震荡），记中性。")
    elif key == "cci":
        val = _f(r.cci20, 0)
        why = "CCI > +100：价格明显强于近 20 根均值。" if vote > 0 else "CCI < −100：价格明显弱于近 20 根均值。" if vote < 0 else "CCI 在 ±100 之内，属正常波动。"
    elif key == "wr":
        val = _f(r.wr14, 1)
        why = f"收盘处在近 14 根高低区间的 {100 + float(r.wr14):.0f}% 位置：{'靠近区间高位（> −40）偏多' if vote > 0 else '靠近区间低位（< −60）偏空' if vote < 0 else '区间中部'}。"
    elif key == "obv":
        val = f"{_f(r.obv, 0)}"
        why = f"能量潮{'高于' if vote > 0 else '低于'}自身 20 根均线：近期{'放量上涨多于放量下跌' if vote > 0 else '放量下跌多于放量上涨'}。" if vote else "能量潮贴着均线，量能没有方向。"
    elif key == "mfi":
        val = _f(r.mfi14, 1)
        why = "资金流指数 > 60：带量上涨占优。" if vote > 0 else "资金流指数 < 40：带量下跌占优。" if vote < 0 else "资金流指数 40~60，买卖量均衡。"
    elif key == "vwap":
        val = _px(r.vwap)
        why = (f"收盘{'高于' if vote > 0 else '低于'}当日（UTC 0 点起）成交量加权均价，当天买方{'占优' if vote > 0 else '偏弱'}。" if avail
               else "VWAP 只在日内周期计算（日线没有「当日」概念），此周期不计。")
    elif key in ("dc20", "dc55"):
        n = 20 if key == "dc20" else 55
        hi, lo = float(r[f"dc{n}_hi"]), float(r[f"dc{n}_lo"])
        val = f"{_px(lo)} ~ {_px(hi)}"
        brk = "，已突破前高" if c > hi else "，已跌破前低" if c < lo else ""
        why = f"收盘在过去 {n} 根的高低区间里{'靠上（>70%）' if vote > 0 else '靠下（<30%）' if vote < 0 else '居中'}{brk}。"
    elif key == "supertrend":
        val = _px(r.st_line)
        why = f"超级趋势线在价格{'下方（多头支撑）' if vote > 0 else '上方（空头压力）'}；收盘穿过这条线才会翻转。" if vote else "数据不足。"
    elif key == "ichimoku":
        val = f"转 {_px(r.ich_tenkan)} · 基 {_px(r.ich_kijun)}"
        top, bot = max(r.ich_span_a, r.ich_span_b), min(r.ich_span_a, r.ich_span_b)
        pos = "云上" if c > top else "云下" if c < bot else "云中"
        why = (f"价格在{pos}，转换线{'>' if r.ich_tenkan > r.ich_kijun else '<'}基准线，收盘{'高于' if r.ich_mom26 > 0 else '低于'} 26 根前。"
               + ("三项同时向上 → 偏多。" if vote > 0 else "三项同时向下 → 偏空。" if vote < 0 else "三项不一致 → 中性。"))
    elif key == "volz":
        z = float(r.vol_z)
        val = f"{z:+.2f}σ"
        why = (f"本根成交量比近 20 根均值高 {_f(z, 1)} 个标准差（明显放量），K 线{'收阳' if vote > 0 else '收阴'}，放量方向{'向上' if vote > 0 else '向下'}。" if vote
               else "成交量没有明显放大（< 2σ），不给方向。")
    if not avail:
        val = "—"
        why = why if key == "vwap" else "K 线数量不足，暂时算不出来。"
    return {"key": key, "name": name, "group": group, "weight": w, "value": val, "vote": int(vote) if avail else 0,
            "tag": "中性" if not avail or not vote else ("偏多" if vote > 0 else "偏空"), "reason": why, "available": bool(avail),
            "context_only": w == 0}


def cards(ind: pd.DataFrame, V: pd.DataFrame | None = None) -> list[dict]:
    V = votes(ind) if V is None else V
    r, vr = ind.iloc[-1], V.iloc[-1]
    return [_card(k, r, int(vr[k]), bool(_available(ind, k).iloc[-1])) for k, *_ in SPECS]


def summarize(cs: list[dict]) -> dict:
    used = [x for x in cs if x["available"] and x["weight"] > 0]
    den = sum(x["weight"] for x in used)
    sc = sum(x["weight"] * x["vote"] for x in used) / den if den else 0.0
    return {"score": round(sc, 3), "label": label(sc), "bull": sum(1 for x in used if x["vote"] > 0),
            "bear": sum(1 for x in used if x["vote"] < 0), "neutral": sum(1 for x in used if x["vote"] == 0),
            "n": len(used), "threshold": BULL_TH}


def tech_snapshot(df: pd.DataFrame, interval: str) -> dict:
    ind = compute(df, interval)
    cs = cards(ind)
    out = summarize(cs)
    out["as_of_open"] = int(pd.Timestamp(ind["open_time"].iloc[-1]).timestamp()) if len(ind) else None
    out["close"] = float(ind["close"].iloc[-1]) if len(ind) else None
    return out


# ---------------------------------------------------------------- 合约公共数据（资金费率 / 持仓量）
_DERIV_CACHE: dict[tuple, tuple[float, dict]] = {}
_DERIV_TTL = 60.0


def _okx_deriv(symbol: str) -> dict:
    from .market.base import HttpJson
    from .market.okx import swap_id
    from .net import okx_rest_bases
    http = HttpJson(okx_rest_bases(), timeout=6, max_retries=1, backoff=0.3)
    inst = swap_id(symbol)
    out: dict[str, Any] = {"source": "okx_public_rest"}
    j = http.get("/api/v5/public/funding-rate", {"instId": inst})
    d = (j.get("data") or [{}])[0]
    if d.get("fundingRate") not in (None, ""):
        out["funding_rate"] = float(d["fundingRate"])
        out["funding_next_ms"] = int(d.get("fundingTime") or 0)
        out["funding_interval_h"] = 8
    j = http.get("/api/v5/rubik/stat/contracts/open-interest-history", {"instId": inst, "period": "1H", "limit": 30})
    rows = sorted((r for r in (j.get("data") or []) if len(r) >= 4), key=lambda r: int(r[0]))
    if len(rows) >= 25:
        out["oi_usd"], out["oi_usd_24h_ago"] = float(rows[-1][3]), float(rows[-25][3])
        out["oi_time_ms"] = int(rows[-1][0])
    else:
        j = http.get("/api/v5/public/open-interest", {"instType": "SWAP", "instId": inst})
        d = (j.get("data") or [{}])[0]
        if d.get("oiUsd"):
            out["oi_usd"] = float(d["oiUsd"])
    out["host"] = http.last_host
    return out


def _gate_deriv(symbol: str) -> dict:
    from .market.base import HttpJson
    from .market.gate import BASES, pair
    http = HttpJson(BASES, timeout=6, max_retries=1, backoff=0.3)
    out: dict[str, Any] = {"source": "gate_public_rest"}
    d = http.get(f"/futures/usdt/contracts/{pair(symbol)}")
    if d.get("funding_rate") not in (None, ""):
        out["funding_rate"] = float(d["funding_rate"])
        out["funding_next_ms"] = int(float(d.get("funding_next_apply") or 0)) * 1000
        out["funding_interval_h"] = round(float(d.get("funding_interval") or 28800) / 3600, 1)
    rows = http.get("/futures/usdt/contract_stats", {"contract": pair(symbol), "interval": "1h", "limit": 30})
    rows = sorted((r for r in rows or [] if r.get("open_interest_usd") is not None), key=lambda r: int(r["time"]))
    if len(rows) >= 25:
        out["oi_usd"], out["oi_usd_24h_ago"] = float(rows[-1]["open_interest_usd"]), float(rows[-25]["open_interest_usd"])
        out["oi_time_ms"] = int(rows[-1]["time"]) * 1000
    out["host"] = http.last_host
    return out


def derivatives(venue: str, symbol: str) -> dict:
    """官方公共接口的资金费率与持仓量（60 秒内存缓存）。失败返回 {"error": ...}，页面显示「跳过」，绝不编造。"""
    key = (venue, symbol)
    now = time.time()
    hit = _DERIV_CACHE.get(key)
    if hit and now - hit[0] < _DERIV_TTL:
        return hit[1]
    try:
        d = _okx_deriv(symbol) if venue == "okx" else _gate_deriv(symbol)
    except Exception as e:  # noqa: BLE001
        d = {"error": f"{type(e).__name__}: {str(e)[:160]}"}
    _DERIV_CACHE[key] = (now, d)
    return d


def deriv_cards(d: dict, price_chg_24h: float | None) -> list[dict]:
    out = []
    name, group, w = EXTRA_SPECS["funding"]
    fr = d.get("funding_rate")
    if fr is None:
        out.append({"key": "funding", "name": name, "group": group, "weight": w, "value": "—", "vote": 0, "tag": "中性",
                    "available": False, "context_only": False, "reason": "交易所公共接口暂时没有返回资金费率，已跳过（不编造）。" + (f"（{d['error']}）" if d.get("error") else "")})
    else:
        vote = -1 if fr > 0.0005 else 1 if fr < -0.0005 else 0
        why = (f"每 {d.get('funding_interval_h', 8):g} 小时结算一次，当前 {fr * 100:+.4f}%。" +
               ("费率明显为正（> +0.05%）：多头付钱给空头，多头过度拥挤，容易被挤兑回落 → 反向偏空。" if vote < 0 else
                "费率明显为负（< −0.05%）：空头付钱给多头，空头过度拥挤，容易被逼空 → 反向偏多。" if vote > 0 else
                "费率在 ±0.05% 之内，属正常水平，不给方向。"))
        out.append({"key": "funding", "name": name, "group": group, "weight": w, "value": f"{fr * 100:+.4f}%", "vote": vote,
                    "tag": "偏多" if vote > 0 else "偏空" if vote < 0 else "中性", "available": True, "context_only": False, "reason": why})
    name, group, w = EXTRA_SPECS["oi"]
    oi, oi0 = d.get("oi_usd"), d.get("oi_usd_24h_ago")
    if oi is None or oi0 is None or not oi0 or price_chg_24h is None:
        out.append({"key": "oi", "name": name, "group": group, "weight": w, "value": f"{oi / 1e6:,.1f}M U" if oi else "—", "vote": 0, "tag": "中性",
                    "available": False, "context_only": False, "reason": "该交易所没有返回足够的持仓量历史（需要 24 小时），只显示当前值，不计入证据分。"})
    else:
        ch = oi / oi0 - 1
        vote = 0
        if ch > 0.03:
            vote = 1 if price_chg_24h > 0 else -1 if price_chg_24h < 0 else 0
        why = (f"24 小时持仓量 {ch * 100:+.1f}%，同期价格 {price_chg_24h * 100:+.1f}%。" +
               ("持仓增加且价格上涨：新资金在做多 → 偏多。" if vote > 0 else "持仓增加且价格下跌：新资金在做空 → 偏空。" if vote < 0 else
                "持仓没有明显增加（< 3%），多是平仓或观望，不给方向。"))
        out.append({"key": "oi", "name": name, "group": group, "weight": w, "value": f"{oi / 1e6:,.1f}M U · {ch * 100:+.1f}%", "vote": vote,
                    "tag": "偏多" if vote > 0 else "偏空" if vote < 0 else "中性", "available": True, "context_only": False, "reason": why})
    return out


def btc_regime_card(btc4h: pd.DataFrame | None, n: int = 1200) -> dict:
    name, group, w = EXTRA_SPECS["btc_regime"]
    if btc4h is None or len(btc4h) < n:
        return {"key": "btc_regime", "name": name, "group": group, "weight": w, "value": "—", "vote": 0, "tag": "中性",
                "available": False, "context_only": False, "reason": f"BTC 4 小时 K 线不足 {n} 根，暂时算不出。"}
    c = btc4h["close"].astype(float)
    ma = float(c.rolling(n).mean().iloc[-1])
    last = float(c.iloc[-1])
    vote = 1 if last > ma else -1
    why = (f"BTC 现货 4 小时收盘 {_px(last)}，{'高于' if vote > 0 else '低于'} 1200 根（约 200 天）均线 {_px(ma)}。"
           + ("大盘在牛市体制里。" if vote > 0 else "大盘在熊市体制里：当前策略因此暂停所有币的新开多单（已有多单不受影响）。"))
    return {"key": "btc_regime", "name": name, "group": group, "weight": w, "value": f"{(last / ma - 1) * 100:+.1f}%", "vote": vote,
            "tag": "偏多" if vote > 0 else "偏空", "available": True, "context_only": False, "reason": why}


SERIES_COLS = ["sma50", "sma150", "ma100", "ema12", "ema26", "macd", "macd_sig", "macd_hist", "rsi14", "kdj_k", "kdj_d", "kdj_j",
               "bb_mid", "bb_up", "bb_lo", "bb_pctb", "bb_bw", "atr14", "atr_pct", "adx", "pdi", "mdi", "cci20", "wr14", "obv",
               "obv_ma20", "mfi14", "vwap", "dc20_hi", "dc20_lo", "dc55_hi", "dc55_lo", "st_line", "st_dir", "ich_tenkan",
               "ich_kijun", "ich_span_a", "ich_span_b", "vol_z", "score"]


def series_payload(ind: pd.DataFrame, n: int) -> dict:
    tail = ind.tail(n)

    def col(k):
        a = tail[k].astype(float).to_numpy()
        return [None if not math.isfinite(x) else float(f"{x:.7g}") for x in a]
    return {k: col(k) for k in SERIES_COLS if k in tail}
