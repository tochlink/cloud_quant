# 短线新族：SEC EDGAR 官方 8-K Item 1.05（重大网络安全事件披露）→ 8 币永续篮子 1h 事件（2026-11-23 ~03:30–03:55 PST，研究，不改默认；否决）

## 查重
docs / `output/research_*.csv` / 记忆中没有 Item 1.05、网络安全披露、cyber 8-K 作为事件。不同于已否决的 `edgar_crypto_etf_s1`（加密 ETF S-1）、`mstr_8k`（Strategy 单家 8-K）、`us_megacap_earnings_8k`（Item 2.02 财报）、`defillama_hack`（链上协议被盗）、`exchange_status_incident`（交易所状态页故障）。

## 数据（全部官方，不编造、不回补）
- 事件：SEC EDGAR 官方批量 `Archives/edgar/daily-index/bulkdata/submissions.zip`（Last-Modified 2026-11-21 05:15 UTC，999,458 个 CIK 文件），取 form ∈ {8-K, 8-K/A} 且官方 items 含 `1.05` 的全部申报：87 份（8-K 60、8-K/A 27），2023-12 → 2026-10。时间戳 = 官方 `acceptanceDateTime`（UTC；20–21 UTC 即美股收盘后最多）。表：`output/sec_8k_item105_cyber_official.csv`。
- 集合：init = 8-K（非 /A）且同一 CIK 前 30 天无 1.05 申报（59 份，同小时合并后 57 个事件：train 23 / test 18 / post 16）；all = 全部（83 个事件小时）；init_listed = init 且 exchanges 含 NYSE / Nasdaq（47）。
- 价格：OKX 官方 1h 永续 K 线 + 官方资金费（d8 默认 8 币；new8 未调参 LINK LTC DOT TRX BCH ATOM NEAR UNI），Gate 官方 1h 永续（2025-09-24 起），截至 2026-11-23 06:00 UTC。

## 公式（`scratch/cyber8k1h/PRE_REGISTER.json`，sha256 1d1f138a…，看 PnL 前锁定 40 格）
- t0 = 受理时刻向下取整到 UTC 小时；入场 = t0+1h 开盘，出场 = 入场 +H 开盘；H ∈ {4, 12, 24, 48}。
- side：集合 ∈ {init, all, init_listed} × {long, short}（24 格）；follow / fade：init 集合、篮子 t0 小时收益 r0，|r0| > k·σ720（k = 0 / 1）时顺 / 逆势（16 格）。
- 真实 taker 费 5.1 bps/边（压力 15.1），含资金费，不重叠。分段 train < 2024-10-21 ≤ test < 2026-03-05 ≤ post；可用 = 8 槽（OKX d8 train/test/post、new8 train/test/post、Gate post/窗口）全正且 n ≥ 10 / 6 / 4。
- 先验 `init_short_H24`（重大网络安全事件 = 风险偏好 / 安全情绪冲击 → 做空篮子一天），回退 `init_short_H48`。安慰剂：同小时随机日、±24h / ±168h 平移。

## 结果（`output/research_sec_8k_cyber_incident_event_1h.csv`，2,716 行；真实费每笔净 bps，括号为事件数）

| 格子 | OKX train | OKX test | OKX post | new8 train | new8 test | new8 post | Gate post | Gate 窗口 | 8 槽 |
|---|---|---|---|---|---|---|---|---|---|
| 先验 init short H24 | −52.2 (23) | −25.7 (18) | +17.8 (15) | −75.0 | −104.5 | −52.8 | +17.2 (15) | −14.6 | 2/8 |
| 回退 init short H48 | −164.7 (23) | −1.2 (17) | +73.2 (13) | −181.8 | −78.8 | −9.6 | +71.9 (13) | +83.7 | 3/8 |
| all short H48（非先验最好 side） | −119.3 (32) | +98.8 (22) | +104.5 (17) | −125.7 | +30.5 | +0.1 | +102.8 | +171.7 | 6/8 |
| follow k0 H12 | +66.7 (23) | +23.0 (18) | +19.7 (15) | +38.7 | +49.9 | −38.7 | +12.5 | −3.4 | 6/8 |
| follow k1 H4 | +43.3 (6) | +15.4 (4) | +267.7 (2) | +40.8 | +49.2 | +197.4 | +264.3 (2) | +235.4 | 8/8 但 n 太少 |

- 可用 8/8：**0 / 40**。唯一 8/8 的 follow k1 H4 / H12 只有 6 / 4 / 2 次事件，不满足 n 门槛。
- 先验：train / test 都亏（deep unseen −52 bps，压力费 −72），new8 三段全负；同小时随机日安慰剂 pctile train 29 / test 44 / post 63。
- 回退：deep unseen −165 bps；post +73 bps（13 次）但 −168h 平移安慰剂 post +117.7 更好，post 月份 6/8 正，new8 全负；压力费更差。
- 背景：同脚本「每天 21:00 UTC 做多 24h」基线 OKX post −19.5 bps / Gate post −18.9（post 段整体下跌），做空类 post 正值大多来自市场本身下跌，不是事件。

## 结论
**否决**。不实现、不进观察名单、不加 shadow、不改默认、无代码改动，仅文档；纸面实例未动。

- 勿重测（never retest via）：不要换 H / 方向 / k / 集合（init / all / listed / 8-K/A）/ 30 天去重窗口，不要改用 Item 8.01 网络安全披露、文本关键词搜索、公司市值或行业子集、EDGAR 全文检索替代集合，或改成 4h 闸门 / 计数趋势。
- 文件：`output/research_sec_8k_cyber_incident_event_1h.csv`、`output/sec_8k_item105_cyber_official.csv`（不入库）；脚本 `scratch/cyber8k1h/{parse,prereg,events,run,analyze}.py`。
- 下一轮（长线）：克利夫兰联储官方日度通胀 nowcast（CPI / 核心 CPI 当月环比预测）趋势 / 意外 → 4h 默认书入场闸门（docs / output 中无 Cleveland / nowcast 条目）。
