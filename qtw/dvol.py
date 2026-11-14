"""Deribit 官方 DVOL（30 天隐含波动率指数）1h 序列：只读公共接口，不需要密钥。

接口：GET https://www.deribit.com/api/v2/public/get_volatility_index_data
      ?currency=ETH&start_timestamp=…&end_timestamp=…&resolution=3600（每次最多约 1000 根，分页拉取）。
时间戳 ts_ms = 该小时线开盘时间；接口也返回进行中的当前小时线，这里丢弃，只保存已收盘的小时线（ts_ms + 1h ≤ 现在），
与 1h K 线 open_time「收盘后已知」的对齐方式相同。
缓存：data/dvol_<CUR>_1h.csv（不入库），只追加真实返回值；拉取失败时返回已有缓存，绝不补造数据。
"""
from __future__ import annotations

import csv
import json
import logging
import threading
import time
import urllib.request

import numpy as np
import pandas as pd

from .paths import DATA_DIR

log = logging.getLogger(__name__)
URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
H_MS = 3_600_000
_LOCK = threading.Lock()
_MEM: dict[str, tuple[float, pd.Series]] = {}
REFRESH_SEC = 300.0
FIRST_MS = 1616544000000  # 2021-03-24：Deribit DVOL 公开序列起点附近
_NO_OLDER: set[str] = set()


def _path(cur: str):
    return DATA_DIR / f"dvol_{cur.upper()}_1h.csv"


def _read_cache(cur: str) -> pd.Series:
    p = _path(cur)
    if not p.exists():
        return pd.Series(dtype=float)
    d = pd.read_csv(p)
    return d.drop_duplicates("ts_ms", keep="last").set_index("ts_ms")["close"].astype(float).sort_index()


def _fetch(cur: str, start_ms: int, end_ms: int) -> list[tuple[int, float]]:
    out, t = [], int(start_ms)
    while t < end_ms:
        e = min(t + 999 * H_MS, end_ms)
        u = f"{URL}?currency={cur.upper()}&start_timestamp={t}&end_timestamp={e}&resolution=3600"
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "qtw/1"}), timeout=15) as r:
            data = json.load(r)["result"]["data"]
        done = int(time.time() * 1000) - H_MS  # 进行中的小时线（ts + 1h > 现在）丢弃，收盘后再取
        out += [(int(x[0]), float(x[4])) for x in data if int(x[0]) <= done]
        t = e
    return out


def series(cur: str = "ETH", start_ms: int | None = None, end_ms: int | None = None) -> pd.Series:
    """返回 {ts_ms: DVOL close}（升序）。缺口只按缓存 + 接口真实返回补齐；失败时返回已有部分。"""
    cur = cur.upper()
    now = int(time.time() * 1000)
    end_ms = int(end_ms or now)
    with _LOCK:
        hit = _MEM.get(cur)
        s = hit[1] if hit else _read_cache(cur)
        fresh = hit is not None and time.time() - hit[0] < REFRESH_SEC
        need_new = not fresh and (s.empty or s.index[-1] < min(end_ms, now) - 2 * H_MS)
        need_old = (start_ms is not None and not s.empty and s.index[0] > max(int(start_ms), FIRST_MS) + 24 * H_MS
                    and cur not in _NO_OLDER)
        try:
            rows = []
            if s.empty:
                rows = _fetch(cur, int(start_ms if start_ms is not None else now - 400 * H_MS), now)
            else:
                if need_old:
                    old = _fetch(cur, max(int(start_ms), FIRST_MS), int(s.index[0]))
                    if not old:
                        _NO_OLDER.add(cur)
                    rows += old
                if need_new:
                    rows += _fetch(cur, int(s.index[-1]) + H_MS, now)
            if rows:
                add = pd.Series({t: v for t, v in rows}, dtype=float)
                s = pd.concat([s, add]).groupby(level=0).last().sort_index()
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                with open(_path(cur), "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["ts_ms", "close"])
                    w.writerows((int(k), float(v)) for k, v in s.items())
        except Exception as e:  # 网络失败：只用已有真实数据
            log.warning("DVOL %s 拉取失败：%s", cur, e)
        _MEM[cur] = (time.time(), s)
    return s


def zscore_on(idx_ms: np.ndarray, s: pd.Series, window: int = 168) -> np.ndarray:
    """把 DVOL 对齐到 1h K 线 open_time（ms），算 window 小时滚动 z 分数；缺数据处为 nan（不触发）。"""
    v = s.reindex(idx_ms).ffill(limit=3).to_numpy(dtype=float) if len(s) else np.full(len(idx_ms), np.nan)
    x = pd.Series(v)
    return ((x - x.rolling(window).mean()) / x.rolling(window).std()).to_numpy()


def idx_to_ms(idx) -> np.ndarray | None:
    """K 线索引（open_time）→ UTC 毫秒；无法识别为时间则返回 None。"""
    try:
        if isinstance(idx, pd.RangeIndex):
            return None
        if np.issubdtype(np.asarray(idx).dtype, np.integer):
            a = np.asarray(idx, dtype="int64")
            return a if a.size and a.max() > 10**12 else None
        return pd.DatetimeIndex(pd.to_datetime(idx, utc=True)).as_unit("ms").asi8.copy()
    except Exception:
        return None
