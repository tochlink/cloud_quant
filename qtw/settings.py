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
        # 2026-11-10 12:30：由 20/60 改为 50/150。官方 Gate / OKX 4h 长历史（4500 根，2024-10 起）上，
        # 20/60 在调参窗口之前（2024-12-31 ~ 2026-03-05）亏 −41%（回撤 −47.6%）；40~60 / 120~200 慢均线是一片平台，
        # 50/150 两段都为正：Gate +27.0% / +21.9%、OKX +30.3% / +25.0%，整段回撤约 −28%，压力费率同向
        # （output/research_gate_long_history_param_revalidation.csv、research_gate_long_history_slow_ma_plateau.csv）
        "fast_ma": 50,
        "slow_ma": 150,
        "atr_period": 14,
        "atr_stop_mult": 2.0,
        "confirm_bars": 2,  # 2026-11-10：OKX+Gate 各 3 段滚动样本外均优于 1
        # 2026-11-10：仅入场的趋势过滤（多需收盘>SMA100，空需收盘<SMA100；不强制平仓）。
        # 6 段不重叠窗口：前 3 段选出 100，后 3 段（未参与选择）在 OKX/Gate、4/14bps 下均优于不过滤。0=关闭
        "trend_ma": 100,
        # 2026-11-10：空头熔断。影子「只做空」账本最近 N 根已平仓合计亏损时暂停新开空单（因果，不平已有仓）。
        # 6/12 段不重叠窗口：前半段从 {60,120,240} 选出 60，后半段（未参与选择）在 OKX/Gate、4/14bps 下均明显优于不熔断。0=关闭
        # 2026-11-10 12:30：随 50/150 改为 0（关闭）。长历史上 50/150 + 熔断 60 调参前段只有 +7.8%（不熔断 +27.0%），
        # 2025Q1 熔断拦掉了盈利空单。仍可手动设为 10–500 开启
        "short_breaker_bars": 0,
        # 2026-11-10 12:45：BTC 熊市体制过滤（仅入场）。BTC 现货 4h 收盘 < SMA_N（上一根已收盘）时不新开多单，不平已有仓、空单不受影响。
        # 1200 根 4h ≈ 日线 SMA200。Gate / OKX 官方 4500 根长历史、50/150 基线：调参前段（未见）Gate +27.0%→+42.2%、OKX +30.3%→+45.6%，
        # 2026-03 后 +21.9%→+56.7% / +25.0%→+57.9%；N = 300–1500 全部两段都优于不过滤，压力费率（现货 20 / 永续 15.1 bps）同向；
        # 滚动选 N（回看 90/180/365 天、测下 30 天）12 组全部优于不过滤。最大回撤不变（约 −28%）。0=关闭
        # （output/research_long_history_regime_filter_and_knobs_50_150.csv、research_long_history_btc_regime_fee_stress.csv、
        #   research_long_history_btc_regime_walkforward.csv）
        "btc_regime_ma": 1200,
        # 2026-11-11：可选震荡指数入场闸门（默认关闭）。上一根 CHOP_n > chop_max 时不新开 / 反手开仓，离场、止损、调仓不变。
        # 严格月度 walk-forward（候选 off + n{42,56,70}×T{48,50,52}，回看 3/6/12 个月按 Calmar/Sharpe 选）：Gate/OKX、真实与压力费率
        # 24 组全部 ≥ 固定关闭、回撤低 0.5–5 个百分点，但收益主要来自 2026-03 之前，n42 固定参数整段明显差于关闭（参数敏感），
        # 未达到改默认的标准（output/research_choppiness_entry_gate_monthly_walkforward.csv）。0=关闭；建议试用 chop_n 56 / chop_max 50
        "chop_n": 0,
        "chop_max": 50.0,
        # 2026-11-12：可选 Elder-Ray 空头入场闸门（默认关闭，只拦新开 / 反手空单）。现货 4h：E = EMA_N(close)，bull = (high − E) / WilderATR14；
        # 上一根 bull < −X（整根 K 线低于 EMA 超过 X 个 ATR，空头过度延伸）时不新开空，已有持仓 / 止损 / 离场 / 调仓不变。
        # 研究（scratch/eray_*.py，docs/STRATEGY_FORMULAS.md）：N26 X0 Gate +196.6% / OKX +193.3%（基线约 +156% / +159%），
        # 2026-03 后 +59.6…+60.5% vs +57.3%，10 个时移安慰剂 2026-03 后都更差；3/6 个月 walk-forward 胜基线、12 个月略低，未改默认。
        # 0=关闭；建议试用 elder_short_gate_n 26–50 / elder_short_gate_x 0–0.5
        "elder_short_gate_n": 0,
        "elder_short_gate_x": 0.0,
        # 2026-11-10：可选浮盈加仓（默认关闭）。前一根收盘浮盈 ≥ pyramid_r × R 时加仓一次，规模 pyramid_frac × 原名义，止损不动。
        # 12 组邻域整段全优于基线，但前推后 6 段只高约 0.5 个百分点，未达到改默认的标准。0=关闭（仅回测生效）
        "pyramid_r": 0.0,
        "pyramid_frac": 0.5,
        # 2026-11-10：可选固定止盈（默认关闭）。目标价 = 入场价 ± tp_r × R（R = 初始止损距离 = atr_stop_mult × ATR），触及全部平仓。
        # tp_reentry = False：止盈后像止损一样锁定，信号改变前不再开同向仓；True：下一根若信号仍在则按新 ATR 重新开仓。0=关闭
        "tp_r": 0.0,
        "tp_reentry": False,
        # 2026-11-11：持仓调仓（每根新收盘 K 线一次）。目标名义 = min(权益×单笔风险/现有止损距离%, 权益×单币权重)，
        # 再按总敞口等比缩放；|当前−目标|/目标 > rebalance_band 才调，先减后加，止损不变（见 qtw/rebalance.py）。
        # 真实费率（现货 10 / 永续 5.1 bps）：前 6 段选出 0.1，后 6 段（未参与选择）OKX +33.6% vs 基线 +29.4%，
        # Gate +33.2% vs +29.3%；费率 ×2 仍更好；0.1/0.25/0.5 三档全优（平台而非尖峰）。0 = 关闭
        "rebalance_band": 0.1,
        # 2026-11-12 19:55：可选「减仓专用阈值」（非对称调仓带）。0 = 与 rebalance_band 相同（默认，行为不变）；
        # >0 时：当前名义高于目标（减仓）需偏离 > rebalance_band_down，加仓仍用 rebalance_band。研究建议 0.3–0.35
        #（4500 根 4h：0.3 时 Gate +163% / OKX +169% 对基线 +156% / +159%，2026-03 后 +4 点；OKX walk-forward 全胜，Gate 3 个月训练略输，暂不设为默认，详见 docs/STRATEGY_FORMULAS.md）
        "rebalance_band_down": 0.0,
        # 2026-11-10 13:05 改为默认 30%/180，并已接入模拟/实盘引擎（qtw/engine.vol_scaled_cfg：账本按 4h 分桶的收盘权益，
        # 不足 181 根即约 30 天时 k=1 不缩放）。严格月度 walk-forward（候选 0/25/30/35%，训练 3/6/12 月 × Calmar/夏普，两所 × 真实/压力费率
        # 共 24 组）：月度切换不优于固定选择；固定 30% 相对 0% 在全部 24 组样本外窗口回撤都更小（约 −2~−5 点）、夏普都更高，收益真实费率 −9~+4 点、压力费率 −16~−2 点（用收益换回撤）
        # （output/research_port_vol_target_monthly_walkforward.csv）。原 13:00 结论：组合波动率目标。最近 port_vol_lookback 根 4h 权益收益的年化波动 σ，
        # 单笔风险与单币权重上限 × min(1, 目标/σ)。Gate / OKX 4500 根长历史、新基线：目标 25–40% × 回看 90/180/360 共 12 组最大回撤全部
        # 从 −28.3% 降到 −20%~−26%、日夏普 1.25→1.3–1.5；30%/180：Gate 调参前 +42.2%→+54.7%、之后 +56.7%→+55.4%，回撤 −23.5%。
        # （output/research_long_history_drawdown_equity_vol_throttle.csv、research_long_history_port_vol_target_robustness.csv）0=关闭
        "port_vol_target": 0.30,
        "port_vol_lookback": 180,
        # 2026-11-10 14:10 新默认：单币波动率封顶。σ_s = 最近 name_vol_lookback 根 4h 对数收益年化标准差（多头用现货、空头用永续），
        # 单笔风险与单币权重上限再 × min(1, name_vol_target/σ_s)（叠加在组合波动率系数之上，只缩不放）。默认风险 5% 在 2×ATR 下几乎总被
        # 单币 20% 截住，原本接近等名义；封顶只压极高波动的币。Gate / OKX 4500 根：abs 0.6–0.7 × L 60–360 是平台，回撤 −23.5%→−19~−21%，
        # 夏普 1.47→1.55–1.68；严格月度 walk-forward（候选 关闭 / 0.6 / 0.7 × L120 / 180，训练 3/6/12 月 × Calmar/夏普，两所 × 真实/压力费率
        # 共 24 组）：固定 0.6/120 相对关闭在全部 12 个样本外窗口回撤都更小、夏普都更高，收益 11/12 更高，2026-03 后段也略高
        # （output/research_inverse_vol_sizing.csv、_abs_nbhd.csv、_monthly_walkforward.csv）。0 = 关闭
        "name_vol_target": 0.60,
        "name_vol_lookback": 120,
        "rebalance_mode": "stop",  # stop：按现有止损距离定目标；atr：再取与最新 ATR 止损距离的较大者（更保守）
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
    # 手续费（bps，1 bp = 0.01%）。2026-11-10 按 kean 实际账户费率：现货 maker 0.08% / taker 0.10%，
    # 永续 maker 0.02% / taker 0.051%。策略在下一根开盘以市价成交，按 taker 计费、每条市价腿各收一次。
    # taker_bps 为旧版单一费率字段（仅在缺少分市场费率时回退使用）。
    "fees": {"spot_taker_bps": 10.0, "spot_maker_bps": 8.0, "perp_taker_bps": 5.1, "perp_maker_bps": 2.0, "taker_bps": 4.0},
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


