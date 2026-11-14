"""成交页默认显示全部成交数据，并在周期 / 平仓事件后重新拉取（不靠定时轮询）。"""
import re
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(r"(?:async )?function " + name + r"\(.*?\n}\n", JS, re.S)
    assert m, name
    return m.group(0)


def test_page_trades_defaults_to_all_tab_and_parallel_fetch():
    body = _fn("pageTrades")
    assert 'S.tradeTab = "all"' in body
    load = _fn("loadTrades")
    assert 'Promise.all([api("/api/trades"), api("/api/orders")])' in load


def test_refresh_all_reloads_trades_on_trades_page():
    body = _fn("refreshAll")
    assert 'S.page === "trades"' in body and "loadTrades()" in body


def test_no_timer_polling_for_trades():
    assert not re.search(r"setInterval\([^)]*(loadTrades|pageTrades)", JS)
