"""OKX 官方 USDT 借贷利率体制闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

数据：OKX 官方公共接口（不需要密钥）
      GET https://openapi.okx.com|www.okx.com/api/v5/finance/savings/lending-rate-history?ccy=USDT&limit=100[&after=ts]
      逐小时 `lendingRate`（年化），`after` 向更早分页。只保存接口真实返回值，绝不补造。
缓存：DATA_DIR/okx_usdt_lending_rate_1h.csv（data/ 不入库）。首次至少回补 BACKFILL_DAYS 天；
      之后每小时（REFRESH_SEC）向新增量拉取；最新一条落后 > 2h 时每 5 分钟重试。拉取失败只用已有缓存并记日志。

公式（与 scratch/lend/run.py 研究口径一致，docs/STRATEGY_FORMULAS.md「OKX 官方 USDT 借贷利率体制闸门」）：
  r(t)  = 时间戳 ≤ t 的最近一条小时 lendingRate（小时网格前向填充）
  z(t)  = (r − mean_{W 天小时 r}) / std_{W 天小时 r}（窗口 W·24 个小时点、至少 W·12 个点、样本标准差 ddof=1）
  闸门：z > q 时不新开多单（已持多不动，空单不受影响）。
  t 取「信号 K 线（最近已收盘那根）」的开盘时间 —— 回测第 i 根开盘入场用第 i−1 根的信号与 z(open_{i−1})，
  模拟盘在第 i−1 根收盘后决策用 z(open_{i−1})，两边逐位同口径，且只用时间戳 ≤ 该开盘时间的利率（无前视）。
失败开放（fail-open）：数据取不到 / 最新利率早于 t − stale_hours / 历史不足 → z = NaN → 不拦，并记录原因。
"""
from __future__ import annotations

import csv
import json
import logging
import threading
import time
import urllib.request

import numpy as np

from .paths import DATA_DIR

log = logging.getLogger(__name__)
PATH_NAME = "okx_usdt_lending_rate_1h.csv"
API_PATH = "/api/v5/finance/savings/lending-rate-history"
H_MS = 3_600_000
REFRESH_SEC = 3600.0
RETRY_SEC = 300.0
BACKFILL_DAYS = 45
FIRST_MS = 1639440000000  # 2021-12-14：OKX USDT 借贷利率公开历史起点附近
_LOCK = threading.Lock()
_MEM: dict = {"t": 0.0, "rows": None, "err": "", "no_older": False}


def _path():
    return DATA_DIR / PATH_NAME


def _bases() -> list[str]:
    try:
        from .net import okx_rest_bases
        return list(okx_rest_bases()) or ["https://www.okx.com"]
    except Exception:  # noqa: BLE001
        return ["https://openapi.okx.com", "https://www.okx.com"]


