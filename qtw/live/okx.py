"""OKX v5 私有 REST 签名与下单。

签名: base64(HMAC_SHA256(secret, timestamp + METHOD + requestPath + body))
模拟盘: 请求头 x-simulated-trading: 1
只有 send=True 且 guard.require 通过时才会真正发出请求。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
from datetime import datetime, timezone

import requests

BASE = "https://www.okx.com"


def _ts() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def sign(secret: str, ts: str, method: str, path: str, body: str) -> str:
    mac = hmac.new(secret.encode(), f"{ts}{method.upper()}{path}{body}".encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def build(keys: dict, method: str, path: str, payload: dict | None = None, demo: bool = True, ts: str | None = None) -> dict:
    body = json.dumps(payload, separators=(",", ":")) if payload else ""
    ts = ts or _ts()
    headers = {
        "OK-ACCESS-KEY": keys["api_key"],
        "OK-ACCESS-SIGN": sign(keys["secret"], ts, method, path, body),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": keys["passphrase"],
        "Content-Type": "application/json",
    }
    if demo:
        headers["x-simulated-trading"] = "1"
    return {"method": method, "url": BASE + path, "headers": headers, "body": body}


def redacted(req: dict) -> dict:
    """给界面/日志看的版本：不含任何密钥或签名。"""
    return {"method": req["method"], "url": req["url"], "body": req["body"],
            "headers": {k: ("***" if k.startswith("OK-ACCESS") and k != "OK-ACCESS-TIMESTAMP" else v)
                        for k, v in req["headers"].items()}}


def _send(req: dict) -> dict:
    r = requests.request(req["method"], req["url"], headers=req["headers"], data=req["body"] or None, timeout=15)
    try:
        j = r.json()
    except ValueError:
        j = {"code": str(r.status_code), "msg": r.text[:200]}
    if r.status_code != 200 or str(j.get("code")) != "0":
        raise RuntimeError(f"OKX 拒绝: HTTP {r.status_code} code={j.get('code')} msg={j.get('msg')} data={j.get('data')}")
    return j


def order_payload(symbol: str, market: str, action: str, qty: float, price: float, spec: dict | None = None) -> dict:
    """action: open_long(现货买) / close_long(现货卖) / open_short(永续卖) / close_short(永续买, reduceOnly)。"""
    base = symbol[:-4]
    if market == "spot":
        if action == "open_long":
            return {"instId": f"{base}-USDT", "tdMode": "cash", "side": "buy", "ordType": "market",
                    "tgtCcy": "quote_ccy", "sz": f"{qty * price:.4f}"}
        return {"instId": f"{base}-USDT", "tdMode": "cash", "side": "sell", "ordType": "market",
                "tgtCcy": "base_ccy", "sz": f"{qty:.8f}".rstrip("0").rstrip(".")}
    spec = spec or {"ct_val": 1, "lot_sz": 1}
    lots = math.floor(qty / spec["ct_val"] / spec["lot_sz"]) * spec["lot_sz"]
    p = {"instId": f"{base}-USDT-SWAP", "tdMode": "isolated", "ordType": "market",
         "side": "sell" if action == "open_short" else "buy", "sz": f"{lots:g}"}
    if action == "close_short":
        p["reduceOnly"] = True
    return p


class OkxTrader:
    def __init__(self, keys: dict, demo: bool = True):
        self.keys, self.demo = keys, demo

    def preview_order(self, symbol, market, action, qty, price, spec=None) -> dict:
        return redacted(build(self.keys, "POST", "/api/v5/trade/order",
                              order_payload(symbol, market, action, qty, price, spec), self.demo))

    def place_order(self, cfg: dict, symbol, market, action, qty, price, spec=None) -> dict:
        from .guard import require
        require(cfg, "okx")
        if market == "perp" and action == "open_short":
            _send(build(self.keys, "POST", "/api/v5/account/set-leverage",
                        {"instId": f"{symbol[:-4]}-USDT-SWAP", "lever": "1", "mgnMode": "isolated"}, self.demo))
        return _send(build(self.keys, "POST", "/api/v5/trade/order",
                           order_payload(symbol, market, action, qty, price, spec), self.demo))

    def balance(self) -> dict:
        """只读：查询余额（不下单）。"""
        return _send(build(self.keys, "GET", "/api/v5/account/balance", None, self.demo))
