# 长线新族：美国 Census 官方周度新设企业申请（Business Formation Statistics）同比趋势 → 4h 默认书 #1（MA 50/150）入场闸门（2026-11-22 ~20:08–20:30 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md 与全部 docs/*.md 中「Census」只出现在 HOUST 营建开工（按揭 / 营建 4h 闸门，已否决）；无 business application / Business Formation / BFS / 新设企业；约 1,228 个 `output/research_*.csv` 无对应文件；/workspace/scratch 无 bfs 目录；记忆中无。最近的已否决族：初请失业金、NY Fed WEI、TSA、IPO（S-1）发行、按揭 / 营建、Empire / 费城调查、CPI / 非农事件。（上一轮指针「克利夫兰联储通胀 nowcast」因与 breakeven / CPI 族机制重叠、且 nowcast 有修订，本轮未选。）
- 数据（仅官方）：US Census BFS 周度未季调 `bfs_us_apps_weekly_nsa.csv`（https://www.census.gov/econ/bfs/csv/bfs_us_apps_weekly_nsa.csv，Last-Modified 2026-11-12 15:09 GMT，sha256 8eb058e3ab4f0007…）+ 官方周日期表 `date_table.csv`。1,086 周，周末 2006-01-07 → 2026-10-31；一个官方 14 天周（2020 第 52 周止于 2021-01-02）。不补值、不插值；存 `output/census_bfs_weekly_official.csv`（不入库）。
- **滞后（point-in-time）**：官方周四发布（当前文件滞后 12 天）；保守取周六结束的周 E 从 **E+21 天 00:00 UTC** 起才使用；2025 年联邦政府停摆（无发布）期间周末 2025-09-13..11-15 的值统一推迟到 2025-12-11 00:00 UTC。
- 公式：y = ln(4 周申请数之和) − ln(364 天前对应 4 周之和)（同比，去未季调季节性）。序列 `ba` = 全部申请 BA_NSA，`hba` = 高倾向（可能雇员）申请 HBA_NSA。flag = 1 表示申请**走弱**：`yoy_lt0`：y < 0；`trend_nN`：y < 近 N 周均值（N 13 / 26 / 52）；`momN_lt0`：y − y[−N] < 0（N 4 / 13）；`z_n104_lt1`：y 相对 104 周滚动 z < −1。侧：long_off（flag=1 不开新多）/ short_off（flag=0 不开新空）/ both / contra_both（flag=1 不开新空、flag=0 不开新多）；只拦新开仓，已持仓、止损、离场不变。
- 预注册：2 序列 × 7 形式 × 4 侧 = **56 格** + 同脚本基线；`scratch/bfsapps4h/PRE_REGISTER.json` 于 2026-11-22 20:10:26 PST、任何 PnL（及占用率）之前锁定（sha256 803e2146…852b）。唯一先验 `hba_trend_n26_long_off`（高倾向申请同比跌破 26 周均值 = 美国零售 / 创业风险偏好退潮 → 拦新多）；回退 `ba_yoy_lt0_both`。
- 验证：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续 + 官方资金费；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（永续 maker 2 / taker 5.1 bps，现货 10），压力费 taker 15.1 bps；安慰剂 = 先验 / 回退各 10 个时间平移（±7 / ±14 / ±60 / +180 / −120 / +365 / −119 天）+ 5 个 13 周块随机打乱；邻域；未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI，最近 4,500 根）。
- 占用率（flag=1 比例）：先验 hba_trend_n26 deep 0.48 / tune 0.36 / post 0.33；回退 ba_yoy_lt0 0.46 / 0.32 / **post 0.06**。

## 结果（`output/research_census_business_applications_gate_4h.csv` 309 行；`_new8.csv` 16 行；事后安慰剂 `_supp.csv`）

