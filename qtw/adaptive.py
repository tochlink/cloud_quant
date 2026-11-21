"""运行时自适应：趋势强度仓位乘子、体制方向偏置、滚动（walk-forward）自动调参。

全部只用已收盘 K 线：第 t 根收盘算出的值，最早在第 t+1 根开盘（回测）/ 下一个决策周期（纸面、实盘）使用。

1) 趋势强度仓位乘子（strategy.adaptive_size_mode，"off" = 关闭）
   spread：ts = |SMA_fast − SMA_slow| / ATR，m = clip(ts / 滚动中位数(ts, 1000 根, 至少 200 根), lo, hi)
   adx   ：m = clip(ADX14 / 25, lo, hi)
   m 乘到单币风险 / 权重上限乘子上（与单币波动率封顶同一处），乘积封顶在 max(原乘子, 1)，
   所以 5% 单笔风险、20% 单币权重上限永远不会被突破；调仓（rebalance_band）用同一个乘子，持仓随趋势强弱加减。
2) 体制方向偏置（strategy.direction_bias，默认关）
   上一根 BTC（体制线来源）收盘 > SMA_N × (1 + band) → 只做多（拦新开空）；< SMA_N → 只做空（原有 BTC 体制过滤拦新开多）；
   其余双向。只拦新开仓，已有持仓、止损不受影响。
3) 滚动自动调参（strategy.auto_retune，默认关）
   每 every_days 天，用「调参时刻之前已收盘」的最近 lookback_days 天数据，对预先声明的小网格
   （fast_ma × slow_ma × atr_stop_mult × btc_regime_ma）各跑一次同口径回测，按日 Sharpe 选最优；
   迟滞：只有挑战者 Sharpe 比现任高出 margin 才切换（防止参数来回抖）。选中的参数与时间写入 SQLite
   （adaptive_params 表），运行中的引擎通过热加载在下一周期生效；已有持仓保留原止损，离场按新参数的信号。
研究与默认开关依据：docs/STRATEGY_FORMULAS.md「运行时自适应」一节。
"""
from __future__ import annotations

import itertools
import json
import logging
import threading
import time
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

SIZE_MODES = ("off", "spread", "adx")
RETUNE_KEYS = ("fast_ma", "slow_ma", "atr_stop_mult", "btc_regime_ma")
RETUNE_GRID: dict[str, tuple] = {
    "fast_ma": (30, 50, 70),
    "slow_ma": (100, 150, 200),
    "atr_stop_mult": (1.5, 2.0, 2.5),
    "btc_regime_ma": (900, 1200, 1500),
}
BARS_PER_DAY = {"15m": 96, "1h": 24, "4h": 6, "1d": 1}


