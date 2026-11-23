# 短线新族：美联储理事会官方讲话 / 国会证词（federalreserve.gov）发布时刻 → 8 币永续篮子 1h 事件（2026-11-23 ~04:45–05:15 PST，研究，不改默认；否决）

## 查重
docs/*.md、`docs/STRATEGY_FORMULAS.md`、`output/research_*.csv`、`/workspace/scratch/*` 中无 Fed speech / testimony / Powell / Beige Book 事件。不同于已测的 FOMC 决议（`fomc_event_shortterm_1h`）、FOMC 纪要（`fomc_minutes_event_1h`）、ECB/BoE 决议、美国宏观数据发布（CPI/NFP/PPI）。

## 数据（全部官方，不编造、不回补）
- 事件：美联储理事会官方 JSON `https://www.federalreserve.gov/json/ne-speeches.json`（last update 2026-11-20，sha256 2696c888…）与 `ne-testimony.json`（last update 2026-07-15，sha256 276ad54a…），每条含官方日期时刻（按美东解释，含夏令时）。2010 年后全部可解析（不可解析的 274 条均为 2006–2009 仅日期条目，不在价格窗口内）。表：`output/fed_speech_testimony_official.csv`（1,365 条，2008-10 → 2026-11-20）。
- 集合（同一 UTC 小时合并）：chair = Chair/Chairman/Chair Pro Tempore（train 26 / test 16 / post 4）；leaders = chair + Vice Chair + Vice Chair for Supervision（76 / 56 / 30）；all = 全部讲话与证词（248 / 144 / 68）。
- 价格：OKX 官方 1h 永续 K 线 + 官方深历史资金费（d8：BTC ETH BNB SOL XRP ADA DOGE AVAX，2022-01-29 07:00 → 2026-11-23 06:00 UTC，42,216 根，0 缺口；new8 未调参 LINK LTC DOT TRX BCH ATOM NEAR UNI，42,205 根，0 缺口），Gate 官方 1h 永续 + 资金费（2025-09-24 08:00 → 2026-11-23 06:00 UTC，10,199 根，0 缺口）。

## 公式（`scratch/fedspeech1h/PRE_REGISTER.json`，sha256 588b8c687065…，看任何 PnL 前锁定 126 格）
- t0 = 官方时刻向下取整到 UTC 小时。
- side：集合 × {long, short} × H ∈ {12, 24, 48}，入场 t0+1h 开盘（18 格）。
- follow / fade：r0 = 篮子从 t0 开盘到 t0+R−1 收盘的等权收益（R ∈ {1, 2}），σ = 前 720 根 1h 篮子收益标准差 × √R；|r0| > k·σ（k ∈ {0.5, 1.0, 1.5}）时在 t0+R 开盘入场，follow 方向 = sign(r0)，fade 相反；出场 = 入场 + H 开盘（108 格）。Gate 用 Gate 自己的篮子算信号，new8 用 OKX d8 信号。
- 真实 taker 5.1 bps/边（压力 15.1），含资金费，不重叠。分段 train（深度未见，2022-01-29 起）< 2024-10-21 ≤ test < 2026-03-05 ≤ post；Gate 窗口 ≥ 2025-09-24。可用 = 8 槽（OKX d8 train/test/post、new8 train/test/post、Gate post/窗口）全正且 n ≥ 10 / 6 / 4。
- 先验 `leaders_follow_k1.0_R1_H24`（主席/副主席讲话是 FOMC 之外信息量最大的美联储沟通，加密对首小时反应不足 → 顺势一天）；回退 `all_follow_k1.0_R1_H24`。安慰剂：同 UTC 小时随机日（先验/回退 1000 次，其余 200 次）、±24h / ±168h 平移。

## 结果（`output/research_fed_speech_testimony_event_1h.csv`，7,920 行；真实费每笔净 bps，括号为事件数）

| 格子 | OKX train（深度未见） | OKX test | OKX post | new8 train / test / post | Gate post | Gate 窗口 | 8 槽正 |
|---|---|---|---|---|---|---|---|
| 先验 leaders_follow_k1.0_R1_H24 | −20.2 (21) | −104.4 (21) | +127.9 (10) | −27.7 / −79.6 / +20.5 | +128.6 (10) | −13.0 (17) | 3/8 |
| 回退 all_follow_k1.0_R1_H24 | +33.2 (62) | −55.5 (48) | +79.3 (21) | +35.5 / −41.3 / +20.8 | +78.9 (21) | −55.6 (34) | 5/8 |
| 唯一可用（非先验）all_follow_k1.5_R1_H12 | +41.9 (28) t0.87 | +25.2 (32) t0.52 | +117.6 (11) t2.15 | +34.2 / +5.7 / +115.2 | +83.2 (10) | +7.8 (18) | 8/8 |
| 基准 all_long_H12（同入场槽） | +26.4 (194) | −7.8 | −39.1 | — | −38.8 | — | — |
| 基准 all_short_H12 | −46.8 | −12.6 | +18.7 | — | +18.4 | — | — |

- 126 格中 8/8 可用仅 1 格。先验 3/8、回退 5/8：test 段大幅为负，安慰剂分位 test 13.9 / 18.7（远低于 80），只有 post 段为正（post 分位 95.8 / 94.9），说明 post 正收益更像 2026 行情特征而不是讲话效应。
- 非先验 all_follow_k1.5_R1_H12：压力费下 OKX test 仅 +5.2、Gate 窗口 −12.2、new8 test −14.3；Gate test 段 −86.5（8 笔）；随机同小时安慰剂 test 分位 76（< 80 门槛），post 99；+168h 平移 post +84.1 / test +19.9（接近实盘）；post 月份 OKX 正 5 / 9（3 个月无交易）、Gate 正 4 / 9 → 不满足 ≥6/9。
- 邻域：k1.5 R1 H24 7/8、H48 6/8，但 R=2（同 k）全部 2/8 且 post 为负；k1.0 R1 各 H 5/8；k0.5 多数 2–4/8 → 只在 k1.5/R1 一个孤点成立。
- side 格只是跟随市场漂移（post 段全部做空赚、做多亏，train 相反），无讲话特有效应。

## 结论
**否决**。先验 / 回退均未过（test 段亏损且安慰剂分位 < 20）；唯一 8/8 非先验格安慰剂 test 76 未达 80、post 月份 5/9 与 4/9、R 邻域塌缩、压力费下 Gate 窗口为负 → 不进观察，不加纸面账本，不起记录器，默认不变。

## 勿重测（never retest by…）
不要通过改 k / R / H / 方向（follow↔fade↔side）、改讲话人集合（主席 / 副主席 / 理事 / 地区联储主席）、只取证词或只取讲话、加文本情绪（鹰鸽）分类、换成 Beige Book / 地区联储讲话 / 其他央行官员讲话来重测这一族。

## 文件
- `scratch/fedspeech1h/`：parse.py、prereg.py、PRE_REGISTER.json(.sha256)、run.py、analyze.py、analyze.log、analyze_wide.csv、events_real.csv、原始 ne-speeches.json / ne-testimony.json
- `output/research_fed_speech_testimony_event_1h.csv`、`output/fed_speech_testimony_official.csv`