def _get_page(after: int | None) -> list[tuple[int, float]]:
    q = f"?ccy=USDT&limit=100" + (f"&after={int(after)}" if after else "")
    last = None
    for base in _bases():
        for k in range(3):
            try:
                req = urllib.request.Request(base.rstrip("/") + API_PATH + q, headers={"User-Agent": "qtw/1"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    j = json.load(r)
                if str(j.get("code")) != "0":
                    raise RuntimeError(f"OKX code {j.get('code')}: {j.get('msg')}")
                return [(int(x["ts"]), float(x["lendingRate"])) for x in j.get("data", []) if x.get("lendingRate") not in (None, "")]
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(0.5 + k)
    raise RuntimeError(f"借贷利率拉取失败：{last}")


def _read_cache() -> dict[int, float]:
    p = _path()
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[int(row["ts_ms"])] = float(row["lending_rate"])
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_ms", "lending_rate"])
        w.writerows((k, d[k]) for k in sorted(d))
    tmp.replace(_path())


def _fetch_new(d: dict[int, float], stop_ms: int) -> int:
    """从最新一页往更早翻，直到与缓存重叠（或到 stop_ms）。返回新增条数。"""
    n, after, newest = 0, None, (max(d) if d else None)
    while True:
        page = _get_page(after)
        if not page:
            break
        for t, v in page:
            if t not in d:
                n += 1
            d[t] = v
        oldest = min(t for t, _ in page)
        if (newest is not None and oldest <= newest) or oldest <= stop_ms:
            break
        after = oldest
        time.sleep(0.2)
    return n


def _fetch_old(d: dict[int, float], start_ms: int) -> int:
    n, after = 0, min(d)
    while after > start_ms:
        page = _get_page(after)
        if not page:
            _MEM["no_older"] = True
            break
        for t, v in page:
            if t not in d:
                n += 1
            d[t] = v
        after = min(t for t, _ in page)
        time.sleep(0.2)
    return n


def series(start_ms: int | None = None, force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (ts_ms 升序, lendingRate)。按需刷新缓存；失败时返回已有真实数据（可能为空）。"""
    now_ms = int(time.time() * 1000)
    with _LOCK:
        d = _MEM["rows"]
        if d is None:
            d = _read_cache()
            _MEM["rows"] = d
        age = time.time() - float(_MEM["t"] or 0)
        stale = (not d) or max(d) < now_ms - 2 * H_MS
        want_old = (start_ms is not None and d and min(d) > max(int(start_ms), FIRST_MS) + 24 * H_MS and not _MEM["no_older"])
        if fetch and (force or age >= REFRESH_SEC or (stale and age >= RETRY_SEC) or want_old):
            _MEM["t"] = time.time()
            try:
                added = 0
                if not d:
                    added += _fetch_new(d, now_ms - BACKFILL_DAYS * 86_400_000)
                else:
                    added += _fetch_new(d, max(d))
                floor_ms = min(int(start_ms), now_ms - BACKFILL_DAYS * 86_400_000) if start_ms is not None else now_ms - BACKFILL_DAYS * 86_400_000
                if d and min(d) > max(floor_ms, FIRST_MS) + 24 * H_MS and not _MEM["no_older"]:
                    added += _fetch_old(d, max(floor_ms, FIRST_MS))
                if added:
                    _write_cache(d)
                _MEM["err"] = ""
                log.info("OKX USDT 借贷利率：新增 %d 条，共 %d 条，最新 ts=%s", added, len(d), max(d) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                _MEM["err"] = str(e)[:300]
                log.warning("OKX USDT 借贷利率拉取失败（闸门失败开放，用已有缓存 %d 条）：%s", len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error() -> str:
    return str(_MEM.get("err") or "")


def zscore_at(query_ms, ts_ms, rates, window_days: int = 30, stale_hours: float = 6.0) -> np.ndarray:
    """对每个查询时间 t（UTC 毫秒）返回 z(t)，只用 ts ≤ t 的利率；不可用时为 NaN（失败开放）。
    与研究脚本同口径：小时网格前向填充 → 滚动 W·24 点均值 / 样本标准差（至少 W·12 点）。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    ts = np.asarray(ts_ms, dtype="int64")
    rv = np.asarray(rates, dtype=float)
    if ts.size == 0 or q.size == 0:
        return out
    o = np.argsort(ts, kind="stable")
    ts, rv = ts[o], rv[o]
    g0 = (ts[0] // H_MS) * H_MS
    grid = np.arange(g0, ts[-1] + 1, H_MS, dtype="int64")
    pos = np.searchsorted(ts, grid, side="right") - 1  # 每个网格点：ts ≤ 网格时间的最后一条
    gv = rv[pos]
    n, mp = int(window_days) * 24, int(window_days) * 12
    cs = np.concatenate([[0.0], np.cumsum(gv)])
    cs2 = np.concatenate([[0.0], np.cumsum(gv * gv)])
    i = np.arange(len(grid))
    lo = np.maximum(0, i - n + 1)
    cnt = (i - lo + 1).astype(float)
    s1, s2 = cs[i + 1] - cs[lo], cs2[i + 1] - cs2[lo]
    mean = s1 / cnt
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (s2 - cnt * mean * mean) / (cnt - 1)
        var = np.where(var < 0, 0.0, var)
        sd = np.sqrt(var)
        z = (gv - mean) / sd
    z[(cnt < mp) | ~(sd > 1e-12)] = np.nan
    k = np.searchsorted(grid, q, side="right") - 1  # 网格点 ≤ t
    ok = k >= 0
    lt = np.searchsorted(ts, q, side="right") - 1   # 实际最新一条 ts ≤ t
    fresh = (lt >= 0) & ((q - ts[np.clip(lt, 0, None)]) <= float(stale_hours) * H_MS)
    m = ok & fresh
    out[m] = z[k[m]]
    return out


def blocks_long(z, q: float) -> np.ndarray:
    """z > q 才拦新开多；NaN（数据不可用）不拦。"""
    za = np.asarray(z, dtype=float)
    return np.nan_to_num(za, nan=-np.inf) > float(q)


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("lending_gate_enabled", False)), "W": int(st.get("lending_gate_window_days", 30) or 30),
            "q": float(st.get("lending_gate_z", 1.0) if st.get("lending_gate_z") is not None else 1.0),
            "side": str(st.get("lending_gate_side", "long") or "long"),
            "stale_hours": float(st.get("lending_gate_stale_hours", 6.0) or 6.0)}


def block_mask(st: dict, open_ms, ts_ms=None, rates=None) -> tuple[np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多 bool, z)。闸门关闭时全 False。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    if not g["enabled"]:
        return np.zeros(q.shape, dtype=bool), np.full(q.shape, np.nan)
    if ts_ms is None:
        start = int(q.min()) - (g["W"] + 2) * 86_400_000 if q.size else None
        ts_ms, rates = series(start_ms=start)
    z = zscore_at(q, ts_ms, rates, g["W"], g["stale_hours"])
    return blocks_long(z, g["q"]), z


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新利率与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "window_days": g["W"], "z_max": g["q"], "side": g["side"], "blocked": False,
           "z": None, "rate": None, "rate_ts": None, "eval_open_ms": signal_open_ms, "n_rates": 0, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        ts, rv = series(start_ms=(int(signal_open_ms) if signal_open_ms else int(time.time() * 1000)) - (g["W"] + 2) * 86_400_000)
        out["n_rates"] = int(ts.size)
        out["error"] = last_error()
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("借贷利率闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        j = int(np.searchsorted(ts, t, side="right") - 1) if ts.size else -1
        if j >= 0:
            out["rate"], out["rate_ts"] = float(rv[j]), int(ts[j])
        bl, z = block_mask(st, [t], ts, rv)
        zv = float(z[0])
        out["z"] = zv if zv == zv else None
        out["blocked"] = bool(bl[0])
        if zv != zv:
            out["fail_open"] = ("无 ≤ 开盘时间的利率" if j < 0 else
                                f"最新利率过旧（> {g['stale_hours']:g}h）" if (t - int(ts[j])) > g["stale_hours"] * H_MS else
                                f"历史不足 {g['W'] * 12} 个小时点")
            log.warning("借贷利率闸门失败开放（不拦）：%s；缓存 %d 条；%s", out["fail_open"], ts.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("借贷利率闸门失败开放（不拦）：%s", e)
    return out
