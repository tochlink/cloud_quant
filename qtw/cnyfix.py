"""人民币汇率中间价（央行授权外汇交易中心每个银行间营业日 09:15 北京时间 = 01:15 UTC 公布）日度序列：只读官方公开页面，不需要密钥。

来源：国家外汇管理局官方查询页 POST https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do（startDate / endDate / queryYN=true，
单次跨度 ≤ 366 天；页面注明「数据来源于中国外汇交易中心」），解析表格里 日期 / 美元 / 欧元 / 日元（每 100 外币折合人民币）。
缓存：data/cny_fix_daily.csv（不入库），只追加官方真实返回值；拉取失败时返回已有缓存，绝不补造 / 插值。

#16 用法（qtw.strategies.sig_cny_fix_basket）：bskt_t = 1e4 × mean(Δln 美元, Δln 欧元, Δln 日元 中间价)（正 = 人民币对三币中间价篮子走弱），
对前 L 个公布日做稳健 z（中位数 / 1.4826×MAD）；z ≥ k 的公布日，把事件放在当天 01:00 UTC 那根 1h K 线（该根 02:00 UTC 收盘时中间价已公布）。
"""
from __future__ import annotations

import csv
import datetime as dt
import html as _html
import logging
import re
import threading
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from .paths import DATA_DIR

log = logging.getLogger(__name__)
URL = "https://www.safe.gov.cn/AppStructured/hlw/RMBQuery.do"
COLS = ("usd100", "eur100", "jpy100")
_NAMES = {"美元": "usd100", "欧元": "eur100", "日元": "jpy100"}
_LOCK = threading.Lock()
_MEM: dict = {"t": 0.0, "df": None}
REFRESH_SEC = 600.0
H_MS = 3_600_000


def _path():
    return DATA_DIR / "cny_fix_daily.csv"


def _read_cache() -> pd.DataFrame:
    p = _path()
    if not p.exists():
        return pd.DataFrame(columns=["date", *COLS])
    d = pd.read_csv(p, dtype={"date": str})
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def parse_page(text: str) -> list[tuple[str, float, float, float]]:
    """解析官方查询页 HTML 表格 → [(YYYY-MM-DD, 美元, 欧元, 日元)]；表头按名字定位列，缺列 / 非数字的行丢弃。"""
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S)
    cell = lambda x: _html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
    pos = None
    out = []
    for tr in trs:
        cs = [cell(x) for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        if pos is None and any(c.endswith("美元") for c in cs):
            pos = {}
            for j, c in enumerate(cs):
                for nm, key in _NAMES.items():
                    if c.endswith(nm) and key not in pos:
                        pos[key] = j
            if len(pos) < 3:
                pos = None
            continue
        if pos and cs and re.fullmatch(r"\d{4}-\d\d-\d\d", cs[0]):
            try:
                out.append((cs[0], *(float(cs[pos[k]]) for k in COLS)))
            except (IndexError, ValueError):
                continue
    return out


def _fetch(start: dt.date, end: dt.date) -> list[tuple[str, float, float, float]]:
    out, a = [], start
    while a <= end:
        b = min(a + dt.timedelta(days=365), end)
        body = urllib.parse.urlencode({"startDate": a.isoformat(), "endDate": b.isoformat(), "queryYN": "true"}).encode()
        req = urllib.request.Request(URL, data=body, headers={"User-Agent": "Mozilla/5.0 (qtw)", "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out += parse_page(r.read().decode("utf-8", "ignore"))
        a = b + dt.timedelta(days=1)
        if a <= end:
            time.sleep(1.0)
    return out


def series(start_ms: int | None = None) -> pd.DataFrame:
    """返回官方中间价日表（date, usd100, eur100, jpy100，升序）。缺口只用官方查询页真实返回补齐；失败时返回已有缓存。"""
    now = time.time()
    with _LOCK:
        d = _MEM["df"] if _MEM["df"] is not None else _read_cache()
        today = dt.datetime.now(dt.timezone.utc).date()
        want0 = (pd.Timestamp(start_ms, unit="ms", tz="UTC").date() if start_ms is not None else today - dt.timedelta(days=400))
        utc = dt.datetime.now(dt.timezone.utc)
        # 公布窗口（01:10–04:00 UTC）内且缓存还没有今天：每 10 分钟查一次；其它时间每 3 小时查一次（减轻官方站压力）
        last_d = str(d.date.iloc[-1]) if len(d) else ""
        in_win = (dt.time(1, 10) <= utc.time() <= dt.time(4, 0)) and last_d < today.isoformat()
        fresh = _MEM["df"] is not None and now - _MEM["t"] < (REFRESH_SEC if in_win else 3 * 3600.0)
        try:
            rows = []
            if d.empty:
                rows = _fetch(want0, today)
            else:
                first = dt.date.fromisoformat(str(d.date.iloc[0]))
                if want0 < first - dt.timedelta(days=7):
                    rows += _fetch(want0, first - dt.timedelta(days=1))
                if not fresh:
                    last = dt.date.fromisoformat(str(d.date.iloc[-1]))
                    rows += _fetch(last - dt.timedelta(days=7), today)
            if rows:
                add = pd.DataFrame(rows, columns=["date", *COLS])
                d = pd.concat([d, add]).drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                with open(_path(), "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["date", *COLS])
                    w.writerows((r.date, r.usd100, r.eur100, r.jpy100) for r in d.itertuples())
        except Exception as e:  # 网络失败：只用已有真实数据
            log.warning("人民币中间价拉取失败：%s", e)
        _MEM.update(t=now if (not fresh) else _MEM["t"], df=d)
    return d


def robust_z(x: np.ndarray, L: int) -> np.ndarray:
    """z_t = (x_t − median(x_{t−L..t−1})) / (1.4826 × MAD)；窗口不满 / MAD=0 为 nan。"""
    x = np.asarray(x, dtype=float)
    z = np.full(len(x), np.nan)
    for t in range(L, len(x)):
        w = x[t - L:t]
        if not np.isfinite(w).all() or not np.isfinite(x[t]):
            continue
        m = np.median(w)
        mad = 1.4826 * np.median(np.abs(w - m))
        if mad > 0:
            z[t] = (x[t] - m) / mad
    return z


def basket_events(df: pd.DataFrame, L: int = 120, k: float = 2.0) -> pd.Series:
    """{01:00 UTC K 线 open_time 毫秒: z}，只含 z ≥ k（人民币对中间价篮子异常走弱）的公布日。"""
    if df is None or len(df) < L + 2:
        return pd.Series(dtype=float)
    d = df.sort_values("date")
    lg = np.log(d[list(COLS)].to_numpy(dtype=float))
    x = np.r_[np.nan, 1e4 * np.diff(lg, axis=0).mean(axis=1)]
    z = robust_z(x, L)
    t = (pd.to_datetime(d["date"].astype(str), utc=True) + pd.Timedelta(hours=1)).dt.as_unit("ms").astype("int64").to_numpy()
    m = np.isfinite(z) & (z >= k)
    return pd.Series(z[m], index=t[m])
