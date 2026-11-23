"""日本财务省（MoF）周度居民对外债券投资闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

想法：日本居民（寿险 / 银行 / 年金等指定报告机构）净买外国中长期债券 = 日元资金外流 / 套息与全球风险偏好上升（risk-on）；
      净买放缓到自身均线以下（资金回流）= risk-off。
数据（只用官方真实值，绝不补造）：财务省「対外及び対内証券売買契約等の状況（週次・指定報告機関ベース）」
      https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/week.csv（Shift-JIS，单位亿日元）
      第 1 部分「対外証券投資（居住者による取得・処分）」中长期债 ネット（第 6 列数值）。2005-01 起；财务省每年不公布跨年那一周（不补）。
缓存：DATA_DIR/mof_itn_week.csv（data/ 不入库）；每 6 小时刷新一次（运行中自动，无需重启），失败时用已有缓存并记日志。

公式（与研究脚本 scratch/mofsec4h/run.py 的 b13_trend26_contra_both 同口径，docs/mof_resident_foreign_bond_flow_gate_4h.md）：
  b_w   = 第 w 个公布周（按周排序，只数有值的周）的居民中长期外债净买
  S_w   = b_w + … + b_{w−12}（最近 13 个公布周之和，sum_n = 13）
  M_w   = S 最近 26 个值（含本周）的均值（trend_n = 26），不足 → NaN
  flag_w = 1 若 S_w > M_w（外流在加速 → risk-on），否则 0
  可用时刻 known_w = 周末（周六）+ 6 天 00:00 UTC（官方下周四 08:50 JST = 周三 23:50 UTC 发布，多留一天吸收节假日顺延）。
  闸门（contra_both）：信号 K 线开盘时间 t 上取 known ≤ t 的最新一周 flag；flag = 1 时不新开空，flag = 0 时不新开多
        （已持同向仓位不动，只拦新开仓 / 反手）。
失败开放：取不到数据 / 最新已知周 known 早于 t − stale_days / 历史不足 → NaN → 不拦，并记录原因。
"""
from __future__ import annotations

import csv
import io
import logging
import re
import threading
import time
import unicodedata
import urllib.request

import numpy as np

from .paths import DATA_DIR

log = logging.getLogger(__name__)
URL = "https://www.mof.go.jp/policy/international_policy/reference/itn_transactions_in_securities/week.csv"
D_MS = 86_400_000
LAG_DAYS = 6
REFRESH_SEC = 6 * 3600.0
RETRY_SEC = 900.0
_LOCK = threading.Lock()
_MEM: dict = {}
_PER = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})~(\d{1,2})\.(\d{1,2})$")


def _path():
    return DATA_DIR / "mof_itn_week.csv"


def _day_ms(y: int, m: int, d: int) -> int:
    return int(np.datetime64(f"{y:04d}-{m:02d}-{d:02d}", "ms").astype("int64"))


def parse_week_csv(text: str) -> dict[int, float]:
    """官方 week.csv 文本 → {周末（周六）00:00 UTC 毫秒: 居民中长期外债净买（亿日元）}。"""
    out: dict[int, float] = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 23 or not row[0].strip():
            continue
        p = unicodedata.normalize("NFKC", row[0]).replace(" ", "")
        m = _PER.match(p)
        if not m:
            continue
        y, m1, d1, m2, d2 = (int(x) for x in m.groups())
        try:
            v = float(row[6].replace(",", "").strip())
        except ValueError:
            continue
        out[_day_ms(y + (1 if m2 < m1 else 0), m2, d2)] = v
    return out


def _download() -> dict[int, float]:
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    d = parse_week_csv(raw.decode("cp932", "replace"))
    if not d:
        raise RuntimeError("MoF week.csv 返回空数据")
    return d


def _read_cache() -> dict[int, float]:
    p = _path()
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[int(row["week_end_ms"])] = float(row["res_ltbond_net"])
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["week_end_ms", "week_end", "res_ltbond_net"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d[k]) for k in sorted(d))
    tmp.replace(_path())


