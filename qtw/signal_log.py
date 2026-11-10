"""信号变化日志：每个周期把各标的最新已收盘 K 线信号与上一次记录比较，变化时记一行（时间、标的、旧 → 新、执行动作）；
信号不变但发生调仓（加仓 / 减仓）时也记一行（旧 = 新）。

首次见到某标的时，用历史 K 线里最近一次信号切换补一行（标注「系统启动前」），让页面能看到当前信号从何时开始。
"""
from __future__ import annotations

from . import db
from .timeutil import iso, sh, utcnow

ADVICE = {1: "做多", -1: "做空", 0: "空仓"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS signal_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT NOT NULL, bar_time TEXT NOT NULL, symbol TEXT NOT NULL,
  old_signal INTEGER, new_signal INTEGER NOT NULL, action TEXT, venue TEXT
);
CREATE INDEX IF NOT EXISTS signal_log_sym ON signal_log(symbol, id);
"""


def _ensure(conn):
    conn.executescript(SCHEMA)


def last_signals(conn=None) -> dict[str, int]:
    c = conn or db.connect()
    _ensure(c)
    rows = db.query("SELECT symbol, new_signal FROM signal_log WHERE id IN (SELECT MAX(id) FROM signal_log GROUP BY symbol)", (), c)
    return {r["symbol"]: int(r["new_signal"]) for r in rows}


def record(rows: list[dict], actions: dict[str, str], venue: str, conn=None) -> list[dict]:
    """rows：compute_signals 的行（需含 signal / as_of / signal_since / prev_signal）。返回新写入的日志行。"""
    c = conn or db.connect()
    _ensure(c)
    prev = last_signals(c)
    now = iso(utcnow())
    out = []
    for r in rows:
        if r.get("error") or "signal" not in r or not r.get("as_of"):
            continue
        s, new = r["symbol"], int(r["signal"])
        if s not in prev:
            # 首次记录：补上历史里最近一次切换（系统启动前），没有切换就记数据起点
            old = r.get("prev_signal")
            row = dict(time=now, bar_time=r.get("signal_since") or r["as_of"], symbol=s,
                       old_signal=None if old is None else int(old), new_signal=new,
                       action="开始记录（该信号在系统启动前已生效）", venue=venue)
        elif prev[s] != new:
            row = dict(time=now, bar_time=r["as_of"], symbol=s, old_signal=prev[s], new_signal=new,
                       action=actions.get(s) or "无持仓动作", venue=venue)
        elif "调仓" in (actions.get(s) or ""):
            # 信号未变但按新 K 线调了仓位（加仓 / 减仓）也记一行，方便看到仓位随风险预算变化
            row = dict(time=now, bar_time=r["as_of"], symbol=s, old_signal=new, new_signal=new,
                       action=actions[s], venue=venue)
        else:
            continue
        db.execute("INSERT INTO signal_log(time,bar_time,symbol,old_signal,new_signal,action,venue) VALUES(?,?,?,?,?,?,?)",
                   tuple(row.values()), c)
        out.append(row)
    return out


def recent(limit: int = 30, conn=None) -> list[dict]:
    c = conn or db.connect()
    _ensure(c)
    rows = db.query("SELECT * FROM signal_log ORDER BY id DESC LIMIT ?", (int(limit),), c)
    import pandas as pd
    for r in rows:
        try:
            r["bar_time_sh"] = sh(pd.Timestamp(r["bar_time"]).to_pydatetime())
            r["time_sh"] = sh(pd.Timestamp(r["time"]).to_pydatetime())
        except (ValueError, TypeError):
            r["bar_time_sh"] = r["time_sh"] = ""
        r["old_cn"] = ADVICE.get(r["old_signal"], "—") if r["old_signal"] is not None else "—"
        r["new_cn"] = ADVICE.get(r["new_signal"], "—")
    return rows
