"""热加载（不重启生效）：策略参数 + 策略代码。

* 参数：后台线程每 POLL_SEC 秒比对「已保存设置（风控 → 策略参数，SQLite）+ 自动调参覆盖（adaptive_params）」的策略 / 风控 / 费率，
  有变化就记一张「参数 / 旧值 / 新值」表到日志与 SQLite（param_changes 表），并立即唤醒 worker 用新参数跑一轮决策
  （信号、开平、反手；调仓每根 K 线只做一次）。
* 代码：RELOADABLE 里的模块文件（qtw/strategy.py、qtw/adaptive.py、qtw/rebalance.py、qtw/settings.py 默认值文件）
  修改时间变化 → 先编译检查，再 importlib.reload；成功后把其它 qtw 模块里 `from .x import f` 绑定的旧函数换成新函数。
  编译失败 / 执行出错 / 必需函数缺失 → 原样恢复旧模块（继续用上一版），并记录错误。
* 持仓：热加载只换参数与函数，不碰纸面账本 / 持仓 / 止损；已有持仓保留原止损，离场按新参数的信号与止损判定，不会成为孤儿仓。
  重载与交易周期互斥（持有 engine.CYCLE_LOCK 时才换模块）。
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)
POLL_SEC = 5.0
RELOADABLE = {
    "qtw.strategy": ("indicators", "combine", "side_of", "trend_ok", "btc_regime_blocks_long", "name_vol_mult"),
    "qtw.adaptive": ("trend_size_mult", "combine_mult", "bias_blocks_short", "effective_cfg", "retune_once"),
    "qtw.rebalance": ("plan",),
    "qtw.settings": ("load", "save", "update", "validate", "DEFAULTS"),
}
PRESERVE = {"qtw.settings": ("_LOCK",)}  # 进程内共享的锁不能被重建
WATCH_SECTIONS = ("strategy", "risk", "fees", "symbols", "venue")

_state = {"running": False, "last_check": "", "last_change": None, "last_reload": None, "last_error": "", "changes": 0, "reloads": 0}
_stop = threading.Event()
_thread: threading.Thread | None = None
_snap: dict = {"params": None, "mtimes": {}}
_lock = threading.Lock()


def _flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = d
    return out


def params_snapshot(cfg: dict | None = None) -> dict:
    from . import adaptive
    from . import settings as S
    cfg = cfg if cfg is not None else S.load()
    eff = adaptive.effective_cfg(cfg)
    return _flatten({k: eff.get(k) for k in WATCH_SECTIONS})


def diff(old: dict, new: dict) -> list[list]:
    keys = sorted(set(old) | set(new))
    return [[k, old.get(k), new.get(k)] for k in keys if old.get(k) != new.get(k)]


def _mtimes() -> dict:
    out = {}
    for name in RELOADABLE:
        m = sys.modules.get(name)
        f = getattr(m, "__file__", None) if m else None
        if f and os.path.exists(f):
            out[name] = os.path.getmtime(f)
    return out


def _rebind(name: str, old: dict, new_mod) -> int:
    """把其它 qtw 模块里绑定到旧模块对象（函数 / 类 / 常量字典）的名字换成新对象。返回替换个数。"""
    n = 0
    for mname, m in list(sys.modules.items()):
        if not mname.startswith("qtw") or m is None or mname == name:
            continue
        d = getattr(m, "__dict__", None)
        if not d:
            continue
        for attr, val in list(d.items()):
            if attr.startswith("__"):
                continue
            ov = old.get(attr)
            if ov is None or val is not ov or not hasattr(new_mod, attr):
                continue
            if callable(val) or isinstance(val, (dict, list, tuple)):
                setattr(m, attr, getattr(new_mod, attr))
                n += 1
    return n


def reload_module(name: str) -> dict:
    """安全重载一个模块。失败时恢复旧版本。返回 {"ok", "module", "error", "rebound"}。"""
    mod = sys.modules.get(name)
    if mod is None:
        return {"ok": False, "module": name, "error": "模块未加载", "rebound": 0}
    path = Path(mod.__file__)
    snap = dict(mod.__dict__)
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")  # 语法错误：不动旧模块
    except SyntaxError as e:
        return {"ok": False, "module": name, "error": f"语法错误（继续用上一版）：{e}", "rebound": 0}
    try:
        try:  # 同一秒内改动且文件大小不变时 .pyc 会被误判为最新：先删掉缓存的字节码
            import importlib.util
            os.remove(importlib.util.cache_from_source(str(path)))
        except OSError:
            pass
        importlib.invalidate_caches()
        new = importlib.reload(mod)
        for attr in PRESERVE.get(name, ()):
            if attr in snap:
                setattr(new, attr, snap[attr])
        missing = [a for a in RELOADABLE.get(name, ()) if not hasattr(new, a)]
        if missing:
            raise RuntimeError(f"缺少必需的函数 / 常量：{', '.join(missing)}")
        if name == "qtw.settings":
            new.validate(new._merge(new.DEFAULTS, {}))  # 默认值本身必须能通过校验
    except Exception as e:  # noqa: BLE001 —— 任何错误都回退到上一版
        mod.__dict__.clear()
        mod.__dict__.update(snap)
        sys.modules[name] = mod
        return {"ok": False, "module": name, "error": f"重载失败（已回退上一版）：{type(e).__name__}: {e}"[:400], "rebound": 0}
    n = _rebind(name, snap, new)
    return {"ok": True, "module": name, "error": "", "rebound": n}


def check_once(kick: bool = True) -> dict:
    """比对一次参数与代码文件；有变化时记录并（可选）唤醒 worker。返回本次结果。"""
    from . import adaptive
    from . import logtable as LT
    from .timeutil import iso, utcnow
    out = {"param_changes": [], "reloads": []}
    with _lock:
        # 1) 代码文件
        mt = _mtimes()
        if not _snap["mtimes"]:
            _snap["mtimes"] = mt
        changed = [n for n, t in mt.items() if _snap["mtimes"].get(n) != t]
        if changed:
            try:
                from .engine import CYCLE_LOCK
            except Exception:  # noqa: BLE001
                CYCLE_LOCK = threading.RLock()
            with CYCLE_LOCK:  # 不在交易周期中途换函数
                for n in changed:
                    r = reload_module(n)
                    out["reloads"].append(r)
                    _snap["mtimes"][n] = mt[n]
            rows = [[r["module"], "成功" if r["ok"] else "失败（回退上一版）", r["rebound"], r["error"]] for r in out["reloads"]]
            log.info("%s", LT.block("策略代码热加载", ["模块", "结果", "重绑定", "错误"], rows))
            _state.update(last_reload={"time": iso(utcnow()), "rows": rows}, reloads=_state["reloads"] + 1)
            if any(not r["ok"] for r in out["reloads"]):
                _state["last_error"] = "；".join(r["error"] for r in out["reloads"] if not r["ok"])[:400]
            try:
                adaptive.log_change("code_reload", rows)
            except Exception:  # noqa: BLE001
                pass
        # 2) 参数
        try:
            snap = params_snapshot()
        except Exception as e:  # noqa: BLE001
            _state["last_error"] = f"读取设置失败：{e}"[:300]
            return out
        if _snap["params"] is None:
            _snap["params"] = snap
        else:
            d = diff(_snap["params"], snap)
            if d:
                out["param_changes"] = d
                _snap["params"] = snap
                log.info("%s", LT.block("策略参数热加载（下一周期 / 立即生效，持仓保留原止损）", ["参数", "旧值", "新值"],
                                        [[k, json.dumps(a, ensure_ascii=False), json.dumps(b, ensure_ascii=False)] for k, a, b in d]))
                _state.update(last_change={"time": iso(utcnow()), "rows": d}, changes=_state["changes"] + 1)
                try:
                    adaptive.log_change("settings", d)
                except Exception:  # noqa: BLE001
                    pass
        _state["last_check"] = iso(utcnow())
    if kick and (out["param_changes"] or any(r["ok"] for r in out["reloads"])):
        try:
            from . import realtime, worker
            realtime.invalidate_cfg()
            worker.kick("hot_reload")
        except Exception:  # noqa: BLE001
            pass
    return out


def _loop():
    from . import settings as S
    while not _stop.is_set():
        try:
            if S.load()["strategy"].get("hot_reload", True):
                check_once()
        except Exception as e:  # noqa: BLE001
            _state["last_error"] = str(e)[:300]
            log.warning("热加载检查失败：%s", e)
        _stop.wait(POLL_SEC)
    _state["running"] = False


def start() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _state["running"] = True
    _thread = threading.Thread(target=_loop, name="qtw-hotreload", daemon=True)
    _thread.start()


def stop(timeout: float = 3.0) -> None:
    _stop.set()
    t = _thread
    if t and t.is_alive():
        t.join(timeout=timeout)
    _state["running"] = False


def status() -> dict:
    return {**_state, "poll_sec": POLL_SEC, "modules": list(RELOADABLE)}
