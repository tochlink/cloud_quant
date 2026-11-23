<!-- Sidecar for docs/STRATEGY_FORMULAS.md (main file exceeds the GitHub connector 1MB push cap). -->

## 短线新族：Nasdaq Trader 官方美股停牌 / LULD 暂停日内爆发 → 8 币永续篮子 1h 事件（持有 24 / 48h，2026-11-23 ~02:10 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,256 个）中无 halt / LULD / 停牌 测试（只有两处「下一轮」指针）。最接近的是已否决的 `us_equity_index_shock_event_1h`（FRED 日度 NASDAQCOM / SP500 收盘冲击）——那是指数日度收益，本条用的是逐笔停牌事件、秒级时间戳、日内小时爆发，数据和机制都不同。
- 数据（只用官方，不回补、不插值）：Nasdaq Trader Trade Halts RSS 按日归档 `https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts&haltdate=MMDDYYYY`，覆盖全部美股上市市场（Mkt Q/N/A/P/Z），HaltTime 为美东时间、精确到秒。抓了 2019-01-01 → 2026-11-20 的 2,059 个工作日（75 个休市日为 0 条，包括 2025-01-09 国葬休市），共 75,042 条停牌，其中 LULD 暂停 66,256 条（LUDP 52,298 / M 13,958），另有 T3 7,029、D 1,713。注意：归档里新闻类停牌（T1 / T12 / H10 / H11）几乎没有（合计 < 50 条），所以 n_all 实际约等于 LULD + T3 + D。按美东→UTC（含夏令时）汇总成 UTC 小时：69,144 根，2019-01-01 05:00 → 2026-11-21 04:00 UTC，缺口 0。峰值出现在 2020-03（2020-03-19 14:00 UTC 有 384 次 LULD），说明数据可信。文件：`scratch/nasdaqhalt1h/nasdaq_halts_official_events.csv`、`nasdaq_halts_official_1h.csv`。
- 公式：x = log1p(序列)，序列为 n_luld（LUDP + M 的次数）、n_luld_sym（发生 LULD 的不同股票数）或 n_all（全部停牌次数）。基线是此前 L 个有交易的归档日里**同一美东小时**的 x 的均值和标准差（严格早于当天）；z = (x − mean) / max(sd, 0.25)。只有美东 9–15 点（常规交易时段）可以触发。小时 t 收盘后才知道信号，在 t+1 的 1h 开盘进场，等权做多或做空 8 币，持有 H 小时，持仓期间不重复开。网格：3 个序列 × L {20, 60} × k {2, 3, 4} × 多 / 空 × H {24, 48} = 72 格。`PRE_REGISTER.json` 在任何 PnL 之前锁定（sha256 `eea9c811…22ad26`）。
- 先验（锁定）：全市场 LULD 爆发对应美股流动性冲击（强制去杠杆），24/7 的加密被当作流动性风险代理先被抛售，随后反弹 → **逆势做多**。先验格 `n_luld_L60_k3_long_H48`，回退格 `n_luld_sym_L60_k2_long_H48`。
- 交易与成本：OKX 官方 1h 永续 d8（2022-01-29 起）、未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）、Gate 官方 1h 永续 d8（2025-09-24 起）；资金费用官方数据（OKX 深历史 / Gate）。taker 0.051% × 2（真实），压力 15.1 bps。分段：train = 深度未见（< 2024-10-21）、test（2024-10-21 → 2026-03-05）、post（≥ 2026-03-05）、gate_window（≥ 2025-09-28）。评分 8 槽，「可用 8/8」还要求 OKX d8 事件数 train ≥ 10 / test ≥ 8 / post ≥ 6。安慰剂：z 平移 ±720h；随机日期 200 次（同期、同笔数，用作同一脚本的基线）。

### 结果（真实费用，平均每笔净收益，单位 bps）

