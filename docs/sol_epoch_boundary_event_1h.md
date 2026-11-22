# Solana 官方 epoch 边界（解质押到账 / 通胀奖励发放）→ SOL 永续 1h 事件（否决）

## 短线新族：Solana epoch 边界 1h 事件（2026-11-22 ~01:45 PST，研究，不改默认；否决）

- 查重：上一轮指定的「以太坊 Beacon 罚没 / 大额退出」先核查后放弃：大额退出已被 `research_eth_validator_withdrawal_burst_event_1h.csv`（EIP-4895 ≥32 ETH 全额提款 = 退出）与 `research_eth_beacon_staking_gate_4h.csv`（进出排队）覆盖；罚没本身从未测过，但官方 Xatu `canonical_beacon_block_{attester,proposer}_slashing` 自 2020-12 起合计只有 594 个被罚验证者、195 个事件小时（≥7 个/小时的只有约 15 次），且 proposer 表自 2025-04-28、attester 表自 2026-08-28 起官方文件 404，post 段不完整，不满足「官方数据 >~40 个有效事件且完整」，不做（抓取脚本与原始结果保留在 `scratch/ethslash1h/`）。改选 Solana epoch 边界：docs / `output/research_*.csv`（1,152 个）/ 记忆中无 epoch / 解质押 / Cardano 条目；已否决的 Solana 优先费 1h 是手续费微结构，不是质押解锁日程。
- 机制：Solana 解质押（deactivation）只在 epoch 边界生效，到账的 SOL 才能卖出；通胀奖励也在边界发放 → 先验：边界后 SOL 有卖压（做空）。边界由 slot 号决定（432,000 slot/epoch），可提前预知，所以同时测「边界前」窗口。ADA（Cardano 每 5 天 epoch，奖励在边界发放、无锁定）作为未调参复制。
- 数据（仅官方，不编造、不回补）：Solana 官方 RPC `api.mainnet-beta.solana.com`（`getEpochSchedule`：432,000 slot、无 warmup）；对每个 epoch e 取 ≥ e·432000 的第一个有官方 `getBlockTime` 的 slot（跳过的 slot 返回 −32009）。epoch 250–1093，2021-11-21 → 2026-11-21 共 844 个边界，0 缺失（epoch 617 首次超时，重取成功）。epoch 间隔 2022 年约 70h，2026 年约 26h（slot 变快）。Cardano：Shelley 创世参数 2020-07-29T21:44:51Z + k·432,000 s。交易：OKX 官方 1h 永续（2022-01-29 →）+ OKX 官方资金费；Gate 官方 1h 永续（2025-09-24 →）+ Gate 官方资金费。
- 公式：b = 包含边界时刻的 1h K 线。after：b+1 开盘入场，持 H 小时后开盘平；before：b+1−H 开盘入场，b+1 开盘平。outright = side·r_SOL − 2·fee；hedged_btc = side·(r_SOL − r_BTC) − 4·fee（r 含资金费）。不重叠。费用 real 5.1 bps/边/腿，stress 15.1 bps。
- 预注册（PRE_REGISTER.csv sha256 前 8 位 e3e58847，PnL 前锁定）：资产 SOL / ADA × 腿 outright / hedged_btc × 窗口 after / before × 方向 short / long × H 6/12/24/48 = 64 格；先验 `SOL_outright_after_short_H24`，回退 `SOL_hedged_btc_after_short_H24`；分段 train < 2024-10-21（深未见）/ test → 2026-03-05 / post；安慰剂 ±24h 平移 + 500 次同数量随机时刻；强观察门槛见 PRE_REGISTER。
- 结果（每笔均值 bps，real 费；括号 t / post 月份正）：

| 格 | OKX train（深未见） | OKX test | OKX post | Gate test | Gate post | stress OKX post |
|---|---|---|---|---|---|---|
| 先验 SOL 边界后做空 24h | −21.5（n413, t −0.83） | −17.3（n249） | −1.2（n157, 月 4/9） | +41.8（n82） | −1.6（n157, 月 4/9） | −21.2 |
| 回退 SOL−BTC 对冲做空 24h | −30.6（t −1.57） | −9.1 | −19.8（月 4/9） | +18.4 | −19.6（月 5/9） | −59.8 |
| 邻域 SOL 做空 12h | −29.9 | +8.6 | +8.6（月 6/9） | +32.4 | +8.4 | — |
| 邻域 SOL 做空 48h | −42.5 | −3.8 | −5.8 | +108.7 | −6.5 | — |

  - 安慰剂：先验 post −1.2 不如 +24h 平移 +4.8 / −24h 平移 +14.8；随机时刻分位 train 59%、test 32%、post 58%（p95 约 +37 bps）——与随机无异。
  - 64 格中只有 2 格四段（OKX train/test/post + Gate post）全正，都是 ADA 未调参复制：`ADA_outright_after_short_H12` OKX +11.8 / +29.9 / +23.6（t 0.53 / 0.90 / 0.68），Gate post +23.1，post 月份 6/9，胜过 ±24h 平移；但非先验、t < 1、stress 下 OKX train −8.2，Cardano 没有解质押锁定、机制不成立，不升格。stress 费下 0 格四段全正。SOL train 32 格中 6 格 t < −2、1 格 t > 2。
- 结论：**否决**。不实现、不进观察名单、不加模拟盘、不改默认，无代码改动，仅文档。SOL epoch 边界解质押 / 奖励发放没有可交易卖压：先验三段为负，回退更差，邻域方向乱，安慰剂不输真实。
- 勿重测：不要通过改 H、方向、before/after 窗口、对冲腿、换其他 PoS 链 epoch（ADA / DOT era / NEAR / ATOM 解绑 21 天到期）、换成 epoch 内解质押金额或奖励金额来重测本族；以太坊罚没在官方数据补全且有效事件足够前也不重测。
- 文件（不入库）：`output/research_sol_epoch_boundary_event_1h.csv`（1,548 行，含 stress、±24h 平移、随机 500 次安慰剂）；官方边界序列 `scratch/solepoch1h/sol_epoch_boundaries_official.csv`；脚本 `scratch/solepoch1h/{fetch,fetch_part,run}.py`、`PRE_REGISTER.csv`；罚没核查 `scratch/ethslash1h/{fetch.py,events.csv,days.csv}`。
- 下一轮（长线）：欧央行 ECB 官方周度合并财务报表总资产（ECB Data Portal `ILM` 周度序列）+ 日本央行官方旬报 / 营业概况总资产 → 非美央行资产负债表趋势作为 4h 默认书入场闸门。docs 中「ecb balance / 全球流动性 / BoJ balance」0 条，已否决的只有美联储净流动性（WALCL−RRP−TGA）、H.4.1 托管、M2、H.6/H.8、日债收益率、ECB/BoE 决议事件，不是同一序列。
