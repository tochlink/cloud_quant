# 长线新族：FHFA 官方购房价格指数（purchase-only HPI，首发版本）增速 → 4h 默认书 #1 入场闸门（2026-11-27 ~19:15 PST，否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 已超过 GitHub 连接器写入上限，只在本地追加）。

- 查重：`docs/STRATEGY_FORMULAS.md`（全部轮换记录）、`docs/*.md`（174 篇）、`output/research_*.csv`（1,373 个）、`scratch/ROTATION_LOCK.txt`、记忆检索 FHFA / HPI / HPIPONM / house price / home price / 房价 / Case-Shiller / CSUSHPI：只有 `docs/bea_pce_gdp_release_event_1h.md` 的「下一轮（长线）」指针，从未测过。
  勿重测核对：`us_mortgage_housing_gate_4h` 只禁 30 年按揭**利率**与营建**开工**；`nyfed_sce_expectations_gate_4h` 禁的是 SCE 家庭**房价预期**（调查），不是成交房价；SLOOS、G.19、M2、金融压力均是不同序列。本族是成交房价（财富效应）本身。
- 数据（只用官方，不编造、不插值、不回补）：FHFA 美国购房价格指数（purchase-only，月度，季调）经 ALFRED（圣路易斯联储官方实时版本库）`HPIPONM226S` 的 143 个 vintage（2015-01-22 → 2026-11-24）。每个**首次发布新月份 M** 的 vintage 内部计算增速（首发值，无修订泄漏），只修订的 vintage 跳过；142 个首发月份 2014-11 → 2026-09，**2025-10 官方从未发布**（缺口保留，不补）。最新首发 2026-09：同比 +2.52%，3 个月年化 +2.03%，1 个月年化 +0.49%。
  可用时点：vintage（发布日，09:00 ET）**次日 00:00 UTC** 起使用。官方表 `output/fhfa_hpi_firstrelease.csv`。
- 公式（看 PnL 前锁定 `scratch/fhfahpi4h/PRE_REGISTER.json`，sha256 `b8ab4a7a…`，2026-11-27 18:57 PST 写入并随即开跑；文件内 locked_at 字段误写为 19:20，未改以保持 sha），120 格：flag = 1 表示**房价增速走弱**。
  序列：sa_yoy（同比）、sa_3m（3 个月年化）、sa_1m（1 个月年化）；形式：trend_n{6,12}（低于近 n 次发布均值）、chg_n{3,12}（比 n 次前低）、z36lt{0.5,1,1.5,2}（36 次发布 z < −k）。
  侧：long_off（走弱 → 不新开多）、short_off（不走弱 → 不新开空）、both、contra_both、cap_short_off（走弱 → 不新开空）。只拦新开仓，已有同向仓位不受影响。
  经济先验 `sa_yoy_chg_n3_long_off`（同比比 3 个月前低 → 不新开多），回退 `sa_3m_trend_n6_long_off`；安慰剂 = 先验 8 个时移（±30 / ±90 / +180 / −120 / +365 / −119 天）。
- 回测：同脚本默认 #1（双均线 50/150，8 币 perp_both 10×，官方资金费），官方 OKX / Gate 4h 永续深缓存；真实费 maker 2 / taker 5.1 bps，压力费 perp 15.1 / spot 20 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根 4h）。

## 结果（`output/research_fhfa_house_price_gate_4h.csv` 435 行；`_supp.csv` 36 行；`_new8.csv` 20 行）

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | Gate d8 深未见 / 调参 | OKX d7 深未见 / 调参 | post 收益 / Sharpe（OKX、Gate）；月份 好/差 | new8 pre Sharpe（OKX、Gate） |
|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | 0.09 / 1.46 | 0.75 / 1.56 | +59.90%/2.23、+60.32%/2.25 | 0.75、0.73 |
| **先验 sa_yoy_chg_n3_long_off** | 3/9 | 1.22 / 0.79 | 0.50 / 0.77 | 1.05 / 0.98 | 与基线逐位相同（0/0） | 0.88、0.86 |
| **回退 sa_3m_trend_n6_long_off** | 0/9 | 0.48 / 0.53 | 0.06 / 0.49 | 0.59 / 0.72 | +31.58%/1.51、+32.01%/1.53；0/4 | 0.60、0.56 |
| 最高 sa_3m_trend_n12_cap_short_off（非先验） | 8/9 | 0.70 / 1.82 | 0.18 / 1.83 | 0.89 / 1.90 | +60.76%/2.27、+61.33%/2.28；2/5、2/5 | 0.88、0.89（post 0.26 vs 0.28、0.97 vs 1.00） |
| 邻域 n9（事后，非预注册） | 9/9 | 0.85 / 1.69 | 0.31 / 1.74 | 1.00 / 1.79 | +70.72%/2.57、+71.21%/2.58；5/2、5/2 | 0.86、0.84（post 0.80 vs 0.28、1.41 vs 1.00） |
| 邻域 n6 / n18 / n24 / n3 / n4 / n36 | 6/9、4/9… | — | — | — | +35.7、+35.0、+35.0、+25.7、+25.7、+9.4%（OKX），全部远低于基线 | — |

