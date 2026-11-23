# 长线新族：BLS 官方 JOLTS 职位空缺率 / 离职率 / 空缺数实时趋势 → 4h 默认书 #1 入场闸门（2026-11-23 ~04:30 PST，研究，否决）

## 查重
`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、ROTATION_LOCK 检索 JOLTS / job openings / 职位空缺 / quits / 离职率 / JTSJOR / JTSQUR：只有两处「下一轮（长线）」指针（STRATEGY_FORMULAS 第 10901 行、`eia_natgas_storage_report_event_1h.md`），从未执行。不同于已否决的 `fed_policy_labor_cycle_gate_4h`（DFF 利率周期 + UNRATE 失业率 / 萨姆规则）、`jobless_claims_regime_gate_4h`（周度初请 / 续请）、NFP / CPI 1h 发布事件。

## 数据（全部官方，不编造、不插值、不回补）
- BLS JOLTS 经 ALFRED（圣路易斯联储官方实时 vintage 存档）：`JTSJOR`（职位空缺率 %）、`JTSQUR`（离职率 %）、`JTSJOL`（职位空缺数，千人），每条 195 个 vintage 2010-08-11 → 2026-11-03；vintage 日 = BLS 发布日。
- 实时（防修订前视）：在 vintage V 只用该 vintage 自己的整条序列；V 的值从 V+1 00:00 UTC 起才用（BLS 10:00 ET 发布），日度前向填充到 4h K 线。2025 年政府停摆导致最大发布间隔 70 天（2025-12-09），照实前向填充。
- 最新官方值（2026-11-03 发布，2026-09 月，初值 P）：空缺率 4.5%、离职率 2.1%、空缺数 7,523 千；已与 api.bls.gov v1（`JTS000000000000000JOR/QUR/JOL`）逐值核对一致。
- 文件：`output/jolts_official_monthly.csv`（每月初值 + 初次发布日 + 最新值，三序列各 310 个观测月 2000-12 → 2026-09），`scratch/jolts4h/jolts_alfred_vintages_long.csv`（124,056 行 vintage×观测，不入库）。
- 价格：同脚本官方 OKX / Gate 4h 现货 + 永续深历史（至 2026-11-23 04:00 UTC）、官方资金费。

## 公式（`scratch/jolts4h/PRE_REGISTER.json`，sha256 `d84c6459…af90`，2026-11-23 04:15 PST 看任何 PnL 前锁定 60 格）
- X = vintage V 的序列（jol 取 log）；flag = 1（劳动力走强，有利）当 mean(最近 kind 个观测) − mean(最近 n 个观测) > 0；形式 {last: kind=1, n=3/6/12；m3: kind=3, n=12/24}。
- 侧：long_off（flag=0 劳动力走弱时拦新多）、cap_short_off（走强时拦新空）、both、contra_both（「坏消息即好消息」反向）。
- 先验 `qur_last_n12_long_off`（离职率 = 最干净的实时劳动者信心；低于 12 月均值 → 增长担忧 → 不开新多）；回退 `jor_m3_n12_long_off`（空缺率 3 月均 < 12 月均 = 劳动需求下行，平滑 0.1pp 取整噪声）。
- 只拦新开仓（默认 #1 双均线 50/150 4h、8 币永续），出场 / 止损 / 已有同向仓不动。真实费率永续 maker 2 / taker 5.1 bps；压力 spot 20 / perp 15.1 bps。
- 9 项 = {OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01} × {深度未见 < 2024-10-21、tune 2024-10-21 → 2026-03-05、post ≥ 2026-03-05 → 2026-11-23} Sharpe 胜同脚本基线；强观察还需 post 月份双所 ≥6/9 更好、post 收益不差、new8 未调参不差、邻域与安慰剂不匹配。

## 结果（真实费率，收益 % / Sharpe）
| 格 | 9 项 | OKX d8 深度 | Gate d8 深度 | OKX d8 tune | Gate d8 tune | OKX d8 post（月胜/负） | Gate d8 post（月胜/负） |
|---|---|---|---|---|---|---|---|
| 基线 | – | +35.14 / 0.71 | −4.32 / 0.08 | +85.08 / 1.47 | +84.25 / 1.46 | +72.98 / 2.49 | +73.40 / 2.51 |
| 先验 qur_last_n12_long_off | 1/9 | +21.20 / 0.56 | +1.90 / 0.15 | +52.16 / 1.08 | +50.40 / 1.06 | +68.46 / 2.47（1/2） | +69.12 / 2.49（1/2） |
| 回退 jor_m3_n12_long_off | 0/9 | +21.20 / 0.56 | −5.71 / 0.03 | +24.07 / 0.68 | +22.79 / 0.65 | +72.98 / 2.49（0/0，post 从未拦截） | +73.40 / 2.51（0/0） |
| 最好非先验 jol_last_n6_both | 9/9 | +67.59 / 1.27 | +48.98 / 0.79 | +80.48 / 1.50 | +78.75 / 1.48 | +78.42 / 2.66（4/4） | +79.63 / 2.69（4/4） |
| jol_last_n6_cap_short_off | 8/9 | +61.00 / 1.07 | +17.54 / 0.38 | +103.42 / 1.65 | +102.38 / 1.64 | +78.42 / 2.66（4/4） | +79.63 / 2.69（4/4） |
| jor_last_n12_cap_short_off | 7/9 | +35.14 / 0.71 | −0.44 / 0.15 | +92.57 / 1.56 | +91.86 / 1.55 | +84.54 / 2.81（5/2） | +85.24 / 2.83（5/2） |

- 2022–2025 劳动力市场几乎一直走弱，long_off 类格在深度 / tune 段大量拦多，tune 大损（先验 OKX tune 1.08 vs 1.47）；回退 post 从未触发。
- 最好格 jol_last_n6_both 的 post 边际全部来自空头侧（post 与 cap_short_off 完全相同），OKX d7 post 月 2/5；post 月份双所只有 4/4，达不到 ≥6/9。
- 压力费：jol_last_n6_both OKX d8 深度 +59.54 / 1.16（基线 +24.67 / 0.56），post +75.40 / 2.59（基线 +68.62 / 2.38），月份仍 4/4。
- 安慰剂（锚 jol_last_n6_both：±30/60/180/−120/±365 天平移 + 5 个 30 天块洗牌）：平移全部 0–3/9；但块洗牌 shuf5 同样 9/9（OKX post +71.80 / 2.57，月 5/4），shuf2 6/9（post +82.65 / 2.77）→ 真格不优于随机时间块。
- 邻域：n2 3/9、n4 5/9、n9 4/9、n18 3/9、n24 4/9、n36 0/9、m2_n6 6/9 → n=6 是孤点，邻域塌陷。
- new8 未调参（OKX / Gate 近 4500 根 4h）：jol_last_n6_both pre Sharpe 0.968 vs 0.971（OKX）、0.960 vs 0.971（Gate），post 0.80 vs 0.78、1.44 vs 1.39 → pre 双所略差。先验 pre 0.960 / 0.949（略差）。
- CSV：`output/research_jolts_gate_4h.csv`（297 行，含安慰剂 / 邻域 / 压力）、`output/research_jolts_gate_4h_new8.csv`（均不入库）。脚本 `scratch/jolts4h/{fetch,build,run,new8}.py`。

## 结论
**否决**。先验 1/9、回退 0/9；唯一 9/9 是非先验 jol_last_n6_both，但 post 月份 4/4（未达 ≥6/9 双所）、块洗牌安慰剂同样 9/9、邻域 n=6 孤点、new8 pre 略差。不实现、不进观察、不改默认、不改纸面。

## never retest by
改 n / 均值窗口 / 阈值 / 侧，在 JTSJOR / JTSQUR / JTSJOL 之间互换、做差或合成，改用招聘率 / 离职总数 / 裁员率（JTSHIR / JTSTSR / JTSLDR）、分行业 / 分地区 JOLTS、Beveridge 曲线（空缺 / 失业比）、修订后最新值代替实时 vintage、改发布滞后，或做 1h 发布事件 / 15m / 1d 版本、换交易所 / 换币池来重试这个「JOLTS 劳动力趋势闸门」机制。
