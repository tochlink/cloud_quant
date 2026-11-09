"""Gate.io 官方公共 REST v4。文档: https://www.gate.io/docs/developers/apiv4/"""
from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from .base import INTERVAL_MS, HttpJson, MarketDataError, Quote, finalize

BASES = ["https://api.gateio.ws/api/v4", "https://api.gate.io/api/v4"]


def pair(sym: str) -> str:
    return f"{sym[:-4]}_USDT" if sym.endswith("USDT") else sym


class GatePublic:
    venue = "Gate"
    data_source = "gate_public_rest"

    def __init__(self, *, timeout: float = 15, max_retries: int = 3, backoff: float = 1.0):
        self.http = HttpJson(BASES, timeout=timeout, max_retries=max_retries, backoff=backoff)

    def candles(self, symbol: str, interval: str = "4h", limit: int = 300, market: str = "spot") -> pd.DataFrame:
        step = INTERVAL_MS[interval] // 1000
        end = int(time.time())
        start = end - step * (limit + 2)
        rows: list = []
        cur = start
        while cur < end:
            to = min(end, cur + step * 900)
            if market == "spot":
                data = self.http.get("/spot/candlesticks",
                                     {"currency_pair": pair(symbol), "interval": interval, "from": cur, "to": to})
                for r in data:
                    # [t, quote_vol, close, high, low, open, base_vol, window_closed]
                    if len(r) >= 8 and str(r[7]).lower() != "true":
                        continue
                    rows.append([int(r[0]), r[5], r[3], r[4], r[2], r[6]])
            else:
                data = self.http.get("/futures/usdt/candlesticks",
                                     {"contract": pair(symbol), "interval": interval, "from": cur, "to": to})
                for r in data:
                    rows.append([int(r["t"]), r["o"], r["h"], r["l"], r["c"], r.get("v", 0)])
            if not isinstance(data, list):
                raise MarketDataError(f"Gate 返回格式异常: {str(data)[:120]}")
            cur = to + 1
        df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume"])
        if not df.empty:
            df["open_time"] = pd.to_datetime(df["open_time"], unit="s", utc=True)
        return self._tag(finalize(df, interval).tail(limit).reset_index(drop=True), market)

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
        now = datetime.now(timezone.utc)
        if market == "spot":
            d = self.http.get("/spot/tickers", {"currency_pair": pair(symbol)})
            if not d:
                raise MarketDataError(f"Gate 无 {symbol} 现货报价")
            return self._q(Quote(symbol, "spot", float(d[0]["last"]), "last", now, self.venue))
        d = self.http.get(f"/futures/usdt/contracts/{pair(symbol)}")
        if not d or "mark_price" not in d:
            raise MarketDataError(f"Gate 无 {symbol} 永续标记价")
        return self._q(Quote(symbol, "perp", float(d["mark_price"]), "mark", now, self.venue))

    def perp_spec(self, symbol: str) -> dict:
        d = self.http.get(f"/futures/usdt/contracts/{pair(symbol)}")
        return {"ct_val": float(d["quanto_multiplier"]), "lot_sz": 1.0, "min_sz": float(d.get("order_size_min", 1))}