- **先验**：深未见三处都大胜（OKX 1.22 vs 0.71），但 2024-11 → 2026-03 房价同比持续下行，flag 常开、拦掉大选后大部分新多，调参窗 0.79 / 0.77 / 0.98 vs 1.47 / 1.46 / 1.56 全输；post 段默认书几乎没有被拦的新多 → 与基线相同 → 3/9。8 个时移安慰剂同样 3/9（与真实相同，无时点特异性）。否决。
- **回退**：拦多过多，九段 0 胜，post −28 pp。否决。
- **8/9 的 sa_3m_trend_n12_cap_short_off**（房价 3 个月年化低于 12 次均值 → 不新开空，与经济先验无关）：post 边只有 +0.9 / +1.0 pp，post 月份 2 好 5 差（两所），远达不到 ≥ 6/9；压力费下 post +57.36 vs +55.94、+57.93 vs +56.78；new8 post 两所都略差。邻域塌陷：n3 / n4 post −34 pp，n6 −24 pp，n18 / n24 −25 pp，n36 −50 pp；只有事后 n9 单点 9/9（post +10.8 pp，月份 5/2，new8 也更好），但两侧 n6 与 n12 都不成立，是孤立峰值。事后时移安慰剂（`_supp.csv`）：n12 与 n9 的 ±30 / ±90 / +180 / −120 天 post 全部低于真实（OKX / Gate d8 为 +23.9% ~ +54.3%），但 −90d 时移的调参窗 Sharpe（n12：1.97 / 2.02 / 2.00；n9：1.87 / 1.85 / 1.91）高于真实 → 调参窗增益不是时点特异。
- 结论：**否决**。不实现、不进观察名单、不改默认、无纸面变更、无代码改动。月度房价首发是极慢的体制变量（每月一次、约 2 个月滞后），作为闸门只能整段开关，结果对窗口长度极度敏感。

## 勿重测（never retest by…）

不要通过改 n / k / z 窗 / 侧 / 滞后重测本族；不要在同比 / 3 个月 / 1 个月 / 水平 / 季调与非季调之间换序列，也不要改用 FHFA 全交易指数（USSTHPI，季度）、分州 / 分普查区 HPI、标普 Case-Shiller、Zillow / Redfin、NAR 成屋销售与中位价、新屋销售价格、Census 房价、BIS / OECD 房价、或中国 70 城房价等其他房价序列来重测「房价财富效应 → 默认 #1 入场闸门」同一机制；也不要把 FHFA 发布日改成 1h 事件来绕过本条（如要做 1h 事件须另立机制并先查重）。n9 cap_short_off 单点只能用 2026-11-27 之后的前向数据复核，不得据此调参。

## 文件
- `output/research_fhfa_house_price_gate_4h.csv`、`_supp.csv`、`_new8.csv`、`output/fhfa_hpi_firstrelease.csv`（均不入库）。
- 脚本 `scratch/fhfahpi4h/{fetch_batch,build,run,supp,new8}.py`、`PRE_REGISTER.json(.sha256)`、`alfred_batch/`（ALFRED 原件，不推送）。

## 下一轮（短线 1h）
美国财政部官方国债回购（Treasury Securities Buybacks，fiscaldata.treasury.gov / TreasuryDirect 公告与结果，2024-05 起每周多次）单次回购「接受额 / 报价额」比率冲击 → 8 币永续篮子 1h 顺势 / 逆势事件（`docs/safe_gold_reserves_gate_4h.md` 的指针，尚未被执行）；须先核对 `us_treasury_auction_event_1h`、`us_treasury_auction_demand_gate_4h`、`tga_dts_shock_event_1h`、`jgb_auction_result_event_1h` 勿重测范围，若判同机制就换题。
