"""逐仓保证金：杠杆封顶，保证止损先于强平触发（纯函数，生产暂未接入，仍为 1 倍）。

研究依据（docs/STRATEGY_FORMULAS.md「逐仓强平 vs 2×ATR 止损」，2026-11-13）：
2×ATR 止损距离最大可达 17–21%，空单盈利后调仓在更低价加仓会把加权均价下移、
止损价不动，止损相对均价的距离 p90 约 20.6%。固定 10 倍逐仓时历史上 28% 的空单
「止损之前先强平」。因此每笔永续仓的实际杠杆必须按

    L_eff = min(L_req, floor(1 / (d + mmr + buffer)))

封顶，其中 d 为止损相对 **加权均价** 的不利距离；每次加仓 / 调仓 / 移动止损后重算。

线性 USDT 永续逐仓强平价（与研究脚本 scratch/liq_long.py 一致的近似，不含手续费）：
    多：liq = P̄ · (1 − 1/L + mmr)
    空：liq = P̄ · (1 + 1/L − mmr)
"""
from __future__ import annotations

import math

DEFAULT_MMR = 0.005      # 维持保证金率（主流币档位约 0.4%–0.5%；高档位更高，调用方可传入）
DEFAULT_BUFFER = 0.005   # 额外安全垫：强平价至少比止损再远 0.5%（滑点 / 标记价偏差）
MAX_LEVERAGE = 100


def _side(side: str) -> int:
    s = str(side).lower()
    if s in ("long", "buy", "多", "1", "+1"):
        return 1
    if s in ("short", "sell", "空", "-1"):
        return -1
    raise ValueError(f"unknown side: {side!r}")


def _pos(x: float, name: str) -> float:
    x = float(x)
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {x!r}")
    return x


def isolated_liq_price(side: str, avg_entry: float, leverage: float, mmr: float = DEFAULT_MMR) -> float:
    """逐仓强平价（线性 USDT 永续近似）。leverage ≥ 1。"""
    p = _pos(avg_entry, "avg_entry")
    lev = _pos(leverage, "leverage")
    if lev < 1:
        raise ValueError("leverage must be >= 1")
    return p * (1.0 - _side(side) * (1.0 / lev - float(mmr)))


def adverse_stop_distance(side: str, avg_entry: float, stop: float) -> float:
    """止损相对加权均价的不利距离（比例）。多：(P̄−stop)/P̄；空：(stop−P̄)/P̄。
    止损已锁定利润（在均价有利一侧）时为负数。"""
    p = _pos(avg_entry, "avg_entry")
    s = _pos(stop, "stop")
    return _side(side) * (p - s) / p


def max_safe_isolated_leverage(side: str, avg_entry: float, stop: float, mmr: float = DEFAULT_MMR,
                               buffer: float = DEFAULT_BUFFER, cap: int = MAX_LEVERAGE) -> int:
    """保证「强平价比止损至少再远 buffer」的最大整数杠杆，结果夹在 [1, cap]。
    即使返回 1，若 d + mmr + buffer ≥ 1（止损距离接近 100%），1 倍逐仓也不能保证，
    调用方应用 stop_precedes_liquidation 复核（或改用全仓 / 现货）。"""
    cap = max(1, int(cap))
    need = adverse_stop_distance(side, avg_entry, stop) + float(mmr) + float(buffer)
    if need <= 0:
        return cap
    return max(1, min(cap, int(math.floor(1.0 / need + 1e-12))))


def effective_isolated_leverage(requested: float, side: str, avg_entry: float, stop: float,
                                mmr: float = DEFAULT_MMR, buffer: float = DEFAULT_BUFFER,
                                cap: int = MAX_LEVERAGE) -> int:
    """实际下单杠杆 = min(请求杠杆, 安全上限)，夹在 [1, cap]。"""
    req = max(1, min(int(cap), int(math.floor(_pos(requested, "requested")))))
    return min(req, max_safe_isolated_leverage(side, avg_entry, stop, mmr, buffer, cap))


def stop_precedes_liquidation(side: str, avg_entry: float, stop: float, leverage: float,
                              mmr: float = DEFAULT_MMR, buffer: float = 0.0) -> bool:
    """价格不利移动时，止损是否先于强平（含 buffer 比例的额外距离）触发。"""
    sd = _side(side)
    liq = isolated_liq_price(side, avg_entry, leverage, mmr)
    p = float(avg_entry)
    # 多：止损应高于强平价；空：止损应低于强平价。
    return sd * (float(stop) - liq) >= buffer * p - 1e-12


def isolated_margin(notional: float, leverage: float) -> float:
    """逐仓所需初始保证金 = 名义 / 杠杆。"""
    n = abs(float(notional))
    return n / _pos(leverage, "leverage")
