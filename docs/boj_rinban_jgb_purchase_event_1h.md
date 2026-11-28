# 短线新族：日本央行官方国债购入操作（Rinban）结果 1h 事件 → 8 币永续篮子（2026-11-27 ~21:20 PST，研究；否决，仅文档，不改默认、无纸面变更）

**结论：否决（REJECTED）。** 0/144 格可用 8/8。先验 `otcl_z_N20_k1.0_stress_short_H24` 6/8（test 段 OKX −59 / new8 −105 bps），回退 `spr_z_N20_k1.0_stress_short_H24` 4/8（train −51、test −93）。唯一 7/8 的非先验 `otcl_z_N60_k1.0_stress_short_H48`：test 段 +38.9 bps 与同脚本「所有操作日无条件做空 H48」基线 +37.3 持平，new8 test −19.9，train/test 随机安慰剂分位 72 / 73（<80），邻域（N20 / k0.5 / k1.5）test 多为负；post +330 bps 只有 8 笔，且 −24h / +24h 平移安慰剂 post 也有 +137 / +251 → 不到观察。

## 查重 / 换题
- 原定候选 1「Uniswap v4 PoolManager Swap 1h 成交量冲击」= **重复**：`uniswap_v3_ethusdc_shock_event_1h` 勿重测禁止「其它池、v2 / 其它 DEX 成交」，`univ3_lp_liquidity_shock_event_1h` 禁止 v4 LP，`univ2_newpair_gate_4h` 禁止 V4 Initialize；且 v4 2025-01 才上线，没有 2024-10-21 前的深度未见段。
- 原定候选 2「OpEx 期权到期日 1h」= **重复**：`vix_vro_settlement_event_1h` 勿重测已禁止 SPX OPEX / 四巫日，CME / IBIT（`cme_ibit_expiry_event_1h`）、Deribit、Gate / OKX 期权到期都已否决。
- 改测：上一轮 `cftc_tff_crossasset_spec_gate_4h.md` 留下的短线指针「日本央行国债购入（Rinban）结果」。docs / 侧文档 / 约 1,390 个 `output/research_*.csv` / 记忆中 rinban / 国債買入 / 国债购入 0 条完成测试（只有该指针与一个放弃的 scratch 目录：旧的 www3 页面 404）。不同于：`jgb_auction_result_event_1h`（财务省**发行**拍卖，勿重测禁的是期限 / 指标互换与「其他主权拍卖」）、`jgb10y_yield_gate_4h`（收益率水平闸门）、`us_treasury_buyback_event_1h`（美国财政部回购）、ECB/BoE 决议（禁 BoJ 议息，本族不是议息）。本族是**央行买入操作的逆向拍卖**：交易商卖给日本央行的意愿（应札倍率 / 落札利回较差）。

## 数据（只用官方，不编造、不回补）
- 日本银行官方月度《Market Operations by the Bank of Japan》xlsx：`https://www.boj.or.jp/en/statistics/boj/fm/ope/m_release/YYYY/opeYYMM.xlsx`（sheet `ope1`，「国債買入（変動利付債、物価連動債を除く）（利回り入札方式）」段），2021-01 → 2026-10，共 70 个文件；2026-11 用官方日度 `d_release/ope/2026/ope202611DD.xlsx`。
- 1,270 笔操作 / 367 个オファー日，2021-01-05 → 2026-11-26；其中含 >10 年（10–25 年、25 年超）档的日子 290 个。表头按列名定位（2022-05 起列位移已处理）。官方表：`output/boj_jgb_purchase_ops_official.csv`、`output/boj_jgb_purchase_days_official.csv`。
- 公布时刻：BoJ 官方 Operation Timetable，利回り入札方式国債買入 10:10 オファー、结果约 12:00 JST（03:00 UTC）；本研究保守在同日 **04:00 UTC**（13:00 JST）1h 开盘入场（日本无夏令时）。
- 交易：官方 OKX 1h 永续 d8（2022-01-29 → 2026-11-27 19:00 UTC）+ 官方 OKX 资金费；未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）；官方 Gate 1h 永续 d8 + 资金费（2025-09-24 →）。

## 公式（看 PnL 前锁定 `scratch/bojrinban1h/PRE_REGISTER.json`，sha256 `f6ea4dd03404fff59a3c33f3dcdee2324d17196e55a995bc10b9ecaa18035c38`，144 格）
- 每个オファー日：`otc` = Σ応札額 / Σオファー額（全部档）；`otcl` = 同上只取 >10 年档；`spr` = 按オファー额加权的平均落札利回較差。
- `z = (x − 前 N 个操作日均值) / 前 N 日标准差`（只用之前的操作日，至少 N/2 个），N ∈ {20, 60}；stress = z ≥ k，calm = z ≤ −k，k ∈ {0.5, 1.0, 1.5}。
- 方向：stress_short（交易商踊跃卖债给央行 = 日债需求弱 → 做空篮子）、hyp_both（stress 空 / calm 多）、contra_both（镜像）、stress_long；持有 H ∈ {24, 48} 根 1h，不重叠，8 币等权，计官方资金费。
- 网格 3 指标 × 2 N × 3 k × 4 方向 × 2 H = 144 格。先验 `otcl_z_N20_k1.0_stress_short_H24`（超长债卖压 → 日元利率 / 套息平仓通道，2024-08 那类 → 加密次日走弱）；回退 `spr_z_N20_k1.0_stress_short_H24`。
- 费用：taker 5.1 bps/边（压力 15.1）。分段：train（深度未见）2022-01-29 → 2024-10-21，test → 2026-03-05，post 2026-03-05 →，gate_window 2025-09-24 →。安慰剂：入场平移 ±24h / ±168h；随机工作日 04:00 UTC 同数量同方向（先验 / 回退 1000 次，其余 200 次）。同脚本基线：所有操作日无条件做多 / 做空 H24 / H48。
- 可用门槛（预注册）：8 槽（OKX d8 train/test/post、new8 train/test/post、Gate post/gate_window）全正，且 OKX d8 n train ≥ 8、test ≥ 5、post ≥ 4。

