"""Gate 官方 BTC 3 倍杠杆代币（BTC3L / BTC3S）多空成交额比闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

想法：Gate 的 BTC3L（3 倍做多）/ BTC3S（3 倍做空）杠杆代币主要是现货账户散户在用；两者 7 日成交额之比 = 散户方向性杠杆需求。
      比值高于自身 90 日均线（散户杠杆偏多上升）= 顺势确认 → 不新开空；低于均线 → 不新开多（contra_both 侧，确认式）。
      注意：研究里预注册的「反向（拥挤 → 拦多）」先验 ls7_trend_n30_long_off 被否决（0/9），本闸门是非先验的确认方向，只做纸面前向检验。
数据（只用官方真实值，绝不补造）：Gate.io 官方公开 API v4 /spot/candlesticks?currency_pair=BTC3L_USDT|BTC3S_USDT&interval=1d
      （UTC 日 K，第 2 列 = 计价币 USDT 成交额；2020-02-26 起）。只用已收盘的完整 UTC 日；零成交日（交易所数据缺口）当作缺失。
缓存：DATA_DIR/gate_levtoken_btc_daily.csv（data/ 不入库）；每 1 小时刷新一次（运行中自动，无需重启），失败时用已有缓存并记日志。

公式（与研究脚本 scratch/levtok4h/run.py 的 lsbtc7_trend_n90_contra_both 同口径，docs/gate_leveraged_token_flow_gate_4h.md）：
  x_d    = ln( Σ_{7 日} qv(BTC3L) / Σ_{7 日} qv(BTC3S) )，窗口内任一日缺失 → NaN（按连续 UTC 日历，不跳日）
  M_d    = x 最近 90 个日历日（含当日）的均值，窗口内有 NaN 或不足 → NaN
  flag_d = 1 若 x_d > M_d，否则 0
  可用时刻 known_d = 日 D + 28 小时（D+1 00:00 UTC 日 K 收盘后再多等一根 4h，即 D+1 04:00 UTC）。
  闸门（contra_both）：信号 K 线开盘时间 t 上取 known ≤ t 的最新一日 flag；flag = 1 时不新开空，flag = 0 时不新开多
        （已持同向仓位不动，只拦新开仓 / 反手）。
失败开放：取不到数据 / 最新已知日 known 早于 t − stale_days / 历史不足 → NaN → 不拦，并记录原因。
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
URL = "https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1d&limit={limit}"
PAIRS = ("BTC3L_USDT", "BTC3S_USDT")
D_MS = 86_400_000
LAG_MS = 28 * 3_600_000
REFRESH_SEC = 3600.0
RETRY_SEC = 600.0
_LOCK = threading.Lock()
_MEM: dict = {}


def _path():
    return DATA_DIR / "gate_levtoken_btc_daily.csv"


def parse_candles(rows, now_ms: int | None = None) -> dict[int, float]:
    """Gate v4 candlesticks JSON 行 → {UTC 日 00:00 毫秒: 计价成交额}；只保留已收盘的完整日。"""
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    out: dict[int, float] = {}
    for r in rows or []:
        try:
            t = int(float(r[0])) * 1000
            qv = float(r[1])
        except (TypeError, ValueError, IndexError):
            continue
        if t % D_MS or t + D_MS > now_ms:
            continue  # 未收盘的当日 K 不用
        out[t] = qv
    return out


def _download(limit: int = 400) -> dict[str, dict[int, float]]:
    out = {}
    for p in PAIRS:
        req = urllib.request.Request(URL.format(pair=p, limit=int(limit)), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = parse_candles(json.loads(r.read().decode("utf-8", "replace")))
        if not d:
            raise RuntimeError(f"Gate {p} 日 K 返回空数据")
        out[p] = d
    return out


def _read_cache() -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {p: {} for p in PAIRS}
    p_ = _path()
    if not p_.exists():
        return out
    with open(p_, newline="") as f:
        for row in csv.DictReader(f):
            try:
                t = int(row["day_ms"])
                out["BTC3L_USDT"][t] = float(row["qv_btc3l"])
                out["BTC3S_USDT"][t] = float(row["qv_btc3s"])
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(d: dict[str, dict[int, float]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    ks = sorted(set(d["BTC3L_USDT"]) & set(d["BTC3S_USDT"]))
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["day_ms", "day", "qv_btc3l", "qv_btc3s"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d["BTC3L_USDT"][k], d["BTC3S_USDT"][k]) for k in ks)
    tmp.replace(_path())


def series(force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 (UTC 日 00:00 毫秒 升序, BTC3L 成交额, BTC3S 成交额)，只含两边都有值的日。按需刷新；失败时返回已有真实数据。"""
    with _LOCK:
        m = _MEM.setdefault("lt", {"t": 0.0, "rows": None, "err": ""})
        d = m["rows"]
        if d is None:
            d = _read_cache()
            m["rows"] = d
        age = time.time() - float(m["t"] or 0)
        have = set(d["BTC3L_USDT"]) & set(d["BTC3S_USDT"])
        stale = (not have) or max(have) < int(time.time() * 1000) - 2 * D_MS
        if fetch and (force or age >= REFRESH_SEC or (stale and age >= RETRY_SEC)):
            m["t"] = time.time()
            try:
                new = _download()
                changed = False
                for p in PAIRS:
                    for k, v in new[p].items():
                        if d[p].get(k) != v:
                            d[p][k] = v
                            changed = True
                if changed:
                    _write_cache(d)
                m["err"] = ""
                have = set(d["BTC3L_USDT"]) & set(d["BTC3S_USDT"])
                log.info("Gate BTC3L/3S 日 K：共 %d 日，最新 %s", len(have),
                         str(np.datetime64(max(have), "ms").astype("datetime64[D]")) if have else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("Gate 杠杆代币日 K 拉取失败（闸门失败开放，用已有缓存 %d 日）：%s", len(have), e)
        ks = np.array(sorted(set(d["BTC3L_USDT"]) & set(d["BTC3S_USDT"])), dtype="int64")
        lv = np.array([d["BTC3L_USDT"][k] for k in ks], dtype=float)
        sv = np.array([d["BTC3S_USDT"][k] for k in ks], dtype=float)
    return ks, lv, sv


def last_error() -> str:
    return str((_MEM.get("lt") or {}).get("err") or "")


def _roll_full(a: np.ndarray, n: int, fn) -> np.ndarray:
    """长度 n 的滑窗（含当日），窗口内全部有限才计算，否则 NaN（与 pandas rolling(n, min_periods=n) 同口径）。"""
    out = np.full(a.shape, np.nan)
    if a.size < n:
        return out
    bad = ~np.isfinite(a)
    cb = np.cumsum(np.r_[0, bad.astype(int)])
    av = np.where(bad, 0.0, a)
    cs = np.cumsum(np.r_[0.0, av])
    s = cs[n:] - cs[:-n]
    nb = cb[n:] - cb[:-n]
    out[n - 1:] = np.where(nb == 0, fn(s, n), np.nan)
    return out


def flag_series(day_ms, long_qv, short_qv, sum_n: int = 7, trend_n: int = 90) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """按连续 UTC 日历展开 → (日历日毫秒, x, M, flag)。缺失日 / 零成交日 → NaN（不补）。"""
    ks = np.asarray(day_ms, dtype="int64")
    if ks.size == 0:
        e = np.zeros(0)
        return np.zeros(0, "int64"), e, e.copy(), e.copy()
    grid = np.arange(int(ks.min()), int(ks.max()) + D_MS, D_MS, dtype="int64")
    pos = ((ks - grid[0]) // D_MS).astype(int)
    L = np.full(grid.shape, np.nan)
    S_ = np.full(grid.shape, np.nan)
    L[pos] = np.asarray(long_qv, float)
    S_[pos] = np.asarray(short_qv, float)
    L[~(L > 0)] = np.nan  # 零成交（交易所数据缺口）→ 缺失，与研究 df.replace(0, NaN) 同口径
    S_[~(S_ > 0)] = np.nan
    l7 = _roll_full(L, int(sum_n), lambda s, n: s)
    s7 = _roll_full(S_, int(sum_n), lambda s, n: s)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.log(l7 / s7)
    x[~np.isfinite(x)] = np.nan
    ma = _roll_full(x, int(trend_n), lambda s, n: s / n)
    f = np.where(np.isfinite(ma) & np.isfinite(x), (x > ma).astype(float), np.nan)
    return grid, x, ma, f


def flag_at(query_ms, day_ms, long_qv, short_qv, sum_n: int = 7, trend_n: int = 90, stale_days: float = 3.0) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一日 flag（known = 日 + 28h）；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    grid, _, _, f = flag_series(day_ms, long_qv, short_qv, sum_n, trend_n)
    if grid.size == 0 or q.size == 0:
        return out
    known = grid + LAG_MS
    j = np.searchsorted(known, q, side="right") - 1
    ok = j >= 0
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = f[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("levtok_gate_enabled", False)),
            "sum_n": int(st.get("levtok_gate_sum_n", 7) or 7),
            "trend_n": int(st.get("levtok_gate_trend_n", 90) or 90),
            "stale_days": float(st.get("levtok_gate_stale_days", 3.0) or 3.0)}


def block_mask(st: dict, open_ms, day_ms=None, long_qv=None, short_qv=None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多, 拦新开空, flag)。闸门关闭时全 False；NaN 不拦。
    contra_both：flag = 1（散户杠杆偏多高于均线）拦新开空；flag = 0 拦新开多。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    z = np.zeros(q.shape, dtype=bool)
    if not g["enabled"]:
        return z, z.copy(), np.full(q.shape, np.nan)
    if day_ms is None:
        day_ms, long_qv, short_qv = series()
    f = flag_at(q, day_ms, long_qv, short_qv, g["sum_n"], g["trend_n"], g["stale_days"])
    return np.isfinite(f) & (f < 0.5), np.isfinite(f) & (f > 0.5), f


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知日与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "sum_n": g["sum_n"], "trend_n": g["trend_n"], "flag": None, "block_long": False,
           "block_short": False, "x": None, "ma": None, "day": None, "known_from": None, "eval_open_ms": signal_open_ms,
           "n_days": 0, "latest_day": None, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        ks, lv, sv = series()
        out["n_days"], out["error"] = int(ks.size), last_error()
        if ks.size:
            out["latest_day"] = str(np.datetime64(int(ks[-1]), "ms").astype("datetime64[D]"))
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("杠杆代币闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        grid, x, ma, _ = flag_series(ks, lv, sv, g["sum_n"], g["trend_n"])
        known = grid + LAG_MS
        j = int(np.searchsorted(known, t, side="right") - 1) if grid.size else -1
        if j >= 0:
            out["x"] = round(float(x[j]), 4) if x[j] == x[j] else None
            out["ma"] = round(float(ma[j]), 4) if ma[j] == ma[j] else None
            out["day"] = str(np.datetime64(int(grid[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
        bl, bs, f = block_mask(st, [t], ks, lv, sv)
        fv = float(f[0])
        out["flag"] = int(fv) if fv == fv else None
        out["block_long"], out["block_short"] = bool(bl[0]), bool(bs[0])
        if fv != fv:
            out["fail_open"] = ("无已收盘的杠杆代币日 K" if j < 0 else
                                f"最新已知日过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足或窗口内缺日")
            log.warning("杠杆代币闸门失败开放（不拦）：%s；缓存 %d 日；%s", out["fail_open"], ks.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("杠杆代币闸门失败开放（不拦）：%s", e)
    return out
