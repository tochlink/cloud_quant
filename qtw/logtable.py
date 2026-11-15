"""日志用的框线表格（多币种开平仓记录一行一个币，而不是一长串分号）。

列宽按终端显示宽度计算：中日韩字符 / 全角符号算 2 格，其余 1 格（类 wcwidth，无额外依赖）。
"""
from __future__ import annotations

import re
import unicodedata

from .timeutil import utcnow


def dwidth(s: str) -> int:
    """字符串在等宽终端里的显示宽度（东亚宽字符 W / F 算 2，组合字符算 0）。"""
    w = 0
    for ch in str(s):
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _pad(s: str, w: int) -> str:
    s = str(s)
    return s + " " * max(0, w - dwidth(s))


def table(headers: list[str], rows: list[list]) -> str:
    """框线表格：每列宽 = 该列最宽单元格 + 左右各 1 格空白。"""
    cells = [[str(c) for c in headers]] + [[("" if c is None else str(c)) for c in r] for r in rows]
    n = len(headers)
    cells = [r + [""] * (n - len(r)) for r in cells]
    ws = [max(dwidth(r[i]) for r in cells) for i in range(n)]
    line = lambda l, m, r: l + m.join("─" * (w + 2) for w in ws) + r  # noqa: E731
    row = lambda r: "│" + "│".join(" " + _pad(c, w) + " " for c, w in zip(r, ws)) + "│"  # noqa: E731
    out = [line("┌", "┬", "┐"), row(cells[0]), line("├", "┼", "┤")]
    out += [row(r) for r in cells[1:]]
    out.append(line("└", "┴", "┘"))
    return "\n".join(out)


def stamp() -> str:
    """本机时间 YYYY-MM-DD HH:MM:SS（与日志时间同一时区）。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def block(title: str, headers: list[str], rows: list[list]) -> str:
    """多行日志块：第一行「时间 标题」，下面是表格。前面加换行，让表格从行首开始对齐。"""
    return f"\n{stamp()} {title}\n{table(headers, rows)}"


# 主账本事件串：「BTCUSDT 开空·永续 0.012 @ 63419.5，止损 65000（…）」「ETHUSDT 平多 0.5 @ 1739（ATR止损·实时，盈亏 -3.21）」
_EV = re.compile(r"^(?P<sym>[A-Z0-9]+USDT)\s+(?P<act>\S+)\s+(?P<qty>[-+0-9.eE]+)\s*@\s*(?P<px>[-+0-9.eE]+)(?P<rest>.*)$")
_PNL = re.compile(r"(?:盈亏|已实现|损失保证金)\s*([-+][0-9.]+)")


def event_rows(events: list[str]) -> list[list]:
    """把主账本事件字符串拆成表格行：币种 / 动作 / 数量 / 价格 / 盈亏(U) / 说明。拆不开的整句放「说明」。"""
    rows = []
    for e in events:
        m = _EV.match(str(e).strip())
        if not m:
            rows.append(["—", "", "", "", "", str(e)])
            continue
        rest = m.group("rest").strip().lstrip("，,").strip()
        pm = _PNL.search(rest)
        note = rest.strip("（）() ")
        rows.append([m.group("sym"), m.group("act"), m.group("qty"), m.group("px"), pm.group(1) if pm else "", note])
    return rows


EVENT_HEADERS = ["币种", "动作", "数量", "价格", "盈亏(U)", "说明"]


def events_block(title: str, events: list[str]) -> str:
    return block(title, EVENT_HEADERS, event_rows(events))


__all__ = ["dwidth", "table", "block", "event_rows", "events_block", "EVENT_HEADERS", "utcnow"]
