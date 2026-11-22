"""#15 人民币中间价篮子走弱冲击：用官方中间价真实片段（国家外汇管理局查询页 / 历史工作簿，来源外汇交易中心）检验事件时点与持有逻辑。"""
from pathlib import Path

import numpy as np
import pandas as pd

from qtw import cnyfix as CF
from qtw import settings as S
from qtw import strategies as R

FIX = pd.read_csv(Path(__file__).with_name("data") / "cny_fix_official_2025-06_2026-11.csv", dtype={"date": str})


def _ind(idx, syms):
    c = np.full(len(idx), 100.0)
    d = {s: pd.DataFrame({"close": c, "high": c, "low": c, "open": c}, index=idx) for s in syms}
    return {"spot": d, "perp": d}


def _p(**kw):
    p = dict(R.BY_ID["cny_fix_basket_1h"]["params"])
    p.update(kw)
    return p


def test_events_on_official_fixings_land_on_0100_utc_bar():
    ev = CF.basket_events(FIX, 120, 2.0)
    days = set(pd.to_datetime(ev.index, unit="ms", utc=True).strftime("%Y-%m-%d %H:%M"))
    # 研究 prior_events / supp 事件表里的 2026 年 post 事件日（02:00 UTC 入场）
    for d in ("2026-08-20", "2026-09-03", "2026-10-23", "2026-11-06"):
        assert f"{d} 01:00" in days
    assert all(t.endswith("01:00") for t in days)


def test_signal_holds_24_bars_from_event_bar_and_no_retrigger():
    idx = pd.date_range("2026-08-18", "2026-09-10", freq="h", tz="UTC")
    syms = [f"S{i}" for i in range(8)]
    sig = R.sig_cny_fix_basket(_ind(idx, syms), idx, syms, _p(_fix_df=FIX))["S0"]
    i0 = idx.get_loc(pd.Timestamp("2026-08-20 01:00", tz="UTC"))
    assert sig[:i0].sum() == 0 and sig[i0:i0 + 24].all() and sig[i0 + 24] == 0
    j0 = idx.get_loc(pd.Timestamp("2026-09-03 01:00", tz="UTC"))
    j1 = idx.get_loc(pd.Timestamp("2026-09-04 01:00", tz="UTC"))  # 9/4 也是事件，但仍在 9/3 持有期内 → 不重复触发
    assert sig[j0:j0 + 24].all() and sig[j0 + 24] == 0 and j1 == j0 + 24
    assert int(sig.sum()) % 24 == 0


def test_no_official_data_or_range_index_means_no_trade():
    idx = pd.date_range("2026-08-18", periods=100, freq="h", tz="UTC")
    syms = ["A", "B"]
    assert R.sig_cny_fix_basket(_ind(idx, syms), idx, syms, _p(_fix_df=FIX.iloc[:50]))["A"].sum() == 0
    ri = pd.RangeIndex(100)
    assert R.sig_cny_fix_basket(_ind(ri, syms), ri, syms, _p(_fix_df=FIX))["A"].sum() == 0


def test_parse_official_page_table():
    html = ("<table><tr><td>日期</td><td>美元</td><td>欧元</td><td>日元</td><td>港元</td></tr>"
            "<tr><td>2026-11-20</td><td>671.31</td><td>734.46</td><td>4.1961</td><td>85.618</td></tr>"
            "<tr><td>2026-11-19</td><td>671.28</td><td>734.44</td><td>4.1995</td><td>85.62</td></tr></table>")
    assert CF.parse_page(html) == [("2026-11-20", 671.31, 734.46, 4.1961), ("2026-11-19", 671.28, 734.44, 4.1995)]


def test_registered_as_watch_event_and_default_unchanged():
    spec = R.BY_ID["cny_fix_basket_1h"]
    assert spec["no"] == 15 and R.is_event("cny_fix_basket_1h")
    assert R.VERDICTS["cny_fix_basket_1h"]["status"] == "观察"
    c = R.strategy_cfg(S.DEFAULTS, "cny_fix_basket_1h")
    assert c["strategy"]["interval"] == "1h" and c["risk"]["max_weight_per_name"] == 0.0625
    assert S.DEFAULTS["strategy"].get("interval", "4h") == "4h"
