# 短线：Aave V3 以太坊 Core 官方 Borrow / Repay 稳定币借还流量 1h 冲击 → 8 币永续篮子（2026-11-22 ~21:30–22:05 PST，否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、全部 `docs/*.md` 侧文档、`output/research_*.csv`（1,235 个）、`/workspace/scratch`、记忆中检索 Borrow / Repay / 借款 / 借贷需求 / 新增借款 / leverage demand：没有链上借贷**借还流量**短线条目。已测且不同的有：Aave V3 LiquidationCall 1h 清算冲击（强平，否决）、Aave V3 借款年化 4h 闸门（利率水平 / 趋势，否决）、闪电贷突发、Morpho / Compound / GMX 清算、交易所资金费 / OI / 强平微观结构。本轮先排除的候选：特朗普 X 帖子（X 全量归档里 2022 年起含 tariff 的帖子只有 6 条，Truth Social 官方 API 被 Cloudflare 403 拦截）、SEC 加密执法新闻稿（官网只有日期、没有发布时刻，post 段事件极少）。
- 机制（看 PnL 前锁定的先验）：用 ETH / BTC 抵押、在 Aave 上突发大量借出稳定币 = 新的加杠杆做多需求 → 做多 8 币篮子（顺势）。Repay 突发 = 去杠杆，作为对照序列。

## 数据
- 只用官方链上日志：以太坊主网 Aave V3 Core Pool 代理 `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`（bgd-labs/aave-address-book）的 `Borrow`（topic0 `0xb3d08482…7dce0`）和 `Repay`（topic0 `0xa534c8db…84051`），通过公共 RPC 调 `eth_getLogs`，分片抓取、可断点续传。不用 subgraph / Dune / DefiLlama，不回补、不插值。
- 稳定币只算 USDC / USDT（6 位小数）和 DAI（18 位），按面值计美元，不用外部价格。
- 共 33,501 个完整 UTC 小时，2023-01-27 08:00 → 2026-11-23 04:00 UTC，0 个日历缺口；Borrow 931,685 笔，Repay 753,577 笔。稳定币借款按年：2023 年 38.9 亿、2024 年 360 亿、2025 年 1,245 亿、2026 年（到 11-22）511 亿美元。
- 官方小时表 `output/aave_v3_borrow_repay_official_1h.csv`（不入库）。
- 行情用官方 OKX 1h 永续（默认 8 币 + 未调参 new8：LINK LTC DOT TRX BCH ATOM NEAR UNI）、官方 Gate 1h 永续（2025-09-24 起），资金费用官方历史。

## 公式 / 参数（`scratch/aaveborrow1h/PRE_REGISTER.json`，看任何 PnL 前锁定，sha256 `d220bc67…23c0`）
- 序列：`log_stable_borrow = log1p(当小时 USDC+USDT+DAI 借款额)`、`log_n_borrow = log1p(当小时 Borrow 笔数)`、`log_stable_repay = log1p(当小时稳定币还款额)`。
- `z_t = (x_t − 过去 L 小时均值) / 过去 L 小时标准差`（滚动窗口右移 1 小时）；当小时收盘后 `z ≥ k`，就在下一根 1h 开盘等权进场 8 币，持有 H 小时，事件之间不重叠。
- 网格：L ∈ {168, 720} × k ∈ {2, 3, 4} × H ∈ {12, 24, 48} × 多 / 空 × 3 个序列 = 108 格。
- 先验格 `log_stable_borrow_L720_k3_long_H24`；回退格 `log_n_borrow_L720_k3_long_H24`。
- 费用：实费 taker 5.1 bps × 2 加官方资金费；压力费 15.1 bps × 2。
- 切分：train（深未见）到 2024-10-21；test 2024-10-21 → 2026-03-05；post 2026-03-05 之后；Gate 窗口 2025-09-28 之后。打分看 8 个槽位（OKX d8 三段、new8 三段、Gate post 和 Gate 窗口），另加 ±720h 时移安慰剂和邻域。

