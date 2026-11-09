"""K 线缓存 + 并发拉取（遵守限频：最多 4 并发）。缓存的是真实公共数据，不做任何插值。"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .base import MarketDataError, get_client

_CACHE: dict[tuple, tuple[float, pd.DataFrame]] = {}
_LOCK = threading.Lock()
TTL = 120


def candles(venue: str, symbol: str, interval: str, limit: int, market: str = "spot") -> pd.DataFrame:
    key = (venue, symbol, interval, limit, market)
    with _LOCK:
        hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1].copy()
    df = get_client(venue).candles(symbol, interval, limit, market)
    with _LOCK:
        _CACHE[key] = (time.time(), df)
    return df.copy()


def many(venue: str, symbols: list[str], interval: str, limit: int) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    out, errs = {}, {}

    def one(s):
        try:
            return s, candles(venue, s, interval, limit), None
        except (MarketDataError, Exception) as e:  # noqa: BLE001
            return s, None, str(e)

    with ThreadPoolExecutor(max_workers=4) as ex:
        for s, df, err in ex.map(one, symbols):
            if err:
                errs[s] = err
            else:
                out[s] = df
    return out, errs
