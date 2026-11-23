# 长线：德国 ifo 商业景气（实时 vintage）/ ZEW 经济景气预期 → 默认 4h 书入场闸门（2026-11-23 ~00:20–00:40 PST，否决）

## 查重
- `docs/*.md`、`docs/STRATEGY_FORMULAS.md`、`ls output/research_*.csv`、`/workspace/scratch` 检索 `ifo` / `ZEW` / `Geschäftsklima` / `business climate` / `economic sentiment`：只出现在"下一轮（未测）"指针里，0 条已完成测试。
- 不是已否决的 OECD CLI（含 OECD BCI/CCI）、中国 NBS PMI、美国宏观（GDPNow / WEI / CFNAI / 初请 / CPI 体制 / UMich 等）、韩国出口。

## 数据（官方，未编造、未回补）
- ifo 研究所官方 `ifo-zeitreihen` 页：`Deutschland-ifo-Vintage.xlsx`（Sauer & Wohlrabe 实时 vintage 数据集，v2018m04 → v2025m12 共 93 个发布版本，每列 = 当月原始发布时的完整序列）+ `gsk-d-202610.xlsx`（当前版，2026-01 → 2026-10 的发布用当前版截断到发布月；与 v2025m12 在 2024-01→2025-12 的修订平均 0.09、最大 0.3 点）。ifo.de 有 JS 挑战，用无头浏览器下载公开文件。
- ZEW 官方 `ftp.zew.de/pub/zew-docs/div/konjunktur.xlsx`：ZEW 德国经济景气预期差值 + 现状差值，1991-12 → 2026-11（420 个月，日期为发布日，ZEW 不修订）；最新 2026-11-17：预期 35.6、现状 −33.2。官方发布日程 PDF（11:05 CET）核对：2026-11-17 一致，2026-10 文件日 19 日、日程 20 日。
- 本地 `output/ifo_zew_official_monthly.csv`（523 行：ifo 首发值 2018-04 → 2026-10 + ZEW 1991-12 → 2026-11，每行带 `known_from_utc`）。ifo 最新 2026-10：景气 90.2、预期 91.6、现状 88.8。
- 发布时滞：ifo 月 M 仅于 **M+1 月 1 日 01:00 UTC** 起使用（官方约 M 月 22–27 日 10:00 CET 发布，保守多等约 1 周）；特征按当期 vintage 计算（只用该次发布时可见的数据，无修订前视）。ZEW 自 **文件日 +1 天 12:00 UTC** 起使用（≥ 官方 11:05 CET 发布）。前向填充到 4h K 线。

## 公式与预注册（看任何 PnL 前锁定，`PRE_REGISTER.json` / `PRE_REGISTER.csv` 2026-11-23 00:20:59 PST，sha256 ce1927bf…14dd）
- 序列 `zew`（ZEW 预期差值）/ `ifoclim`（ifo 景气指数 2015=100 季调）/ `ifoexp`（ifo 商业预期）。
- 形式（flag=1 = 景气偏强/上行）：`lvlgtmean` 值 > 扩张均值（≥60 个月）；`chgN` 值−N 月前 >0，N∈{1,3,6}；`trendN` 值 > SMA(N)，N∈{6,12}；`z60gtK` (值−SMA60)/STD60 > K，K∈{0,0.5}。
- 五侧：long_off（flag=1 拦新多）/ short_off（flag=0 拦新空）/ both / contra_both / cap_short_off（flag=1 拦新空）；已有同向仓保留。3×8×5 = **120 格** + 同脚本基线（默认 #1 MA50/150）。
- 经济先验（锁定）：德国景气预期改善 = 欧洲/全球 risk-on → 不开新空。先验 `zew_chg3_cap_short_off`；回退 `ifoexp_chg3_cap_short_off`。
- 验证：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续+现货、官方资金费；真实费（永续 maker 2 / taker 5.1 bps，现货 10）、压力费（永续 15.1 / 现货 20）；深度未见 →2024-10-21 / 调参 →2026-03-05 / post →2026-11-14；9 片 Sharpe 胜场；post 月份胜负；邻域；日历平移安慰剂 ±7/±14/±60/+180/−120/+365/−119 天；未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI，最近 4500 根，OKX+Gate）。

