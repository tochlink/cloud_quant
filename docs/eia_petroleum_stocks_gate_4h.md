# 长线族：美国 EIA 周度石油库存（商业原油 / 原油+成品油总库存 / 车用汽油）→ 默认 #1 4h 入场闸门

- 研究时间：2026-11-27（预注册锁定 11:58 PST，sha 见 `scratch/eiacrude4h/PRE_REGISTER.sha256`）；结论 **否决（REJECTED）**，不改默认、不改候选、不上纸面。
- 族名：`eia_petroleum_stocks_gate_4h`；脚本 `scratch/eiacrude4h/`（build.py、run.py、new8.py、supp.py 及日志）。
- 结果 CSV（不入库）：`output/research_eia_petroleum_stocks_gate_4h.csv`（528 行，含邻域 / 安慰剂 / 压力费）、`_new8.csv`、`_supp.csv`。

## 机制
美国商业石油库存高于趋势 / 上升 = 实体原油需求偏弱 = 增长放缓 → 风险偏好下降：拦截**新开多**（经济先验侧 long_off / both）。闸门只拦新开仓；持仓、止损、退出、再平衡不变。

查重：EIA 周度石油库存此前只作为 1h WPSR 发布意外事件测过（`eia_wpsr_crude_event_1h`，已否决），从未作为长线 4h 库存体制闸门。也不是 WTI 价格趋势（us_rates_oil_trend）、钻机数（us_rigcount）、天然气价格 / 库存（henryhub_natgas、eia_natgas_storage_report_event_1h）、汽柴油零售价（gasoline_diesel_price_gate_4h）。原定财政部季度再融资已被 `us_treasury_auction_demand_gate_4h` 的勿重测条款覆盖，故换题。

## 数据与滞后
- EIA 官方周度历史表（eia.gov/dnav/pet/hist/LeafHandler.ashx，千桶）：
  - `WCESTUS1` 商业原油（不含 SPR）1982-08-20 → 2026-11-20，2,304 周（1983 年前 6 个早期日历缺口）；
  - `WTESTUS1` 原油+成品油总库存（不含 SPR）与 `WGTSTUS1` 车用汽油总库存 1990-01-05 → 2026-11-20，各 1,925 周，0 缺口。
- 截至周五 D 的数据 **D+8 00:00 UTC** 才使用（WPSR 周三 10:30 ET 发布，节假日顺延到周四；2022 年以来 251 次官方首发最晚为 D+7 18:00 UTC）。用当前版本（修订罕见；251 次中 250 次与首发日历表一致）。
- 最新值（2026-11-20 周）：商业原油 418,906、总库存 1,222,567、汽油 217,682（千桶）。

## 公式（120 格预注册）
- 序列 s ∈ {crude, tot, gas}；
- `trend_n`（n = 4 / 13 / 26 周）：库存 > n 周均线 → flag=1；
- `chg_n`（n = 4 / 13 周）：n 周变化 > 0 → flag=1；
- `z52gt_k`（k = 0.5 / 1 / 2）：52 周 z > k → flag=1；
- 方向 side ∈ {long_off, short_off, both, contra_both, cap_short_off}（flag=1 时 long_off 拦新开多；both = flag=1 拦多、flag=0 拦空；contra_both 反之；short_off / cap_short_off 为对照侧）。
- 先验格 `crude_trend_n13_long_off`；回退格 `tot_chg_n4_both`；经济先验侧 long_off / both。
- 框架：`scratch/fedswap4h/run.py` 同构（只换数据 / 序列 / 先验 / 回退），qtw.backtest.run_backtest 默认双均线 50/150 4h；OKX d8（2023-02→）、Gate d8（2022-07→）、OKX d7_noBNB（2022-04→）；deep_unseen < 2024-10-21，tune_pre，post 2026-03-05 → 2026-11-14；官方资金费；永续吃单 5.1 / 挂单 2 bps，压力费现货 20 / 永续 15.1 bps；new8 不调参。
- 判定线：9 个 Sharpe 切片 ≥6/9、OKX 与 Gate d8 post 收益不差、post 月份两所都 ≥6/9 更好、deep_unseen 成立、邻域稳定、安慰剂更差；弱观察 = 先验 / 经济侧格 ≥6/9 且两所 post 不差但月份线不达标（仍需邻域与安慰剂不反证）。

