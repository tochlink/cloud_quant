"""美元广义指数做空闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

想法：美元走弱（风险偏好上升）时加密下行动能弱，此时新开空单胜率差 → 美元低于自身均线时暂不新开空。
数据（只用官方真实值，绝不补造）：FRED DTWEXBGS = 美联储 H.10 名义广义美元指数（日度，每周一发布上一周）。
      公开免 key 接口 https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&cosd=2006-01-01
      （不带 cosd 的全量请求在本机经常超时；带 cosd 时 < 1 秒，数值与研究存档 scratch/macro/DTWEXBGS.csv 逐日相同）。
      空值行（美国假日）丢弃。
缓存：DATA_DIR/fred_DTWEXBGS.csv（data/ 不入库）；每 6 小时刷新一次（运行中自动，无需重启），失败时用已有缓存并记日志。

公式（与研究脚本 scratch/macro/run.py 的 DTWEXBGS_N20_short_on 同口径，docs/usd_broad_dollar_short_gate_paper_4h.md）：
  v_d  = 观测日 d 的指数（只数有值的观测）
  ma_d = 最近 n 个观测（含 d）的均值，默认 n = 20；不足 n 个 → NaN
  diff_d = v_d − ma_d
  可用时刻 known_d = d + lag_days 天 00:00 UTC（默认 10 天，保守覆盖 H.10 周一发布 + 节假日）
  闸门：信号 K 线开盘时间 t 上取 known ≤ t 的最新一个观测；diff ≤ 0（美元不高于 N 日均线，研究里 off = v > ma 的反面）
        时不新开空单（已持空不动，多单不受影响）。
失败开放：取不到数据 / 最新已知观测 known 早于 t − stale_days / 历史不足 → NaN → 不拦，并记录原因。
"""
from __future__ import annotations

import csv
import io
import logging
import threading
import time
import urllib.request

import numpy as np

from .paths import DATA_DIR

log = logging.getLogger(__name__)
FRED_ID = "DTWEXBGS"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}&cosd={cosd}"
COSD = "2006-01-01"
D_MS = 86_400_000
REFRESH_SEC = 6 * 3600.0
RETRY_SEC = 900.0
_LOCK = threading.Lock()
_MEM: dict = {}


def _path():
    return DATA_DIR / f"fred_{FRED_ID}.csv"


def parse_fred(text: str) -> dict[int, float]:
    """FRED fredgraph.csv → {观测日 00:00 UTC 毫秒: 值}；空值 / '.' 行丢弃。"""
    out: dict[int, float] = {}
    rd = csv.reader(io.StringIO(text))
    next(rd, None)
    for row in rd:
        if len(row) < 2:
            continue
        try:
            v = float(row[1])
            y, m, d = (int(x) for x in row[0].split("-"))
        except ValueError:
            continue
        if v > 0:
            out[int(np.datetime64(f"{y:04d}-{m:02d}-{d:02d}", "ms").astype("int64"))] = v
    return out


def _download() -> dict[int, float]:
    # 不设自定义 User-Agent：实测 FRED 对 "qtw/1" / 浏览器 UA 会挂起超时，Python 默认 UA（Python-urllib/3.x）正常返回
    req = urllib.request.Request(URL.format(fid=FRED_ID, cosd=COSD))
    with urllib.request.urlopen(req, timeout=30) as r:
        d = parse_fred(r.read().decode("utf-8", "replace"))
    if not d:
        raise RuntimeError(f"FRED {FRED_ID} 返回空数据")
    return d


def _read_cache() -> dict[int, float]:
    p = _path()
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                v = float(row["value"])
                if v > 0:
                    out[int(row["obs_ms"])] = v
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["obs_ms", "obs_date", "value"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d[k]) for k in sorted(d))
    tmp.replace(_path())