## 结果（真实费，每笔净 bps 均值；n = 笔数）
| 格 | 8 槽为正 | OKX d8 train / test / post | new8 train / test / post | Gate post | 随机分位 train / test / post | post 月份 OKX / Gate |
|---|---|---|---|---|---|---|
| 先验 otcl_z_N20_k1.0_stress_short_H24 | 6/8 | +22.3 (n24, t0.41) / −59.2 (n18) / +108.5 (n8, t2.0) | +17.5 / −104.9 / +82.7 | +108.0 (n8) | 73 / 30 / 86 | 6/9 / 6/9 |
| 回退 spr_z_N20_k1.0_stress_short_H24 | 4/8 | −51.1 (n28) / −92.9 (n12) / +92.0 (n10, t2.0) | −63.0 / −120.3 / +117.7 | +91.4 (n10) | 37 / 25 / 84 | 6/9 / 6/9 |
| 最好非先验 otcl_z_N60_k1.0_stress_short_H48 | 7/8 | +35.6 (n20, t0.4) / +38.9 (n16) / +330.1 (n8, t3.0) | +29.4 / −19.9 / +229.8 | +329.4 (n8) | 72 / 73 / 98.5 | 6/9 / 6/9 |
| 基线 always_short H48（全部操作日） | — | +0.5 (n176) / +37.3 (n74) / +76.4 (n34) | +4.0 / 0.0 / +21.7 | — | — | — |
| 基线 always_short H24 | — | −32.9 / +1.9 / −23.6 | −28.5 / +12.7 / −26.9 | −23.9 | — | — |

- 压力费（15.1 bps/边）：先验 OKX train +2.3 / test −79.2 / post +88.6；最好非先验 +15.6 / +18.9 / +310.1（new8 test −39.9）。
- 平移安慰剂（OKX post）：先验 −168h +10.9、−24h −88.9、+24h +103.4、+168h +98.5；最好非先验 −24h +137.4、+24h +251.0（train −125 / +148，方向不稳），说明 post 段大部分是 2026 年操作日附近的整体下跌漂移，不是结果本身的信息。
- 邻域（otcl stress_short H48）：N20 k1.0 test −3.2 / new8 test −120.9；N60 k0.5 test +35.3 / new8 −91.5；N60 k1.5 test −44.2 / post n3。`spr` / `otc` 的 stress_short H48 在 post 全为 +60 ~ +330，但 train 多为负 —— 同一 post 漂移。
- 分布：144 格中 7/8 只有 1 格、6/8 25 格、≤5/8 118 格；0 格 8/8。全部格见 `output/research_boj_rinban_jgb_purchase_event_1h.csv`（9,156 行，逐格 × 宇宙 × 段 × 费率 × 安慰剂）。

## 结论
**否决**，不实现、不进观察名单、不改默认、不动纸面实例（8788 / 8789 / 8792 未动，未加 shadow），无代码改动。日本央行 Rinban 的交易商卖压对 8 币永续篮子在深度未见段与 test 段没有增量：先验 test 段为负，最好格 test 只等于无条件做空基线，post 的大正值被平移安慰剂复现。官方月度 xlsx 每月上旬更新，历史完整，不需要实时记录器。

## 勿重测（never retest by…）
不要通过改 N / k / H / 方向（顺势↔逆势↔单边）、在应札倍率（全部 / 超长 / 单档）/ 落札利回較差（平均 / 按分 / 全取）/ 按分比率 / 落札额之间互换、只取某个残存期间档（1 年以下 / 1–3 / 3–5 / 5–10 / 10–25 / 25 年超）、改用变动利付债 / 物价连动债买入、固定利回り方式（指値オペ）、国库短期证券买入 / 卖出、共通担保资金供给、国債補完供給（SLF）、改入场小时或日本央行月度「買入れ予定」/ 减购计划公布日来重测本族；也不要换成其他央行的 QE / QT 买入操作（美联储 SOMA、ECB APP/PEPP、BoE APF）重测同一「央行债券买入逆向拍卖卖压」机制。

## 文件
- `output/research_boj_rinban_jgb_purchase_event_1h.csv`、`output/boj_jgb_purchase_ops_official.csv`、`output/boj_jgb_purchase_days_official.csv`（均不入库）。
- `scratch/bojrinban1h/`：fetch.py、build.py、prereg.py、PRE_REGISTER.json(.sha256)、run.py（复用 `scratch/ustbuyback1h/run.py` 的同一回测框架）、analyze.py、analyze.log、analyze_wide.csv、events_real.csv、days_with_z.csv、raw/*.xlsx。

## 下一轮（长线 4h）
日本证券业协会（JSDA）官方月度《公社債店頭売買高》中「外国人」对日本国债（尤其超长期）的净买入额 n 月趋势 / 变化 → 4h 默认书入场闸门（海外资金对日债的需求体制；每月 20 日前后公布，次日 00:00 UTC 才用，不补数据）。须先查重 `mof_resident_foreign_bond_flow_gate_4h`（禁的是**本国居民对外**证券投资）、`jpx_foreign_investor_flow_gate_4h`（股票投资者分类）、`jgb10y_yield_gate_4h`、本轮 Rinban 族的勿重测；若判同机制就换一个未测过、官方历史覆盖 2024-10-21 / 2026-03-05 切分的长线族。
