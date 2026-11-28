# 短线族：美国 BEA 核心 PCE / GDP 公布（08:30 ET）→ 8 币永续篮子 1h 事件（2026-11-27 ~18:45–19:10 PST，否决）

- 族名：`bea_pce_gdp_release_event_1h`；预注册 `scratch/beapcegdp1h/PRE_REGISTER.json`（任何 PnL 之前锁定，90 格，sha256 `985b3881…510e76f5`）。脚本 `scratch/beapcegdp1h/{fetch,build,prereg,run}.py`（研究脚本不推送）。
- 结果 CSV（不入库）：`output/research_bea_pce_gdp_release_event_1h.csv`（5,916 行：90 格 × 实费 / 压力费 × OKX d8 / OKX new8 / Gate d8 × train / test / post / gate_window，含 ±24h / ±168h 平移、随机工作日 13/14 UTC 安慰剂、always long/short 基线）；官方事件表 `output/bea_pce_gdp_releases_official.csv`。
- 结论：**否决（REJECTED）**。不进观察名单，默认、候选、纸面实例全部不变，无代码改动。

## 查重
- 文档 / `output/research_*.csv` / ROTATION_LOCK 中无 PCE、个人收入与支出、GDP 公布作为 1h 事件。已覆盖且不同：CPI / 非农 / PPI 公布（`us_macro_release_event_1h`，该节只把这三项视为覆盖）、Empire / 费城联储调查、FOMC 决议 / 纪要 / 讲话、初请失业金 4h 闸门、GDPNow 4h 闸门、G.19 消费信贷 4h 闸门、日历族。本族是 BEA 两个独立发布（核心 PCE 为联储首选通胀口径；GDP 预估 / 修正）。

## 数据（只用官方，不编造、不回补）
- 信号：ALFRED（圣路易斯联储实时 vintage 档案，转载 BEA 官方发布）`PCEPILFE`（核心 PCE 价格指数，月度）与 `GDPC1`（实际 GDP，季度）全部 vintage，2020-06 → 2026-11-25。每个 vintage 日 = 一次 BEA 08:30 ET 发布；去掉「参考期与数值都与上一 vintage 相同」的非发布 vintage（PCE 2026-10-01、GDP 2026-07-01 各 1 个）。有效发布 PCE 78 次、GDP 77 次，落在 OKX 窗口内各 58 / 57 次（2025 年起 BEA 常把两者同日发布）。
- 指标（只用当次 vintage 自身数据）：pce = 最新月核心 PCE 环比 %；gdp = 最新季度环比年化 %；z_N = 相对此前 N 次发布（严格之前）的均值 / 标准差。
- 交易：OKX 官方 1h 永续默认 8 币 2022-01-29 → 2026-11-27 + 官方资金费；OKX 未调参 new8；Gate 官方 1h 永续 2025-09-24 →。入场 = 09:00 ET 那根 1h K 线开盘（发布后 30 分钟），持有 H 根后开盘离场，重叠事件跳过。实费双边 5.1 bps、压力 15.1 bps，含资金费。
- 分段：train = 深历史未见（< 2024-10-21）、test（→ 2026-03-05）、post（2026-03-05 →）、gate_window（2025-09-24 →）。

## 公式（90 格预注册）
- 意外格：series ∈ {pce, gdp} × N ∈ {6, 12} × k ∈ {0.5, 1.0} × 侧 × H ∈ {6, 24, 48}。pce `hyp_both`：z ≥ k（偏热、鹰派）做空篮子，z ≤ −k 做多；`hot_short` 只做偏热；gdp `hyp_both`：强做多、弱做空；`strong_long` 只做强；`contra_both` 镜像。
- 反应格：r = 篮子均值 O[09:00 ET] / O[08:00 ET] − 1（含发布的那根），follow = sign(r)、fade = −sign(r)；set ∈ {pce, gdp, all} × H ∈ {6, 24, 48}。
- 先验 `pce_z_N12_k1.0_hyp_both_H24`；回退 `pce_react_L1_follow_H24`（对应 CPI 首小时顺势弱观察的同构版）。

## 主要结果（实费 bps / 事件（次数, t）；括号外为 OKX d8，new8 = 未调参 8 币）

