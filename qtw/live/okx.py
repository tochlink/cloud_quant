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


def order_payload(symbol: str, market: str, action: str, qty: float, price: float, spec: dict | None = None,
                  pos_mode: str = "net_mode") -> dict:
    """action: open_long(现货买) / close_long(现货卖) / open_short(永续卖) / close_short(永续买, reduceOnly)。
    pos_mode：OKX 账户持仓模式。开平仓模式（long_short_mode）下永续单必须带 posSide（本系统只做空 → "short"），
    且 reduceOnly 只适用于买卖模式（net_mode），不带；否则交易所会拒单（posSide 参数错误）。"""
    base = symbol[:-4]
    if market == "spot":
        # 2026-11-13：按数量下单（币数量，已按 lotSz 向下取整，见 qtw/lots.py）；买卖都用 base_ccy
        return {"instId": f"{base}-USDT", "tdMode": "cash", "side": "buy" if action == "open_long" else "sell",
                "ordType": "market", "tgtCcy": "base_ccy", "sz": f"{qty:.12g}"}
    spec = spec or {"ct_val": 1, "lot_sz": 1}
    lots = math.floor(qty / spec["ct_val"] / spec["lot_sz"] + 1e-9) * spec["lot_sz"]
    p = {"instId": f"{base}-USDT-SWAP", "tdMode": "isolated", "ordType": "market",
         "side": "sell" if action == "open_short" else "buy", "sz": f"{lots:.10g}"}
    if pos_mode == "long_short_mode":
        p["posSide"] = "short"
    elif action == "close_short":
        p["reduceOnly"] = True
    return p


class OkxTrader:
    def __init__(self, keys: dict, demo: bool = True):
        self.keys, self.demo = keys, demo
        self._pos_mode: str | None = None

    def pos_mode(self) -> str:
        """只读：账户持仓模式 posMode（net_mode 买卖模式 / long_short_mode 开平仓模式），进程内缓存。"""
        if self._pos_mode is None:
            j = _send(build(self.keys, "GET", "/api/v5/account/config", None, self.demo))
            self._pos_mode = str(((j.get("data") or [{}])[0] or {}).get("posMode") or "net_mode")
        return self._pos_mode

    def preview_order(self, symbol, market, action, qty, price, spec=None) -> dict:
        return redacted(build(self.keys, "POST", "/api/v5/trade/order",
                              order_payload(symbol, market, action, qty, price, spec), self.demo))

    def place_order(self, cfg: dict, symbol, market, action, qty, price, spec=None) -> dict:
        from .guard import require
        require(cfg, "okx")
        mode = self.pos_mode() if market == "perp" else "net_mode"
        if market == "perp" and action == "open_short":
            lev = {"instId": f"{symbol[:-4]}-USDT-SWAP", "lever": "1", "mgnMode": "isolated"}
            if mode == "long_short_mode":
                lev["posSide"] = "short"  # 开平仓模式下逐仓设杠杆必须指定持仓方向
            _send(build(self.keys, "POST", "/api/v5/account/set-leverage", lev, self.demo))
        return _send(build(self.keys, "POST", "/api/v5/trade/order",
                           order_payload(symbol, market, action, qty, price, spec, mode), self.demo))

    def balance(self) -> dict:
        """只读：查询余额（不下单）。"""
        return _send(build(self.keys, "GET", "/api/v5/account/balance", None, self.demo))

    def spot_available(self, base: str) -> float:
        """只读：现货（交易账户）某币的可用数量 availBal。现货市价买入的手续费从到手的币里扣，
        平多卖出前用它把卖出数量夹到实际可用余额，避免「余额不足」被拒。"""
        j = _send(build(self.keys, "GET", f"/api/v5/account/balance?ccy={base}", None, self.demo))
        for acct in j.get("data") or []:
            for d in acct.get("details") or []:
                if str(d.get("ccy")).upper() == base.upper():
                    return float(d.get("availBal") or 0)
        return 0.0
