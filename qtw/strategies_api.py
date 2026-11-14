"""多策略页 API（v7）：策略列表 / 详情 / 单策略回测 / 影子子账本。路由单独放这里，app.py 只 include。"""
from __future__ import annotations

import math
import threading

import pandas as pd
from fastapi import APIRouter, Body, HTTPException

from . import carry, shadow
from . import settings as S
from . import strategies as R
from .backtest import btc_spot_for_regime
from .market import cache as mcache

router = APIRouter()
_bt_lock = threading.Lock()


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if hasattr(o, "item"):
        try:
            return _clean(o.item())
        except (ValueError, AttributeError):
            return str(o)
    return o


def _ok(data):
    return _clean(data)


@router.get("/api/strategies")
def strategies_list():
    res = R.load_research()
    items = []
    for s in R.public_list():
        sid = s["id"]
        items.append({**s, "metrics": res.get("metrics", {}).get(sid, {}), "blends": res.get("blends", {}).get(sid, {}),
                      "curve": res.get("curves", {}).get(sid, {}), "shadow": sid in shadow.active_ids()})
    return _ok({"items": items, "rule": res.get("rule"), "window": res.get("window"), "cut": res.get("cut"),
                "generated_at": res.get("generated_at"), "corr": res.get("corr_gate_daily", {}),
                "walkforward": res.get("walkforward", []), "default": "ma_trend"})


@router.get("/api/strategies/shadow")
def strategies_shadow():
    return _ok({"books": shadow.status(), "recent": shadow._LAST["decisions"][-20:]})


@router.post("/api/strategies/{sid}/backtest")
def strategies_backtest(sid: str, body: dict = Body(default={})):
    """用官方公共历史 K 线现跑一次该策略与 #1（同一批数据），返回周度权益、关键指标和最近成交。"""
    if sid not in R.BY_ID:
        raise HTTPException(404, "未知策略")
    spec = R.BY_ID[sid]
    cfg = S.load()
    # 策略参数一律用注册表 / 默认值（与研究同口径），风控 / 费率 / 交易方式跟随当前设置；页面上保存的旧策略参数不参与这里的对比
    cfg["strategy"] = {**cfg["strategy"], **{k: v for k, v in S.DEFAULTS["strategy"].items()}}
    if body.get("venue") in ("okx", "gate"):
        cfg["venue"] = body["venue"]
    if spec.get("separate_sim") and cfg["venue"] != "gate":
        raise HTTPException(400, "资金费率套利只在 Gate 上回测（OKX 公共接口只给约 3 个月资金费率）")
    iv = spec["interval"] if spec["interval"] in ("1h", "4h") else "4h"
    bars = int(body.get("bars") or (9000 if iv == "1h" else 4500))
    if not _bt_lock.acquire(blocking=False):
        raise HTTPException(409, "已有策略回测在运行")
    try:
        fr, errs = mcache.many(cfg["venue"], cfg["symbols"], iv, bars)
        if not fr.get("spot") or not fr.get("perp"):
            raise HTTPException(502, f"官方公共行情获取失败（不会用任何替代数据）：{errs}")
        syms = [s for s in cfg["symbols"] if s in fr["spot"] and s in fr["perp"]]
        n = min(len(fr[m][s]) for m in fr for s in syms)
        fr = {m: {s: fr[m][s].iloc[-n:].reset_index(drop=True) for s in syms} for m in fr}
        c = {**cfg, "symbols": syms, "strategy": {**cfg["strategy"], "interval": iv}}
        if spec.get("separate_sim"):
            since = int(pd.Timestamp(fr["spot"][syms[0]]["open_time"].iloc[0]).value // 1_000_000) - 4 * 86_400_000
            fund = {s: carry.fetch_gate_funding(s, since) for s in syms}
            res = carry.simulate(fr, fund, c, **spec["params"])
        else:
            # 标的里没有 BTCUSDT 时单独取 BTC 现货供体制过滤（与模拟盘 / 实盘引擎同口径）
            btc_df, btc_err = btc_spot_for_regime(c, fr, bars)
            if btc_err:
                errs = {**errs, "BTCUSDT(regime)": btc_err}
            res = R.run(sid, fr, c, btc_spot=btc_df)
        if iv == "4h":
            base = R.run("ma_trend", fr, cfg, btc_spot=btc_spot_for_regime(cfg, fr, bars)[0]) if sid != "ma_trend" else res
        else:
            f4, _ = mcache.many(cfg["venue"], syms, "4h", 4500)
            n4 = min(len(f4[m][s]) for m in f4 for s in syms)
            f4 = {m: {s: f4[m][s].iloc[-n4:].reset_index(drop=True) for s in syms} for m in f4}
            base = R.run("ma_trend", f4, cfg, btc_spot=btc_spot_for_regime(cfg, f4, 4500)[0])

        def weekly(r, t0=None):
            e = r["equity"]
            x = pd.Series(e["equity"].to_numpy(float), index=pd.to_datetime(e["time"], utc=True, format="ISO8601"))
            if t0 is not None:
                x = x[x.index >= t0]
            w = x.resample("W").last().dropna()
            return [[t.strftime("%Y-%m-%d"), round(float(v / w.iloc[0]), 4)] for t, v in w.items()] if len(w) else []
        t0 = pd.to_datetime(res["equity"]["time"].iloc[0], utc=True, format="ISO8601")
        sm = res["summary"]
        tr = res["trades"]
        trades = tr.tail(60).iloc[::-1].fillna("").to_dict("records") if len(tr) else []
        keys = ("total_return", "max_drawdown", "sharpe", "closed_trades", "win_rate", "profit_factor", "payoff_ratio",
                "fees_usdt", "avg_gross_exposure_pct", "funding_usdt", "start_time", "end_time")
        return _ok({"sid": sid, "venue": cfg["venue"], "interval": iv, "summary": {k: sm.get(k) for k in keys},
                    "base_summary": {k: base["summary"].get(k) for k in keys}, "curve": weekly(res), "base_curve": weekly(base, t0),
                    "trades": trades, "data_errors": errs})
    finally:
        _bt_lock.release()
