# 短线：美国财政部官方 DTS 每日 TGA 余额冲击 → 8 币永续篮子 1h 事件（2026-11-21 ~13:10 PST，否决；非先验 H48 弱观察，不实现）

## 查重
- 检索 docs/STRATEGY_FORMULAS.md 全部轮换记录、docs/*.md 侧记、`output/research_*.csv`（1,000+ 个）、记忆：Daily Treasury Statement / DTS / operating cash / TGA 日度冲击 0 个完成条目。
- 不是已否决的联储净流动性（WALCL − TGA − RRP，周度 / 日度水平与趋势当 4h 入场闸门）、财政部 MTS 月度财政闸门、财政部拍卖结果 1h 事件（docs/us_treasury_auction_event_1h.md）、SOFR−IORB、MMF/H.8，也不是 FOMC / ECB / BoE / CPI / NFP 等宏观公布事件。本轮是**每日 TGA 变动的 z 冲击**，在 DTS 官方公布时刻做 1h 事件、持有 4–48h。

## 数据（仅官方）
- 财政部 Fiscal Data API `v1/accounting/dts/operating_cash_balance`（https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance），2015-01-02 → 2026-11-19，2,985 个营业日记录。
- 账户口径：≤2021-09-30 `Federal Reserve Account` close_today_bal；2021-10-01→2022-04-15 `Treasury General Account (TGA)` close_today_bal；≥2022-04-18 `Treasury General Account (TGA) Closing Balance`（API 把当日收盘放在 open_today_bal）。连续性检查：每日开盘 = 前一日收盘，**0 处断点**。最大日历间隔 4 天（周末 + 联邦假日），无补数、无合成行。
- 公布滞后：记录日 D 的 DTS 在下一个营业日美东 16:00 公布（= 官方序列下一条记录日；最后一条取下一个工作日）。入场 = 公布日美东 17:00 开始的 1h 根开盘（≥公布 + 60 分钟），出场 = H 根后开盘。
- 官方序列 `output/tga_dts_official_daily.csv`（不入库）。

## 公式与预注册（PRE_REGISTER.json，13:03 PST 锁定，先于任何 PnL，72 格）
- chg1 = TGA_close(D) − TGA_close(上一条)；chg5 = TGA_close(D) − TGA_close(5 条前)。
- z = (x_D − 前 N 条均值) / 前 N 条标准差（不含 D），N ∈ {60, 250}，k ∈ {2, 3}，H ∈ {4, 24, 48}。
- 方向：hyp_both（TGA 骤降 z ≤ −k = 财政投放流动性 → 篮子做多；TGA 骤升 z ≥ k = 抽水 → 做空）、drain_long（只做多）、contra_both（镜像安慰剂）。
- 先验 chg1_z_N250_k2.0_hyp_both_H24；备选 chg5_z_N250_k2.0_hyp_both_H24。
- 8 币默认篮子（BTC ETH BNB SOL XRP ADA DOGE AVAX）等权；OKX 与 Gate 官方 1h 永续 K 线 + 官方资金费；吃单 5.1 bps/边，压力 15.1 / 20 bps；重叠事件跳过。未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）。分段：train（OKX 起点 2022-01-29 → 2024-10-21，深未见）/ test（→2026-03-05）/ post（2026-03-05 →）/ Gate 窗口（2025-09-24 →）。安慰剂：±168h 平移；2,000 次同数量同方向的随机工作日美东 17:00 根。

## 结果（实费，均值 bps/笔，`output/research_tga_dts_shock_event_1h.csv`，3,973 行）
- 先验 chg1_N250_k2_hyp_both_H24：OKX d8 train +17.6（n41, t0.43）/ test **−38.0**（n24）/ post +203.6（n11, t2.51, 逐月 8/9）；new8 train −33.8 / test −26.2 / post +119.2；Gate post +203.7（逐月 8/9）。只有 5/8，test 与 new8 深段为负；随机安慰剂分位 train 70 / test 37 / post 99。压力 15.1 bps 下 train −2.4 / test −58.1。**不过线。**
- 备选 chg5_N250_k2_hyp_both_H24：OKX train −88.5 / test −41.7 / post −33.0，new8 全负，0/8。**否决。**
- 基线（每个 DTS 公布日无条件多 / 空，同脚本）：多 H24 OKX post −38.3，空 H24 post +17.9（post 是下跌段）。
- 72 格中 usable 8/8 只有 4 格：chg1_N250_k2_hyp_both_H48、chg1_N60_k2_hyp_both_H48（非先验），以及 2 个 chg5 contra_both H24（和假设方向相反，判为噪音）。
- 非先验 chg1_N250_k2_hyp_both_H48：OKX train +90.9（n40, t1.3）/ test +134.3（n20, t1.0）/ post +229.1（n11, t1.7, 逐月 8/9）；new8 +4.8 / +90.9 / +161.9；Gate post +229.4（逐月 8/9）；压力 15.1 bps 仍正（70.9 / 114.3 / 209.1），20 bps 也正。事后随机安慰剂分位 train 92 / test 89 / post 98；±168h 平移 train 为负，但 test +168h 也有 +106、Gate 窗口 +168h 有 +159（和真实值接近）。按年：2022 +31%、2023 −2.7%、2024 +41%、2025 −3.0%、2026 +22%（单笔 bps 求和）。邻域：N60 同样 8/8，k3 H48 7/8，但 H24 与 H4 大多不过（H24 test 为负），t 值都 ≤1.7。
- 结论：先验 / 备选都没过 → **否决**（按预注册不实现、不加影子账本）。chg1 k2 hyp_both H48 作为**弱观察**（只能事后选出、t 值低、2023/2025 为负、H24 邻格失败），每月新 DTS 数据后前向复核，不进纸面。

## 不再重测
勿以同一机制换 N / k / H / 方向、换 chg1/chg5/chgN 或百分比变化、换存款 / 取款分项（Table II）、换 TGA 水平趋势、换公布入场时刻、换 MTS / 净流动性组合或改单币再测；H48 弱观察只做前向复核，不事后再调。

## 文件
- `output/research_tga_dts_shock_event_1h.csv`、`output/tga_dts_official_daily.csv`（均不入库）；脚本 scratch/tgadts1h/{fetch,events,run,analyze,diag,placebo_h48}.py、PRE_REGISTER.json（+ sha256）；事后安慰剂 scratch/tgadts1h/placebo_h48_posthoc.csv。
- 纸面：8788/8789/8792/8793 均 health ok，12:55 PST 后 0 笔新成交，无代码 / 参数改动。
