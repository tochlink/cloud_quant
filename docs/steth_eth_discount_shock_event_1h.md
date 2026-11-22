# 短线新族：stETH/ETH 折价 1h 冲击（OKX 官方 STETH-ETH 直报盘）→ 8 币永续篮子（2026-11-21 ~23:35 PST，研究，不改默认；预注册先验 / 回退否决，非先验 L24 加宽→做多 列弱观察，不实现）

- 查重：stETH/ETH 折价此前只做过 **4h 默认书入场闸门**（日线收盘，`output/research_steth_eth_basis_gate_4h.csv`，否决；勿重测条款限定「作为 4h 入场闸门」），从未做过 **1h 折价冲击事件 → 8 币篮子**。不同于已否决的 Curve 3pool 稳定币构成冲击（本轮不使用任何 Curve 池数据，避开该节「换 Curve 池」条款）、Lido 提款请求队列 1h 突发、Lido 协议 APR 4h 闸门、EIP-4895 执行层提款 1h、信标进出排队 4h 闸门。任务种子 (a) Deribit 到期、(b) 稳定币官方增发（stablemint1h）、(c) Coinbase 溢价冲击、(e) 验证者退出 / 提款均已测过，故选 (d)。
- 机制：stETH 折价在 1 小时到 1 天内急剧扩大 = stETH/ETH 循环杠杆被强平 / 退出排队恐慌（Aave/Morpho 清算），属被迫卖出；预注册假设为永续篮子随后反弹（流动性提供者被付费接盘）。
- 数据（全部官方，不编造、不插值、不回补）：OKX 官方现货 `STETH-ETH` 1H `history-candles`（直接报价，只取 confirm=1 已收盘），2023-07-18 10:00 UTC → 2026-11-22 06:00 UTC，29,349 根，0 日历缺口；35% 为零成交小时（OKX 官方延续价，原样保留）。折价分布：中位 −4 bp，1% 分位 −30 bp，最深 −103 bp（2025-10），−94 bp（2024-08），−83 bp（2026-04）。交易：OKX 官方 1h 永续 d8 与未调参 new8（2022-01 →），Gate 官方 1h 永续 d8（2025-09-24 →），官方资金费；本轮把 OKX/Gate 永续与资金费追加到 2026-11-22 06:00 UTC（只追加官方已收盘 K 线）。
- 公式：`x_t = (close_t − 1) × 1e4`（bp，负 = 折价）。
  - `dl`：`d_t = x_t − x_{t−L}`；加宽 `d_t ≤ −θ`，收窄 `d_t ≥ +θ`。
  - `zlev`：`z_t = (x_t − mean_168h,t−1) / max(std_168h,t−1, 1bp)`（min 84）；加宽 `z ≤ −k`，收窄 `z ≥ +k`。
  - 信号小时收盘后下一根 1h 永续开盘吃单入场，8 币等权，持有 H 根后开盘平，不重叠；费用 2 × taker 5.1 bp（压力 15.1）+ 官方资金费。maker 不假设。
- 预注册（`scratch/stethdisc1h/PRE_REGISTER.json`，sha256 `2bb0fd28…879a`，任何 PnL 前锁定 **192 格**）：dl L {1,4,24} × θ {10,15,25} bp + zlev k {3,4,5}，× side {widen, narrow} × dir {long, short} × H {6,12,24,48}。先验 `dl L4 θ15 widen long H24`，回退 `zlev k4 widen long H24`。切分 train（深度未见）2023-08-18 → 2024-10-21 / test → 2026-03-05 / post → 2026-11-22；Gate 窗 2025-09-28 →；安慰剂信号时移 ±720h；同脚本无条件基线（每 H+1 根入场）。
- 结果（`output/research_steth_eth_discount_shock_event_1h.csv`，7,776 行；每事件净 bp，真实费）：

