"""真实公共 K 线的 SQLite 缓存 + 并发拉取（最多 4 并发，遵守限频）。

规则：
* 只缓存从 OKX / Gate 官方公共 REST 实际拉到的已收盘 K 线；
* 命中条件：库里最近 limit 根连续（无缺口）且最新一根就是“当前应已收盘”的那根；
* 否则向交易所补拉（缺得少就只拉缺的部分），写库后再读；
* 交易所本身若有缺口，原样返回真实数据，**绝不插值或补假 K 线**。
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from qtw import db
from qtw.timeutil import iso, utcnow

from .base import CANDLE_COLS, INTERVAL_MS, MarketDataError, get_client

MARKETS = ("spot", "perp")


def _expected_last_open(interval: str) -> int:
    step = INTERVAL_MS[interval]
    now = int(time.time() * 1000)
    return (now // step) * step - step


def _read(venue, market, symbol, interval, limit) -> pd.DataFrame:
    rows = db.query(
        "SELECT open_time, open, high, low, close, volume, data_source, source_host, fetched_at FROM candles "
        "WHERE venue=? AND market=? AND symbol=? AND interval=? ORDER BY open_time DESC LIMIT ?",
        (venue, market, symbol, interval, limit))
    df = pd.DataFrame(rows[::-1])
    if df.empty:
        return pd.DataFrame(columns=CANDLE_COLS)
    step = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
    meta = {"venue": venue, "market": market, "data_source": df["data_source"].iloc[-1],
            "source_host": df["source_host"].iloc[-1], "fetched_at": df["fetched_at"].max()}
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = df["open_time"] + step
    df = df[CANDLE_COLS].reset_index(drop=True)
    df.attrs.update(meta)
    return df


def _contiguous(df: pd.DataFrame, interval: str) -> bool:
    if len(df) < 2:
        return True
    d = df["open_time"].diff().dropna()
    return bool((d == pd.Timedelta(milliseconds=INTERVAL_MS[interval])).all())


def _upsert(venue, market, symbol, interval, df: pd.DataFrame) -> None:
    a = df.attrs
    rows = [(venue, market, symbol, interval, int(r.open_time.value // 1_000_000), float(r.open), float(r.high),
             float(r.low), float(r.close), float(r.volume), a.get("data_source", ""), a.get("source_host", ""),
             a.get("fetched_at", iso(utcnow()))) for r in df.itertuples()]
    if not rows:
        return
    with db.tx() as c:
        c.executemany(
            "INSERT INTO candles(venue,market,symbol,interval,open_time,open,high,low,close,volume,data_source,"
            "source_host,fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(venue,market,symbol,interval,open_time) "
            "DO UPDATE SET open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close, "
            "volume=excluded.volume, data_source=excluded.data_source, source_host=excluded.source_host, "
            "fetched_at=excluded.fetched_at", rows)


def candles(venue: str, symbol: str, interval: str, limit: int, market: str = "spot") -> pd.DataFrame:
    if market not in MARKETS:
        raise ValueError("market 只能是 spot 或 perp")
    venue = venue.lower()
    exp = _expected_last_open(interval)
    have = _read(venue, market, symbol, interval, limit)
    newest = int(have["open_time"].iloc[-1].value // 1_000_000) if len(have) else None
    if len(have) >= limit and newest == exp and _contiguous(have, interval):
        have.attrs["cache"] = "sqlite"
        return have
    # 需要补拉：缺得少只拉缺口 + 余量，否则全量
    step = INTERVAL_MS[interval]
    n = limit
    if newest is not None and len(have) >= limit and _contiguous(have, interval) and newest < exp:
        n = min(limit, int((exp - newest) // step) + 3)
    fresh = get_client(venue).candles(symbol, interval, max(n, 2), market)
    if fresh.empty:
        raise MarketDataError(f"{venue.upper()} {symbol} {market} 未返回任何已收盘 K 线")
    _upsert(venue, market, symbol, interval, fresh)
    out = _read(venue, market, symbol, interval, limit)
    if not _contiguous(out, interval) and len(fresh) >= min(limit, len(out)):
        # 库里拼接出现缺口（例如很久没更新），直接用本次实拉的真实数据
        out = fresh.tail(limit).reset_index(drop=True)
    out.attrs.update(fresh.attrs)
    out.attrs["cache"] = "refreshed"
    return out


def many(venue: str, symbols: list[str], interval: str, limit: int, markets=MARKETS):
    """返回 ({market: {symbol: df}}, {"SYMBOL:market": error})。"""
    out: dict[str, dict[str, pd.DataFrame]] = {m: {} for m in markets}
    errs: dict[str, str] = {}
    jobs = [(s, m) for s in symbols for m in markets]

    def one(job):
        s, m = job
        try:
            return s, m, candles(venue, s, interval, limit, m), None
        except Exception as e:  # noqa: BLE001 —— 真实错误原样上报，不伪造
            return s, m, None, str(e)

    with ThreadPoolExecutor(max_workers=4) as ex:
        for s, m, df, err in ex.map(one, jobs):
            if err:
                errs[f"{s}:{m}"] = err
            else:
                out[m][s] = df
    return out, errs


def data_provenance(frames: dict[str, dict[str, pd.DataFrame]]) -> dict:
    srcs, hosts, fetched = set(), set(), []
    for m in frames.values():
        for df in m.values():
            srcs.add(df.attrs.get("data_source", ""))
            hosts.add(df.attrs.get("source_host", ""))
            if df.attrs.get("fetched_at"):
                fetched.append(df.attrs["fetched_at"])
    return {"data_source": "+".join(sorted(x for x in srcs if x)), "source_host": "+".join(sorted(x for x in hosts if x)),
            "fetched_at": max(fetched) if fetched else ""}
