# 短线新族：Sky/Maker PSM（USDC-A 稳定兑换模块）官方链上流量冲击 → 8 币永续篮子（1h）

> 侧记（仅文档）。研究，不改默认、不改 paper；**否决**。

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv 中无 Maker/Sky PSM / LitePSM / SellGem / BuyGem 条目（仅有 sky_ssr_dsr_gate_4h = 储蓄利率水平闸门，机制不同）。不同于已否决的 USDT 发行/赎回、稳定币供给 1h 冲击、Curve 3pool 池构成冲击、CCTP USDC 跨链流量。
- 数据（只用官方链上，不编造、不插值、不回补）：以太坊主网 `MCD_PSM_USDC_A`（DssPsm）`0x89B78CfA322F6C5dE0aBcEecab66Aee45393cC5A` + `MCD_LITE_PSM_USDC_A`（DssLitePsm，含 USDS 包装流量）`0xf6e72Db5454dd049d0788e411b06CfAF16853042`。公共 RPC `eth_getLogs`（address + topic0 过滤）抓两个官方事件：SellGem `0xef75f5a4…` （USDC 入 → DAI 出）、BuyGem `0x085d06ec…`（DAI 入 → USDC 出）；金额 = gem 数量 /1e6 美元；时间用日志 blockTimestamp。区块 14,120,000（2022-02-01）→ 26,472,141 全覆盖（248 段、0 缺段，失败段直接中止不插值），SellGem 774,925 条（合计 $344.2B）、BuyGem 929,706 条（$346.4B）。按 UTC 小时汇总，无事件小时（2,515 个）= 真实零流量；当前未收完的小时丢弃。小时序列 scratch/makerpsm1h/maker_psm_official_1h.csv：2022-02-01 13:00 → 2026-11-22 16:00 UTC 共 42,124 小时，0 日历缺口，0 无效。核对：2023-03-11（USDC 脱锚）SellGem 当日 $1,388.4M、BuyGem $86.1M（逃离 USDC → DAI）。
- 公式：net_sell = asinh((Sell_usd − Buy_usd)/1e6)（正 = USDC→DAI）；log_sell = log1p(Sell_usd)；log_buy = log1p(Buy_usd)。z：L=1 时 (x−μ)/σ，L>1 时 (Σ_L x − Lμ)/(σ√L)，μ/σ 为截至 h−1 的 168h 滚动（min 84）。
- 滞后规则：信号小时 h 收盘（h+1h）后，**下一根 1h 永续开盘入场**，持有 H 根，事件不重叠；等权 8 币篮子。成本 2×taker 5.1 bps（压力 15.1）+ 官方资金费（同 curve3pool1h / eigenlayer1h 框架）。
- 预注册（scratch/makerpsm1h/PRE_REGISTER.json，sha256 `b0d365289e84ce6b…`，任何 PnL 前锁定 432 格）：metric {net_sell, log_sell, log_buy} × L {1,4,8} × k {3,4,5} × {high z≥k, low z≤−k} × {long, short} × H {6,12,24,48}。先验 `net_sell_L4_k3_high_long_H24`（4h 内集中 USDC→DAI = 还金库债的强制 DAI 需求 / 逃离 USDC → 投降 → 次日反弹）；回退 `log_buy_L4_k3_high_long_H24`（集中 DAI→USDC 赎回 = USDC 被提去 CEX 加风险 → 次日看多）。切分 train 2022-02-15 → 2024-10-21（深度未见段）、test → 2026-03-05、post → 今；Gate 自 2025-09-28；new8 未调参；安慰剂 z 平移 ±720h。
- 评分（同 curve3pool1h）：8 槽 = OKX d8 train/test/post、new8 train/test/post、Gate post / gate_window 的均值全 > 0，且 OKX d8 train n≥10、test n≥8、post n≥8 才算 usable 8/8。强观察还要求：先验 test+post 两所都成立、未见段成立、胜过 ±720h 安慰剂、post 月份 ≥6/9 两所为正、邻域稳定。

## 结果（真实费，每笔净 bps；`output/research_maker_psm_flow_shock_event_1h.csv` 17,280 行）