## 结果（`output/research_ifo_zew_gate_4h.csv` 507 行；`_new8.csv`；`_best_placebo.csv`）
- 基线：OKX d8 深度 +35.14%/0.71、调参 +85.08%/1.47、post +59.90%/2.23；Gate d8 深度 −3.63%/0.09、调参 +84.25%/1.46、post +60.32%/2.25。
- 120 格 9 片胜场分布：0:31，1:12，2:23，3:45，4:2，5:3，6:4；无 7/9 以上。

| 格 | OKX post 收益/Sharpe | Gate post 收益/Sharpe | post 好/差月（OKX, Gate） | 深度未见 Sharpe OKX / Gate | 调参 Sharpe OKX / Gate | 9 片 | new8 post Sharpe OKX / Gate（基线 0.28 / 1.00） |
|---|---|---|---|---|---|---|---|
| 基线 | +59.90% / 2.23 | +60.32% / 2.25 | – | 0.71 / 0.09 | 1.47 / 1.46 | – | 0.28 / 1.00 |
| 先验 zew_chg3_cap_short_off | +39.93% / 1.82 | +40.49% / 1.84 | 4/2, 4/2 | 0.72 / 0.11 | 1.86 / 1.81 | 6/9 | 0.23 / 1.04（pre 0.69/0.70 vs 0.99/0.96） |
| 回退 ifoexp_chg3_cap_short_off | +34.74% / 1.58 | +35.44% / 1.61 | 2/2, 2/2 | 0.39 / −0.21 | 1.76 / 1.72 | 3/9 | 0.21 / 1.01（pre 0.59/0.56） |
| 最佳非先验 zew_chg1_short_off | +68.32% / 2.54 | +68.67% / 2.55 | 2/1, 2/1 | 0.47 / −0.11 | 1.49 / 1.47 | 6/9 | 0.52 / 1.30（pre 0.61/0.56） |

- 先验 6/9 全靠调参期，post 大幅跑输（−20 pp，Sharpe −0.4），月份 4/2 仅因多数月不触发。回退 3/9，post 更差。
- 唯一 post 双所都胜基线的是非先验 `zew_chg1_short_off`（ZEW 月环比走弱 → 拦新空），但：深度未见 3 个切片全输；post 只有 3 个月与基线不同（2 好 1 差，远低于 ≥6/9）；邻域 chg2/chg3 post 崩到 +33%/1.68（OKX 1 好 8 差），chg4–6 +30–35%，chg9 +12%；安慰剂 +7d / −7d post 也有 OKX +65.9%/2.46、+64.2%/2.48（Gate +66.2% / +64.7%），+365d 也 +63.7%→ 无时点特异性；new8 pre 也更差（0.61/0.56 vs 0.99/0.96）。
- 先验安慰剂：+7d 与原格几乎相同，+365d post 反而 +69.0%/2.58 → ZEW 信息无增量。压力费下排序不变（zew_chg1_short_off post OKX +65.2%/2.46 vs 基线 +55.9%/2.12，但同样的稀疏触发问题）。

## 结论
**否决**。不改代码、不改默认、不加模拟盘。
勿重测：换 N / K / 侧 / 阈值，换 ifo 景气↔预期↔现状↔分行业（制造/服务/贸易/建筑）↔东德/萨克森，换 ZEW 预期↔现状↔欧元区，改用 ifo 出口预期 / 就业晴雨表 / 不确定性 / 景气灯，或缩短发布时滞（用精确发布日）、改用当前版代替 vintage。

## 文件
- 结果 CSV（不入库）：`output/research_ifo_zew_gate_4h.csv`、`output/research_ifo_zew_gate_4h_new8.csv`、`output/research_ifo_zew_gate_4h_best_placebo.csv`；官方月度 `output/ifo_zew_official_monthly.csv`。
- 脚本（不推送）：`scratch/ifozew4h/{build.py,prereg.py,run.py,new8.py,plc_best.py}`、`PRE_REGISTER.{json,csv,sha256}`、原始 xlsx。

下一轮（短线）：德国 Xetra DAX 官方开盘跳空（09:00 CET 开盘 vs 前日 17:30 收盘，Deutsche Börse / STOXX 官方指数历史）→ 8 币永续篮子 1h 事件（顺势 / 逆势）；已查 dax / xetra / stoxx 0 条（不同于已否决的日经 225 开盘跳空、CME 周末缺口），需先确认官方日内开盘价历史可免费下载。
