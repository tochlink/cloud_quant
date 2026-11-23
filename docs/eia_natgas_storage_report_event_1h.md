# 短线新族：EIA 官方每周天然气库存报告（WNGSR）发布 → 8 币永续篮子 1h 事件（2026-11-23 ~03:51–03:58 PST，研究，不改默认；否决）

## 查重 / 换题
- 原建议「美国国债拍卖结果 1h 事件」已测：`output/research_us_treasury_auction_event_1h.csv`、`docs/us_treasury_auction_event_1h.md`（另有 `us_treasury_auction_demand_gate_4h`）→ 不重测，换题。
- `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`scratch/ROTATION_LOCK.txt` 中「natural gas storage / WNGSR / 天然气库存」0 条事件测试；已测的只有 Henry Hub 日度现货价长线闸门（`natgas4h`）与 EIA 原油 WPSR 1h 事件（`eia_wpsr_crude_event_1h`），二者都不是本族。

## 数据（仅官方）
- EIA Natural Gas Navigator 周度 `NW2_EPG0_SWO_R48_BCF`（Lower-48 working gas，Bcf），https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls（文件戳 11/19/2026 10:38:52 AM，sha256 560938c1d643b8fa…），2010-01-01 → 2026-11-13 周度无缺口；与官方 ir.eia.gov/ngs/ngs.html 2026-11-19 报告核对一致（3,882 Bcf，+20 Bcf）。
- 发布时间：EIA 官方日程 = 周四 10:30 ET（周截止日 F + 6 天）；节假日改期取自 `ir.eia.gov/ngs/schedule.html`（2026-11-23 实时页 + Wayback 2021-12 / 2023-06 / 2024-07 / 2024-12 / 2025-05 / 2025-12），共 17 次改期（如 2025-12-29 周一 12:00、2026-11-13 周五 10:30）。
- 285 份报告（周截止 2021-06-04 → 2026-11-13），可算 z 的 233 份；回测落在 OKX 1h 数据（2022-01-29 起）内。
- 「意外」只用官方数据：chg = S_t − S_{t−1}；avg5 = 前 5 年同周变化均值（自算，周截止最接近 F − 364k 天）；surp5 = chg − avg5；dchg = chg − 上周 chg；z = (x − 前 52 份均值) / 前 52 份标准差。无市场一致预期（不编造）。
- 永续：仓库现有官方 OKX / Gate 1h K 线 + 资金费（数据到 2026-11-23 06:00 UTC）。

## 公式 / 预注册（72 格，PRE_REGISTER.json sha256 e24862ba…，先锁后看 PnL）
- t0 = 发布时刻向下取整的 UTC 小时 K；入场 = t0+1h 开盘（发布后第一根完整小时），出场 = 入场 + H 根开盘；非重叠；真实费 5.1 bps/边（压力 15.1），含资金费。
- surprise：z ≥ +k（注入偏多 / 抽取偏少 = 天然气偏空 = 能源通胀压力低）→ hyp 做多篮子，z ≤ −k → 做空；contra 反向。metric ∈ {surp5, dchg}，k ∈ {0.5, 1.0, 1.5}，H ∈ {4, 12, 24, 48}（48 格）。
- follow / fade：t0 篮子 K 线收益 |r0| > k·σ720，k ∈ {0, 1}（16 格）；side：每份报告固定多 / 空（8 格，同脚本朴素基线）。
- 先验 `surp5_k1.0_hyp_H24`，回退 `surp5_k1.0_hyp_H48`。
- 切分：train（deep unseen，< 2024-10-21）/ test / post（≥ 2026-03-05）；okx_d8、okx_new8（未调参 LINK LTC DOT TRX BCH ATOM NEAR UNI）、gate_d8（≥ 2025-09-24）；8 槽全正 + n 门槛为 usable。安慰剂：随机同小时日期（先验 / 回退 1000 次，其余 300 次）、±168h / ±720h 平移。

## 结果（`output/research_eia_natgas_storage_report_event_1h.csv`，4,724 行；真实费每笔净 bps，括号为事件数）

| 格子 | OKX deep | OKX test | OKX post | new8 deep | new8 test | new8 post | Gate post | Gate 窗口 | 8 槽 |
|---|---|---|---|---|---|---|---|---|---|
| 先验 surp5 k1.0 hyp H24 | −76.2 (32) | −94.8 (21) | +279.5 (3) | −44.7 | −67.6 | +198.2 | +278.9 (3) | −44.6 (12) | 3/8 |
| 回退 surp5 k1.0 hyp H48 | −31.1 (32) | −89.7 (21) | +260.6 (3) | +24.2 | −78.8 | +163.1 | +261.4 (3) | −76.7 (12) | 4/8 |
| 唯一 usable 非先验 dchg k1.0 hyp H12 | +12.9 (24) | +24.4 (20) | +88.8 (5) | +27.7 | +37.7 | +62.3 | +88.9 (5) | +71.4 (13) | 8/8 |
| 基线 side_long H24 | −5.4 (142) | −11.4 (71) | −25.6 (38) | +8.6 | +6.8 | +23.1 | −25.2 | −45.2 | 3/8 |
| 基线 side_short H24 | −15.0 (142) | −9.0 (71) | +5.2 (38) | −29.0 | −27.2 | −43.5 | +4.8 | +24.8 | 3/8 |

- 先验：deep / test 两家都亏（OKX −76 / −95，压力费 −96 / −115；Gate test −152），随机同小时安慰剂分位 train 13 / test 11；post 只有 3 次且全在 2026-03（+838 bps 合计），post 月份正 1/9 → 不成立。
- 回退：test 两家都亏（OKX −89.7、Gate −189.4），Gate 窗口 −76.7；post 同样只有 3 次。
- dchg k1.0 hyp H12（非先验，8/8 usable）：边际很薄（deep +12.9 t 0.27，test +24.4 t 0.37；压力费 deep −7.1），test 随机安慰剂分位 72.7 < 80；+168h 平移 test +167.9 远好于真实；post 5 次只在 2026-03 / 04（月份 +455.8 / −11.7 → 正 1/9）；邻域崩：同 k 的 H24 deep −47.3、H48 deep −172.9，k0.5 H12 deep −18.2 / test −25.6 → 不进观察。
- surp5 k1.0 hyp H4 / H12 也是 8 槽全正但 post n = 3 < 4、边际 ≤ +54 bps，与 H24 / H48 符号相反，H 邻域不稳。
- 注入季（4–10 月）周变化方差低，以前 52 份冬季高波动为分母的 z 几乎不触发，post（2026-03 之后）|z| ≥ 1 只有 3–5 次 —— 族的结构性局限。

## 结论
**否决**。不实现、不进观察名单、不加 shadow、不改默认、无代码改动，仅文档；纸面实例未动。

- 勿重测（never retest via）：不要换 k / H / z 窗口 / hyp↔contra / 方向，不要把 surp5 换成 dchg、同比（year-ago）差、5 年区间上 / 下限、库存水平偏离 5 年均值（%），不要改用分地区（East / Midwest / South Central / Salt…）、隐含流量（implied flow）、EIA 补充报告或月度 EIA-191 存量，不要改成 Henry Hub / NYMEX NG 期货的发布小时反应 follow/fade，不要换篮子 / 交易所 / 入场延迟。
- 文件：`output/research_eia_natgas_storage_report_event_1h.csv`（不入库）、官方周度 `output/eia_wngsr_storage_official_weekly.csv`；脚本 `scratch/ngstor1h/{events,prereg,run,analyze}.py`。
- 下一轮（长线）：BLS 官方 JOLTS 职位空缺率 / 离职率（`JTS000000000000000JOR` / `JTS000000000000000QUR`，按官方发布日点时对齐）趋势 → 4h 默认书 #1 入场闸门（docs 中 JOLTS 0 条；已测的是初请失业金体制，不同序列；先查重）。
