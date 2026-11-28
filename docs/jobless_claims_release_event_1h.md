# 短线族：美国每周初请失业金（ICSA）公布（周四 08:30 ET）→ 8 币永续篮子 1h 事件（2026-11-28 ~00:20–00:35 PST，否决）

- 族名：`jobless_claims_release_event_1h`；预注册 `scratch/claimsrel1h/PRE_REGISTER.json`（任何 PnL 之前锁定，78 格，sha256 `6e7d8ba6dfa38d827f81fc848d5e26bf475593fd130169b68b6fd556d9ab5210`）。脚本 `scratch/claimsrel1h/{fetch,build,prereg,run}.py`（不推送）。
- 结果 CSV（不入库）：`output/research_jobless_claims_release_event_1h.csv`（5,058 行：78 格 × 实费 / 压力费 × OKX d8 / OKX new8 / Gate d8 × train / test / post / gate_window，含 ±24h / ±168h 平移、随机工作日 13/14 UTC 安慰剂、always long/short 基线）；官方事件表 `output/icsa_releases_official.csv`。
- 结论：**否决（REJECTED）**。默认、候选、纸面实例全部不变，无代码改动。

## 查重
- 只有 `jobless_claims_regime_gate_4h`（FRED ICSA 长线体制闸门，否决）用过初请失业金；CPI / 非农 / PPI、PCE / GDP、Empire / 费城联储、FOMC 都是别的发布。从未把**每周初请失业金公布本身**当 1h 事件（周频，样本比月度 / 季度发布多 4–12 倍）。

## 数据（只用官方，不编造、不回补）
- 信号：ALFRED（圣路易斯联储实时 vintage 档案，转载美国劳工部官方发布）`ICSA`（季调初请）全部 vintage，2021-11 → 2026-11-25，259 个，去掉参考期与上一 vintage 相同者 1 个，剩 258 次发布（246 周四、12 周三，假日提前）。每个 vintage 日 = 一次 08:30 ET 发布，只用该 vintage 自身数据。
- 交易：OKX 官方 1h 永续默认 8 币 2022-01-29 → 2026-11-27 + 官方资金费；OKX 未调参 new8；Gate 官方 1h 永续 2025-09-24 →。入场 = 09:00 ET 那根 1h 开盘（发布后 30 分钟），H 根后开盘离场，重叠事件跳过。实费双边 5.1 bps、压力 15.1 bps，含资金费。
- 分段：train < 2024-10-21（深历史未见）、test → 2026-03-05、post 2026-03-05 →、gate_window 2025-09-24 →。

## 公式（78 格预注册）
- chg = 首发 ICSA − 上周（同 vintage 内修正值）；dev = 首发 − 前 4 周均值；z_N = (x − 此前 N 次发布均值) / 标准差（严格之前），N ∈ {13, 26}，k ∈ {0.5, 1.0}。z ≥ k（申领偏高 = 劳动力偏弱）：`hyp_both` 做空 / z ≤ −k 做多；`up_short` 只做空；`contra_both` 镜像。H ∈ {6, 24, 48}。
- 反应格：r = 篮子 O[09:00 ET] / O[08:00 ET] − 1，follow / fade。
- 先验 `icsa_chg_z_N26_k1.0_hyp_both_H24`；回退 `icsa_react_L1_follow_H24`。

## 主要结果（OKX d8，实费 bps / 次数 / t）
| 格 | train | test | post | Gate gate_window |
|---|---|---|---|---|
| 先验 hyp_both H24 | +53.9 (40, 1.3) | −13.5 (20, −0.1) | +63.9 (5, 0.4) | −24.1（Gate test −110.4）|
| 回退 react follow H24 | −52.5 (142, −1.6) | +66.0 (64, 1.4) | **−89.7 (39, −1.8)** | −35.4 |
- 先验 test 为负、post 只有 5 次；回退 post 显著为负，Gate / new8 同向亏损。
- 78 格里 OKX 三段 + new8 三段 + Gate 一段（共 7 段）实费全部为正的有 9 格（均非先验），post t ≤ 2.0、test 段 t ≤ 1.0；其中压力费 7 段仍全正的 5 格（chg_N13_k1.0_up_short_H24、chg_N26_k1.0_up_short_H48、dev_N13_k0.5_up_short_H48、dev_N26_k0.5_hyp_both_H48、dev_N26_k0.5_up_short_H48）post 只有 2–22 次、test t ≤ 1.0。
- 安慰剂：这 9 格的 ±24h 平移 post 多数和真值同量级或更高（如 chg_N13_k1.0_up_short_H24：真值 +135，−24h +285，+24h +304）；随机工作日 13/14 UTC 分位 train 89–99、post 59–96，但 test 仅 52–89。always short 基线 train −27 / test +34 / post −33，方向跨期翻转，说明正格只是空头漂移 + 极小样本。
- 邻域：N13 / N26、k0.5 / k1.0、chg / dev 之间正格不连贯，post 样本 2–22 次。

## 结论：否决
先验 test 为负、回退 post −90（t −1.8）；9 个非先验正格都是小样本且平移安慰剂不低于真值。初请失业金周度公布不构成 1h 事件边际。不加入 shadow / 纸面。

## 不要重测（never-retest）
- 不要改 z 窗 N / k / H / 侧，不要在 chg / dev / 4 周均值 / 水平 / 持续申领（CCSA）/ 未季调（ICNSA）/ 4 周移动平均（IC4WSA）/ 州级申领之间换序列，不要把先验改成「只做空」或把发布后第一小时换成其他窗，不要换成事前共识预期（无官方数据）。
- 初请失业金 4h 体制闸门与本 1h 事件均已否决，视为整个初请失业金族已覆盖。
- 下一轮：长线新族。