# ---------------------------------------------------------------- 1) 趋势强度仓位乘子
def adx(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    """Wilder ADX（只用已收盘 K 线）。前 2n 根为 NaN。"""
    h, l, c = (df[k].astype(float).to_numpy() for k in ("high", "low", "close"))
    if len(c) < 2 * n + 1:
        return np.full(len(c), np.nan)
    up = np.r_[np.nan, h[1:] - h[:-1]]
    dn = np.r_[np.nan, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    a = 1.0 / n
    s = lambda x: pd.Series(x).ewm(alpha=a, adjust=False).mean().to_numpy()  # noqa: E731
    atr = s(tr)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * s(pdm) / atr
        mdi = 100 * s(mdm) / atr
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    out = np.array(s(np.nan_to_num(dx, nan=0.0)), dtype=float)
    out[: 2 * n] = np.nan
    return out


def trend_size_mult(ind: pd.DataFrame, mode: str, lo: float = 0.5, hi: float = 1.0, ref_bars: int = 1000) -> np.ndarray:
    """逐根趋势强度乘子 m_t（第 t 根收盘可得）。ind 需含 high/low/close/sma_fast/sma_slow/atr（strategy.indicators 输出）。
    关闭或数据不足时为 1。"""
    n = len(ind)
    if not mode or mode == "off" or n == 0:
        return np.ones(n)
    lo, hi = float(lo), float(hi)
    if mode == "spread":
        ts = (ind["sma_fast"].astype(float) - ind["sma_slow"].astype(float)).abs() / ind["atr"].astype(float).replace(0, np.nan)
        ref = ts.rolling(int(ref_bars), min_periods=min(200, int(ref_bars))).median()
        m = (ts / ref.replace(0, np.nan)).to_numpy()
    elif mode == "adx":
        m = adx(ind, 14) / 25.0
    else:
        raise ValueError(f"未知的自适应仓位模式：{mode}")
    m = np.array(np.clip(m, lo, hi), dtype=float)
    m[~np.isfinite(m)] = 1.0
    return m


def combine_mult(base, m):
    """把趋势乘子乘到已有单币乘子上，乘积封顶在 max(原乘子, 1)：5% / 20% 上限永不被突破。"""
    b = np.asarray(base, dtype=float)
    return np.minimum(b * np.asarray(m, dtype=float), np.maximum(b, 1.0))


# ---------------------------------------------------------------- 2) 体制方向偏置
def bias_blocks_short(close, n: int, band: float):
    """上一根体制线来源收盘 > SMA_n × (1 + band) 时为 True（只做多 → 拦新开空）。SMA 未形成时 False。"""
    c = pd.Series(close, dtype=float)
    if not n:
        return pd.Series(False, index=c.index)
    ma = c.rolling(int(n)).mean()
    return (c > ma * (1.0 + float(band))).fillna(False)


def bias_label(blocks_long: bool, blocks_short: bool) -> str:
    return "short_only" if blocks_long else ("long_only" if blocks_short else "both")


# ---------------------------------------------------------------- 3) 滚动自动调参
def grid_params(grid: dict | None = None) -> list[dict]:
    g = grid or RETUNE_GRID
    out = []
    for vals in itertools.product(*(g[k] for k in RETUNE_KEYS)):
        p = dict(zip(RETUNE_KEYS, vals))
        if p["fast_ma"] < p["slow_ma"]:
            out.append(p)
    return out


def daily_sharpe(eq: pd.Series) -> float:
    dr = eq.resample("1D").last().pct_change().dropna()
    if len(dr) < 10 or not dr.std() > 0:
        return float("nan")
    return float(dr.mean() / dr.std() * 365 ** 0.5)


def _slice(frames: dict, asof: pd.Timestamp, bars: int, step: pd.Timedelta) -> dict:
    out = {}
    for m, d in frames.items():
        out[m] = {}
        for s, df in d.items():
            x = df[df["open_time"] + step <= asof]  # 只用调参时刻前已收盘的 K 线
            out[m][s] = x.tail(int(bars)).reset_index(drop=True)
    return out


def score_window(frames: dict, cfg: dict, params: dict, asof, lookback_days: int, funding=None, btc_spot=None) -> float:
    """在调参时刻 asof 之前已收盘的数据上：预热段 + 最近 lookback_days 天跑一次同口径回测，返回窗口内日 Sharpe。"""
    from . import backtest as B
    from .market.base import INTERVAL_MS
    from .settings import _merge
    st = cfg["strategy"]
    step = pd.Timedelta(milliseconds=INTERVAL_MS[st["interval"]])
    asof = pd.Timestamp(asof)
    warm = max(int(params.get("slow_ma", st["slow_ma"])), int(params.get("btc_regime_ma", st.get("btc_regime_ma", 0)) or 0),
               int(st.get("trend_ma", 0) or 0), int(st.get("port_vol_lookback", 180) or 180)) + 50
    bars = warm + int(lookback_days) * BARS_PER_DAY.get(st["interval"], 6)
    F = _slice(frames, asof, bars, step)
    bs = None
    if btc_spot is not None:
        bs = btc_spot[btc_spot["open_time"] + step <= asof].tail(bars).reset_index(drop=True)
    c = _merge(cfg, {"strategy": {**{k: params[k] for k in RETUNE_KEYS if k in params}, "adaptive_size_mode": "off",
                                  "direction_bias": False, "auto_retune": False}})
    try:
        r = B.run_backtest(F, c, funding=funding, btc_spot=bs)
    except Exception as e:  # noqa: BLE001 —— 数据不足等：该格不参与选择
        log.debug("score_window %s failed: %s", params, e)
        return float("nan")
    eq = r["equity"]
    e = eq.set_index(pd.to_datetime(eq["time"]))["equity"]
    e = e[e.index > asof - pd.Timedelta(days=int(lookback_days))]
    return daily_sharpe(e)


def choose(scores: dict, incumbent: dict, margin: float) -> tuple[dict, str]:
    """scores: {params_key(json): sharpe}。迟滞：挑战者需比现任高 margin 才切换；现任无分数时直接取最优。"""
    ok = {k: v for k, v in scores.items() if v == v}
    if not ok:
        return dict(incumbent), "no_scores"
    best_k = max(ok, key=lambda k: (ok[k], k))
    inc_k = pkey(incumbent)
    inc_s = ok.get(inc_k)
    if inc_s is None:
        return json.loads(best_k), "incumbent_unscored"
    if ok[best_k] > inc_s + float(margin) and best_k != inc_k:
        return json.loads(best_k), f"switch {inc_s:.2f}->{ok[best_k]:.2f}"
    return dict(incumbent), f"keep {inc_s:.2f} (best {ok[best_k]:.2f})"


def pkey(p: dict) -> str:
    return json.dumps({k: (float(p[k]) if k == "atr_stop_mult" else int(p[k])) for k in RETUNE_KEYS}, sort_keys=True)


def retune_once(frames: dict, cfg: dict, asof, incumbent: dict, lookback_days: int, margin: float,
                funding=None, btc_spot=None, grid: dict | None = None) -> dict:
    scores = {pkey(p): score_window(frames, cfg, p, asof, lookback_days, funding, btc_spot) for p in grid_params(grid)}
    chosen, why = choose(scores, incumbent, margin)
    return {"asof": pd.Timestamp(asof).isoformat(), "params": {k: chosen[k] for k in RETUNE_KEYS}, "reason": why,
            "scores": scores}


def walk_forward_schedule(frames: dict, cfg: dict, start, end, every_days: int, lookback_days: int, margin: float,
                          funding=None, btc_spot=None, grid: dict | None = None, score_cache: dict | None = None) -> list:
    """研究 / 回放用：从 start 到 end 每 every_days 天调参一次，返回 [(生效时间, params), ...]（只用过去数据）。
    score_cache 可在不同 margin 之间复用同一批窗口回测分数。"""
    st = cfg["strategy"]
    inc = {k: st[k] for k in RETUNE_KEYS}
    out = [(pd.Timestamp(start) - pd.Timedelta(days=36500), dict(inc))]
    t = pd.Timestamp(start)
    while t < pd.Timestamp(end):
        ck = (t.isoformat(), int(lookback_days))
        if score_cache is not None and ck in score_cache:
            scores = score_cache[ck]
        else:
            scores = {pkey(p): score_window(frames, cfg, p, t, lookback_days, funding, btc_spot) for p in grid_params(grid)}
            if score_cache is not None:
                score_cache[ck] = scores
        inc, _ = choose(scores, inc, margin)
        out.append((t, dict(inc)))
        t += pd.Timedelta(days=int(every_days))
    return out


# ---------------------------------------------------------------- 运行时：SQLite 记录与覆盖
_DDL = """
CREATE TABLE IF NOT EXISTS adaptive_params (
  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, venue TEXT NOT NULL, params TEXT NOT NULL,
  reason TEXT, lookback_days INTEGER, margin REAL, scores TEXT
);
CREATE TABLE IF NOT EXISTS param_changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, source TEXT NOT NULL, changes TEXT NOT NULL
);
"""
_ddl_done: set[str] = set()


def _ensure(conn=None) -> None:
    from . import db
    c = conn or db.connect()
    key = str(id(c))
    if key in _ddl_done:
        return
    with db._LOCK:
        c.executescript(_DDL)
    _ddl_done.add(key)


def latest(venue: str | None = None, conn=None) -> dict | None:
    from . import db
    _ensure(conn)
    q = "SELECT * FROM adaptive_params" + (" WHERE venue=?" if venue else "") + " ORDER BY id DESC LIMIT 1"
    r = db.query(q, (venue,) if venue else (), conn=conn)
    if not r:
        return None
    out = dict(r[0])
    out["params"] = json.loads(out["params"])
    return out


def record(venue: str, res: dict, lookback_days: int, margin: float, conn=None) -> int:
    from . import db
    from .timeutil import iso, utcnow
    _ensure(conn)
    return db.execute("INSERT INTO adaptive_params(time, venue, params, reason, lookback_days, margin, scores) VALUES (?,?,?,?,?,?,?)",
                      (iso(utcnow()), venue, json.dumps(res["params"]), res.get("reason", ""), int(lookback_days), float(margin),
                       json.dumps({k: (None if v != v else round(v, 4)) for k, v in (res.get("scores") or {}).items()})), conn=conn)


def log_change(source: str, changes: list, conn=None) -> None:
    from . import db
    from .timeutil import iso, utcnow
    _ensure(conn)
    db.execute("INSERT INTO param_changes(time, source, changes) VALUES (?,?,?)", (iso(utcnow()), source, json.dumps(changes, ensure_ascii=False)), conn=conn)


def recent_changes(limit: int = 20, conn=None) -> list[dict]:
    from . import db
    _ensure(conn)
    rows = db.query("SELECT * FROM param_changes ORDER BY id DESC LIMIT ?", (int(limit),), conn=conn)
    for r in rows:
        r["changes"] = json.loads(r["changes"])
    return rows


def effective_cfg(cfg: dict, conn=None) -> dict:
    """auto_retune 开启时，把最近一次自动调参结果覆盖到策略参数上（不写回设置；页面保存的设置不被污染）。"""
    st = cfg.get("strategy") or {}
    if not st.get("auto_retune") or cfg.get("_adaptive_applied"):
        return cfg
    try:
        rec = latest(cfg.get("venue"), conn)
    except Exception as e:  # noqa: BLE001
        log.warning("读取自动调参记录失败：%s", e)
        return cfg
    if not rec:
        return {**cfg, "_adaptive_applied": True}
    p = {k: rec["params"][k] for k in RETUNE_KEYS if k in rec["params"]}
    return {**cfg, "strategy": {**st, **p}, "_adaptive_applied": True, "_adaptive": {"time": rec["time"], "params": p}}


# ---------------------------------------------------------------- 运行时：后台自动调参线程
_rt = {"running": False, "last_run": "", "last_result": None, "last_error": ""}
_rt_lock = threading.Lock()


def due(cfg: dict, now=None, conn=None) -> bool:
    st = cfg["strategy"]
    if not st.get("auto_retune"):
        return False
    rec = latest(cfg.get("venue"), conn)
    if not rec:
        return True
    now = pd.Timestamp(now or pd.Timestamp.utcnow())
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    return now - pd.Timestamp(rec["time"]) >= pd.Timedelta(days=int(st.get("retune_every_days", 30) or 30))


def run_retune(cfg: dict, conn=None) -> dict:
    """运行时调参一次：官方公共 K 线（缓存）→ 网格窗口回测 → 迟滞选择 → 写 SQLite。不下单。"""
    from .market import cache as mcache
    st = cfg["strategy"]
    L = int(st.get("retune_lookback_days", 365) or 365)
    margin = float(st.get("retune_margin", 0.3) or 0.0)
    warm = max(max(RETUNE_GRID["slow_ma"]), max(RETUNE_GRID["btc_regime_ma"]), int(st.get("trend_ma", 0) or 0), 180) + 60
    bars = warm + L * BARS_PER_DAY.get(st["interval"], 6)
    frames, errs = mcache.many(cfg["venue"], list(cfg["symbols"]), st["interval"], bars)
    if errs:
        raise RuntimeError("自动调参取数失败：" + "；".join(f"{k} {v}" for k, v in list(errs.items())[:3]))
    btc = None
    sym = str(st.get("btc_regime_symbol") or "BTCUSDT").upper()
    if sym not in frames.get("spot", {}):
        btc = mcache.candles(cfg["venue"], sym, st["interval"], bars, "spot")
    rec = latest(cfg.get("venue"), conn)
    inc = rec["params"] if rec else {k: st[k] for k in RETUNE_KEYS}
    asof = pd.Timestamp.utcnow()
    res = retune_once(frames, cfg, asof, inc, L, margin, None, btc)
    record(cfg["venue"], res, L, margin, conn)
    changes = [[k, inc.get(k), res["params"][k]] for k in RETUNE_KEYS if inc.get(k) != res["params"][k]]
    log_change("auto_retune", changes or [["(不变)", "", res["reason"]]], conn)
    return res


def maybe_retune_async(cfg: dict) -> bool:
    """到期则在后台线程调参（不阻塞交易周期）。返回是否启动。"""
    try:
        if not due(cfg):
            return False
    except Exception as e:  # noqa: BLE001
        log.warning("自动调参检查失败：%s", e)
        return False
    with _rt_lock:
        if _rt["running"]:
            return False
        _rt["running"] = True

    def job():
        from . import logtable as LT
        from .timeutil import iso, utcnow
        t0 = time.time()
        try:
            res = run_retune(cfg)
            _rt.update(last_result={k: res[k] for k in ("asof", "params", "reason")}, last_error="")
            log.info("%s", LT.block("自动调参（walk-forward）完成", ["参数", "值"],
                                    [[k, v] for k, v in res["params"].items()] + [["原因", res["reason"]], ["耗时", f"{time.time() - t0:.0f}s"]]))
            try:
                from . import worker
                worker.kick("auto_retune")
            except Exception:  # noqa: BLE001
                pass
        except Exception as e:  # noqa: BLE001
            _rt["last_error"] = str(e)[:300]
            log.warning("自动调参失败：%s", e)
        finally:
            _rt.update(running=False, last_run=iso(utcnow()))

    threading.Thread(target=job, name="qtw-retune", daemon=True).start()
    return True


def status(cfg: dict) -> dict:
    st = cfg["strategy"]
    rec = None
    try:
        rec = latest(cfg.get("venue"))
    except Exception:  # noqa: BLE001
        pass
    active = {k: st[k] for k in RETUNE_KEYS}
    if st.get("auto_retune") and rec:
        active.update({k: rec["params"][k] for k in RETUNE_KEYS if k in rec["params"]})
    return {
        "auto_retune": bool(st.get("auto_retune")), "adaptive_size_mode": st.get("adaptive_size_mode", "off"),
        "adaptive_size_lo": st.get("adaptive_size_lo"), "adaptive_size_hi": st.get("adaptive_size_hi"),
        "direction_bias": bool(st.get("direction_bias")), "direction_bias_band": st.get("direction_bias_band"),
        "retune_every_days": st.get("retune_every_days"), "retune_lookback_days": st.get("retune_lookback_days"),
        "retune_margin": st.get("retune_margin"),
        "active_params": active, "saved_params": {k: st[k] for k in RETUNE_KEYS},
        "last_adaptation": {"time": rec["time"], "params": rec["params"], "reason": rec.get("reason")} if rec else None,
        "retune_running": _rt["running"], "retune_last_error": _rt["last_error"],
        "grid": {k: list(v) for k, v in RETUNE_GRID.items()},
    }