## 主要结果（真实费；收益 % / Sharpe；月份 = post 更好 / 更差）

| 格 | 场所 | deep_unseen | tune_pre | post | 月份 | Sharpe 胜 |
|---|---|---|---|---|---|---|
| 基线 | OKX d8 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | — | — |
| 基线 | Gate d8 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / 2.25 | — | — |
| 基线 | OKX d7_noBNB | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / 2.10 | — | — |
| 先验 crude_trend_n13_long_off | OKX d8 | +62.47 / 1.09 | +61.87 / 1.24 | +49.18 / 2.17 | 1 / 3 | 合计 3/9 |
| 先验 | Gate d8 | +28.51 / 0.51 | +59.86 / 1.21 | +49.41 / 2.18 | 1 / 3 | |
| 先验 | OKX d7_noBNB | +78.87 / 0.97 | +62.76 / 1.26 | +42.11 / 1.97 | 1 / 3 | |
| 回退 tot_chg_n4_both | OKX d8 | +87.30 / 1.39 | +28.17 / 0.79 | −11.02 / −1.48 | 2 / 6 | 合计 3/9 |
| 回退 | Gate d8 | +47.10 / 0.72 | +26.29 / 0.75 | −10.96 / −1.48 | 2 / 6 | |
| 回退 | OKX d7_noBNB | +86.56 / 1.07 | +38.13 / 0.98 | −11.78 / −1.68 | 2 / 6 | |
| 最佳经济侧 crude_chg_n13_both | OKX d8 | +53.23 / 1.09 | +98.05 / 1.65 | +71.07 / 2.64 | 4 / 2 | 9/9 |
| crude_chg_n13_both | Gate d8 | +36.51 / 0.65 | +99.90 / 1.66 | +71.67 / 2.66 | 4 / 2 | |
| crude_chg_n13_both | OKX d7_noBNB | +60.32 / 0.89 | +99.08 / 1.69 | +60.52 / 2.50 | 3 / 3 | |
| 最佳整体（非先验侧）tot_chg_n4_cap_short_off | OKX d8 | +34.58 / 0.78 | +92.39 / 1.58 | +73.38 / 2.73 | 4 / 3 | 9/9 |
| tot_chg_n4_cap_short_off | Gate d8 | +4.52 / 0.20 | +94.01 / 1.60 | +73.94 / 2.74 | 4 / 3 | |
| tot_chg_n4_cap_short_off | OKX d7_noBNB | +60.28 / 0.86 | +93.12 / 1.63 | +64.70 / 2.66 | 3 / 4 | |

- 120 格中 9/9 仅 2 格（上表两格），6/9 有 11 格；先验与回退都只有 3/9。
- 压力费（post）：基线 OKX +55.94 / 2.12、Gate +56.78 / 2.15；crude_chg_n13_both OKX +68.08 / 2.56、Gate +68.66 / 2.58；tot_chg_n4_cap_short_off OKX +70.83 / 2.66、Gate +71.42 / 2.68；先验 OKX +46.22 / 2.06、Gate +46.64 / 2.08。

