# 长线新族：美国人口普查局 M3 耐用品订单预估报告（官方首发 vintage：核心资本品订单 / 耐用品总订单）→ 4h 默认书 #1 入场闸门（2026-11-28 ~01:00 PST，研究，否决）

## 查重
本轮候选（1）美联储 G.19 消费信贷（`fed_g19_consumer_credit_gate_4h`）、（2）人行社融（`pboc_tsf_credit_gate_4h`）、（3）零售销售 RSAFS（`us_real_activity_sentiment_gate_4h`）与 JOLTS（`jolts_gate_4h`）、以及 M2（`m2_money_supply_regime_gate_4h`）**均已测过并否决**，按规则不重测。改选同类「官方首发宏观月度」中从未测过的耐用品订单：rg `durable / DGORDER / NEWORDER / ADXTNO / capital goods / factory orders / 耐用品 / 核心资本品` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、约 1,406 个 `output/research_*.csv` 文件名、`/workspace/scratch`：0 条。区别于已否决的 INDPRO（产出）、RSAFS（消费）、Census 企业申请、SLOOS、货运。

## 数据（全部官方，不编造、不插值、不回补）
- 美国人口普查局 M3 耐用品报告，经 ALFRED（圣路易斯联储官方实时 vintage 存档）：`DGORDER`（耐用品新订单总额）、`NEWORDER`（非国防资本品不含飞机新订单 = 核心资本品订单）、`ADXTNO`（不含运输，仅存档），季调，各 292 个 vintage 2015-01-06 → 2026-11-25。
- 首发口径：每个**首次发布新月份 M** 的 vintage（= 预估报告 Advance Report）里，只用该 vintage 自己的整条序列计算增速；完整 M3 报告的修订 vintage 跳过。三序列各 144 个首发 2014-11 → 2026-10 月，0 缺月。
- 发布时间：08:30 ET；保守地从 vintage 日 +1 天 00:00 UTC 起用，日度前向填充到 4h K 线。
- 最新首发（2026-11-25 发布，2026-10 月）：核心资本品订单同比 +14.67%、3m3m 年化 +14.68%；耐用品总订单同比 +12.73%。
- 文件：`output/census_durable_goods_firstrelease.csv`（不入库）；脚本 `scratch/durgood4h/{fetch_batch,build,run,new8}.py`。
- 价格：同脚本官方 OKX / Gate 4h 现货 + 永续深历史（至 2026-11-14）、官方资金费。

## 公式（`scratch/durgood4h/PRE_REGISTER.json`，sha256 `e3b25d03…fada4`，2026-11-28 00:40 PST 看任何 PnL 前锁定 120 格）
- 序列：core_yoy = NEWORDER 同比；core_3m3m = (近 3 月均 / 前 3 月均)^4 − 1；dg_yoy = DGORDER 同比（均为首发值）。
- flag = 1（订单走弱）：trend_n（x < 最近 n 次发布均值，n=6/12）、chg_n（x − x[−n] < 0，n=3/12）、z36lt_k（36 次发布 z < −k，k=0.5/1/1.5/2）。
- 侧：long_off（走弱拦新多）、short_off、both、contra_both、cap_short_off（走强拦新空）。
- 先验 `core_yoy_trend_n6_long_off`（企业资本开支收缩 → 增长担忧 → 不开新多）；回退 `dg_yoy_chg_n3_long_off`。
- 只拦新开仓（默认 #1 双均线 4h、8 币永续），出场 / 止损 / 已有同向仓不动。真实费率永续 maker 2 / taker 5.1 bps；压力 spot 20 / perp 15.1 bps。
- 9 项 = {OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01} × {深度未见 < 2024-10-21、tune → 2026-03-05、post → 2026-11-14} Sharpe 胜同脚本基线。