def series(force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (周末 00:00 UTC 毫秒 升序, 居民中长期外债净买)。按需刷新；失败时返回已有真实数据（可能为空）。"""
    with _LOCK:
        m = _MEM.setdefault("mof", {"t": 0.0, "rows": None, "err": ""})
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
                log.info("MoF 周度对外证券：共 %d 周，最新周末 %s", len(d),
                         str(np.datetime64(max(d), "ms").astype("datetime64[D]")) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("MoF 周度对外证券拉取失败（闸门失败开放，用已有缓存 %d 周）：%s", len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error() -> str:
    return str((_MEM.get("mof") or {}).get("err") or "")


def _roll_mean(v: np.ndarray, n: int) -> np.ndarray:
    out = np.full(v.shape, np.nan)
    ok = np.isfinite(v)
    if v.size < n:
        return out
    c = np.cumsum(np.r_[0.0, np.where(ok, v, 0.0)])
    cn = np.cumsum(np.r_[0, ok.astype(int)])
    s = (c[n:] - c[:-n]) / n
    full = (cn[n:] - cn[:-n]) == n
    out[n - 1:] = np.where(full, s, np.nan)
    return out


def flag_series(values, sum_n: int = 13, trend_n: int = 26) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(S, M, flag)：S = 最近 sum_n 周之和，M = S 最近 trend_n 个的均值；flag = 1.0 / 0.0，不足 → NaN（与 pandas rolling 同口径）。"""
    v = np.asarray(values, dtype=float)
    s = _roll_mean(v, sum_n) * sum_n
    ma = _roll_mean(s, trend_n)
    f = np.where(np.isfinite(ma) & np.isfinite(s), (s > ma).astype(float), np.nan)
    return s, ma, f


def flag_at(query_ms, week_end_ms, values, sum_n: int = 13, trend_n: int = 26, stale_days: float = 21.0,
            lag_days: float = LAG_DAYS) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一周 flag（known = 周末 + lag_days 天 00:00 UTC）；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    ob = np.asarray(week_end_ms, dtype="int64")
    if ob.size == 0 or q.size == 0:
        return out
    _, _, f = flag_series(values, sum_n, trend_n)
    known = ob + int(round(float(lag_days) * D_MS))
    j = np.searchsorted(known, q, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = f[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("mof_gate_enabled", False)),
            "sum_n": int(st.get("mof_gate_sum_n", 13) or 13),
            "trend_n": int(st.get("mof_gate_trend_n", 26) or 26),
            "stale_days": float(st.get("mof_gate_stale_days", 21.0) or 21.0)}


def block_mask(st: dict, open_ms, week_end_ms=None, values=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多, 拦新开空, flag)。闸门关闭时全 False；NaN 不拦。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    z = np.zeros(q.shape, dtype=bool)
    if not g["enabled"]:
        return z, z.copy(), np.full(q.shape, np.nan)
    if week_end_ms is None:
        week_end_ms, values = series()
    f = flag_at(q, week_end_ms, values, g["sum_n"], g["trend_n"], g["stale_days"])
    return np.isfinite(f) & (f < 0.5), np.isfinite(f) & (f > 0.5), f


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知周与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "sum_n": g["sum_n"], "trend_n": g["trend_n"], "flag": None,
           "block_long": False, "block_short": False, "s": None, "ma": None, "week_end": None, "known_from": None,
           "eval_open_ms": signal_open_ms, "n_weeks": 0, "latest_week_end": None, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        ob, vs = series()
        out["n_weeks"], out["error"] = int(ob.size), last_error()
        if ob.size:
            out["latest_week_end"] = str(np.datetime64(int(ob[-1]), "ms").astype("datetime64[D]"))
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("MoF 闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        known = ob + int(round(LAG_DAYS * D_MS))
        j = int(np.searchsorted(known, t, side="right") - 1) if ob.size else -1
        if j >= 0:
            s, ma, _ = flag_series(vs, g["sum_n"], g["trend_n"])
            out["s"] = float(s[j]) if s[j] == s[j] else None
            out["ma"] = float(ma[j]) if ma[j] == ma[j] else None
            out["week_end"] = str(np.datetime64(int(ob[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
        bl, bs, f = block_mask(st, [t], ob, vs)
        fv = float(f[0])
        out["flag"] = int(fv) if fv == fv else None
        out["block_long"], out["block_short"] = bool(bl[0]), bool(bs[0])
        if fv != fv:
            out["fail_open"] = ("无已公布的 MoF 周度数据" if j < 0 else
                                f"最新已知周过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足")
            log.warning("MoF 闸门失败开放（不拦）：%s；缓存 %d 周；%s", out["fail_open"], ob.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("MoF 闸门失败开放（不拦）：%s", e)
    return out