| 格 | OKX d8 train (n) | test (n) | post (n) | new8 train / post | Gate post | post 正收益月数 OKX / Gate | ±720h post | 随机分位 post | 8 槽 |
|---|---|---|---|---|---|---|---|---|---|
| 先验 n_luld L60 k3 long H48 | +14.2 (11) | +73.7 (3) | −41.6 (2) | +37.8 / −82.0 | −41.4 | 1 / 1 | −82.8 / +57.5 | 51.5 | 3/8 |
| 回退 n_luld_sym L60 k2 long H48 | +98.3 (56) | −101.2 (20) | −162.0 (12) | +100.8 / −95.3 | −160.6 | 2 / 2 | +166.3 / −38.8 | 9.5 | 2/8 |
| 唯一 8/8 n_luld_sym L60 k4 short H24（非先验） | +444 (1) | +226 (2) | +45.8 (2) | +376 / +31.0 | +45.3 | 1 / 1 | −185.5 / +59.4 | 62.0 | 8/8，不可用 |
| post 最好之一 n_luld L60 k2 short H24（非先验） | −83.3 (69) | +25.5 (23) | +165.1 (12) | −80.6 / +193.3 | +164.0 | 3 / 3 | −131.1 / −41.7 | 99.0 | 6/8 |
| n_all L60 k2 short H48（非先验） | −82.0 (56) | +105.8 (21) | +311.8 (9) | −87.6 / +234.0 | +311.1 | 3 / 3 | −141.4 / +86.0 | 98.5 | 6/8 |

- 分布：72 格 8 槽正收益个数 0:3、1:5、2:22、3:13、4:2、5:7、6:18、7:1、8:1；**可用 8/8 为 0**。
- 方向发生了体制翻转：做多格在深度未见 train（2022–2024）为正，但 2025–2026 的 test / post 普遍为负；做空格正好相反（train 为负，test / post 为正）。没有任何一格能同时在深度未见和 post 都成立。k ≥ 3 每段只有 1–3 笔事件，统计上不可用。
- 压力费（15.1 bps）：先验 post −61.6、回退 post −182.0。
- 邻域：n_luld 做多 12 格的 post 全部为负（−41.6 ~ −278.4）；k=4 的格在 post 没有事件。
- 结论：**否决**。先验 3/8、回退 2/8，post 两所都亏，只有 1–2 个月为正；唯一的 8/8 只有 1/2/2 笔事件；做空格在深度未见段全负，属于体制翻转，不是稳定 edge。不实现、不进观察名单、不改默认、不动纸面实例。
- **勿重测**：不要换 L / k / H / z 底 / 方向或时段窗口，不要在 n_luld / n_luld_sym / n_all / LUDP / M / T3 / D 之间互换，不要改用停牌时长、复牌时间、单个市场（只看 Nasdaq / NYSE）、个股或板块停牌、熔断（MWCB）计数，也不要换成 NYSE / Cboe 自己的停牌数据或其他国家交易所停牌，以「美股停牌爆发 → 加密篮子」同一机制重测。
- 文件（不入库）：`output/research_nasdaq_trade_halt_luld_burst_event_1h.csv`（2,520 行，含压力费 / 安慰剂 / 随机基线）；脚本 `scratch/nasdaqhalt1h/{fetch,parse,run,analyze,plog}.py`、`PRE_REGISTER.json`、`analyze_wide.csv`、原始 XML `raw/`。
- 下一轮（长线）：美联储官方央行流动性互换额度使用量（H.4.1「Central bank liquidity swaps」，FRED `SWPT` 周度，周四公布，按公布时间滞后）作为离岸美元融资压力体制，做 4h 默认书入场闸门。查重：docs / output 中无 swap line / SWPT / 美元融资 条目；与已否决的 H.4.1 外国官方托管（8794，持有量）、SOFR−IORB、ON RRP / SRF、OFR 金融压力不同。注意：2021 年后使用量多数时间接近 0，先查数据是否足以形成体制，不够就换题。
