"""永续杠杆 / 逐仓保证金 / 强平价 / 资金费率（全部来自 OKX、Gate 官方公共接口；不含任何密钥）。

口径（USDT 本位线性永续，逐仓 isolated）：
  * 保证金 = 名义 / 杠杆；默认「杠杆不放大风险」：名义仍由单笔风险 / 单币权重 / 总敞口决定，杠杆只决定占用多少保证金。
  * 强平价（含平仓 taker 费，维持保证金率 mmr 取交易所公开的阶梯第 1 档 / 按名义选档）：
        多：liq = 均价 × (1 − 1/L + mmr + fee)
        空：liq = 均价 × (1 + 1/L − mmr − fee)      （qtw/margin.isolated_liq_price，fee = 平仓 taker）
    交易所实际用标记价格触发、并可能另扣强平费；逐仓被强平时该仓保证金全部损失，这里按「损失全部逐仓保证金」计。
  * 止损必须先于强平：L_eff = min(L, 交易所上限, floor(1/(d + mmr + fee + 0.5%)))，d = 止损相对加权均价的不利距离
    （qtw/margin.py 纯函数）；开仓、加仓 / 调仓、移动止损后都重算，记录降杠杆原因。
  * 资金费率：持仓跨过结算时刻时 PnL = −方向 × 费率 × 数量 × 价格（多头在正费率时付费，空头收取）。
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

from . import margin as M

LEV_MIN, LEV_MAX, LEV_DEFAULT = 1, 100, 10
LEV_WARN = 20  # 超过 20 倍页面给出红色警示

# 2026-11-13 从官方公共接口抓取的快照（OKX /api/v5/public/position-tiers isolated + instruments；
# Gate /api/v4/futures/usdt/contracts + risk_limit_tiers）。本账户名义很小，都落在第 1 档。
# 运行时若 data/leverage_tiers.json 存在（refresh() 拉取的最新阶梯），优先用它。
SNAPSHOT = {
    "okx": {
        "BTCUSDT": (0.004, 100), "ETHUSDT": (0.004, 100), "BNBUSDT": (0.0065, 50), "SOLUSDT": (0.004, 100),
        "XRPUSDT": (0.004, 100), "ADAUSDT": (0.0065, 50), "DOGEUSDT": (0.0065, 50), "AVAXUSDT": (0.0065, 50),
    },
    "gate": {
        "BTCUSDT": (0.003, 200), "ETHUSDT": (0.003, 200), "BNBUSDT": (0.0066, 75), "SOLUSDT": (0.005, 100),
        "XRPUSDT": (0.005, 100), "ADAUSDT": (0.0066, 75), "DOGEUSDT": (0.008333, 75), "AVAXUSDT": (0.008333, 75),
    },
}
DEFAULT_MMR, DEFAULT_VMAX = 0.01, 50  # 未知币种的保守近似（文档注明）
_CACHE: dict | None = None


def _cache_path() -> Path:
    from .paths import DATA_DIR
    return Path(DATA_DIR) / "leverage_tiers.json"


def _tiers() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = {}
        try:
            p = _cache_path()
            if p.exists():
                _CACHE = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            _CACHE = {}
    return _CACHE


def instrument(venue: str, symbol: str, notional: float = 0.0, price: float = 0.0) -> dict:
    """{"mmr", "max_lev", "source"}：按名义选维持保证金阶梯；没有阶梯缓存时用快照第 1 档。"""
    v, s = (venue or "okx").lower(), symbol.upper()
    t = (_tiers().get(v) or {}).get(s)
    if t and t.get("tiers"):
        for tr in t["tiers"]:
            cap = tr.get("risk_limit_usdt")
            if cap is None and tr.get("max_sz_contracts") is not None:
                cap = tr["max_sz_contracts"] * float(t.get("ct_val", 0) or 0) * float(price or 0) or float("inf")
            if notional <= float(cap or float("inf")):
                return {"mmr": float(tr["mmr"]), "max_lev": float(min(tr["max_lev"], t.get("max_lever", tr["max_lev"]))), "source": "官方阶梯（缓存）"}
        tr = t["tiers"][-1]
        return {"mmr": float(tr["mmr"]), "max_lev": float(tr["max_lev"]), "source": "官方阶梯（缓存，超出已拉档位）"}
    if s in SNAPSHOT.get(v, {}):
        m, x = SNAPSHOT[v][s]
        return {"mmr": m, "max_lev": float(x), "source": "官方第 1 档快照 2026-11-13"}
    return {"mmr": DEFAULT_MMR, "max_lev": float(DEFAULT_VMAX), "source": "近似（未知币种）"}


def liq_price(side: str, entry: float, lev: float, mmr: float, fee: float = 0.0) -> float:
    """逐仓强平价：复用 qtw/margin.isolated_liq_price（维持保证金率按 mmr + 平仓 taker 费，偏保守）。"""
    if not (entry > 0 and lev > 0):
        return float("nan")
    return max(0.0, M.isolated_liq_price(side, entry, max(1.0, lev), float(mmr) + float(fee)))


def liq_distance(side: str, entry: float, liq: float) -> float:
    if not (entry > 0) or liq != liq:
        return float("nan")
    return (entry - liq) / entry if side == "long" else (liq - entry) / entry


def pick(side: str, entry: float, stop: float, requested: float, venue: str, symbol: str, *,
         fee: float = 0.0, notional: float = 0.0, protect: bool = True, buffer: float = M.DEFAULT_BUFFER) -> dict:
    """为一笔永续仓选杠杆：min(设置, 交易所该币上限)；protect 时再用 margin.effective_isolated_leverage
    降到「止损（相对加权均价）先于强平」的最大整数倍。开仓、加仓 / 调仓、移动止损后都要重新调用。
    返回 {"lev", "liq", "mmr", "reason", "requested", "venue_max", "tier_source"}。"""
    ins = instrument(venue, symbol, notional, entry)
    req = max(1.0, min(float(requested), float(LEV_MAX)))
    lev = float(max(1, math.floor(min(req, ins["max_lev"]))))
    why = []
    if lev < req:
        why.append(f"{symbol} 在 {venue.upper()} 最高 {ins['max_lev']:g} 倍")
    mm = ins["mmr"] + float(fee)
    if protect and entry > 0 and stop > 0:
        safe = float(M.effective_isolated_leverage(lev, side, entry, stop, mm, buffer, LEV_MAX))
        if safe < lev:
            d = M.adverse_stop_distance(side, entry, stop)
            why.append(f"止损距均价 {d*100:.2f}%：{lev:g} 倍强平距离仅 {liq_distance(side, entry, liq_price(side, entry, lev, mm))*100:.2f}%，"
                       f"会先于止损强平 → 降到 {safe:g} 倍")
            lev = safe
    liq = liq_price(side, entry, lev, mm)
    return {"lev": float(lev), "liq": liq, "mmr": ins["mmr"], "reason": "；".join(why), "requested": req, "venue_max": ins["max_lev"],
            "tier_source": ins["source"]}


def stop_before_liq(side: str, stop: float, liq: float) -> bool:
    if liq != liq or liq <= 0:
        return True
    return stop > liq if side == "long" else stop < liq


# ---------------- 官方阶梯 / 资金费率拉取（公共接口，无密钥） ----------------

def refresh(timeout: float = 15) -> dict:
    """拉取两家交易所 8 个币的维持保证金阶梯写入 data/leverage_tiers.json（失败则保留快照）。"""
    from .market.base import HttpJson
    from .net import okx_rest_bases
    from .settings import SUPPORTED_SYMBOLS
    out: dict = {"okx": {}, "gate": {}, "fetched_at": int(time.time())}
    ok, gt = HttpJson(okx_rest_bases(), timeout=timeout, max_retries=2), HttpJson(["https://api.gateio.ws/api/v4"], timeout=timeout, max_retries=2)
    for s in SUPPORTED_SYMBOLS:
        b = s[:-4]
        try:
            tiers = ok.get("/api/v5/public/position-tiers", {"instType": "SWAP", "tdMode": "isolated", "instFamily": f"{b}-USDT"})["data"]
            ins = ok.get("/api/v5/public/instruments", {"instType": "SWAP", "instId": f"{b}-USDT-SWAP"})["data"][0]
            out["okx"][s] = {"ct_val": float(ins["ctVal"]), "max_lever": float(ins["lever"]),
                             "tiers": [{"max_sz_contracts": float(t["maxSz"]), "mmr": float(t["mmr"]), "max_lev": float(t["maxLever"])} for t in tiers[:8]]}
        except Exception:  # noqa: BLE001
            pass
        try:
            c = gt.get(f"/futures/usdt/contracts/{b}_USDT")
            tiers = gt.get("/futures/usdt/risk_limit_tiers", {"contract": f"{b}_USDT", "limit": 8})
            out["gate"][s] = {"max_lever": float(c["leverage_max"]),
                              "tiers": [{"risk_limit_usdt": float(t["risk_limit"]), "mmr": float(t["maintenance_rate"]), "max_lev": float(t["leverage_max"])} for t in tiers]}
        except Exception:  # noqa: BLE001
            pass
    if out["okx"] or out["gate"]:
        global _CACHE
        p = _cache_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out), encoding="utf-8")
        _CACHE = out
    return {"okx": len(out["okx"]), "gate": len(out["gate"])}


_FUND_SQL = ("CREATE TABLE IF NOT EXISTS funding_rates (venue TEXT NOT NULL, symbol TEXT NOT NULL, t_ms INTEGER NOT NULL, "
             "rate REAL NOT NULL, PRIMARY KEY (venue, symbol, t_ms))")


def _fund_table() -> None:
    from . import db
    db.execute(_FUND_SQL)


def fetch_funding(venue: str, symbol: str, since_ms: int, timeout: float = 15) -> int:
    """从官方公共接口补拉 since_ms 之后的已结算资金费率并写库。OKX 公共接口只保留约 3 个月。"""
    from . import db
    from .market.base import HttpJson
    from .net import okx_rest_bases
    _fund_table()
    b, rows = symbol.upper()[:-4], []
    if venue == "okx":
        h = HttpJson(okx_rest_bases(), timeout=timeout, max_retries=2)
        after = None
        for _ in range(30):
            p = {"instId": f"{b}-USDT-SWAP", "limit": 400}
            if after:
                p["after"] = after
            d = h.get("/api/v5/public/funding-rate-history", p).get("data", [])
            if not d:
                break
            rows += [(int(x["fundingTime"]), float(x.get("realizedRate") or x["fundingRate"])) for x in d]
            after = d[-1]["fundingTime"]
            if int(after) <= since_ms:
                break
    else:
        h = HttpJson(["https://api.gateio.ws/api/v4"], timeout=timeout, max_retries=2)
        t, end = int(since_ms // 1000), int(time.time())
        while t < end:
            d = h.get("/futures/usdt/funding_rate", {"contract": f"{b}_USDT", "limit": 1000, "from": t, "to": min(end, t + 100 * 86400)})
            rows += [(int(x["t"]) * 1000, float(x["r"])) for x in (d or [])]
            t += 100 * 86400
    rows = [r for r in rows if r[0] > since_ms]
    for tm, r in rows:
        db.execute("INSERT OR REPLACE INTO funding_rates(venue,symbol,t_ms,rate) VALUES(?,?,?,?)", (venue, symbol.upper(), tm, r))
    return len(rows)


_FUND_TRIED: dict = {}  # (venue, symbol) -> 上次补拉时间（秒），同一币 5 分钟内不重复请求


def _funding_due(venue: str, symbol: str, now_s: float | None = None) -> bool:
    """是否该向官方补拉：按库里最近两个结算点推断结算间隔（1–8 小时，默认 8 小时），
    下一个结算点已过去就补拉（之前固定「最新一条早于 9 小时前」才拉，会漏掉刚结算的那一笔：
    例如 08:00 已入库时，16:00 的结算要到 17:00 之后才会去拉，期间平掉的仓位就漏记资金费）。"""
    from . import db
    now_s = time.time() if now_s is None else now_s
    if now_s - _FUND_TRIED.get((venue, symbol), 0.0) < 300:
        return False
    r = db.query("SELECT t_ms FROM funding_rates WHERE venue=? AND symbol=? ORDER BY t_ms DESC LIMIT 2", (venue, symbol))
    if not r:
        return True
    last = int(r[0]["t_ms"])
    step = int(r[0]["t_ms"]) - int(r[1]["t_ms"]) if len(r) > 1 else 8 * 3600_000
    step = min(8 * 3600_000, max(3600_000, step))
    return now_s * 1000 >= last + step


def funding_series(venue: str, symbols: list[str], start_ms: int, *, fetch: bool = True, proxy_gate_for_okx: bool = True) -> tuple[dict, dict]:
    """{symbol: [(t_ms, rate), ...]} 与覆盖说明。库里没有就向官方补拉（fetch=True）。
    OKX 公共历史只有约 3 个月：更早的部分用 Gate 同币种官方费率代替（proxy_gate_for_okx，结果里注明）。"""
    from . import db
    _fund_table()
    out, info = {}, {}
    for s in symbols:
        def rows(v):
            return [(int(r["t_ms"]), float(r["rate"])) for r in db.query(
                "SELECT t_ms, rate FROM funding_rates WHERE venue=? AND symbol=? AND t_ms>=? ORDER BY t_ms", (v, s, start_ms))]
        if fetch:
            for v in ({venue, "gate"} if venue == "okx" and proxy_gate_for_okx else {venue}):
                try:
                    if _funding_due(v, s):
                        last = db.query("SELECT MAX(t_ms) m FROM funding_rates WHERE venue=? AND symbol=?", (v, s))[0]["m"]
                        _FUND_TRIED[(v, s)] = time.time()
                        fetch_funding(v, s, max(start_ms - 1, int(last or 0)))
                except Exception as e:  # noqa: BLE001
                    info[f"{s}:{v}:error"] = str(e)[:120]
        own = rows(venue)
        if venue == "okx" and proxy_gate_for_okx:
            first = own[0][0] if own else float("inf")
            px = [r for r in rows("gate") if r[0] < first]
            if px:
                info[s] = f"OKX 官方 {len(own)} 条 + 之前 {len(px)} 条用 Gate 官方费率代替"
            own = px + own
        else:
            info[s] = f"{venue.upper()} 官方 {len(own)} 条"
        out[s] = own
    return out, info


def funding_by_bar(times_ns, rows: list[tuple[int, float]]):
    """把结算点按 (times[i-1], times[i]] 归到第 i 根（i ≥ 1）：返回与 times 同长的费率和数组。"""
    import numpy as np
    t = np.asarray(times_ns, dtype="int64")
    acc = np.zeros(len(t))
    if not rows or not len(t):
        return acc
    ts = np.array([r[0] for r in rows], dtype="int64") * 1_000_000
    rs = np.array([r[1] for r in rows], dtype=float)
    k = np.searchsorted(t, ts, side="left")  # t[k-1] < ts <= t[k]
    ok = (k >= 1) & (k < len(t))
    np.add.at(acc, k[ok], rs[ok])
    return acc


def market_for(sig_or_side, cfg: dict) -> str:
    """某方向在哪个市场成交：perp_both → 多空都在 USDT 永续；spot_perp → 多现货、空永续。"""
    side = sig_or_side if isinstance(sig_or_side, str) else {1: "long", -1: "short"}.get(int(sig_or_side), "flat")
    if side not in ("long", "short"):
        return "-"
    mode = str((cfg.get("risk") or {}).get("trade_mode", "perp_both"))
    return "perp" if side == "short" or mode == "perp_both" else "spot"


def exposure_mult(cfg: dict) -> float:
    """「杠杆放大敞口」开关打开且多空都在永续时 = 杠杆倍数，否则 1（默认）。"""
    rk = cfg.get("risk") or {}
    if bool(rk.get("leverage_scales_exposure", False)) and str(rk.get("trade_mode", "perp_both")) == "perp_both":
        return float(max(1, min(LEV_MAX, int(rk.get("perp_leverage", 1) or 1))))
    return 1.0
