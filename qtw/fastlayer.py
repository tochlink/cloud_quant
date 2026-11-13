"""快速判断层：官方 1m / 5m（10m 由官方 1m 聚合）与 1D K 线，服务于 4h 主账本的风控 / 离场判断。

不是独立的高频策略：
* 盘中顺序：有快周期 K 线时，4h 持仓的止损 / 止盈 / 分批止盈按快周期逐根、按时间先后判定（回测 FastSeries.walk）；
  模拟盘本来就用实时公共报价（WS / REST）轮询止损，等价于更细的粒度。
* 快速离场（strategy.fast_exit_tf，默认 off）：快周期收盘价相对 EMA(n) 逆持仓方向连续 confirm 根 → 平仓（「快速离场」），
  并像止损一样锁定，直到 4h 信号方向改变。回测与引擎都用 ema_break_flags。
只聚合交易所真实已收盘 K 线；缺根时不补、不插值（聚合桶不完整则丢弃该桶）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FAST_MS = {"1m": 60_000, "5m": 300_000, "10m": 600_000}


def aggregate(df: pd.DataFrame, minutes: int, src_minutes: int = 1) -> pd.DataFrame:
    """把官方 src_minutes 分钟 K 线聚合成 minutes 分钟（UTC 对齐）；子 K 线不齐全的桶丢弃。"""
    if df is None or df.empty:
        return pd.DataFrame(columns=["open_time", "open", "high", "low", "close", "volume", "close_time"])
    need = minutes // src_minutes
    d = df.copy()
    ot = pd.to_datetime(d["open_time"], utc=True)
    d["bucket"] = ot.dt.floor(f"{minutes}min")
    g = d.groupby("bucket", sort=True)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                        "close": g["close"].last(), "volume": g["volume"].sum() if "volume" in d else 0.0, "n": g.size()})
    out = out[out["n"] == need].drop(columns="n").reset_index().rename(columns={"bucket": "open_time"})
    out["close_time"] = out["open_time"] + pd.Timedelta(minutes=minutes)
    out.attrs.update(df.attrs)
    out.attrs["aggregated_from"] = f"{src_minutes}m"
    return out[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


def to_ms(open_time) -> np.ndarray:
    """open_time（任意 datetime64 精度 / 带时区）→ UTC 毫秒 int64。pandas 2 可能是 us 精度，不能直接 astype(int64)//1e6。"""
    ts = pd.to_datetime(pd.Series(open_time), utc=True)
    return ts.dt.tz_convert("UTC").astype("datetime64[ms, UTC]").astype("int64").to_numpy()


def ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1)
    out = np.empty(len(x))
    m = float("nan")
    for k, v in enumerate(np.asarray(x, dtype=float)):
        m = v if m != m else a * v + (1 - a) * m
        out[k] = m
    out[: max(0, n - 1)] = np.nan  # 前 n−1 根尚未形成
    return out


def ema_break_flags(close: np.ndarray, n: int, confirm: int) -> tuple[np.ndarray, np.ndarray]:
    """(against_long, against_short)：第 k 根收盘时，最近 confirm 根收盘都在 EMA(n) 下方 / 上方。只用已收盘数据。"""
    c = np.asarray(close, dtype=float)
    e = ema(c, n)
    below = (c < e) & np.isfinite(e)
    above = (c > e) & np.isfinite(e)
    k = max(1, int(confirm))
    if k == 1:
        return below, above
    bl = pd.Series(below).rolling(k).sum().to_numpy() == k
    ab = pd.Series(above).rolling(k).sum().to_numpy() == k
    return bl, ab