def taker_rate(cfg: dict, market: str) -> float:
    """某市场（spot / perp）的 taker 费率（小数）。缺少分市场字段时回退到旧版 taker_bps。"""
    fees = cfg.get("fees") or {}
    v = fees.get(f"{market}_taker_bps")
    if v is None:
        v = fees.get("taker_bps", 0.0)
    return float(v) / 10_000


def validate(s: dict) -> dict:
    st, rk = s["strategy"], s["risk"]
    for k in ("spot_taker_bps", "spot_maker_bps", "perp_taker_bps", "perp_maker_bps", "taker_bps"):
        if k in s["fees"]:
            s["fees"][k] = float(s["fees"][k])
            if not 0 <= s["fees"][k] <= 100:
                raise ValueError("手续费需在 0–100 bps 之间")
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
    st["btc_regime_ma"] = int(st.get("btc_regime_ma", 0) or 0)
    if st["btc_regime_ma"] and not 50 <= st["btc_regime_ma"] <= 2000:
        raise ValueError("BTC 熊市过滤 SMA 需为 0（关闭）或 50–2000")
    st["chop_n"] = int(st.get("chop_n", 0) or 0)
    if st["chop_n"] and not 5 <= st["chop_n"] <= 300:
        raise ValueError("震荡指数周期需为 0（关闭）或 5–300")
    st["chop_max"] = float(st.get("chop_max", 50) or 50)
    if not 20 <= st["chop_max"] <= 100:
        raise ValueError("震荡指数阈值需在 20–100 之间")
    st["elder_short_gate_n"] = int(st.get("elder_short_gate_n", 0) or 0)
    if st["elder_short_gate_n"] and not 5 <= st["elder_short_gate_n"] <= 300:
        raise ValueError("Elder-Ray 空头闸门 EMA 周期需为 0（关闭）或 5–300")
    st["elder_short_gate_x"] = float(st.get("elder_short_gate_x", 0) or 0)
    if not 0 <= st["elder_short_gate_x"] <= 5:
        raise ValueError("Elder-Ray 空头闸门 ATR 倍数需在 0–5 之间")
    st["pyramid_r"] = float(st.get("pyramid_r", 0) or 0)
    st["pyramid_frac"] = float(st.get("pyramid_frac", 0.5) or 0)
    if st["pyramid_r"] and not 0.5 <= st["pyramid_r"] <= 5:
        raise ValueError("浮盈加仓触发倍数需为 0（关闭）或 0.5–5 R")
    if not 0 <= st["pyramid_frac"] <= 1:
        raise ValueError("加仓比例需在 0–1 之间")
    st["tp_r"] = float(st.get("tp_r", 0) or 0)
    if st["tp_r"] and not 0.5 <= st["tp_r"] <= 20:
        raise ValueError("止盈倍数需为 0（关闭）或 0.5–20 R")
    st["tp_reentry"] = bool(st.get("tp_reentry", False))
    st["rebalance_band"] = float(st.get("rebalance_band", 0) or 0)
    if st["rebalance_band"] and not 0.05 <= st["rebalance_band"] <= 2:
        raise ValueError("调仓阈值需为 0（关闭）或 0.05–2（即 5%–200%）")
    st["rebalance_band_down"] = float(st.get("rebalance_band_down", 0) or 0)
    if st["rebalance_band_down"] and not 0.05 <= st["rebalance_band_down"] <= 2:
        raise ValueError("减仓调仓阈值需为 0（同调仓阈值）或 0.05–2（即 5%–200%）")
    st["port_vol_target"] = float(st.get("port_vol_target", 0) or 0)
    if st["port_vol_target"] and not 0.05 <= st["port_vol_target"] <= 2:
        raise ValueError("组合波动率目标需为 0（关闭）或 0.05–2（年化 5%–200%）")
    st["port_vol_lookback"] = int(st.get("port_vol_lookback", 180) or 180)
    if not 30 <= st["port_vol_lookback"] <= 1000:
        raise ValueError("组合波动率回看根数需在 30–1000 之间")
    st["name_vol_target"] = float(st.get("name_vol_target", 0) or 0)
    if st["name_vol_target"] and not 0.1 <= st["name_vol_target"] <= 5:
        raise ValueError("单币波动率封顶需为 0（关闭）或 0.1–5（年化 10%–500%）")
    st["name_vol_lookback"] = int(st.get("name_vol_lookback", 120) or 120)
    if not 20 <= st["name_vol_lookback"] <= 1000:
        raise ValueError("单币波动率回看根数需在 20–1000 之间")
    st["rebalance_mode"] = str(st.get("rebalance_mode", "stop") or "stop")
    if st["rebalance_mode"] not in ("stop", "atr"):
        raise ValueError("调仓模式只能是 stop 或 atr")
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