| 格 | train 深历史 | test | post | Gate gate_window | new8 train | new8 post |
|---|---|---|---|---|---|---|
| 先验 pce_z_N12_k1.0_hyp_both_H24 | −121.8 (12, −1.49) | +65.0 (3) | +67.6 (3, 0.39) | −50.2 (4) | −134.9 | −10.3 |
| 回退 pce_react_L1_follow_H24 | −47.1 (32, −0.94) | +66.5 (16) | **−204.1 (10, −2.60)** | −128.5 (15) | −64.0 | −187.1 |
| 非先验 pce_z_N12_k0.5_hot_short_H24 | +8.0 (6) | +49.8 (6) | +169.3 (5, 1.32) | +74.1 (6) | −71.0 | +133.7 |
| 非先验 gdp_z_N6_k1.0_hyp_both_H24（OKX 压力三段唯一全正） | +97.0 (15, 1.01) | +29.8 (9) | +31.5 (5, 0.16) | −32.7 (7) | +66.2 | +17.0 |
| 非先验 gdp_z_N6_k1.0_hyp_both_H48 | +187.3 (15, 1.59) | +5.4 (9) | +106.1 (5) | +44.6 (7) | +179.2 | +83.7 |
| 非先验 gdp_react_L1_fade_H24 | −52.0 (32) | −180.3 (15, −1.87) | +183.7 (10, 2.34) | +123.6 (14) | +4.0 | +166.7 |
| 基线 PCE 日 always long H24 | −38.6 | −54.3 | −50.2 | −21.2 | −52.6 | −42.1 |
| 基线 GDP 日 always long H24 | +102.1 | −175.3 | −50.2 | −42.6 | +109.1 | −42.1 |

- 90 格里没有一格在 OKX 三段 + Gate + new8 六段压力费下全部为正；OKX 压力三段全正只有 1 格（gdp_z_N6_k1.0_hyp_both_H24），但 t 0.16–1.01、Gate gate_window −32.7、随机安慰剂分位 85 / 64 / 63。
- 安慰剂：先验随机分位 train 13 / test 67 / post 66，±24h / ±168h 平移 test 段 +34 ~ +188（比真值好）；回退 post 分位 1.4（显著为负），−168h / −24h 平移 post 反而 +167 / +60。gdp_react_L1_fade_H24 post +183.7 是 2026 年 10 次（PCE 与 GDP 同日）的事后格，test 段 −180（分位 1），方向跨期翻转。
- 邻域：pce_hot_short 在 N6 / k1.0 / H6 / H48 上不连贯（H48 train −43、post +64）；gdp_hyp_both 换 N12 后 post 只剩 1 次事件。

## 结论：否决
- 先验在深历史未见段 −122 bps（12 次），test / post 各只有 3 次；回退 post −204 bps（t −2.6）且 Gate、new8 同向亏损——CPI 首小时顺势的弱观察不能迁移到 PCE。
- 非先验正格都是小样本（post 5–10 次、t < 2.4）且邻域 / 平移安慰剂不稳，事件日本身（always long）各段方向也来回翻，说明是行情漂移而不是发布信息。核心 PCE 大部分已被提前发布的 CPI / PPI 预告，意外幅度小。

## 勿重测
不要通过改 N / k / H / 方向（hyp / contra / 单边 / follow / fade）、改入场时刻（08:00 / 08:30 / 10:00 ET）、改用总体 PCE / 个人收入 / 个人支出 / 储蓄率、改用 GDP 平减指数 / 最终销售 / 国内总收入、只取预估值或只取修正值、改用共识预期差（无官方共识）、或换成 BEA 其他发布（贸易差额、经常账户、个人收入分州）来重测这个族。

## 下一轮（长线）
选一个未测过、官方历史覆盖 2024-10-21 / 2026-03-05 切分的 4h 默认书入场闸门（先查重 docs / 侧文档 / output / 记忆）。候选：美国 FHFA 官方月度房价指数（HPI，fhfa.gov 历史 CSV）同比 / 趋势；须先核对按揭利率 / 营建开工、实体经济 / 情绪等已否决闸门的勿重测条款，若被覆盖则换题（TIC 已被 fed_custody 勿重测禁止）。