## new8（不调参，各所最近 4,500 根；pre = 首根 → 2026-03-05，post 之后）
| 格 | OKX pre | OKX post | 月份 | Gate pre | Gate post | 月份 |
|---|---|---|---|---|---|---|
| 基线 | +33.92 / 0.77 | +3.26 / 0.28 | — | +31.70 / 0.75 | +16.36 / 1.00 | — |
| crude_trend_n13_long_off（先验） | +32.93 / 0.83 | +2.37 / 0.22 | 3 / 1 | +30.88 / 0.81 | +15.92 / 0.99 | 3 / 1 |
| tot_chg_n4_both（回退） | +15.55 / 0.45 | −13.32 / −1.49 | 2 / 7 | +14.19 / 0.43 | −13.59 / −1.53 | 3 / 6 |
| crude_chg_n13_both | +40.06 / 0.96 | +13.07 / 0.98 | 4 / 3 | +38.14 / 0.93 | +26.56 / 1.61 | 5 / 2 |
| tot_chg_n4_cap_short_off | +13.32 / 0.40 | +12.34 / 0.99 | 4 / 3 | +13.93 / 0.42 | +26.82 / 1.69 | 4 / 3 |

压力费 new8：crude_chg_n13_both OKX post +11.48 / 0.87（基线 +1.87 / 0.18），Gate +24.67 / 1.51（基线 +15.34 / 0.95）。tot_chg_n4_cap_short_off 的 new8 pre 两所都大幅落后基线。

## 邻域
- tot_chg_n4_cap_short_off（n = 2 / 3 / 6 / 8 / 10 / 17）：n3 的 post 与 n4 相同但 deep 崩（Gate −26.90 / −0.40），n2 3/9、n6 4/9、n8 / n10 / n17 0 胜；Gate deep 全部为负 → 不稳。
- crude_chg_n13_both（supp，n = 6 / 8 / 10 / 17 / 20 / 26）：只有 n10 post 好于基线（OKX +64.85 / 2.53、Gate +65.54 / 2.56）；n6 崩（OKX post −3.77 / −0.42，月份 1/7），n8 +23.03、n17 +49.27、n20 +37.93、n26 +38.33（OKX）均低于基线 +59.90 → 孤峰，不稳。

## 安慰剂（±30 / ±90 / +180 / −120 / +365 / −119 天平移 + 3 次周度打乱，各三套切片）
- 先验格自己只有 3/9，而它的打乱安慰剂 shuf3 达到 6/9 → 先验不优于安慰剂。
- crude_chg_n13_both 的安慰剂最多 4/9（shuf3），但 +180 天平移的 post 几乎同样好（OKX +66.04 / 2.63、Gate +66.74 / 2.65，对比真实 +71.07 / 2.64、+71.67 / 2.66）→ post 优势不依赖库存信息的时间对齐，像是闸门把交易数压低后的样本效应（交易数 285 vs 基线 439）。

## 结论：否决（REJECTED）
- 先验 crude_trend_n13_long_off：3/9，post 两所都差于基线（OKX +49.18 vs +59.90，Gate +49.41 vs +60.32），月份 1/3，new8 post 也落后 → 失败。
- 回退 tot_chg_n4_both：3/9，post 两所 ≈ −11%，月份 2/6 → 失败。
- crude_chg_n13_both（经济侧 both）：9/9、deep 与 new8 成立、压力费成立，字面上满足预注册的弱观察线，但 post 月份只有 4/2（两所），未到 ≥6/9；邻域只有 n10 / n13 有效、n6 崩；+180 天安慰剂 post 几乎相同 → 不满足邻域稳定与安慰剂优势的常设要求，不升观察。
- tot_chg_n4_cap_short_off：非先验对照侧，月份 4/3，Gate deep 薄、邻域 deep 全负、new8 pre 落后 → 不采纳。
- 默认、候选、纸面实例全部不变，无代码改动。

## 勿重测
不要以下列任何方式重测「美国 EIA 周度石油库存 → 4h 入场闸门」：改 n（趋势窗 / 变化窗）、改方向（long_off / short_off / both / contra_both / cap_short_off）、在商业原油 / 总库存 / 汽油之间互换序列、改 z 阈值或 z 窗口、改用其他 EIA 周度库存序列（馏分油、丙烷、库欣、SPR、炼厂开工率、进出口、PADD 分区库存等）、改滞后或改用首发版本、改用库存天数 / 季节性去趋势等同一机制变体。WPSR 1h 发布意外事件也已另行否决（`eia_wpsr_crude_event_1h`）。