class FastSeries:
    """一只标的、一个市场的快周期 K 线（回测用）。t：开盘时间 ms；brk_long / brk_short：逆多 / 逆空的收盘破位标记。"""

    def __init__(self, t, o, h, l, c, step_ms: int, brk_long=None, brk_short=None, min_cover: float = 0.95):
        self.t = np.asarray(t, dtype=np.int64)
        self.o, self.h, self.l, self.c = (np.asarray(x, dtype=float) for x in (o, h, l, c))
        self.step = int(step_ms)
        self.bl = None if brk_long is None else np.asarray(brk_long, dtype=bool)
        self.bs = None if brk_short is None else np.asarray(brk_short, dtype=bool)
        self.min_cover = min_cover

    def walk(self, tr, start: pd.Timestamp, end: pd.Timestamp, *, tp_r: float, ptp, be, fast_exit: bool):
        """按时间顺序逐根快周期 K 线判定 [start, end) 内的事件。返回 [(kind, price, time_iso)]；
        kind ∈ ptp（分批止盈，可多次出现在列表前部）| stop | tp | fast（终止事件，最多一个）。
        覆盖不足（缺 K 线）返回 None，由调用方退回 4h 口径。每根快 K 线内部的顺序规则与 4h 口径相同：
        开盘跳空先算；同一根同时触及止损与止盈时保守地先算止损；快速离场在该根收盘确认，按下一根开盘价成交。"""
        a = int(np.searchsorted(self.t, int(start.value // 1_000_000), "left"))
        b = int(np.searchsorted(self.t, int(end.value // 1_000_000), "left"))
        exp = (int(end.value // 1_000_000) - int(start.value // 1_000_000)) // self.step
        if b <= a or (b - a) < self.min_cover * exp:
            return None
        from .backtest import breakeven_stop, partial_tp_target  # noqa: F401  (公式同源)
        long = tr.side == "long"
        d = 1 if long else -1
        stop = float(tr.stop_price)
        tg = float(tr.target_price) if tp_r > 0 else float("nan")
        pt = partial_tp_target(tr.side, tr.entry_price, tr.init_stop, ptp[0]) if ptp else float("nan")
        brk = (self.bl if long else self.bs) if fast_exit else None
        ev: list = []
        k = a
        while k < b:
            lo, hi, op = self.l[k:b], self.h[k:b], self.o[k:b]
            m = (lo <= stop) if long else (hi >= stop)
            if tg == tg:
                m = m | ((hi >= tg) if long else (lo <= tg))
            if pt == pt:
                m = m | ((hi >= pt) if long else (lo <= pt))
            if brk is not None:
                m = m | brk[k:b]
            if not m.any():
                return ev
            j = k + int(np.argmax(m))
            o, h, l_ = self.o[j], self.h[j], self.l[j]
            when = pd.Timestamp(int(self.t[j]), unit="ms", tz="UTC").isoformat()
            if pt == pt and d * (o - pt) >= 0:  # 开盘已越过分批价
                ev.append(("ptp", float(o), when))
                pt = float("nan")
                if be is not None and d * (be - stop) > 0:
                    stop = float(be)
                continue  # 同一根继续按新止损检查（开盘之后发生）
            if tg == tg and d * (o - tg) >= 0:
                ev.append(("tp", float(o), when))
                return ev
            if (long and l_ <= stop) or (not long and h >= stop):
                ev.append(("stop", float(min(o, stop) if long else max(o, stop)), when))
                return ev
            if tg == tg and ((long and h >= tg) or (not long and l_ <= tg)):
                ev.append(("tp", float(tg), when))
                return ev
            if pt == pt and ((long and h >= pt) or (not long and l_ <= pt)):
                ev.append(("ptp", float(pt), when))
                pt = float("nan")
                if be is not None and d * (be - stop) > 0:
                    stop = float(be)
                k = j + 1  # 保本止损从下一根快 K 线起生效（同一根内先后未知）
                continue
            if brk is not None and brk[j]:
                nx = self.o[j + 1] if j + 1 < len(self.o) and self.t[j + 1] - self.t[j] <= 2 * self.step else self.c[j]
                ev.append(("fast", float(nx), when))
                return ev
            k = j + 1
        return ev
