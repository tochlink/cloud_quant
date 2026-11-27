"""美联储贴现窗口一级信贷（Primary Credit）周度使用量闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

想法：美国银行向美联储贴现窗口借一级信贷 = 银行融资压力的后备借款；使用量高于自身 13 周均线（压力上升）= risk-off → 不新开多；
      低于均线（压力回落）= risk-on → 不新开空（both 侧）。
数据（只用官方真实值，绝不补造）：美联储 H.4.1「Loans: Primary credit」周三水平（百万美元），FRED 官方序列 WLCFLPCL
      https://fred.stlouisfed.org/graph/fredgraph.csv?id=WLCFLPCL（2002-12 起）。
缓存：DATA_DIR/fed_primary_credit_weekly.csv（data/ 不入库）；每 6 小时刷新一次（运行中自动，无需重启），失败时用已有缓存并记日志。

公式（与研究脚本 scratch/fedswap4h/run.py 的 pcr_trend_n13_both 同口径，docs/fed_backstop_lending_gate_4h.md）：
  x_w    = 第 w 个公布周三的一级信贷余额（按日期排序，只数有值的周）
  M_w    = x 最近 13 个值（含本周）的均值（trend_n = 13），不足 → NaN
  flag_w = 1 若 x_w > M_w（后备借款上升 = 融资压力），否则 0
  可用时刻 known_w = 周三 + 3 天 00:00 UTC（H.4.1 周四 16:30 ET 发布，多留一天吸收节假日顺延）。
  闸门（both）：信号 K 线开盘时间 t 上取 known ≤ t 的最新一周 flag；flag = 1 时不新开多，flag = 0 时不新开空
        （已持同向仓位不动，只拦新开仓 / 反手）。
失败开放：取不到数据 / 最新已知周 known 早于 t − stale_days / 历史不足 → NaN → 不拦，并记录原因。
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
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WLCFLPCL"
D_MS = 86_400_000
LAG_DAYS = 3
REFRESH_SEC = 6 * 3600.0
RETRY_SEC = 900.0
_LOCK = threading.Lock()
_MEM: dict = {}


def _path():
    return DATA_DIR / "fed_primary_credit_weekly.csv"


def _day_ms(s: str) -> int:
    return int(np.datetime64(s.strip()[:10], "ms").astype("int64"))


def parse_fred_csv(text: str) -> dict[int, float]:
    """FRED fredgraph.csv 文本 → {周三 00:00 UTC 毫秒: 一级信贷余额（百万美元）}；缺值（"."）跳过。"""
    out: dict[int, float] = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2 or not row[0][:2] in ("19", "20"):
            continue
        try:
            out[_day_ms(row[0])] = float(row[1])
        except ValueError:
            continue
    return out


def _download() -> dict[int, float]:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    d = parse_fred_csv(raw.decode("utf-8", "replace"))
    if not d:
        raise RuntimeError("FRED WLCFLPCL 返回空数据")
    return d


def _read_cache() -> dict[int, float]:
    p = _path()
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[int(row["wed_ms"])] = float(row["primary_credit_musd"])
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wed_ms", "wed", "primary_credit_musd"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d[k]) for k in sorted(d))
    tmp.replace(_path())


def series(force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (周三 00:00 UTC 毫秒 升序, 一级信贷余额)。按需刷新；失败时返回已有真实数据（可能为空）。"""
    with _LOCK:
        m = _MEM.setdefault("pcr", {"t": 0.0, "rows": None, "err": ""})
        d = m["rows"]
        if d is None:
            d = _read_cache()
            m["rows"] = d
        age = time.time() - float(m["t"] or 0)
        stale = (not d) or max(d) < int(time.time() * 1000) - 9 * D_MS
        if fetch and (force or age >= REFRESH_SEC or (stale and age >= RETRY_SEC)):
            m["t"] = time.time()
            try:
                new = _download()
                if any(d.get(k) != v for k, v in new.items()):
                    d.update(new)
                    _write_cache(d)
                m["err"] = ""
                log.info("FRED 一级信贷 WLCFLPCL：共 %d 周，最新周三 %s", len(d),
                         str(np.datetime64(max(d), "ms").astype("datetime64[D]")) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("FRED 一级信贷拉取失败（闸门失败开放，用已有缓存 %d 周）：%s", len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error() -> str:
    return str((_MEM.get("pcr") or {}).get("err") or "")


def flag_series(values, trend_n: int = 13) -> tuple[np.ndarray, np.ndarray]:
    """(M, flag)：M = 最近 trend_n 个值（含本周）的均值；flag = 1.0 / 0.0，不足 → NaN（与 pandas rolling 同口径）。"""
    v = np.asarray(values, dtype=float)
    n = int(trend_n)
    ma = np.full(v.shape, np.nan)
    if v.size >= n:
        c = np.cumsum(np.r_[0.0, v])
        ma[n - 1:] = (c[n:] - c[:-n]) / n
    f = np.where(np.isfinite(ma) & np.isfinite(v), (v > ma).astype(float), np.nan)
    return ma, f


def flag_at(query_ms, wed_ms, values, trend_n: int = 13, stale_days: float = 21.0,
            lag_days: float = LAG_DAYS) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一周 flag（known = 周三 + lag_days 天 00:00 UTC）；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    ob = np.asarray(wed_ms, dtype="int64")
    if ob.size == 0 or q.size == 0:
        return out
    _, f = flag_series(values, trend_n)
    known = ob + int(round(float(lag_days) * D_MS))
    j = np.searchsorted(known, q, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = f[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("backstop_gate_enabled", False)),
            "trend_n": int(st.get("backstop_gate_trend_n", 13) or 13),
            "stale_days": float(st.get("backstop_gate_stale_days", 21.0) or 21.0)}


def block_mask(st: dict, open_ms, wed_ms=None, values=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多, 拦新开空, flag)。闸门关闭时全 False；NaN 不拦。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    z = np.zeros(q.shape, dtype=bool)
    if not g["enabled"]:
        return z, z.copy(), np.full(q.shape, np.nan)
    if wed_ms is None:
        wed_ms, values = series()
    f = flag_at(q, wed_ms, values, g["trend_n"], g["stale_days"])
    return np.isfinite(f) & (f > 0.5), np.isfinite(f) & (f < 0.5), f


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知周与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "trend_n": g["trend_n"], "flag": None, "block_long": False, "block_short": False,
           "x": None, "ma": None, "wed": None, "known_from": None, "eval_open_ms": signal_open_ms, "n_weeks": 0,
           "latest_wed": None, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        ob, vs = series()
        out["n_weeks"], out["error"] = int(ob.size), last_error()
        if ob.size:
            out["latest_wed"] = str(np.datetime64(int(ob[-1]), "ms").astype("datetime64[D]"))
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("一级信贷闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        known = ob + int(round(LAG_DAYS * D_MS))
        j = int(np.searchsorted(known, t, side="right") - 1) if ob.size else -1
        if j >= 0:
            ma, _ = flag_series(vs, g["trend_n"])
            out["x"] = float(vs[j])
            out["ma"] = round(float(ma[j]), 1) if ma[j] == ma[j] else None
            out["wed"] = str(np.datetime64(int(ob[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
        bl, bs, f = block_mask(st, [t], ob, vs)
        fv = float(f[0])
        out["flag"] = int(fv) if fv == fv else None
        out["block_long"], out["block_short"] = bool(bl[0]), bool(bs[0])
        if fv != fv:
            out["fail_open"] = ("无已公布的一级信贷周度数据" if j < 0 else
                                f"最新已知周过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足")
            log.warning("一级信贷闸门失败开放（不拦）：%s；缓存 %d 周；%s", out["fail_open"], ob.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("一级信贷闸门失败开放（不拦）：%s", e)
    return out
