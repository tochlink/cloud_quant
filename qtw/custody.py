"""美联储 H.4.1 外国官方托管美债闸门（可选，默认关闭；回测与模拟盘 / 实盘同一函数）。

数据：美联储 H.4.1 表 1A 备忘项「为外国官方及国际账户托管的证券」，周三水平（百万美元）。
      主源：美联储官方 Data Download Program 全量包 https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=zip
      （约 9 MB，内含 H41_data.xml；序列 RESH4FG_N.WW = 可交易美债，RESH4F_N.WW = 托管合计），逐块流式解析只取所需序列。
      备源：FRED 镜像 WMTSECL1 / WSEFINTL1（数值逐周相同）。2007-07-04 之前两处都以 0 占位 → 丢弃（≤ 0 的值一律不用）。
      只保存真实返回值，绝不补造。
缓存：DATA_DIR/fed_custody_<series>.csv（data/ 不入库）；每 6 小时刷新一次，失败时用已有缓存并记日志。

公式（与研究脚本 scratch/fedcustody4h/run.py 同口径，docs/fed_custody_gate_4h.md）：
  x_w   = ln(托管水平_w)（按观测周三排序）
  d_w   = x_w − x_{w−h}（h 周对数变化，默认 h = 4）
  z_w   = (d_w − mean(d 最近 N 个)) / std(d 最近 N 个, ddof=1)（含本周、N 个都有值才算，默认 N = 52）
  flag_w = 1 若 z_w < −k（外国官方抛售美债 → 美元融资压力 → risk-off），默认 k = 1
  可用时刻 known_w = 周三 + 3 天 00:00 UTC（官方周四 16:30 ET 发布，节假日顺延到周五 16:30 ET，均早于 W+3）。
  闸门：信号 K 线开盘时间 t 上取 known ≤ t 的最新一周 flag；flag = 1 时不新开多单（已持多不动，空单不受影响）。
失败开放：取不到数据 / 最新已知周早于 t − stale_days / 历史不足 → NaN → 不拦，并记录原因。
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
SERIES = {"tsy": "WMTSECL1", "tot": "WSEFINTL1"}
FED_SERIES = {"tsy": "RESH4FG_N.WW", "tot": "RESH4F_N.WW"}
FED_ZIP = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=zip"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}"
D_MS = 86_400_000
LAG_DAYS = 3
REFRESH_SEC = 6 * 3600.0
RETRY_SEC = 900.0
_LOCK = threading.Lock()
_MEM: dict = {}


def _path(key: str):
    return DATA_DIR / f"fed_custody_{SERIES[key]}.csv"


def _parse(text: str) -> dict[int, float]:
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


def _parse_fed_xml(stream, series_name: str) -> dict[int, float]:
    """从 H41_data.xml 流中逐块找到 SERIES_NAME 对应的 <kf:Series> 块，解析 (TIME_PERIOD, OBS_VALUE)。"""
    import re
    key = f'SERIES_NAME="{series_name}"'.encode()
    buf, body = b"", None
    while True:
        chunk = stream.read(4 << 20)
        if not chunk:
            break
        buf += chunk
        if body is None:
            i = buf.find(key)
            if i < 0:
                buf = buf[-len(key):]
                continue
            buf = buf[i:]
            body = b""
        j = buf.find(b"</kf:Series>")
        if j >= 0:
            body = buf[:j]
            break
    if not body:
        return {}
    out: dict[int, float] = {}
    for tag in re.findall(rb"<frb:Obs [^>]*>", body):
        v = re.search(rb'OBS_VALUE="([^"]*)"', tag)
        d = re.search(rb'TIME_PERIOD="(\d{4})-(\d{2})-(\d{2})"', tag)
        if not v or not d:
            continue
        try:
            val = float(v.group(1))
        except ValueError:
            continue
        if val > 0:
            y, m, dd = (int(x) for x in d.groups())
            out[int(np.datetime64(f"{y:04d}-{m:02d}-{dd:02d}", "ms").astype("int64"))] = val
    return out


def _download_fed(key: str) -> dict[int, float]:
    import zipfile
    req = urllib.request.Request(FED_ZIP, headers={"User-Agent": "qtw/1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith("_data.xml"))
        with z.open(name) as f:
            d = _parse_fed_xml(f, FED_SERIES[key])
    if not d:
        raise RuntimeError(f"H.4.1 包中未找到 {FED_SERIES[key]}")
    return d


def _download(key: str) -> dict[int, float]:
    """主源美联储官方 DDP 全量包；失败再试 FRED 镜像（同一组数值）。"""
    errs = []
    try:
        return _download_fed(key)
    except Exception as e:  # noqa: BLE001
        errs.append(f"Fed DDP: {e}")
    try:
        req = urllib.request.Request(URL.format(fid=SERIES[key]), headers={"User-Agent": "qtw/1"})
        with urllib.request.urlopen(req, timeout=20) as r:
            d = _parse(r.read().decode("utf-8", "replace"))
        if d:
            return d
        errs.append("FRED: 空数据")
    except Exception as e:  # noqa: BLE001
        errs.append(f"FRED: {e}")
    raise RuntimeError("H.4.1 托管数据拉取失败：" + "；".join(errs)[:280])


def _read_cache(key: str) -> dict[int, float]:
    p = _path(key)
    out: dict[int, float] = {}
    if not p.exists():
        return out
    with open(p, newline="") as f:
        for row in csv.DictReader(f):
            try:
                v = float(row["value_musd"])
                if v > 0:
                    out[int(row["obs_ms"])] = v
            except (KeyError, ValueError):
                continue
    return out


def _write_cache(key: str, d: dict[int, float]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _path(key).with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["obs_ms", "obs_date", "value_musd"])
        w.writerows((k, str(np.datetime64(k, "ms").astype("datetime64[D]")), d[k]) for k in sorted(d))
    tmp.replace(_path(key))


def series(key: str = "tsy", force: bool = False, fetch: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """返回 (观测周三 00:00 UTC 毫秒 升序, 托管水平 百万美元)。按需刷新；失败时返回已有真实数据（可能为空）。"""
    if key not in SERIES:
        raise ValueError(f"未知托管序列 {key}")
    with _LOCK:
        m = _MEM.setdefault(key, {"t": 0.0, "rows": None, "err": ""})
        d = m["rows"]
        if d is None:
            d = _read_cache(key)
            m["rows"] = d
        age = time.time() - float(m["t"] or 0)
        stale = (not d) or max(d) < int(time.time() * 1000) - 10 * D_MS
        if fetch and (force or age >= REFRESH_SEC or (stale and age >= RETRY_SEC)):
            m["t"] = time.time()
            try:
                new = _download(key)
                if new != d:
                    d.update(new)
                    _write_cache(key, d)
                m["err"] = ""
                log.info("H.4.1 外国官方托管 %s：共 %d 周，最新 %s", SERIES[key], len(d), max(d) if d else None)
            except Exception as e:  # noqa: BLE001 —— 失败开放：只用已有缓存
                m["err"] = str(e)[:300]
                log.warning("H.4.1 托管数据拉取失败（闸门失败开放，用已有缓存 %d 周）：%s", len(d), e)
        ks = np.array(sorted(d), dtype="int64")
        vs = np.array([d[k] for k in ks], dtype=float)
    return ks, vs


def last_error(key: str = "tsy") -> str:
    return str((_MEM.get(key) or {}).get("err") or "")


def weekly_z(values, n: int = 52, h: int = 4) -> np.ndarray:
    """z_w of h-week log change vs the last n weekly changes (incl. current, ddof=1); NaN until n changes exist."""
    x = np.log(np.asarray(values, dtype=float))
    d = np.full(x.shape, np.nan)
    if x.size > h:
        d[h:] = x[h:] - x[:-h]
    z = np.full(x.shape, np.nan)
    for i in range(x.size):
        if i - n + 1 < 0:
            continue
        w = d[i - n + 1:i + 1]
        if np.isnan(w).any():
            continue
        sd = w.std(ddof=1)
        if sd > 0:
            z[i] = (d[i] - w.mean()) / sd
    return z


def z_at(query_ms, obs_ms, values, n: int = 52, h: int = 4, stale_days: float = 21.0) -> np.ndarray:
    """对每个查询时间 t 返回 known ≤ t 的最新一周 z（known = 周三 + 3 天 00:00 UTC）；不可用 / 过旧 → NaN。"""
    q = np.asarray(query_ms, dtype="int64").reshape(-1)
    out = np.full(q.shape, np.nan)
    ob = np.asarray(obs_ms, dtype="int64")
    if ob.size == 0 or q.size == 0:
        return out
    z = weekly_z(values, n, h)
    known = ob + LAG_DAYS * D_MS
    j = np.searchsorted(known, q, side="right") - 1
    ok = (j >= 0)
    jj = np.clip(j, 0, None)
    ok &= (q - known[jj]) <= float(stale_days) * D_MS
    out[ok] = z[jj[ok]]
    return out


def gate_cfg(st: dict) -> dict:
    return {"enabled": bool(st.get("custody_gate_enabled", False)),
            "series": str(st.get("custody_gate_series", "tsy") or "tsy"),
            "n": int(st.get("custody_gate_n", 52) or 52), "h": int(st.get("custody_gate_h", 4) or 4),
            "k": float(st.get("custody_gate_k", 1.0) if st.get("custody_gate_k") is not None else 1.0),
            "stale_days": float(st.get("custody_gate_stale_days", 21.0) or 21.0)}


def block_mask(st: dict, open_ms, obs_ms=None, values=None) -> tuple[np.ndarray, np.ndarray]:
    """回测 / 引擎共用：对一组信号 K 线开盘时间返回 (拦新开多 bool, z)。闸门关闭时全 False；z = NaN 不拦。"""
    g = gate_cfg(st)
    q = np.asarray(open_ms, dtype="int64").reshape(-1)
    if not g["enabled"]:
        return np.zeros(q.shape, dtype=bool), np.full(q.shape, np.nan)
    if obs_ms is None:
        obs_ms, values = series(g["series"])
    z = z_at(q, obs_ms, values, g["n"], g["h"], g["stale_days"])
    return np.nan_to_num(z, nan=np.inf) < -g["k"], z


def state(st: dict, signal_open_ms: int | None) -> dict:
    """引擎用：最近已收盘信号 K 线开盘时间上的闸门状态（含最新已知周与失败开放原因）。"""
    g = gate_cfg(st)
    out = {"enabled": g["enabled"], "series": g["series"], "n": g["n"], "h": g["h"], "k": g["k"], "blocked": False,
           "z": None, "level_musd": None, "obs_date": None, "known_from": None, "eval_open_ms": signal_open_ms,
           "n_weeks": 0, "fail_open": "", "error": ""}
    if not g["enabled"]:
        return out
    try:
        ob, vs = series(g["series"])
        out["n_weeks"], out["error"] = int(ob.size), last_error(g["series"])
        if signal_open_ms is None:
            out["fail_open"] = "无信号 K 线时间"
            log.warning("托管闸门失败开放：%s", out["fail_open"])
            return out
        t = int(signal_open_ms)
        known = ob + LAG_DAYS * D_MS
        j = int(np.searchsorted(known, t, side="right") - 1) if ob.size else -1
        if j >= 0:
            out["level_musd"] = float(vs[j])
            out["obs_date"] = str(np.datetime64(int(ob[j]), "ms").astype("datetime64[D]"))
            out["known_from"] = str(np.datetime64(int(known[j]), "ms")) + "Z"
        bl, z = block_mask(st, [t], ob, vs)
        zv = float(z[0])
        out["z"] = zv if zv == zv else None
        out["blocked"] = bool(bl[0])
        if zv != zv:
            out["fail_open"] = ("无已公布的托管数据" if j < 0 else
                                f"最新已知周过旧（> {g['stale_days']:g} 天）" if (t - int(known[j])) > g["stale_days"] * D_MS else
                                "历史不足 N 周")
            log.warning("托管闸门失败开放（不拦）：%s；缓存 %d 周；%s", out["fail_open"], ob.size, out["error"])
    except Exception as e:  # noqa: BLE001
        out["fail_open"] = f"异常：{e}"[:300]
        log.warning("托管闸门失败开放（不拦）：%s", e)
    return out
