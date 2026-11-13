"""下单数量取整：按交易所官方合约 / 交易对元数据（公共 REST，无需密钥）。

* OKX 现货：lotSz（数量步长，币）、minSz（最小数量，币）
* OKX 永续：ctVal（每张 = 多少币）、lotSz / minSz（张）→ 币步长 = lotSz × ctVal
* Gate 现货：amount_precision（数量小数位）、min_base_amount、min_quote_amount（最小下单金额 USDT）
* Gate 永续：quanto_multiplier（每张 = 多少币）、整张下单、order_size_min（张）
纸面账本、模拟盘引擎与实盘下单链路都按这里取整后的数量记账 / 发单（向下取整，不会超出风控上限）。
元数据缓存在内存与 SQLite meta 表（24 小时），拉不到时用上次缓存；都没有则抛 MarketDataError，不猜。
"""
from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import asdict, dataclass

from . import db
from .market.base import HttpJson, MarketDataError

TTL = 24 * 3600
_MEM: dict = {}
_LOCK = threading.Lock()


@dataclass
class Lot:
    venue: str
    symbol: str
    market: str
    step: float  # 数量步长（币）
    min_qty: float  # 最小数量（币）
    ct_val: float = 1.0  # 每张合约对应的币数量（现货 = 1）
    contract_step: float = 0.0  # 张数步长（现货 = 0）
    min_quote: float = 0.0  # 最小下单金额（USDT，Gate 现货）
    fetched_at: float = 0.0
    source: str = ""

    @property
    def is_contract(self) -> bool:
        return self.market == "perp"


def _fetch(venue: str, symbol: str, market: str) -> Lot:
    b = symbol[:-4] if symbol.endswith("USDT") else symbol
    if venue == "okx":
        from .net import okx_rest_bases
        h = HttpJson(okx_rest_bases(), timeout=10, max_retries=2)
        inst, typ = (f"{b}-USDT", "SPOT") if market == "spot" else (f"{b}-USDT-SWAP", "SWAP")
        j = h.get("/api/v5/public/instruments", {"instType": typ, "instId": inst})
        d = (j.get("data") or [None])[0]
        if not d:
            raise MarketDataError(f"OKX 无 {inst} 合约信息")
        if market == "spot":
            return Lot("okx", symbol, market, float(d["lotSz"]), float(d["minSz"]), source="okx /public/instruments")
        ct, lot, mn = float(d["ctVal"]), float(d["lotSz"]), float(d["minSz"])
        return Lot("okx", symbol, market, lot * ct, mn * ct, ct, lot, source="okx /public/instruments")
    if venue == "gate":
        h = HttpJson(["https://api.gateio.ws/api/v4", "https://api.gate.io/api/v4"], timeout=10, max_retries=2)
        if market == "spot":
            d = h.get(f"/spot/currency_pairs/{b}_USDT")
            prec = int(d.get("amount_precision", 8))
            return Lot("gate", symbol, market, 10.0 ** -prec, float(d.get("min_base_amount") or 0),
                       min_quote=float(d.get("min_quote_amount") or 0), source="gate /spot/currency_pairs")
        return gate_perp_lot(symbol, h.get(f"/futures/usdt/contracts/{b}_USDT", headers=GATE_SIZE_DECIMAL))
    raise ValueError(venue)


GATE_SIZE_DECIMAL = {"X-Gate-Size-Decimal": "1"}  # Gate 合约数量字段按字符串（可含小数）返回 / 接收


def gate_perp_lot(symbol: str, d: dict) -> Lot:
    """Gate USDT 永续合约元数据 → Lot（张步长 / 最小张数 × quanto_multiplier = 币）。
    元数据必须带请求头 X-Gate-Size-Decimal: 1 取：不带时小数合约（enable_decimal）的 order_size_min 被截断成 0。
    带头后 SOL / ETH / XRP 实测 order_size_min = 0.1 张（2026-11-13）。小数合约的张步长取 order_size_min；
    拿不到正数最小量时退回 1 张（宁可最小量偏大不下单，也不发会被拒绝或截断的数量）。"""
    ct = float(d["quanto_multiplier"])
    raw = d.get("order_size_min")
    mn = float(raw) if raw not in (None, "") else 0.0
    cstep = (mn if mn > 0 else 1.0) if d.get("enable_decimal") else 1.0
    mn = max(mn, cstep)
    return Lot("gate", symbol, "perp", cstep * ct, mn * ct, ct, cstep, source="gate /futures/usdt/contracts (X-Gate-Size-Decimal: 1)")


def spec(venue: str, symbol: str, market: str) -> Lot:
    venue = venue.lower()
    key = f"lot3:{venue}:{market}:{symbol}"  # lot3：Gate 合约元数据改带 X-Gate-Size-Decimal 头后弃用旧缓存
    now = time.time()
    with _LOCK:
        x = _MEM.get(key)
    if x and now - x.fetched_at < TTL:
        return x
    try:
        raw = db.meta_get(key)
        if raw:
            y = Lot(**json.loads(raw))
            if now - y.fetched_at < TTL:
                with _LOCK:
                    _MEM[key] = y
                return y
    except Exception:  # noqa: BLE001
        raw = None
    try:
        y = _fetch(venue, symbol, market)
        y.fetched_at = now
        db.meta_set(key, json.dumps(asdict(y)))
    except Exception as e:  # noqa: BLE001
        if x:
            return x
        if raw:
            return Lot(**json.loads(raw))
        raise MarketDataError(f"{venue.upper()} {symbol} {market} 下单精度获取失败：{e}") from e
    with _LOCK:
        _MEM[key] = y
    return y


def floor_qty(qty: float, lot: Lot, price: float | None = None) -> float:
    """向下取整到步长；低于最小数量 / 最小金额返回 0。"""
    if not (qty and qty > 0 and lot.step > 0):
        return 0.0
    n = math.floor(qty / lot.step + 1e-9)
    q = float(f"{n * lot.step:.12g}")
    if q < lot.min_qty - 1e-15:
        return 0.0
    if lot.min_quote and price and q * price < lot.min_quote:
        return 0.0
    return q


def contracts(qty: float, lot: Lot) -> float:
    """币数量 → 张数（永续）；现货原样返回。"""
    if not lot.is_contract or lot.ct_val <= 0:
        return qty
    return float(f"{qty / lot.ct_val:.10g}")


def describe(lot: Lot) -> dict:
    return {"lot_step": lot.step, "lot_min": lot.min_qty, "ct_val": lot.ct_val if lot.is_contract else None,
            "contract_step": lot.contract_step if lot.is_contract else None, "min_quote": lot.min_quote or None}
