# 短线新族：CoW Protocol GPv2Settlement 批次结算突发 → 1h 永续 8 币篮子（2026-11-22，研究，不改默认；否决）

## 背景与查重
- 计划题目「比特币矿工 coinbase 产出转出（矿池支付）1h 突发」**不可行**：需要逐块、逐笔的 prevout（判断 coinbase 衍生 UTXO 被花费）；mempool.space / Esplora 每页 25 笔、近 2 年约 10 万块，没有官方批量接口，不能在一次研究内用官方链上数据建成，也不允许用第三方派生指标或回补。并且 BTC 侧的 Puell、手续费占比、CBECI 矿工利润、矿池集中度、算力带、难度调整、出块间隔 / 空块、链上手续费冲击、mempool 拥堵、政府地址流出都已测过。故换一个全新的短线族。
- 新族：以太坊主网 CoW Protocol（意图型 DEX 聚合）`GPv2Settlement` 的批次结算事件频率。文档 / output / scratch 中 cow / GPv2 / settlement 均 0 条；与已否决的 Uniswap 池冲击、Uniswap V3 LP、WETH9、闪电贷、Aave 清算、Curve 3pool 不同：信息源是求解器（solver）批量撮合的链上意图成交节奏。

## 数据（全部官方链上，`output/cow_settlement_official_1h.csv`）
- 合约 `0x9008D19f58AAbD9eD0D60971565AA8510560ab41`，事件 `Settlement(address indexed solver)`，topic0 `0x40338ce1…9db4`（本地 keccak 计算并断言）。公共 RPC `eth_getLogs`（pocket / tenderly / 0xrpc，16 分片、带检查点；单次 ≥9,990 条则二分以防提供方截断）。
- 起点 2023-01-01 00:00 UTC（区块 16,308,190），终点最后一个完整 UTC 小时 2026-11-22 10:00（含）。**34,115 个完整小时，0 个日历缺口，0 个杂散小时**，共 3,814,302 个事件（与逐小时汇总一致），0 事件小时 3 个（真实零，不插值）。
- 校验：最近 168 小时用另一个端点重新拉取、独立解码，每小时 n_settle / n_tx / n_solver **全部一致**。
- 列：`n_settle`（每小时结算事件数）、`n_tx`（不同交易数）、`n_solver`（不同 solver 地址数，仅 n_settle 与 n_solver 计入网格）。
- 交易腿：官方 1h 永续 OKX d8（2022-01→2026-11-22 06:00 UTC）、OKX 未调参 new8、Gate d8（2025-09-24→），官方资金费，不用现货替代。

## 公式（`scratch/cowsettle1h/PRE_REGISTER.json`，sha256 b8782e45…，在拉取完成、看任何 PnL 之前锁定 144 格）
- x_t = log1p(最近 L 小时序列之和)；z_t = (x_t − 前 168 小时均值)/前 168 小时标准差（只用 t−168…t−1，shift 1，min_periods 84，sd=0 为 NaN）。
- L ∈ {1,4,8}，k ∈ {3,4}，侧：high（z≥k）/ twosided（|z|≥k）；方向：follow（做多篮子；twosided 时随 z 符号）/ contra（做空）；持有 H ∈ {12,24,48} 小时；序列 {n_settle, n_solver}。共 2×3×2×2×2×3 = 144 格。
- 小时 t 的数据在 t+1 开盘可用，下一根 1h 开盘进场，持有 H，不重叠。真实费用 perp taker 5.1 bps/边 + 官方资金费；压力 15.1 bps/边。
- 分段：train / 深度未见 = 数据起点→2024-10-21（OKX d8），test = 2024-10-21→2026-03-05，post = ≥2026-03-05；Gate 只有 2025-09-24 起（gate_window ≥2025-09-28）。
- **先验（锁定）**：`log_n_settle_L4_k3_high_contra_H24`（批次结算突发 = 链上交易急迫 / 波动压力 → 做空篮子）。**回退**：`log_n_solver_L4_k3_high_contra_H24`。
- 评分 x/8：OKX d8 train/test/post、OKX new8 train/test/post、Gate d8 post/gate_window，均值 >0 的槽位数。