| 格子 | 所 | deep unseen 收益 / Sharpe | tune 收益 / Sharpe | post 收益 / Sharpe | post 月 好/坏 | 9 段 |
|---|---|---|---|---|---|---|
| 基线 | OKX | +35.14% / 0.71 | +85.08% / 1.47 | +59.90% / 2.23 | — | — |
| 基线 | Gate | −3.63% / 0.09 | +84.25% / 1.46 | +60.32% / 2.25 | — | — |
| 先验 hba_trend_n26_long_off | OKX | +19.36% / 0.50 | +51.35% / 1.05 | +58.07% / 2.22 | 2/2 | **0/9** |
| 先验 | Gate | −10.79% / −0.03 | +49.57% / 1.03 | +58.82% / 2.25 | 2/2 | |
| 回退 ba_yoy_lt0_both | OKX | +40.99% / 0.94 | +24.79% / 0.74 | +22.76% / 1.53 | 5/4 | 3/9 |
| 回退 | Gate | +7.13% / 0.23 | +25.03% / 0.74 | +23.13% / 1.56 | 5/4 | |
| 最好 hba_trend_n13_contra_both（非先验、反经济方向） | OKX | +55.09% / 1.09 | +92.52% / 1.62 | +69.30% / 2.49 | 3/4 | 9/9 |
| 最好 | Gate | +33.15% / 0.62 | +91.04% / 1.60 | +70.10% / 2.51 | 3/4 | |

- 先验 0/9：三段两所全部变差（tune −34 pp）；15 个安慰剂中 4 个达 5–6/9，真实信号低于安慰剂。邻域 n18 / n22 / n30 / n34 / n42 全 0–1/9。
- 回退 3/9：只 deep 变好；tune −60 pp、post −37 pp（post 几乎不触发仍大幅拖累：拦掉空头）；安慰剂最高 6/9。
- 56 格分布：9/9 ×1、7/9 ×1、6/9 ×3，其余 ≤5/9。唯一 9/9 `hba_trend_n13_contra_both`（申请加速时不开新多、减速时不开新空 —— 与预注册经济方向相反）post +9 pp / Sharpe +0.26，但 **post 月份两所都只 3/4**（达不到 ≥6/9）；邻域 n9 / n11 4/9（post −11 pp）、n15 4/9（post −35 pp）、n17 1/9、n21 1/9 —— 只在 n=13 单点成立。事后（非预注册）对它跑同一组 15 个安慰剂：块打乱 rnd4 也 **9/9 且 post Sharpe 边际更大（+1.37 vs +0.81）**，−60d / +180d 6/9；±7 天平移即掉到 0/9、3/9 —— 对时点极敏感，属噪声拟合。
- 压力费（taker 15.1 bps）：基线 post OKX +55.94% / 2.12、Gate +56.78% / 2.15；最好格 +65.97% / 2.40、+66.81% / 2.43；先验 +54.32% / 2.11、+54.99% / 2.14（更差）。
- 未调参 new8：先验 pre Sharpe OKX 0.78 vs 0.98、Gate 0.75 vs 0.96（更差），post 0.21 vs 0.28、0.98 vs 1.00；回退 pre 0.39 / 0.42（大幅更差），post 1.27 / 1.18（月 6/3，但只 105 笔、pre 拖累）；最好格 pre 1.37 / 1.37 vs 0.98 / 0.96、post OKX +8.2% vs +3.3%、Gate +21.9% vs +16.4%（月 5/4）—— new8 支持，但不足以抵消邻域崩塌与随机块打乱同等 9/9。

## 结论

**否决**。不实现、不进观察名单、不加模拟盘、不改默认；无代码改动，仅文档。先验 0/9、回退 3/9；唯一 9/9 为非先验反方向格，post 月份 3/4、邻域单点、随机打乱安慰剂同样 9/9。

- 勿重测（never retest via）：换 N / 4 周窗口 / z 窗口 / 阈值 / 侧 / 方向（含 contra）；换 BA ↔ HBA ↔ WBA（有计划工资）↔ CBA（公司申请）；换季调月度 BFS、州 / 地区 BFS、预测的新设企业数（BF4Q / BF8Q）；换同比 ↔ 环比 / 水平；也不要改成 1h「BFS 周四发布」事件，或改用其他国家的企业注册数（英国 Companies House 等）绕过本条。
- 脚本 `scratch/bfsapps4h/{build,prereg,run,new8,supp}.py`、`PRE_REGISTER.json(.sha256)`、`run.log`（研究脚本未推送）。
- 下一轮（短线）：比特币 Ordinals 铭文（witness 中 `OP_FALSE OP_IF "ord"` 信封）每小时数量爆发 → 8 币永续篮子 1h 事件（官方比特币区块数据；先查重 mempool / btc_fee_share / btc_miner 族，确认不是手续费或区块空间机制的换皮；OKX 期权交割已被 deribit_expiry 覆盖，不选）。
