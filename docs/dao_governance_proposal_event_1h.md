# 短线：DeFi DAO 链上治理提案聚集 1h 事件 → 8 永续篮子（2026-11-22 ~22:30–22:45 PST，否决）

## 想法
以太坊主网四大 DeFi DAO（Compound、Uniswap、Aave、ENS）的官方链上治理合约在短时间内集中出现新提案（或集中执行），多为市场压力后的风险参数 / 紧急 / 上新响应。先验：提案聚集 = 压力之后 → 做多 8 永续篮子吃反弹。交易频率低（按聚集触发、不重叠持有 24/48h），不是费用受限的 1h 吃单族。

去重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`/workspace/scratch/*` 中无 governance / governor / proposal 相关族（2026-11-22 22:30 PST 检查）。

## 数据（仅官方）
- 官方 `eth_getLogs`（主 RPC gateway.tenderly.co 公共节点，按 50 万块分段，地址 + topic0 过滤），不用 Tally / Snapshot / 子图 / Dune。
- 8 个治理合约：Compound GovernorAlpha `0xc0dA01a0…3E38`、GovernorBravo `0xc0Da0293…6529`；Uniswap GovernorAlpha v1 `0x5e4be8Bc…D58F`、v2 `0xC4e17245…E6F6`、GovernorBravo `0x408ED635…24C3`；Aave GovernanceV2 `0xEC568fff…252c`、GovernanceV3 `0x9AEE0B04…2BC7`；ENS Governor `0x323A7639…b7E3`。
- 事件：ProposalCreated（Alpha/Bravo/OZ、Aave V2、Aave V3 三种签名）、ProposalQueued、ProposalExecuted、ProposalCanceled。合计 4,366 条：created 1,543 / queued 1,363 / executed 1,345 / canceled 115。
- 校验：各合约链上 `proposalCount()` / `getProposalsCount()`（eth_call @ tip）与 created 日志条数逐一相符（Compound Bravo 393 = Alpha 42 + Bravo 351；Uniswap Bravo 102；Aave V2 417；Aave V3 545；Uniswap Alpha v1 5 / v2 4）；11 个随机 9,000 块窗口 + 最新 9,000 块在 rpc.mevblocker.io 上条数完全一致。
- 1h 序列 `output/dao_governance_official_1h.csv`：58,926 个完整 UTC 小时，2020-03-04 00:00 → 2026-11-23 05:00 UTC，0 缺口；零值为真零。
- 价格：官方 OKX 1h 永续（2022-01-29 → 2026-11-22 17:00 UTC，默认 8 币 + 未调参 new8），官方 Gate 1h 永续（2025-09-24 起），含官方资金费。

## 公式与网格（PRE_REGISTER.json，sha256 1a1064097af3…cffa6，在任何 PnL 之前锁定；文件 mtime 22:35 PST，文件内 registered_at 字段误写 22:45）
- 在已收盘小时 t：series_t ≥ 1 且 过去 W 小时（含 t）累计 ≥ k → t+1 开盘入场，持有 H 小时，不重叠。
- series ∈ {n_created, n_exec, n_act}；W ∈ {24, 72}；k ∈ {2, 3, 4}；方向 多/空；H ∈ {24, 48}；共 72 格。
- 先验格 `n_created_W72_k3_long_H48`；回退格 `n_created_W24_k2_long_H48`。
- 费用：吃单 5.1 bps/边（压力 15.1 bps/边）+ 官方资金费。分段：train（深度未见）OKX 起 → 2024-10-21，test → 2026-03-05，post 之后；Gate 窗口 2025-09-28 起。安慰剂：±720h 平移、每段 200 次同笔数随机日期。

## 结果（真实费用，每笔均值 bps）
- 先验 `n_created_W72_k3_long_H48`：3/8。OKX d8 train +7.0（n=194，t 0.24）、test −22.4（n=77）、post −147.9（n=20，t −2.16）；new8 post −136.5；Gate post −146.7、Gate 窗口 −187.8。post 月份 OKX 3/9、Gate 3/9。随机安慰剂 post 分位 7。压力费 post −167.9。
- 回退 `n_created_W24_k2_long_H48`：4/8。train +21.7（t 0.77）、test +27.7、post −31.9（n=24）；Gate post −30.5、Gate 窗口 −144.1；月份 5/9、5/9；随机安慰剂 post 分位 46.5。
- 先验邻域（n_created 做多 12 格）post 只有 2 格为正（W24 k3 H48 +18.3、W24 k4 H48 n=1），其余 −27.9 ~ −147.9。
- 72 格中仅 1 格 usable 8/8：非先验 `n_exec_W24_k3_short_H24`：train +1.8（n=109，t 0.1，中位 −0.9）、test +36.2（n=44）、post +113.2（n=10，t 1.1）；new8 post +135.6；Gate post +112.7、Gate 窗口 +51.3；随机安慰剂分位 train 68.5 / test 83 / post 93.5；±720h 平移 post −101.1 / +18.6。但深度未见期等于零（压力费 train −18.2），post 只有 10 笔，月份 5/9、5/9（< 6/9），邻域 k4 崩（post −200 / −390），W72 多数 train 为负。

## 结论
**否决**。先验与回退都失败（post 为负、月份 < 6/9、安慰剂未胜）。唯一 8/8 是非先验做空格，深度未见期无边际、post 样本小、月份不过 6/9、邻域不稳，不进观察名单、不加纸面。默认、纸面、应用代码均不变。

勿重测：不要通过换 W / k / H / 方向、换 created / queued / executed / canceled / 合计、增删治理合约（Compound / Uniswap / Aave / ENS / Gitcoin / Arbitrum / Optimism 等 L2 治理）、改用 Snapshot 链下投票、VoteCast 投票数、Timelock 执行事件或 Aave PayloadsController 执行，或改为单币（UNI/COMP/AAVE/ENS）反应来重测同一「DAO 治理提案活动 1h 事件」机制。

结果 CSV：`output/research_dao_governance_proposal_event_1h.csv`（2,520 行）；官方 1h 序列 `output/dao_governance_official_1h.csv`；脚本 `scratch/govprop1h/{fetch.py,verify.py,run.py,analyze.py}`。
