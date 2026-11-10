"""每根新收盘 K 线的持仓调仓（与 qtw/backtest.py 第 2c 步同一公式）。

目标名义（每个已有持仓，本周期新开仓的除外）：
    止损距离% = |现价 − 该仓现有止损| / 现价            （rebalance_mode = "stop"，默认）
              = max(上式, atr_stop_mult × ATR / 现价)     （rebalance_mode = "atr"）
    目标 = min(权益 × max_risk_per_trade / 止损距离%, 权益 × max_weight_per_name)
所有已有持仓的目标再按 (权益 × max_gross_exposure − 本周期新开仓名义) 等比缩放（预留 taker 手续费）。
|当前名义 − 目标| / 目标 > rebalance_band 且差额 ≥ 1 USDT 才调整；先减后加，加仓受剩余总敞口限制。
止损价不变（与回测一致：止损在入场时确定）；加仓后入场价为加权均价。
每根 K 线只评估一次（按最新已收盘 K 线时间记在 paper_state.rebalance_bar），避免盘中价格抖动反复调仓。
实盘：减仓 = close_long / close_short（永续 reduceOnly）部分数量；加仓 = open_long / open_short 差额数量，
     都走 engine._route，只有实盘三重闸门全开才会真的发单。rebalance_band = 0 关闭。
"""
from __future__ import annotations

from . import db

STATE_KEY = "rebalance_bar"


def target_notional(*, side: str, price: float, stop: float, atr: float | None, equity: float, max_risk: float,
                    max_weight: float, atr_mult: float, mode: str = "stop") -> float:
    if price <= 0 or equity <= 0:
        return 0.0
    d = 1 if side == "long" else -1
    if d * (price - stop) <= 0:
        return 0.0  # 已越过止损：交给止损处理
    sp = abs(price - stop) / price
    if mode == "atr" and atr and atr == atr and atr > 0:
        sp = max(sp, atr_mult * atr / price)
    return min(equity * max_risk / sp, equity * max_weight)


def plan(positions: dict, prices: dict, atrs: dict, *, equity: float, new_notional: float, cfg: dict,
         gross_now: float, fee: float, name_mult: dict | None = None) -> list[dict]:
    """纯函数：返回调仓计划 [{symbol, delta_usdt, target_usdt, current_usdt, price}]（先减后加，已按额度截断）。"""
    st, rk = cfg["strategy"], cfg["risk"]
    band = float(st.get("rebalance_band", 0) or 0)
    if band <= 0:
        return []
    mode = str(st.get("rebalance_mode", "stop") or "stop")
    tg = {}
    for s, p in positions.items():
        px = prices.get(s)
        if not px or px <= 0:
            continue
        nm = float((name_mult or {}).get(s, 1.0))  # 单币波动率封顶系数（name_vol_target，默认 1）
        v = target_notional(side=p.side, price=px, stop=p.stop_price, atr=atrs.get(s), equity=equity,
                            max_risk=float(rk["max_risk_per_trade"]) * nm, max_weight=float(rk["max_weight_per_name"]) * nm,
                            atr_mult=float(st["atr_stop_mult"]), mode=mode)
        if v > 0:
            tg[s] = v
    tot = sum(tg.values())
    if tot <= 0:
        return []
    k = min(1.0, max(0.0, equity * float(rk["max_gross_exposure"]) - new_notional) / (tot * (1 + fee)))
    out = []
    for s, v in tg.items():
        p, px = positions[s], prices[s]
        cur, tgt = abs(p.qty) * px, v * k
        if tgt > 0 and abs(cur - tgt) / tgt > band and abs(cur - tgt) >= 1.0:
            out.append({"symbol": s, "delta_usdt": tgt - cur, "target_usdt": tgt, "current_usdt": cur, "price": px})
    out.sort(key=lambda r: r["delta_usdt"])
    room = equity * float(rk["max_gross_exposure"]) - gross_now
    final = []
    for r in out:
        if r["delta_usdt"] < 0:
            room += -r["delta_usdt"]
            final.append(r)
        else:
            add = min(r["delta_usdt"], room / (1 + fee))
            if add < 1.0:
                continue
            room -= add
            final.append({**r, "delta_usdt": add})
    return final


def last_bar(conn) -> str:
    r = db.query("SELECT value FROM paper_state WHERE key=?", (STATE_KEY,), conn)
    return r[0]["value"] if r else ""


def set_last_bar(conn, bar: str) -> None:
    db.execute("INSERT OR REPLACE INTO paper_state(key,value) VALUES(?,?)", (STATE_KEY, bar), conn)