| 格 | 正槽 | OKX d8 train / test / post | new8 train / test / post | Gate test / post | post t | 压力费 post（OKX） | 安慰剂 post +720h / −720h | post 月份 |
|---|---|---|---|---|---|---|---|---|
| 先验 dl L4 θ15 widen long H24 | 4/8 | +286.5 (n21, t4.0) / +283.3 (n10) / **−111.0** (n3) | +227.8 / +244.7 / −16.4 | −102.2 / −111.2 | −0.9 | −131.0 | −54.3 / −94.8 | 0/9（有事件 2 个月） |
| 回退 zlev k4 widen long H24 | 4/8 | +256.5 (n23, t3.6) / +236.0 (n27, t2.3) / **−212.0** (n7, t −2.2) | +193.7 / +227.2 / −140.5 | +239.6 / −211.3 | −2.2 | −232.0 | −16.6 / −62.6 | 2/9（有事件 6 个月） |
| 非先验 dl L24 θ10 widen long H24（唯一 usable 8/8） | 8/8 | +138.3 (n57, t2.9) / +138.4 (n36, t1.6) / **+167.0** (n5, t1.9) | +105.3 / +95.5 / +131.3 | +39.9 / +166.7 | 1.9 | +147.0 | −39.0 / −214.7 | 3/9（有事件 3 个月，全正） |

  - 基线（同脚本无条件做多 H24）：OKX d8 train +22.1 / test −8.1 / post −22.7；Gate post −23.2。非先验格 post 比基线高约 +190 bp/笔。
  - 邻域：加宽→做多 在 L1 / L4 上 train/test 全正（+17 至 +700 bp）但 post **全部为负**（−19 至 −129 bp）；L24 的 H24 / H48 × θ{10,15,25} 6 格中 5 格 8/8、1 格 7/8（post +46 至 +167），但 L24 的 H6 / H12 post 多为负。post 5 个事件中 3 个集中在 2026-04-19/20/21 同一轮，另 2026-06-10、2026-11-20 各 1 个。
  - 与已实现投降 #13/#14 的重叠：非先验格事件前 24h 篮子收益中位 +0.47%，只有 19% 发生在篮子 24h 跌 ≥5% 后；非崩盘子集仍为正（train +86.7 n48 / test +59.2 n27 / post +108.1 n4），纯「24h 跌 ≥5% 做多」对照 post 只有 +17.6（n27），说明有部分增量，但样本很小。
  - 网格分布：192 格中 8/8 共 8 格（usable 1）、7/8 3 格；zlev k4 收窄→做空 H24/48 post +288 bp 但 n=3、test n=4，不可用。
- 结论：**预注册先验与回退均否决**（post 两所同号为负，回退 t −2.2，压力费更差，不胜安慰剂）。非先验 `dl L24 θ10 widen long H24` 8/8、胜 ±720h 安慰剂与基线、压力费为正、L24×H24/48 邻域稳定，但它不是先验、post 只有 5 个事件（3 个同簇）、post 月份 3/9 远低于 6/9，且短 L 版本在 post 反向 → 只列 **弱观察**：不实现、不加 shadow 子书、不改默认、无代码改动。已起官方实时记录器 `scratch/stethdisc1h/record.py`（每 10 分钟追加 OKX STETH-ETH 已收盘 1H，并记录 dl24 ≤ −10 bp 信号），每月复查一次该格 post 事件；post ≥ 10 事件且月份 ≥ 6/9 才可再议强观察。
- **勿重测**：不要以换 L / θ / k / H / 方向 / widen↔narrow、换 dl↔zlev↔其他 z 形式、换 Curve stETH 池 / wstETH / rETH / cbETH 等其他 LST 折价、换 Gate STETH_USDT 隐含比价、换更早起点，或改成 4h 闸门的方式重测本族；只允许按上面的弱观察格做前向复查。
- 文件：`output/research_steth_eth_discount_shock_event_1h.csv`（不入库）；脚本与数据 `scratch/stethdisc1h/{fetch,run,analyze,overlap,record}.py`、`okx_steth_eth_official_1h.csv`、`PRE_REGISTER.json`（研究脚本未推送）。
- 下一轮（长线）：Gate 官方批量 `futures_usdt/funding_applies` 全合约（含已下架）月度 / 周度「资金费触顶合约占比」（|r| ≥ 单合约 funding_rate_limit 一半的合约 ÷ 全部合约）作为全市场山寨杠杆过热体制 → 4h 默认书入场闸门（高占比 → 拦新多）；docs / output 中 0 条完成测试（仅 2026-11-21 22:25 节作为指针出现）。备选：Cboe 官方美股 Total / Equity put-call ratio 日度趋势闸门（同样未测）。
