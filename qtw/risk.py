"""仓位计算：单笔风险 ≤ 权益×5%，单币权重 ≤ 20%，总敞口 ≤ 1×权益。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Sized:
    notional: float
    qty: float
    weight: float
    stop_pct: float
    stop_price: float
    risk_usdt: float
    capped_by: str  # risk | weight | gross | none


def size(*, side: str, equity: float, price: float, atr: float, max_risk: float = 0.05,
         max_weight: float = 0.20, atr_mult: float = 2.0, gross_room: float | None = None) -> Sized:
    if equity <= 0 or price <= 0 or side not in ("long", "short") or not atr or atr <= 0:
        return Sized(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, "none")
    stop_dist = atr_mult * atr
    stop_pct = stop_dist / price
    raw = equity * max_risk / stop_pct
    cap = equity * max_weight
    notional, by = (raw, "risk") if raw <= cap else (cap, "weight")
    if gross_room is not None and notional > gross_room:
        notional, by = max(0.0, gross_room), "gross"
    qty = notional / price
    stop = price - stop_dist if side == "long" else price + stop_dist
    return Sized(notional, qty, notional / equity, stop_pct, stop, notional * stop_pct, by)


def scale_to_room(desired: dict[str, float], room: float, fee_rate: float = 0.0) -> dict[str, float]:
    """同时入场多个标的时，若合计名义 + 手续费超过剩余总敞口额度，则等比缩小（只缩不放）。"""
    room = max(0.0, room)
    tot = sum(max(0.0, v) for v in desired.values())
    if tot <= 0:
        return {k: 0.0 for k in desired}
    k = min(1.0, room / (tot * (1 + fee_rate)))
    return {s: max(0.0, v) * k for s, v in desired.items()}
