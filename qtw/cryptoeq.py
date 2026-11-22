"""加密股相对强弱闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

想法：美股上市的加密股（默认 Strategy MSTR，可选 Coinbase COIN）是美股资金对加密风险偏好的代理。
      rs = ln(股票收盘 / BTC) 在最近 n 个交易日下降 = 美股资金在减少加密敞口 → 暂不新开多单。
数据（只用官方真实值，绝不补造）：
  - 股票：Nasdaq 官方历史行情 https://api.nasdaq.com/api/quote/{SYM}/historical（拆股已调整的日收盘）。
  - BTC：同一交易所官方 BTCUSDT 现货 K 线中收盘时刻 = 当日 20:00 UTC 的那根的收盘价（4h 线 = 16:00 开盘那根；
    研究用 OKX 官方现货，scratch/cryptoeq4h/run.py）。
缓存：DATA_DIR/nasdaq_<SYM>_daily.csv（data/ 不入库）；每 2 小时刷新一次，失败时用已有缓存并记日志。

公式（与研究脚本 scratch/cryptoeq4h/run.py 同口径，docs/crypto_equity_relstrength_gate_4h.md）：
  只取股票交易日 D（且当日 20:00 UTC BTC 收盘存在）：rs_D = ln(close_D / BTC20_D)
  chg_D = rs_D − rs_{D 前第 n 个交易日}（默认 n = 20）
  可用时刻 known_D = D + 1 天 00:00 UTC（美股 16:00 ET 收盘 = 20:00 / 21:00 UTC 之后）
  闸门：信号 K 线开盘时间 t 上取 known ≤ t 的最新一日 chg；chg ≤ 0 时不新开多单（已持多不动，空单不受影响）。
失败开放：取不到数据 / 最新已知日早于 t − stale_days / 历史不足 → NaN → 不拦，并记录原因。
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
SYMBOLS = ("MSTR", "COIN")
URL = "https://api.nasdaq.com/api/quote/{sym}/historical?assetclass=stocks&fromdate={start}&limit=9999&todate={end}"
D_MS = 86_400_000
LAG_DAYS = 1
REFRESH_SEC = 2 * 3600.0
RETRY_SEC = 900.0
_LOCK = threading.Lock()
_MEM: dict = {}


def _path(sym: str):
    return DATA_DIR / f"nasdaq_{sym}_daily.csv"


def _day_ms(y: int, m: int, d: int) -> int:
    return int(np.datetime64(f"{y:04d}-{m:02d}-{d:02d}", "ms").astype("int64"))


def parse_nasdaq(text: str) -> dict[int, float]:
    """Nasdaq 官方 historical JSON → {交易日 00:00 UTC 毫秒: 收盘}。"""
    j = json.loads(text)
    rows = (((j or {}).get("data") or {}).get("tradesTable") or {}).get("rows") or []
    out: dict[int, float] = {}
    for r in rows:
        try:
            mo, dd, yy = (int(x) for x in str(r["date"]).split("/"))
            v = float(str(r["close"]).replace("$", "").replace(",", ""))
        except (KeyError, ValueError):
            continue
        if v > 0:
            out[_day_ms(yy, mo, dd)] = v
    return out


def _download(sym: str, days: int = 400) -> dict[int, float]:
    end = pd.Timestamp.now("UTC").normalize()
    start = end - pd.Timedelta(days=days)
    req = urllib.request.Request(URL.format(sym=sym, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d")),
                                 headers={"User-Agent": "Mozilla/5.0 (qtw)", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = parse_nasdaq(r.read().decode("utf-8", "replace"))
    if not d:
        raise RuntimeError(f"Nasdaq {sym} 历史行情为空")
    return d


def _read_cache(sym: str) -> dict[int, float]:
    p = _path(sym)
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                v = float(row["close"])
                if v > 0:
                    out[int(row["date_ms"])] = v
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(sym: str, d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(sym).with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date_ms", "date", "close"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d[k]) for k in sorted(d))
    tmp.replace(_path(sym))


def series(sym: str = "MSTR", force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (交易日 00:00 UTC 毫秒 升序, 收盘)。按需刷新；失败时返回已有真实数据（可能为空）。"""
    sym = str(sym).upper()
    if sym not in SYMBOLS:
        raise ValueError(f"未知加密股 {sym}")
    with _LOCK:
        m = _MEM.setdefault(sym, {"t": 0.0, "rows": None, "err": ""})
        d = m["rows"]
        if d is None:
            d = _read_cache(sym)
            m["rows"] = d
        age = time.time() - float(m["t"] or 0)
        stale = (not d) or max(d) < int(time.time() * 1000) - 2 * D_MS
        if fetch and (force or age >= REFRESH_SEC or (stale and age >= RETRY_SEC)):
            m["t"] = time.time()
            try:
                new = _download(sym, 400 if d else 4000)
                if any(d.get(k) != v for k, v in new.items()):
                    d.update(new)
                    _write_cache(sym, d)
                m["err"] = ""
                log.info("Nasdaq %s：共 %d 个交易日，最新 %s", sym, len(d), max(d) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("Nasdaq %s 拉取失败（闸门失败开放，用已有缓存 %d 日）：%s", sym, len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error(sym: str = "MSTR") -> str:
    return str((_MEM.get(str(sym).upper()) or {}).get("err") or "")


def btc20(btc_df) -> tuple[np.ndarray, np.ndarray]:
    """BTC 现货 K 线 → (日期 00:00 UTC 毫秒, 当日收盘时刻 = 20:00 UTC 那根 K 线的收盘)。只用已存在的 K 线。"""
    if btc_df is None or not len(btc_df):
        return np.zeros(0, dtype="int64"), np.zeros(0)
    if "close_time" in btc_df:
        ct = pd.DatetimeIndex(pd.to_datetime(btc_df["close_time"], utc=True))
    else:
        ot = pd.DatetimeIndex(pd.to_datetime(btc_df["open_time"], utc=True))
        ct = ot + (ot[1] - ot[0] if len(ot) > 1 else pd.Timedelta(hours=4))
    m = (ct.hour == 20) & (ct.minute == 0)
    days = ct[m].normalize().as_unit("ms").asi8
    px = np.asarray(btc_df["close"], dtype=float)[m]
    o = np.argsort(days, kind="stable")
    days, px = days[o], px[o]
    keep = np.r_[days[1:] != days[:-1], True] if days.size else np.zeros(0, bool)
    return days[keep].astype("int64"), px[keep]


def rs_change(stk_ms, stk_close, btc_ms, btc_close, n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """只在股票交易日且有 BTC 20:00 UTC 收盘时计算 rs = ln(股票 / BTC)，返回 (日期毫秒, chg = rs − rs 前第 n 个交易日)。"""
    sk = np.asarray(stk_ms, dtype="int64")
    sv = np.asarray(stk_close, dtype=float)
    bk = np.asarray(btc_ms, dtype="int64")
    bv = np.asarray(btc_close, dtype=float)
    if sk.size == 0 or bk.size == 0:
        return np.zeros(0, dtype="int64"), np.zeros(0)
    pos = np.searchsorted(bk, sk)
    pos_c = np.clip(pos, 0, bk.size - 1)
    ok = (bk[pos_c] == sk) & (sv > 0)
    ok &= bv[pos_c] > 0
    days = sk[ok]
    rs = np.log(sv[ok] / bv[pos_c[ok]])
    chg = np.full(rs.shape, np.nan)
    if rs.size > n:
        chg[n:] = rs[n:] - rs[:-n]
    return days, chg


def chg_at(query_ms, days_ms, chg, stale_days: float = 7.0) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一个交易日的 chg（known = D + 1 天 00:00 UTC）；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    dk = np.asarray(days_ms, dtype="int64")
    if dk.size == 0 or q.size == 0:
        return out
    known = dk + LAG_DAYS * D_MS
    j = np.searchsorted(known, q, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = np.asarray(chg, dtype=float)[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("cryptoeq_gate_enabled", False)),
            "symbol": str(st.get("cryptoeq_gate_symbol", "MSTR") or "MSTR").upper(),
            "n": int(st.get("cryptoeq_gate_n", 20) or 20),
            "stale_days": float(st.get("cryptoeq_gate_stale_days", 7.0) or 7.0)}


def block_mask(st: dict, open_ms, btc_df=None, stk=None) -> tuple[np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多 bool, chg)。闸门关闭时全 False；chg = NaN 不拦。
    stk = (交易日毫秒, 收盘) 可注入真实历史；btc_df = BTCUSDT 现货 K 线（取 20:00 UTC 收盘）。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    if not g["enabled"]:
        return np.zeros(q.shape, dtype=bool), np.full(q.shape, np.nan)
    sk, sv = stk if stk is not None else series(g["symbol"])
    bk, bv = btc20(btc_df)
    days, chg = rs_change(sk, sv, bk, bv, g["n"])
    c = chg_at(q, days, chg, g["stale_days"])
    return np.nan_to_num(c, nan=np.inf) <= 0, c


def state(st: dict, signal_open_ms: int | None, btc_df=None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知交易日与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "symbol": g["symbol"], "n": g["n"], "blocked": False, "chg": None,
           "close": None, "btc20": None, "obs_date": None, "known_from": None, "eval_open_ms": signal_open_ms,
           "n_days": 0, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        sk, sv = series(g["symbol"])
        out["n_days"], out["error"] = int(sk.size), last_error(g["symbol"])
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("加密股闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        bk, bv = btc20(btc_df)
        days, chg = rs_change(sk, sv, bk, bv, g["n"])
        known = days + LAG_DAYS * D_MS
        j = int(np.searchsorted(known, t, side="right") - 1) if days.size else -1
        if j >= 0:
            out["obs_date"] = str(np.datetime64(int(days[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
            out["close"] = float(sv[np.searchsorted(sk, days[j])])
            out["btc20"] = float(bv[np.searchsorted(bk, days[j])])
        bl, c = block_mask(st, [t], btc_df, (sk, sv))
        cv = float(c[0])
        out["chg"] = cv if cv == cv else None
        out["blocked"] = bool(bl[0])
        if cv != cv:
            out["fail_open"] = ("无已公布的加密股 / BTC 数据" if j < 0 else
                                f"最新已知交易日过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足 n 个交易日")
            log.warning("加密股闸门失败开放（不拦）：%s；缓存 %d 日；%s", out["fail_open"], sk.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("加密股闸门失败开放（不拦）：%s", e)
    return out
