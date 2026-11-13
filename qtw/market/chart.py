"""K 线图周期（仅图表 / 同比展示，不参与 4h 信号）：1m 5m 10m 15m 1h 4h 1d 1w 1M 1y。

* 1m / 5m / 15m / 1h / 4h / 1d：交易所官方原生 K 线（OKX / Gate 公共 REST，SQLite 缓存，按需增量补拉）；
* 10m：两家都没有原生 10m，由官方 1m 聚合（UTC 对齐，子 K 线不齐全的桶丢弃）；
* 1w / 1M / 1y：由官方 1D K 线按 UTC 自然周（周一起）/ 自然月 / 自然年聚合
  （Gate 的 30d 是固定 30 天而非自然月，所以统一用日线聚合；OKX 1Wutc 同样周一 00:00 UTC 起）。
  最后一根若当期未结束，标记 partial（只含已收盘的日线）。
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from . import cache as mcache

CHART_INTERVALS = ["1m", "5m", "10m", "15m", "1h", "4h", "1d", "1w", "1M", "1y"]
NATIVE = {"1m", "5m", "15m", "1h", "4h", "1d"}
SEC = {"1m": 60, "5m": 300, "10m": 600, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800,
       "1M": 2_629_800, "1y": 31_557_600}
DAILY_MAX = 4000  # 约 11 年日线，足够覆盖主流币全部历史


def _agg_daily(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    x = d.copy()
    ot = pd.to_datetime(x["open_time"], utc=True)
    if rule == "1w":
        key = (ot - pd.to_timedelta(ot.dt.day_of_week, unit="D")).dt.normalize()
    elif rule == "1M":
        key = ot.dt.tz_localize(None).dt.to_period("M").dt.start_time.dt.tz_localize("UTC")
    else:
        key = ot.dt.tz_localize(None).dt.to_period("Y").dt.start_time.dt.tz_localize("UTC")
    x["k"] = key
    g = x.groupby("k", sort=True)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum(), "days": g.size()}).reset_index()
    out = out.rename(columns={"k": "open_time"})
    nxt = {"1w": lambda t: t + pd.Timedelta(days=7), "1M": lambda t: t + pd.offsets.MonthBegin(1),
           "1y": lambda t: t + pd.offsets.YearBegin(1)}[rule]
    out["close_time"] = out["open_time"].map(nxt)
    now = pd.Timestamp(datetime.now(timezone.utc))
    out["partial"] = out["close_time"] > now
    out.attrs.update(d.attrs)
    out.attrs["aggregated_from"] = "1d"
    return out


def chart_candles(venue: str, symbol: str, interval: str, bars: int, market: str = "spot") -> pd.DataFrame:
    """返回含 open_time/open/high/low/close/volume/close_time/partial 的 DataFrame（attrs 带数据来源）。"""
    if interval not in CHART_INTERVALS:
        raise ValueError(f"不支持的图表周期 {interval}")
    bars = max(10, int(bars))
    if interval in NATIVE:
        df = mcache.candles(venue, symbol, interval, bars, market).copy()
        df["partial"] = False
        return df
    if interval == "10m":
        from qtw.fastlayer import aggregate
        raw = mcache.candles(venue, symbol, "1m", min(3000, bars * 10 + 10), market)
        df = aggregate(raw, 10, 1).tail(bars).reset_index(drop=True)
        df["partial"] = False
        return df
    need = {"1w": bars * 7 + 7, "1M": bars * 31 + 31, "1y": DAILY_MAX}[interval]
    d = mcache.candles(venue, symbol, "1d", min(DAILY_MAX, need), market)
    return _agg_daily(d, interval).tail(bars).reset_index(drop=True)


def _ref_ts(ts: pd.Timestamp) -> int:
    """映射到参考闰年 2000 的同月同日同时刻（UTC 秒），用于同比叠加的公共横轴。"""
    t = ts.tz_convert("UTC")
    return int(datetime(2000, t.month, t.day, t.hour, t.minute, tzinfo=timezone.utc).timestamp())


def yoy(venue: str, symbol: str, interval: str, years: list[int], market: str = "spot", mode: str = "pct") -> dict:
    """同比叠加：每年一条线，横轴为一年中的同一天（参考年 2000），pct 模式按当年第一根收盘归一为 %。"""
    if interval not in ("4h", "1d", "1w"):
        raise ValueError("同比只支持 4h / 1d / 1w")
    years = sorted({int(y) for y in years})[:6]
    if not years:
        raise ValueError("至少选择一个年份")
    span_days = (datetime.now(timezone.utc).year - years[0] + 1) * 366
    if interval == "4h":
        df = mcache.candles(venue, symbol, "4h", min(9000, span_days * 6), market)
    else:
        d = mcache.candles(venue, symbol, "1d", DAILY_MAX, market)  # 全部日线（缓存后只增量补拉），可选年份取自全历史
        df = d if interval == "1d" else _agg_daily(d, "1w")
    ot = pd.to_datetime(df["open_time"], utc=True)
    have = sorted(set(int(y) for y in ot.dt.year))
    series = []
    for y in years:
        m = ot.dt.year == y
        sub = df[m]
        if sub.empty:
            series.append({"year": y, "points": [], "first_close": None, "last_close": None, "change": None})
            continue
        c0 = float(sub["close"].iloc[0])
        pts = []
        for t, c in zip(ot[m], sub["close"]):
            v = (float(c) / c0 - 1) * 100 if mode == "pct" else float(c)
            pts.append({"time": _ref_ts(t), "value": round(v, 6), "date": t.strftime("%Y-%m-%d %H:%M")})
        series.append({"year": y, "points": pts, "first_close": c0, "last_close": float(sub["close"].iloc[-1]),
                       "change": float(sub["close"].iloc[-1]) / c0 - 1, "first_date": pts[0]["date"], "last_date": pts[-1]["date"]})
    return {"symbol": symbol, "venue": venue, "market": market, "interval": interval, "mode": mode,
            "available_years": have, "series": series, "data_source": df.attrs.get("data_source", ""),
            "source_host": df.attrs.get("source_host", ""), "aggregated_from": df.attrs.get("aggregated_from", "")}
