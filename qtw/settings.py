"""非敏感配置，存于 SQLite（data/qtw.sqlite 的 settings 表）。API 密钥不在这里，见 qtw/vault.py。"""
from __future__ import annotations

import copy
import threading
from typing import Any

import json

import yaml

from . import db
from .paths import DATA_DIR, ensure_dirs
from .timeutil import iso, utcnow

LIVE_CONFIRM_PHRASE = "我已了解实盘交易可能亏损全部资金"

DEFAULTS: dict[str, Any] = {
    "venue": "okx",  # okx | gate —— 行情与（未来的）实盘交易所
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"],
    "strategy": {
        "rule_id": "dual_ma_trend_4h_v1",
        "interval": "4h",
        "fast_ma": 20,
        "slow_ma": 60,
        "atr_period": 14,
        "atr_stop_mult": 2.0,
        "confirm_bars": 2,  # 2026-11-10：OKX+Gate 各 3 段滚动样本外均优于 1
        # 2026-11-10：仅入场的趋势过滤（多需收盘>SMA100，空需收盘<SMA100；不强制平仓）。
        # 6 段不重叠窗口：前 3 段选出 100，后 3 段（未参与选择）在 OKX/Gate、4/14bps 下均优于不过滤。0=关闭
        "trend_ma": 100,
        # 2026-11-10：空头熔断。影子「只做空」账本最近 N 根已平仓合计亏损时暂停新开空单（因果，不平已有仓）。
        # 6/12 段不重叠窗口：前半段从 {60,120,240} 选出 60，后半段（未参与选择）在 OKX/Gate、4/14bps 下均明显优于不熔断。0=关闭
        "short_breaker_bars": 60,
        # 2026-11-10：可选浮盈加仓（默认关闭）。前一根收盘浮盈 ≥ pyramid_r × R 时加仓一次，规模 pyramid_frac × 原名义，止损不动。
        # 12 组邻域整段全优于基线，但前推后 6 段只高约 0.5 个百分点，未达到改默认的标准。0=关闭（仅回测生效）
        "pyramid_r": 0.0,
        "pyramid_frac": 0.5,
        "lookback_bars": 200,
    },
    "risk": {
        "starting_equity_usdt": 1000.0,
        "max_risk_per_trade": 0.05,
        "max_weight_per_name": 0.20,
        "max_gross_exposure": 1.0,  # 总敞口 ≤ 1 倍权益
        "perp_leverage": 1,  # v1 保守：永续 1 倍保证金，不放大
        "allow_spot_long": True,
        "allow_perp_short": True,
    },
    "fees": {"taker_bps": 4.0},
    "worker": {"enabled": True, "interval_sec": 60},  # 7×24 纸面自动交易（服务运行即运行；紧急停止会关闭）
    "live": {
        "mode": "paper",  # paper | live
        "live_enabled": False,
        "confirm_phrase": "",
        "okx_demo": True,  # OKX 模拟盘 (x-simulated-trading: 1)
        "gate_testnet": True,
    },
}

_LOCK = threading.RLock()
PATH = DATA_DIR / "settings.yaml"


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_db() -> dict | None:
    r = db.query("SELECT value FROM settings WHERE key='config'")
    return json.loads(r[0]["value"]) if r else None


def _write_db(s: dict) -> None:
    db.execute("INSERT INTO settings(key,value,updated_at) VALUES('config',?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
               (db.dumps(s), iso(utcnow())))


def load() -> dict:
    with _LOCK:
        ensure_dirs()
        data = _read_db()
        if data is None:
            data = {}
            if PATH.exists():  # 旧版 YAML → SQLite 一次性迁移
                data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
                _write_db(_merge(DEFAULTS, data))
                PATH.rename(PATH.with_suffix(".yaml.migrated"))
        return _merge(DEFAULTS, data)


def validate(s: dict) -> dict:
    st, rk = s["strategy"], s["risk"]
    if st["interval"] not in ("15m", "1h", "4h", "1d"):
        raise ValueError("K 线周期只支持 15m / 1h / 4h / 1d")
    st["fast_ma"], st["slow_ma"], st["atr_period"] = int(st["fast_ma"]), int(st["slow_ma"]), int(st["atr_period"])
    if not (2 <= st["fast_ma"] < st["slow_ma"] <= 400):
        raise ValueError("需要 2 ≤ 快线 < 慢线 ≤ 400")
    st["atr_stop_mult"] = float(st["atr_stop_mult"])
    if not 0.5 <= st["atr_stop_mult"] <= 10:
        raise ValueError("ATR 止损倍数需在 0.5–10 之间")
    st["confirm_bars"] = int(st.get("confirm_bars", 1))
    if not 1 <= st["confirm_bars"] <= 5:
        raise ValueError("信号确认根数需在 1–5 之间")
    st["trend_ma"] = int(st.get("trend_ma", 0) or 0)
    if st["trend_ma"] and not 20 <= st["trend_ma"] <= 400:
        raise ValueError("趋势过滤 SMA 需为 0（关闭）或 20–400")
    st["short_breaker_bars"] = int(st.get("short_breaker_bars", 0) or 0)
    if st["short_breaker_bars"] and not 10 <= st["short_breaker_bars"] <= 500:
        raise ValueError("空头熔断回看根数需为 0（关闭）或 10–500")
    st["pyramid_r"] = float(st.get("pyramid_r", 0) or 0)
    st["pyramid_frac"] = float(st.get("pyramid_frac", 0.5) or 0)
    if st["pyramid_r"] and not 0.5 <= st["pyramid_r"] <= 5:
        raise ValueError("浮盈加仓触发倍数需为 0（关闭）或 0.5–5 R")
    if not 0 <= st["pyramid_frac"] <= 1:
        raise ValueError("加仓比例需在 0–1 之间")
    rk["max_risk_per_trade"] = float(rk["max_risk_per_trade"])
    rk["max_weight_per_name"] = float(rk["max_weight_per_name"])
    if not 0 < rk["max_risk_per_trade"] <= 0.05:
        raise ValueError("单笔风险上限不能超过 5%（已约定规则）")
    if not 0 < rk["max_weight_per_name"] <= 0.20:
        raise ValueError("单币权重上限不能超过 20%（已约定规则）")
    if float(rk["max_gross_exposure"]) > 1.0 or int(rk["perp_leverage"]) != 1:
        raise ValueError("v1 仅支持 1 倍总敞口与 1 倍永续保证金")
    if s["venue"] not in ("okx", "gate"):
        raise ValueError("交易所只能是 okx 或 gate")
    syms = [x.strip().upper().replace("/", "").replace("-", "") for x in s["symbols"] if x.strip()]
    syms = [x if x.endswith("USDT") else x + "USDT" for x in syms]
    if not 1 <= len(syms) <= 30:
        raise ValueError("标的数量需在 1–30 之间")
    s["symbols"] = list(dict.fromkeys(syms))
    if s["live"]["mode"] not in ("paper", "live"):
        raise ValueError("模式只能是 paper 或 live")
    s["worker"]["interval_sec"] = max(60, int(s["worker"]["interval_sec"]))
    return s


def save(s: dict) -> dict:
    with _LOCK:
        s = validate(_merge(DEFAULTS, s))
        _write_db(s)
        return s


def update(patch: dict) -> dict:
    with _LOCK:
        return save(_merge(load(), patch))


def live_armed(s: dict) -> bool:
    lv = s["live"]
    return lv["mode"] == "live" and bool(lv["live_enabled"]) and lv.get("confirm_phrase") == LIVE_CONFIRM_PHRASE