| 格 | OKX d8 train | test | post | new8 train/test/post | Gate post / window | 8 槽正 | usable |
|---|---|---|---|---|---|---|---|
| **先验** net_sell L4 k3 high long H24 | +33.7（n=79, t 0.77）| +29.5（n=13, t 0.41）| +70.1（**n=7**, t 0.39）| +48.4 / +91.5 / +70.1 | +70.3（n=7, t 0.40）/ +18.8（n=9）| 8/8 | 否（post n<8）|
| 回退 log_buy L4 k3 high long H24 | +47.3（**n=2**）| −5.3（n=21, t −0.07）| +50.4（n=11, t 0.46）| +53.5 / +37.1 / +131.8 | +51.6 / +17.2 | 7/8 | 否 |
| 唯一 usable（非先验）log_buy L8 k4 low short H48 | +29.8（n=25, t 0.37）| +106.3（n=23, t 0.99）| +107.8（n=11, t 1.09）| +48.6 / +148.5 / +133.0 | +107.0 / +132.8 | 8/8 | 是 |

- 先验：压力费 train +13.7 / test +9.5 / post +50.1、Gate window **−1.2**。安慰剂 +720h post **+129.2**（好于真实 +70.1）、−720h post −151.1。post 月份（OKX / Gate）正 3/5（05 −18、06 +98、07 +434、09 +701、11 −724），未达 ≥6/9。邻域：L1k3/k4/k5、L4k4/k5、L8k4/k5 的 post 都是 0 事件，L8k3 test −51.3；H6 post −5.3。全部 t < 1.1 → 否决。
- 回退：train 仅 2 笔（深度未见段无样本），test 为负；+720h / −720h post −3.5 / −89.3（真实较好），但 post 月份正 3/7；邻域 L8k3 post −48.2、H6 −63.3、H12 −15.4 → 否决。
- 唯一 usable 8/8 为非先验 log_buy_L8_k4_low_short_H48，post t 1.09；但其 +720h 安慰剂 5 槽全正（train +44.0 / test +113.8 / post +83.8 / Gate post +83.4 / window +88.5），−720h test +125.6、window +204.5 —— 与平移 30 天的随机时点做空 48h 不可区分，不可晋升。
- 全网格：真实 8 槽 n_pos 分布 0:116 / 1:49 / 2:90 / 3:36 / 4:73 / 5:26 / 6:27 / 7:8 / 8:7；usable 8/8 = 1。按安慰剂可比的 5 槽（OKX train/test/post + Gate post/window，同 n 门槛）：真实 5/5 = 12、usable 1；安慰剂 +720h 5/5 = 9、usable 4；−720h 5/5 = 21、usable 6 —— 真实不优于安慰剂。
- 事件数问题（如实说明）：多数格事件极少：432 格中 160 格 OKX d8 post 0 事件、334 格 post < 8 事件；56 格 train 0 事件（如回退格 train 仅 2 笔）。因此大多数格不具备统计意义，结论不依赖它们。

## 结论

**否决**：不实现、不进观察名单、不改默认、不加 paper，无代码改动，仅文档。PSM 的 USDC→DAI 集中流入在 2023-03 脱锚等危机里确实是压力信号，但 先验各段 t 全 < 1.1、唯一 usable 格 post t ≤ 1.12、post 只有 7 笔、+720h 安慰剂更好、月份 3/5，过不了 taker 费和稳健性门槛。

**勿再测**：不得以同一机制换 L / k / H / 方向 / high↔low、互换 metric（net_sell ↔ log_sell ↔ log_buy、净流 ↔ 总量 ↔ 笔数）、只用旧 PSM 或只用 LitePSM、换其他 PSM（USDP/GUSD-A、Spark/Base PSM3、USDS 包装）、换更早起点再测。

- 文件：`output/research_maker_psm_flow_shock_event_1h.csv`；脚本 scratch/makerpsm1h/{fetch,build,run,analyze,evaluate,record}.py、PRE_REGISTER.json（研究脚本与数据未推送）。实时官方记录器 scratch/makerpsm1h/record.py 保持运行（每 10 分钟追加 SellGem/BuyGem 日志到 live_logs.csv）。
