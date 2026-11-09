"""公共行情抽象：只用交易所官方公共 REST，无需 API Key。绝不伪造数据。"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import requests

log = logging.getLogger(__name__)

INTERVAL_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
CANDLE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time"]


class MarketDataError(RuntimeError):
    """行情获取失败（HTTP 错误、地区封锁、限频等）。调用方应展示错误，而不是编造价格。"""


@dataclass
class Quote:
    symbol: str
    market: str  # spot | perp
    price: float
    kind: str  # last | mark
    ts: datetime
    venue: str


class HttpJson:
    def __init__(self, base_urls: list[str], timeout: float = 15, max_retries: int = 3, backoff: float = 1.0):
        self.base_urls = base_urls
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "qtw/2.0 (+public market data)", "Accept": "application/json"})

    def get(self, path: str, params: dict | None = None):
        errors: list[str] = []
        for base in self.base_urls:
            for attempt in range(self.max_retries):
                try:
                    r = self.s.get(base + path, params=params, timeout=self.timeout)
                except requests.RequestException as e:
                    errors.append(f"{base}: {type(e).__name__}")
                    time.sleep(self.backoff * (attempt + 1))
                    continue
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (403, 451):
                    # 地区限制：换下一个官方域名，不重试同一个
                    errors.append(f"{base}: HTTP {r.status_code}（可能是地区限制）")
                    break
                if r.status_code == 429 or r.status_code >= 500:
                    wait = float(r.headers.get("Retry-After", self.backoff * (2 ** attempt)))
                    errors.append(f"{base}: HTTP {r.status_code}")
                    time.sleep(min(wait, 10))
                    continue
                errors.append(f"{base}: HTTP {r.status_code} {r.text[:160]}")
                break
        raise MarketDataError("; ".join(errors[-4:]) or "未知错误")


def finalize(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """去重、排序、并剔除任何尚未收盘的 K 线（防前视）。"""
    if df.empty:
        return pd.DataFrame(columns=CANDLE_COLS)
    df = df.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)
    step = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
    df["close_time"] = df["open_time"] + step
    now = pd.Timestamp(datetime.now(timezone.utc))
    df = df[df["close_time"] <= now].reset_index(drop=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df[CANDLE_COLS]


def get_client(venue: str):
    v = venue.lower()
    if v == "okx":
        from .okx import OkxPublic
        return OkxPublic()
    if v in ("gate", "gateio", "gate.io"):
        from .gate import GatePublic
        return GatePublic()
    raise ValueError(f"不支持的交易所: {venue}")
