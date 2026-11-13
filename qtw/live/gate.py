"""Gate.io APIv4 私有 REST 签名与下单。

签名: hex(HMAC_SHA512(secret, METHOD\\n/api/v4{path}\\n{query}\\nsha512(body)\\n{timestamp}))
测试网（仅合约）：https://fx-api-testnet.gateio.ws/api/v4 —— Gate 现货无公开测试网。
只有 guard.require 通过时才会真正发出请求。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import time

import requests

LIVE = "https://api.gateio.ws"
TESTNET = "https://fx-api-testnet.gateio.ws"
PREFIX = "/api/v4"


def sign(secret: str, method: str, path: str, query: str, body: str, ts: str) -> str:
    h = hashlib.sha512(body.encode()).hexdigest()
    msg = f"{method.upper()}\n{PREFIX}{path}\n{query}\n{h}\n{ts}"
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha512).hexdigest()


def build(keys: dict, method: str, path: str, payload: dict | None = None, query: str = "",
          testnet: bool = False, ts: str | None = None, extra_headers: dict | None = None) -> dict:
    body = json.dumps(payload, separators=(",", ":")) if payload else ""
    ts = ts or str(int(time.time()))
    host = TESTNET if testnet else LIVE
    headers = {"KEY": keys["api_key"], "Timestamp": ts, "SIGN": sign(keys["secret"], method, path, query, body, ts),
               "Content-Type": "application/json", "Accept": "application/json", **(extra_headers or {})}
    url = host + PREFIX + path + (f"?{query}" if query else "")
    return {"method": method, "url": url, "headers": headers, "body": body}


def redacted(req: dict) -> dict:
    return {"method": req["method"], "url": req["url"], "body": req["body"],
            "headers": {k: ("***" if k in ("KEY", "SIGN") else v) for k, v in req["headers"].items()}}


def _send(req: dict):
    r = requests.request(req["method"], req["url"], headers=req["headers"], data=req["body"] or None, timeout=15)
    if r.status_code >= 300:
        raise RuntimeError(f"Gate 拒绝: HTTP {r.status_code} {r.text[:200]}")
    return r.json() if r.text else {}


def order_request(symbol: str, market: str, action: str, qty: float, price: float, spec: dict | None = None):
    pair = f"{symbol[:-4]}_USDT"
    if market == "spot":
        if action == "open_long":  # Gate 现货市价买只接受计价币金额：amount = 取整后的币数量 × 参考价（USDT）
            return "/spot/orders", {"currency_pair": pair, "side": "buy", "type": "market",
                                    "time_in_force": "ioc", "amount": f"{qty * price:.4f}"}
        return "/spot/orders", {"currency_pair": pair, "side": "sell", "type": "market",
                                "time_in_force": "ioc", "amount": f"{qty:.12g}"}
    spec = spec or {"ct_val": 1}
    if spec.get("decimal"):  # 小数合约：张数按步长向下取整，以字符串发送（需请求头 X-Gate-Size-Decimal: 1）
        step = float(spec.get("lot_sz") or 1.0)
        n = math.floor(qty / spec["ct_val"] / step + 1e-9) * step
        s = f"{n:.10g}"
        p = {"contract": pair, "price": "0", "tif": "ioc", "size": f"-{s}" if action in ("open_short", "close_long") else s}
        if action in ("close_short", "close_long"):
            p["reduce_only"] = True
        return "/futures/usdt/orders", p
    n = int(math.floor(qty / spec["ct_val"] + 1e-9))
    # 永续 size 正 = 买、负 = 卖：open_long / close_short 为正，open_short / close_long 为负
    p = {"contract": pair, "price": "0", "tif": "ioc", "size": -n if action in ("open_short", "close_long") else n}
    if action in ("close_short", "close_long"):
        p["reduce_only"] = True
    return "/futures/usdt/orders", p


class GateTrader:
    def __init__(self, keys: dict, testnet: bool = True):
        self.keys, self.testnet = keys, testnet
        self._dual: bool | None = None

    def dual_mode(self) -> bool:
        """只读：USDT 永续账户是否双向持仓模式（GET /futures/usdt/accounts 的 in_dual_mode），实例内缓存。
        双向模式下开空（负 size）/ 平空（正 size + reduce_only）的下单参数与单向模式相同，
        但调杠杆必须走 /futures/usdt/dual_comp/positions/{contract}/leverage。"""
        if self._dual is None:
            j = _send(build(self.keys, "GET", "/futures/usdt/accounts", None, testnet=self.testnet))
            self._dual = bool((j or {}).get("in_dual_mode")) if isinstance(j, dict) else False
        return self._dual

    def preview_order(self, symbol, market, action, qty, price, spec=None) -> dict:
        path, p = order_request(symbol, market, action, qty, price, spec)
        hdr = {"X-Gate-Size-Decimal": "1"} if isinstance(p.get("size"), str) else None
        return redacted(build(self.keys, "POST", path, p, testnet=self.testnet and market == "perp", extra_headers=hdr))

    def place_order(self, cfg: dict, symbol, market, action, qty, price, spec=None, leverage: int | None = None):
        from .guard import require
        require(cfg, "gate")
        if market == "spot" and self.testnet:
            raise RuntimeError("Gate 现货没有测试网；请关闭“测试网”后再用实盘，或只做永续测试")
        if market == "perp" and action in ("open_short", "open_long"):
            L = leverage if leverage is not None else ((cfg or {}).get("risk") or {}).get("perp_leverage", 1)
            L = max(1, min(100, int(L or 1)))
            lev_path = (f"/futures/usdt/dual_comp/positions/{symbol[:-4]}_USDT/leverage" if self.dual_mode()
                        else f"/futures/usdt/positions/{symbol[:-4]}_USDT/leverage")
            _send(build(self.keys, "POST", lev_path, None, query=f"leverage={L}", testnet=self.testnet))
        path, p = order_request(symbol, market, action, qty, price, spec)
        hdr = {"X-Gate-Size-Decimal": "1"} if isinstance(p.get("size"), str) else None
        return _send(build(self.keys, "POST", path, p, testnet=self.testnet and market == "perp", extra_headers=hdr))

    def balance(self):
        """只读：查询现货账户余额（不下单）。"""
        return _send(build(self.keys, "GET", "/spot/accounts", None, testnet=False))

    def spot_available(self, base: str) -> float:
        """只读：现货账户某币的可用数量 available（未开 GT 抵扣时，市价买入手续费从到手的币里扣）。"""
        rows = _send(build(self.keys, "GET", "/spot/accounts", None, query=f"currency={base}", testnet=False))
        for d in rows if isinstance(rows, list) else []:
            if str(d.get("currency")).upper() == base.upper():
                return float(d.get("available") or 0)
        return 0.0
