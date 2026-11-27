"""美联储 H.15 商业票据融资利差闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

想法：3 个月 AA 金融类商业票据利率 − 3 个月国库券利率（短端美元融资压力）高于自身均线 = 融资压力上升 → risk-off，暂不新开多单。
数据（只用官方真实值，绝不补造）：FRED（美联储 H.15）DCPF3M（3M AA 金融类 CP）与 DTB3（3M 国库券二级市场），日度；
      公开免 key 接口 https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>&cosd=2010-01-01；两列缺任一值的日期丢弃。
缓存：DATA_DIR/fred_cp_spread.csv（data/ 不入库）；每 6 小时刷新一次（运行中自动，无需重启），失败时用已有缓存并记日志。

公式（与研究脚本 scratch/cpspread4h/run.py 的 FIN3_trend_n60_long_off 同口径，docs/fed_h15_cp_spread_gate_4h.md）：
  s_d  = DCPF3M_d − DTB3_d（百分点）
  x_d  = 最近 5 个有效观测（含 d）的均值（smooth，默认 5）
  ma_d = 最近 n 个 x（含 d）的均值，默认 n = 60；不足 → NaN
  diff_d = x_d − ma_d
  可用时刻 known_d = 下一个工作日 + 1 天 00:00 UTC（H.15 次一工作日下午发布，保守）。
  闸门：信号 K 线开盘时间 t 上取 known ≤ t 的最新一个观测；diff > 0（融资压力高于均线）时不新开多单（已持多不动，空单不受影响）。
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
IDS = ("DCPF3M", "DTB3")
KEY = "cp_spread"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}&cosd={cosd}"
COSD = "2010-01-01"
D_MS = 86_400_000
REFRESH_SEC = 6 * 3600.0
RETRY_SEC = 900.0
_LOCK = threading.Lock()
_MEM: dict = {}


def _path():
    return DATA_DIR / "fred_cp_spread.csv"


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
        out[int(np.datetime64(f"{y:04d}-{m:02d}-{d:02d}", "ms").astype("int64"))] = v
    return out


def spread_from(a: dict[int, float], b: dict[int, float]) -> dict[int, float]:
    """两序列都有值的日期上的 a − b（百分点，四舍五入到 1e-6 去掉浮点噪声）。"""
    return {k: round(a[k] - b[k], 6) for k in a if k in b}


def _download() -> dict[int, float]:
    # 不设自定义 User-Agent：FRED 对自定义 / 浏览器 UA 会挂起超时，Python 默认 UA 正常返回
    got = {}
    for fid in IDS:
        with urllib.request.urlopen(urllib.request.Request(URL.format(fid=fid, cosd=COSD)), timeout=30) as r:
            got[fid] = parse_fred(r.read().decode("utf-8", "replace"))
    d = spread_from(got[IDS[0]], got[IDS[1]])
    if not d:
        raise RuntimeError("FRED DCPF3M / DTB3 返回空数据")
    return d


def _read_cache() -> dict[int, float]:
    p = _path()
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[int(row["obs_ms"])] = float(row["spread"])
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["obs_ms", "obs_date", "spread"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d[k]) for k in sorted(d))
    tmp.replace(_path())


def series(force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (观测日 00:00 UTC 毫秒 升序, 利差 pp)。按需刷新；失败时返回已有真实数据（可能为空）。"""
    with _LOCK:
        m = _MEM.setdefault(KEY, {"t": 0.0, "rows": None, "err": ""})
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
                log.info("FRED CP 利差：共 %d 个观测，最新 %s", len(d),
                         str(np.datetime64(max(d), "ms").astype("datetime64[D]")) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("FRED CP 利差拉取失败（闸门失败开放，用已有缓存 %d 个观测）：%s", len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error() -> str:
    return str((_MEM.get(KEY) or {}).get("err") or "")


def known_ms(obs_ms) -> np.ndarray:
    """观测日 → 下一个工作日 + 1 天 00:00 UTC（毫秒）。"""
    days = (np.asarray(obs_ms, dtype="int64") // D_MS).astype("datetime64[D]")
    nb = np.busday_offset(days, 1, roll="backward")
    return nb.astype("datetime64[ms]").astype("int64") + D_MS


def _roll_mean(v: np.ndarray, n: int) -> np.ndarray:
    out = np.full(v.shape, np.nan)
    if v.size >= n:
        c = np.cumsum(np.r_[0.0, v])
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def x_diff(values, n: int = 60, smooth: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(x, ma, x − ma)：x = smooth 个观测均值，ma = x 的最近 n 个有效值均值（与 pandas rolling(…).mean() 同口径）；不足 → NaN。"""
    v = np.asarray(values, dtype=float)
    x = _roll_mean(v, int(smooth))
    ma = np.full(v.shape, np.nan)
    ok = np.isfinite(x)
    ma[ok] = _roll_mean(x[ok], int(n))
    return x, ma, x - ma


def diff_at(query_ms, obs_ms, values, n: int = 60, smooth: int = 5, stale_days: float = 10.0) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一个观测的 x − ma；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    ob = np.asarray(obs_ms, dtype="int64")
    if ob.size == 0 or q.size == 0:
        return out
    _, _, df = x_diff(values, n, smooth)
    known = known_ms(ob)
    j = np.searchsorted(known, q, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = df[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("cp_gate_enabled", False)),
            "n": int(st.get("cp_gate_n", 60) or 60),
            "smooth": int(st.get("cp_gate_smooth", 5) or 5),
            "stale_days": float(st.get("cp_gate_stale_days", 10.0) or 10.0)}


def block_mask(st: dict, open_ms, obs_ms=None, values=None) -> tuple[np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多 bool, x − ma)。闸门关闭时全 False；NaN 不拦。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    if not g["enabled"]:
        return np.zeros(q.shape, dtype=bool), np.full(q.shape, np.nan)
    if obs_ms is None:
        obs_ms, values = series()
    d = diff_at(q, obs_ms, values, g["n"], g["smooth"], g["stale_days"])
    return np.nan_to_num(d, nan=-np.inf) > 0, d


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知观测与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "series": "DCPF3M-DTB3", "n": g["n"], "smooth": g["smooth"], "blocked": False,
           "spread": None, "x": None, "ma": None, "diff": None, "obs_date": None, "known_from": None,
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
            log.warning("CP 利差闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        known = known_ms(ob) if ob.size else np.zeros(0, "int64")
        j = int(np.searchsorted(known, t, side="right") - 1) if ob.size else -1
        if j >= 0:
            x, ma, _ = x_diff(vs, g["n"], g["smooth"])
            out["spread"] = float(vs[j])
            out["x"] = float(x[j]) if x[j] == x[j] else None
            out["ma"] = float(ma[j]) if ma[j] == ma[j] else None
            out["obs_date"] = str(np.datetime64(int(ob[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
        bl, d = block_mask(st, [t], ob, vs)
        dv = float(d[0])
        out["diff"] = dv if dv == dv else None
        out["blocked"] = bool(bl[0])
        if dv != dv:
            out["fail_open"] = ("无已公布的 CP 利差数据" if j < 0 else
                                f"最新已知观测过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足")
            log.warning("CP 利差闸门失败开放（不拦）：%s；缓存 %d 个观测；%s", out["fail_open"], ob.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("CP 利差闸门失败开放（不拦）：%s", e)
    return out
