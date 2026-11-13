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
          testnet: bool = False, ts: str | None = None) -> dict:
    body = json.dumps(payload, separators=(",", ":")) if payload else ""
    ts = ts or str(int(time.time()))
    host = TESTNET if testnet else LIVE
    headers = {"KEY": keys["api_key"], "Timestamp": ts, "SIGN": sign(keys["secret"], method, path, query, body, ts),
               "Content-Type": "application/json", "Accept": "application/json"}
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
    n = int(math.floor(qty / spec["ct_val"] + 1e-9))
    p = {"contract": pair, "price": "0", "tif": "ioc", "size": -n if action == "open_short" else n}
    if action == "close_short":
        p["reduce_only"] = True
    return "/futures/usdt/orders", p


class GateTrader:
    def __init__(self, keys: dict, testnet: bool = True):
        self.keys, self.testnet = keys, testnet

    def preview_order(self, symbol, market, action, qty, price, spec=None) -> dict:
        path, p = order_request(symbol, market, action, qty, price, spec)
        return redacted(build(self.keys, "POST", path, p, testnet=self.testnet and market == "perp"))

    def place_order(self, cfg: dict, symbol, market, action, qty, price, spec=None):
        from .guard import require
        require(cfg, "gate")
        if market == "spot" and self.testnet:
            raise RuntimeError("Gate 现货没有测试网；请关闭“测试网”后再用实盘，或只做永续测试")
        if market == "perp" and action == "open_short":
            _send(build(self.keys, "POST", f"/futures/usdt/positions/{symbol[:-4]}_USDT/leverage",
                        None, query="leverage=1", testnet=self.testnet))
        path, p = order_request(symbol, market, action, qty, price, spec)
        return _send(build(self.keys, "POST", path, p, testnet=self.testnet and market == "perp"))

    def balance(self):
        """只读：查询现货账户余额（不下单）。"""
        return _send(build(self.keys, "GET", "/spot/accounts", None, testnet=False))