## 结果（`output/research_aave_v3_borrow_repay_flow_shock_event_1h.csv`，3,456 行）
- **先验格基本不触发**：稳定币借款额的对数分布尾部很厚，L720 下 z ≥ 3 很少出现。train 0 次；test 2 次，均值 −175.8 bps；post 2 次，+52.3 bps；Gate 窗口 3 次，−135.5 bps。只有 2/8 个槽位为正，post 9 个月里只有 1 个月为正。
- **回退格** `log_n_borrow_L720_k3_long_H24`：2/8。train −53.6 bps（30 次），test +89.2（30 次），post −32.8（13 次，t −0.3，中位数 −126.3），new8 post −17.3，Gate post −32.4；post 月份 2/9 为正。
- 全部 108 格里只有 1 格 8/8 可用：非先验的 `log_stable_borrow_L720_k2_long_H24`。train +44.9 bps（29 次，t 0.9），test +54.3（96 次，t 1.4），**post 只有 +0.5 bps（38 次，t 0.0）**，new8 三段 +34.6 / +83.7 / +17.7，Gate post +1.8、Gate 窗口 +12.3。
  - 被安慰剂打败：post 段 +720h 时移是 +34.9、−720h 时移是 +39.1，都高于这一格本身。
  - 压力费下 post 变成 −19.5 bps（Gate −18.2）；post 月份 3/9 为正。
  - 邻域不稳：H12 时 post −29.3，H48 时 post +9.3 但 new8 train 为 −42.0，L168 时 post −3.7。
- 安慰剂整体：真实信号有 4 格在 OKX d8 三段都为正；+720h 时移有 5 格、−720h 时移有 2 格，和真实信号差不多，说明这个信号没有可区分的信息。

## 结论
**否决**。先验格几乎不触发，回退格在 post 和未见段都是负的；唯一 8/8 的非先验格 post 收益接近零，被时移安慰剂打败，压力费下为负，月份 3/9，邻域也不稳。不实现，不进观察名单，不改默认，不加模拟盘，代码没改。

## 勿重测
不要靠下面这些办法重测本族：改 L / k / H / 方向；在借款额、借款笔数、还款额之间互换，或改用净借款（借 − 还）、借款人数、单笔金额；换稳定币子集（加 GHO / USDS / PYUSD / USDe），或改用 WETH / WBTC 借款；改用 Supply / Withdraw 存取流量、利用率变动；换 Aave V2 / Lido / EtherFi 市场或其它链上的 Aave V3；换成 Compound / Morpho / Spark / Fluid 等其它借贷协议的借还流量；或者改成 4h 闸门。

## 文件
- `output/research_aave_v3_borrow_repay_flow_shock_event_1h.csv`（不入库）
- `output/aave_v3_borrow_repay_official_1h.csv`（不入库）
- 脚本 `scratch/aaveborrow1h/{fetch,finish,run,analyze}.py`；`PRE_REGISTER.json`；日志 `fetch.log` / `finish.log` / `run.log` / `analyze.log`
- 本侧文档 `docs/aave_v3_borrow_repay_flow_shock_event_1h.md`

## 下一轮（长线）
日本财务省（MoF）官方每周「对外及对内证券买卖」（International Transactions in Securities，周四 08:50 JST 发布，2005 起）里**日本居民净买外国中长期债券**的 4 / 13 周趋势或 z 极值 → 4h 默认书入场闸门。机制是日元套息资金外流；外流逆转（居民净卖外债、资金回流）= risk-off，此时拦新开多。查重：docs / output 中只有两处把它列为「下一轮」，没有 CSV、没有完成的测试。这和已否决的 JPX 按投资者类别的股票买卖（交易所口径的股票流）不同，也和 JGB 收益率闸门（价格）、美联储托管闸门（外国官方持有美债）不同。为避免和 JPX 重叠，只用居民买外债这一侧，不用非居民买日股。时滞按发布日周四 00:00 UTC 之后才用，历史足够覆盖 2026-03-05 切分。
