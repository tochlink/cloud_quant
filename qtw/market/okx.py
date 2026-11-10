"""OKX 官方公共 REST v5。文档: https://www.okx.com/docs-v5/en/"""
from __future__ import annotations

import pandas as pd

from qtw.timeutil import from_ms

from .base import INTERVAL_MS, HttpJson, MarketDataError, Quote, finalize

BAR = {"15m": "15m", "1h": "1H", "4h": "4H", "1d": "1Dutc"}
# openapi.okx.com 是 2026-05-20 起官方推荐的 Global REST 域名；www.okx.com 仍可用。
# aws.okx.com 已于 2025-04-28 停用，不再作为默认备用。可用 QTW_OKX_REST_HOST 指定官方域名。
BASES = ["https://openapi.okx.com", "https://www.okx.com"]


def spot_id(sym: str) -> str:
    return f"{sym[:-4]}-USDT" if sym.endswith("USDT") else sym


def swap_id(sym: str) -> str:
    return f"{spot_id(sym)}-SWAP"


class OkxPublic:
    venue = "OKX"
    data_source = "okx_public_rest"

    def __init__(self, *, timeout: float = 15, max_retries: int = 3, backoff: float = 1.0):
        # Gap-fill callers pass a short timeout so a hung REST host cannot pin
        # the stream IO pool for tens of seconds (default stays research-friendly).
        from qtw.net import okx_rest_bases
        self.http = HttpJson(okx_rest_bases(), timeout=timeout, max_retries=max_retries, backoff=backoff)

    def _data(self, path, params):
        j = self.http.get(path, params)
        if str(j.get("code")) != "0":
            raise MarketDataError(f"OKX {path} code={j.get('code')} msg={j.get('msg')}")
        return j.get("data", [])

    def candles(self, symbol: str, interval: str = "4h", limit: int = 300, market: str = "spot") -> pd.DataFrame:
        inst = spot_id(symbol) if market == "spot" else swap_id(symbol)
        rows: list = []
        first = self._data("/api/v5/market/candles", {"instId": inst, "bar": BAR[interval], "limit": min(300, limit)})
        rows.extend(first)
        closed = lambda rs: sum(1 for r in rs if len(r) < 9 or str(r[8]) == "1")  # noqa: E731
        while closed(rows) < limit and rows:
            oldest = min(int(r[0]) for r in rows)
            more = self._data("/api/v5/market/history-candles",
                              {"instId": inst, "bar": BAR[interval], "limit": 100, "after": oldest})
            if not more:
                break
            rows.extend(more)
        # 只保留 confirm=1（已收盘）
        rows = [r for r in rows if len(r) < 9 or str(r[8]) == "1"]
        df = pd.DataFrame(
            [[from_ms(r[0]), r[1], r[2], r[3], r[4], r[5]] for r in rows],
            columns=["open_time", "open", "high", "low", "close", "volume"],
        )
        if not df.empty:
            df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
        df = finalize(df, interval).tail(limit).reset_index(drop=True)
        return self._tag(df, market)

    def _tag(self, df, market):
        from qtw.timeutil import iso, utcnow
        df.attrs.update(venue=self.venue.lower(), market=market, data_source=self.data_source,
                        source_host=self.http.last_host, fetched_at=iso(utcnow()))
        return df

    def _q(self, q: Quote) -> Quote:
        from qtw.timeutil import iso, utcnow
        q.source_host, q.data_source, q.fetched_at = self.http.last_host, self.data_source, iso(utcnow())
        return q

    def quote(self, symbol: str, market: str) -> Quote:
        if market == "spot":
            d = self._data("/api/v5/market/ticker", {"instId": spot_id(symbol)})
            if not d:
                raise MarketDataError(f"OKX 无 {symbol} 现货报价")
            return self._q(Quote(symbol, "spot", float(d[0]["last"]), "last", from_ms(d[0]["ts"]), self.venue))
        d = self._data("/api/v5/public/mark-price", {"instType": "SWAP", "instId": swap_id(symbol)})
        if not d:
            raise MarketDataError(f"OKX 无 {symbol} 永续标记价")
        return self._q(Quote(symbol, "perp", float(d[0]["markPx"]), "mark", from_ms(d[0]["ts"]), self.venue))

    def perp_spec(self, symbol: str) -> dict:
        d = self._data("/api/v5/public/instruments", {"instType": "SWAP", "instId": swap_id(symbol)})
        if not d:
            raise MarketDataError(f"OKX 无 {symbol} 永续合约")
        return {"ct_val": float(d[0]["ctVal"]), "lot_sz": float(d[0]["lotSz"]), "min_sz": float(d[0]["minSz"])}


assert set(BAR) <= set(INTERVAL_MS)
