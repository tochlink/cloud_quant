# 长线新族：美国人口普查局 MTIS 库存 / 销售比（官方首发 vintage：全部企业 ISRATIO / 制造商 MNFCTRIRSA / 零售商 RETAILIRSA）→ 4h 默认书 #1 入场闸门（2026-11-28 ~02:05 PST，研究，否决）

## 查重
rg `ISRATIO / MNFCTRIRSA / RETAILIRSA / inventor / business inventories / 库存销售` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、1,414 个 `output/research_*.csv` 文件名、`/workspace/scratch`：0 条已完成测试（只有轮换日志里一条「下一轮候选」提及）。区别于已否决的耐用品订单（`census_durable_goods_gate_4h`，订单 / 资本开支）、零售销售 RSAFS（`us_real_activity_sentiment`）、EIA 原油库存（`eia_petroleum_stocks_gate_4h`，能源库存）、货运、JOLTS、G.19。机制是「库存周期」：库存相对销售堆积。

## 数据（全部官方，不编造、不插值、不回补）
- 美国人口普查局 Manufacturing & Trade Inventories and Sales（MTIS），经 ALFRED（圣路易斯联储官方实时 vintage 存档）：`ISRATIO`（全部企业库存 / 销售比）、`MNFCTRIRSA`（制造商）、`RETAILIRSA`（零售商），季调，各 144 个 vintage 2015-01-14 → 2026-11-17。
- 首发口径：每个**首次发布新月份 M** 的 vintage 只取该 vintage 的 v[M]（不用修订值）。三序列各 143 个首发月 2014-11 → 2026-09，0 缺月。
- 发布时间 10:00 ET；保守从 vintage 日 +1 天 00:00 UTC 起用，前向填充到 4h K 线。
- 最新首发（2026-11-17 发布，2026-09 月）：全部企业 1.33、制造商 1.46、零售商 1.35。
- 文件：`output/census_mtis_isratio_firstrelease.csv`（不入库）；脚本 `scratch/isratio4h/{fetch_batch,build,run,new8}.py`。
- 价格：同脚本官方 OKX / Gate 4h 现货 + 永续深历史（至 2026-11-14）、官方资金费。

## 公式（`scratch/isratio4h/PRE_REGISTER.json`，sha256 `314787b4…ad34`，任何 PnL 前锁定 120 格）
- flag = 1（库存销售比偏高 / 上升）：trend_n（比率 > 最近 n 次发布均值，n=6/12）、chg_n（比率 − n 次前 > 0，n=3/12）、z36（36 次发布 z > k，k=0.5/1/1.5/2）。实现上 x = −比率，沿用耐用品脚本的 flag 代码（格名保留 trend_n / chg_n / z36lt_k 标签）。
- 侧：long_off（偏高拦新多）、short_off、both、contra_both、cap_short_off（偏高拦新空）。
- 先验 `tot_trend_n6_long_off`（库存堆积 → 减产 / 增长担忧 → 不开新多）；回退 `ret_chg_n3_long_off`。
- 只拦新开仓（默认 #1 双均线 50/150 4h、8 币永续），出场 / 止损 / 已有同向仓不动。真实费率永续 maker 2 / taker 5.1 bps；压力 spot 20 / perp 15.1 bps。
- 9 项 = {OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01} × {深度未见 < 2024-10-21、tune → 2026-03-05、post → 2026-11-14} Sharpe 胜同脚本基线。

## 结果（真实费率，收益 % / Sharpe；post 月 = 2026-03 后 9 个月好于 / 差于基线的月数）
| 格 | 9 项 | OKX d8 深度 | Gate d8 深度 | OKX d8 tune | Gate d8 tune | OKX d8 post（月） | Gate d8 post（月） |
|---|---|---|---|---|---|---|---|
| 基线 | – | +35.14 / 0.71 | −3.63 / 0.09 | +85.08 / 1.47 | +84.25 / 1.46 | +59.90 / 2.23 | +60.32 / 2.25 |
| 先验 tot_trend_n6_long_off | 3/9 | +60.97 / 1.05 | +29.85 / 0.52 | +27.33 / 0.73 | +25.99 / 0.71 | 同基线（0/0，post 基本不触发） | 同基线（0/0） |
| 回退 ret_chg_n3_long_off | 3/9 | +96.12 / 1.45 | +58.21 / 0.82 | +45.05 / 0.96 | +42.89 / 0.93 | +55.89 / 2.21（1/2） | +56.48 / 2.23（1/2） |
| 最好 ret_chg_n3_cap_short_off | 6/9 | +41.23 / 0.85 | +11.53 / 0.30 | +109.63 / 1.73 | +107.68 / 1.71 | +29.07 / 1.37（0/2） | +29.53 / 1.39（0/2） |

- 没有任何格 ≥7/9，也没有格同时满足「≥6/9 且两所 post 不差」，压力费按预注册跳过。
- 先验 / 回退在深度未见段（2022–2024 库存高企期）三所都大赢，但 tune 段大亏（OKX 0.73 / 0.96 vs 1.47），post 段库存比回落、闸门几乎不触发。
- 唯一 6/9 格（cap_short_off）post 收益腰斩（+29 vs +60），月份 0/2。
- 安慰剂（锚先验）：**+30 天平移 6/9、+90 天 5/9，都好于真格 3/9** → 真实发布时点没有特异性。
- 邻域（锚 ret_chg_n3_cap_short_off）：n2 / n4 post 同样腰斩，n6 / n9 / n18 / n24 只 3–4/9 且 post 与基线相同 → 不稳。
- new8 未调参（OKX / Gate 近 4500 根 4h，Sharpe pre / post）：基线 0.76 / 0.28、0.71 / 1.00；先验 0.67 / 0.40、0.64 / 1.11（pre 变差）；回退 0.86 / 0.54、0.84 / 1.22（月 3/0）；cap_short_off 0.68 / −0.26、0.60 / 0.60（变差）。回退在 new8 较好，但在 d8 tune 与 post 都输，不足以改变结论。
- CSV（不入库）：`output/research_census_mtis_inventory_sales_gate_4h.csv`（405 行，含安慰剂 / 邻域）、`output/research_census_mtis_inventory_sales_gate_4h_new8.csv`。

## 结论
**否决**。先验 3/9、回退 3/9；唯一 6/9 格 post 大幅落后；post 月份无格两所 ≥6/9；时间平移安慰剂好于真格；邻域不稳。不实现、不进观察、不改默认、不改纸面。

## never retest by
改 n / 均值窗口 / z 阈值 / 侧 / 方向，在 ISRATIO / MNFCTRIRSA / RETAILIRSA / 批发商 WHLSLRIRSA / 汽车零售库存比 / 不含汽车零售库存比之间互换、做差或合成，改用库存水平 / 库存同比 / 销售同比 / 环比，改用修订后最新值代替首发 vintage，改发布滞后，改用预估经济指标（Advance Economic Indicators 零售 / 批发库存）、ISM 库存分项、地区联储库存分项作同类「库存周期」替身，或做发布日 1h 事件 / 15m / 1d 版本、换交易所 / 换币池来重试这个「美国库存 / 销售比闸门」机制。