## 结果（真实费率，收益 % / Sharpe）
| 格 | 9 项 | OKX d8 深度 | Gate d8 深度 | OKX d8 tune | Gate d8 tune | OKX d8 post（月胜/负） | Gate d8 post（月胜/负） |
|---|---|---|---|---|---|---|---|
| 基线 | – | +35.14 / 0.71 | −3.63 / 0.09 | +85.08 / 1.47 | +84.25 / 1.46 | +59.90 / 2.23 | +60.32 / 2.25 |
| 先验 core_yoy_trend_n6_long_off | 3/9 | +103.39 / 1.51 | +53.42 / 0.78 | +48.93 / 1.01 | +46.69 / 0.98 | +59.90 / 2.23（0/0，post 从未触发） | +60.32 / 2.25（0/0） |
| 回退 dg_yoy_chg_n3_long_off | 3/9 | −2.20 / 0.09 | −21.99 / −0.25 | +113.43 / 1.77 | +112.57 / 1.76 | +50.93 / 2.02（1/2） | +51.58 / 2.04（1/2） |
| 最好非先验 core_yoy_trend_n6_cap_short_off | 6/9 | −6.06 / −0.05 | −21.69 / −0.37 | +86.77 / 1.50 | +85.44 / 1.49 | +62.61 / 2.37（1/1） | +63.07 / 2.39（1/1） |
| dg_yoy_trend_n6_long_off | 6/9 | +45.12 / 0.88 | +22.71 / 0.44 | +86.24 / 1.52 | +83.56 / 1.50 | 同基线（0/0） | 同基线（0/0） |
| core_3m3m_z36lt1_long_off | 6/9 | +51.95 / 0.94 | +4.63 / 0.21 | +91.12 / 1.54 | +89.44 / 1.52 | 同基线（0/0） | 同基线（0/0） |

- 没有任何格 ≥7/9。先验在深度未见段（2022–2024 资本开支下行期）大赢三所（OKX d7 +113.6 vs +54.9），但 tune 段大亏（OKX 1.01 vs 1.47），2026 核心订单一直强，post 从未触发 → post 月份 0/0，达不到 ≥6/9。
- 6/9 的 cap_short_off 格深度三所全输（OKX −6 vs +35），post 月份只 1/1；其余两个 6/9 格 post 根本不触发。
- 压力费：先验 OKX d8 深度 +90.57 / 1.39（基线 +24.67 / 0.56），tune +41.08 / 0.89（基线 +75.18 / 1.35），post 与基线相同 +55.94 / 2.12；cap_short_off 深度 −11.32（基线 +24.67）。
- 安慰剂（锚先验，±30/±90/180/−120/365/−119 天平移）：**−90 天平移（提前 90 天用数据）6/9，优于真格 3/9**（OKX d8 深度 +82.43、tune +90.46），−120/−119 天 4/9 → 真实发布时点没有特异性。
- 邻域（锚 cap_short_off）：n3 / n4 6/9（与 n6 post 完全相同），n9 3/9，n18 / n24 0/9，n36 3/9 → 只在短窗口成立，长窗口塌陷。
- new8 未调参（OKX / Gate 近 4500 根 4h）：先验 pre Sharpe 0.770 vs 0.764 / 0.712 vs 0.711（持平，几乎不触发），post 相同；cap_short_off pre 0.689 vs 0.764 / 0.649 vs 0.711（变差），post 0.53 vs 0.28 / 1.30 vs 1.00；回退 pre 1.07 vs 0.76 / 1.02 vs 0.71（较好）但 post 持平略差。
- CSV（不入库）：`output/research_census_durable_goods_gate_4h.csv`（444 行，含安慰剂 / 邻域 / 压力）、`output/research_census_durable_goods_gate_4h_new8.csv`。

## 结论
**否决**。先验 3/9、回退 3/9；最好 6/9 格要么深度全输（cap_short_off），要么 post 不触发；post 月份没有任何格双所 ≥6/9；−90 天平移安慰剂好于真格；邻域塌陷。不实现、不进观察、不改默认、不改纸面。

## never retest by
改 n / 均值窗口 / z 阈值 / 侧 / 方向，在 DGORDER / NEWORDER / ADXTNO / 核心资本品出货（ANDENO 出货、NEWORDER 出货 ACOGNO）/ 不含国防 / 未完成订单（AMDMUO）/ 库存订单比之间互换、做差或合成，改用同比 ↔ 3m3m ↔ 环比 ↔ 水平，用修订后最新值代替首发 vintage，改发布滞后，改用 ISM 新订单 / 地区联储新订单分项 / 工厂订单（AMTMNO）全 M3 报告做同类「企业订单 / 资本开支」替身，或做 08:30 ET 发布日 1h 事件 / 15m / 1d 版本、换交易所 / 换币池来重试这个「美国耐用品 / 核心资本品订单趋势闸门」机制。

## 下一轮（短线）
官方 TRON 主网 USDT（TRC-20 合约 TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t）每小时转账笔数 / 大额转账金额冲击 → 8 币永续篮子 1h 顺势 / 逆势事件（TronGrid 官方节点日志，下一根 1h 入场）。查重：`output/research_*.csv` 与 docs 无 tron 条目；须先确认不被 `stablecoin_supply_shock_event_1h`（只禁发行量 / 链上供给）与 `cctp_usdc_flow_event_1h` 勿重测覆盖，若判同机制就换题。