## 结果（`output/research_cow_settlement_burst_event_1h.csv` 4,608 行；`_nbhd_placebo.csv`）
| 格 | x/8 | OKX 深度未见 bps(n) | OKX test | OKX post bps(n) | Gate post bps | post 月更好 OKX/Gate | 安慰剂 |
|---|---|---|---|---|---|---|---|
| 先验 n_settle L4 k3 high contra H24 | 0/8 | −173.8 (12) | −49.8 | −91.8 (12, t −0.87) | −92.4 | 4/9 · 4/9 | +720h：+172 / −23 / −84；−720h：+33 / −128 / +64 |
| 回退 n_solver L4 k3 high contra H24 | 0/8 | −45.1 (11) | −99.1 | −136.5 (3) | −138.9 | 0/9 · 0/9 | 方向反复 |
| 最佳非先验（按 post 均值 / x/8=8）n_settle L4 k3 high follow H48 | 8/8 | +142.7 (12, t 0.9) | +178.4 (9) | +151.0 (11, t 0.8, 中位 +71.4) | +151.3 | 3/9 · 3/9 | +720h post +114（更好或相当）；−168h / −720h / 2160h 多为负；5 个 168h 块洗牌 post −102…+99 |
| 同族 follow H24 | 8/8 | +153.4 (12) | +29.4 | +71.4 (12) | +72.0 | 3/9 · 3/9 | — |
| 同族 follow H12 | 8/8 | +61.3 (13) | +67.6 | +78.2 (12) | +77.9 | 3/9 · 3/9 | — |
- 144 格中 8/8 共 9 个，7/8 以上 15 个，满足最小样本的「可用」8/8 仅 4 个（follow H12/H24/H48 与 n_solver L1 twosided follow H24）；所有可用格 t ≤ 1.5，post 事件仅 11–12 笔，月度 3/9（n_solver L1 twosided H24 为 4/9 但 post 均值 +4 bps ≈ 0，t 0.1）。压力费下最佳格 post 仍为正（OKX +131 / Gate +131 bps）但 t 0.7、n=11。
- 邻域：n_settle L4 follow 三个持有期同号但事件仅 ~12 笔；L8 同向但样本 6–8 笔；k=4 时事件数降到 1–3 笔无法评估。时间平移 / 洗牌安慰剂在同量级出现正值（+720h post +114、shuf5 +99），说明该量级的均值被少量事件主导，不能区分于噪声。
- 先验方向（做空）全线失效：post 与深度未见都为负。

## 结论
- **否决**：先验 0/8、回退 0/8；唯一 8/8 的非先验方向（突发 → 做多）事件仅 11–12 笔、t<1、post 月度 3/9（两所）、安慰剂同量级，不满足「深度未见 + post ≥6/9 月两所都更好」。不改默认、不入观察名单、不动纸面实例、无代码改动，仅文档。
- 不再重测：勿以改 L / k / z 窗口 / H / 方向、换 n_tx / 不同 solver 数 / Trade 事件数 / 结算 gas 或手续费、换其他意图型 DEX（1inch Fusion、UniswapX、Bebop）在现有历史上重测本族。
- 局限：起点 2023-01，OKX 深度未见段仅 2023-01→2024-10；k≥3 的 z 突发事件稀少；CoW 事件频率有明显日内与周内季节性，已被 168h 滚动基线部分吸收但未显式去季节。

## 文件
- `output/cow_settlement_official_1h.csv`、`output/research_cow_settlement_burst_event_1h.csv`、`output/research_cow_settlement_burst_event_1h_nbhd_placebo.csv`（不入库）；脚本 `scratch/cowsettle1h/{fetch,prereg,run,analyze,extra}.py`、`PRE_REGISTER.json`（研究脚本未推送）。