def series(force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (观测日 00:00 UTC 毫秒 升序, 指数值)。按需刷新；失败时返回已有真实数据（可能为空）。"""
    with _LOCK:
        m = _MEM.setdefault(FRED_ID, {"t": 0.0, "rows": None, "err": ""})
        d = m["rows"]
        if d is None:
            d = _read_cache()
            m["rows"] = d
        age = time.time() - float(m["t"] or 0)
        stale = (not d) or max(d) < int(time.time() * 1000) - 10 * D_MS
        if fetch and (force or age >= REFRESH_SEC or (stale and age >= RETRY_SEC)):
            m["t"] = time.time()
            try:
                new = _download()
                if any(d.get(k) != v for k, v in new.items()):
                    d.update(new)
                    _write_cache(d)
                m["err"] = ""
                log.info("FRED %s：共 %d 个观测，最新 %s", FRED_ID, len(d),
                         str(np.datetime64(max(d), "ms").astype("datetime64[D]")) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("FRED %s 拉取失败（闸门失败开放，用已有缓存 %d 个观测）：%s", FRED_ID, len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error() -> str:
    return str((_MEM.get(FRED_ID) or {}).get("err") or "")


def ma_diff(values, n: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """(ma, v − ma)：ma = 最近 n 个观测（含当前）的简单均值，与 pandas rolling(n).mean() 同口径；不足 n 个 → NaN。"""
    v = np.asarray(values, dtype=float)
    ma = np.full(v.shape, np.nan)
    if v.size >= n:
        c = np.cumsum(np.r_[0.0, v])
        ma[n - 1:] = (c[n:] - c[:-n]) / n
    return ma, v - ma


def diff_at(query_ms, obs_ms, values, n: int = 20, lag_days: float = 10, stale_days: float = 14.0) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一个观测的 v − ma（known = 观测日 + lag_days 天 00:00 UTC）；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    ob = np.asarray(obs_ms, dtype="int64")
    if ob.size == 0 or q.size == 0:
        return out
    _, df = ma_diff(values, n)
    known = ob + int(round(float(lag_days) * D_MS))
    j = np.searchsorted(known, q, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = df[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("usd_gate_enabled", False)),
            "n": int(st.get("usd_gate_n", 20) or 20),
            "lag_days": float(st.get("usd_gate_lag_days", 10) or 10),
            "stale_days": float(st.get("usd_gate_stale_days", 14.0) or 14.0)}


def block_mask(st: dict, open_ms, obs_ms=None, values=None) -> tuple[np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开空 bool, v − ma)。闸门关闭时全 False；NaN 不拦。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    if not g["enabled"]:
        return np.zeros(q.shape, dtype=bool), np.full(q.shape, np.nan)
    if obs_ms is None:
        obs_ms, values = series()
    d = diff_at(q, obs_ms, values, g["n"], g["lag_days"], g["stale_days"])
    return np.nan_to_num(d, nan=np.inf) <= 0, d


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知观测与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "series": FRED_ID, "n": g["n"], "lag_days": g["lag_days"], "blocked": False,
           "value": None, "ma": None, "diff": None, "obs_date": None, "known_from": None,
           "eval_open_ms": signal_open_ms, "n_obs": 0, "latest_obs_date": None, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        ob, vs = series()
        out["n_obs"], out["error"] = int(ob.size), last_error()
        if ob.size:
            out["latest_obs_date"] = str(np.datetime64(int(ob[-1]), "ms").astype("datetime64[D]"))
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("美元闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        known = ob + int(round(g["lag_days"] * D_MS))
        j = int(np.searchsorted(known, t, side="right") - 1) if ob.size else -1
        if j >= 0:
            ma, _ = ma_diff(vs, g["n"])
            out["value"] = float(vs[j])
            out["ma"] = float(ma[j]) if ma[j] == ma[j] else None
            out["obs_date"] = str(np.datetime64(int(ob[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
        bl, d = block_mask(st, [t], ob, vs)
        dv = float(d[0])
        out["diff"] = dv if dv == dv else None
        out["blocked"] = bool(bl[0])
        if dv != dv:
            out["fail_open"] = ("无已公布的美元指数数据" if j < 0 else
                                f"最新已知观测过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足 n 个观测")
            log.warning("美元闸门失败开放（不拦）：%s；缓存 %d 个观测；%s", out["fail_open"], ob.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("美元闸门失败开放（不拦）：%s", e)
    return out
