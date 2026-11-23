# 主网硬分叉 / 网络升级激活（官方客户端配置时刻）→ 本币 USDT 永续 1h 事件（否决；不改默认、不入纸面）

## 短线新族：硬分叉 / 网络升级激活前后「买预期 / 卖事实」（1h，持有 12–72h；2026-11-22 ~17:05–17:40 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv` 文件名、`scratch/` 目录名对 hard fork / hardfork / 硬分叉 / network upgrade / 网络升级 / 主网升级 / The Merge / sell the news / 卖事实 / Luban / Feynman / Durango / Etna 零命中；Dencun / Pectra 只在 beacon_voluntary_exit、pendle 两个侧记里作为数据口径变化被顺带提及（不是事件交易）。不同于已否决的代币解锁（token_unlock，供给事件）、上币 / 下架公告、FOMC / CPI 等宏观日程、期权 / 期货到期、Solana epoch 边界、BTC 难度调整（这些都不是本币协议规则切换）。
- 机制（先验）：协议升级时刻提前数周公开（客户端配置写死时间 / 区块高度），市场常「买预期、卖事实」——激活后本币相对 BTC 回吐。先验格 `short_a0_b48_btc`（激活后做空本币、等名义做多 BTC 对冲，持有 48h）；回退 `long_a-72_b0_btc`（激活前 72h 做多本币对冲 BTC，激活小时开盘前平）。
- 数据（只用官方，不编造、不插值、不回补）：
  - 事件表 `output/hardfork_events_official.csv`（45 行，2 行 emergency 剔除）：ETH = go-ethereum `params/chainspecs/mainnet.json`（shanghai / cancun / prague / osaka / bpo1 / bpo2 时间戳；Gray Glacier 区块 15,050,000、合并后首个 PoS 区块 15,537,394 的区块时间由以太坊 RPC 取得，2–3 个节点一致）；BNB = bnb-chain/bsc `params/config.go`（Kepler→Pasteur 时间戳；Euler→Hertzfix 区块高度 + 官方 bsc-dataseed RPC 区块时间，两节点一致；Nano / Moran 为 2022-10-06 被盗后的紧急分叉，标 emergency 剔除）；AVAX = ava-labs/avalanchego `upgrade/upgrade.go` Mainnet（ApricotPhase6→Helicon）；ADA = cardano.org/hardforks + CIP-0059 特性表（epoch 365 / 394 / 507 / 537 / 644，按 Shelley epoch 208 起点 2020-07-29 21:44:51 UTC、每 epoch 432,000 s 换算）；BCH（new8 未调参）= BCHN `src/chainparams.cpp`（每年 5-15 12:00 UTC MTP，2022–2026）。BTC / SOL / XRP / DOGE 在窗口内无主网硬分叉；LTC / ATOM / DOT / NEAR / TRX 无官方时间表或属治理型 runtime 升级，按预注册排除。
  - 价格：OKX 官方 v5 1H 永续 K 线（`scratch/deep1h` 缓存 2022-01-29→2026-11-22 17:00 UTC；BNB 2022-12-23 起；BCH `scratch/capit/n8`），OKX 官方深历史资金费 `output/okx_funding_history_official_deep.csv`；Gate 官方 download.gatedata.org 月度 1h 永续 K 线 + funding_applies（2022-01-01 起）+ v4 REST 补到 2026-11-23 00:00 UTC（ETH / BNB / BCH / BTC 0 缺口，AVAX 3、ADA 2 个小时缺口，不填）。
  - d8 事件数：OKX 36（deep 20 / test 12 / post 4），Gate 38（deep 22，多出 BNB Euler、Gibbs）；BCH 5（deep 3 / test 1 / post 1）。
- 公式（看 PnL 前锁定 `scratch/hardfork1h/PRE_REGISTER.json`，sha256 `60f41bf5108add140c2a4e61f399b4223147e50c03cee14c4cf413315ef9fad6`，40 格）：
  - Tf = 激活时刻所在小时；Tc = Tf + 1h。b ≤ 0 窗口：open(Tf + a) 入场、open(Tf + b) 出场（激活小时前离场）；a ≥ 0 窗口：open(Tc + a) 入、open(Tc + b) 出；跨窗 (−24, 24)：open(Tf − 24) 入、open(Tc + 24) 出。
  - 每笔净收益 = d·(O_exit/O_entry − 1) − d·Σ(官方资金费 × close/entry) − 腿数 × 2 × 费率；hedge=btc 加同所反向等名义 BTC 永续腿。
  - 窗口 (a,b) ∈ {(−72,0), (−48,0), (−24,0), (−12,0), (−24,24), (0,12), (0,24), (0,48), (12,48), (24,72)} × 方向 {long, short} × 对冲 {none, btc}。
  - 费率：maker 2 bps / 边、taker 5.1 bps / 边（主口径）、压力 15.1 bps / 边。切分 deep < 2024-10-21 ≤ test < 2026-03-05 ≤ post。安慰剂：事件时刻 −15d / −7d / +7d / +15d。邻域：同方向同对冲相邻窗口。
- 结果（`output/research_hardfork_upgrade_event_1h.csv` 17,920 行；每笔净 bps，taker 5.1；括号为事件数）：

| 格 | 场所 | deep | test | post | BCH new8 全部 | 全部 t | 压力费全部 | maker 全部 | 安慰剂胜 |
|---|---|---|---|---|---|---|---|---|---|
| 先验 short_a0_b48_btc | OKX | +34 (20) | −210 (12) | +18 (4) | −22 (5) | −0.60 | −89 | −37 | 1/4 |
| 先验 short_a0_b48_btc | Gate | +41 (22) | −210 (12) | +18 (4) | −12 (5) | −0.49 | −81 | −29 | — |
| 回退 long_a-72_b0_btc | OKX | −171 (20) | −111 (12) | +286 (4) | −69 (5) | −1.40 | −140 | −88 | 0/4 |
| 回退 long_a-72_b0_btc | Gate | −176 (22) | −112 (12) | +285 (4) | −64 (5) | −1.56 | −147 | −95 | — |
| 非先验 short_a-48_b0_btc | OKX | +80 (20) | +5 (12) | +116 (4) | +75 (5) | 0.96 | +19 | +71 | 4/4 |
| 非先验 short_a-48_b0_btc | Gate | +77 (22) | +4 (12) | +114 (4) | +65 (5) | 0.97 | +18 | +71 | — |

  - 安慰剂（OKX d8 deep+test 合并每笔 bps，−15d / −7d / +7d / +15d）：先验 −69 / +69 / −10 / −38 vs 真实 −58；回退 −46 / −34 / +105 / −7 vs 真实 −149；short_a-48_b0_btc −31 / −27 / −75 / +29 vs 真实 +52。
  - 邻域：先验同侧 short_a0_b24_btc deep+test −19、short_a12_b48_btc −65、short_a0_b48_none −66（全负，先验无邻域支撑）。short_a-48_b0_btc 邻居 short_a-72_b0_btc +108（t 1.54，但 post −327）、short_a-24_b0_btc −4。
  - 月份：先验 post 月 1/4 为正（全部 10/26）；回退 post 3/4（全部 11/26）；short_a-48_b0_btc post 2/4（全部 14/26）。
  - 分币（OKX 全部，先验）：ADA +133、AVAX +41、BNB −37、ETH −277（ETH Prague −2176 bps 单笔）；short_a-48_b0_btc：AVAX +176、BNB +113、ADA −132、ETH −40（留一币后 +20 ~ +90）。major_only 诊断：先验 −38（n 32）、short_a-48_b0_btc +46（n 32）。
  - 注意：OKX 与 Gate 是同一批事件、同一时刻，结果几乎相同，不是独立复现。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动、不加 shadow。先验「卖事实」4/8 槽为正，test 段 −210 bps、只胜 1/4 安慰剂、邻域全负；回退「买预期」2/8，deep / test 都为负（OKX t −1.74 / −1.18）。全网格唯一 8/8 的 short_a-48_b0_btc 是非先验（方向与「买预期」相反），t 仅 0.96、test 每笔 +5 bps（≈ 0）、4 个币里 2 个为负、邻居 a−24 为负，且事件每年只有约 6–10 个、未来可前测事件稀少（下一次 BSC Jenner 2026-12-08 02:30 UTC），不值得前测。
- 勿重测：不要改窗口 a / b、方向、BTC 对冲 / 篮子对冲、入场延迟、15m / 4h 周期，不要在 major / minor / emergency 之间换子集，不要加 ATOM / DOT / NEAR / LTC / TRX / XRP 修正案 / SOL 特性激活 / L2（Arbitrum / Optimism / Base）升级或测试网分叉、客户端版本发布时间、升级公告 / 治理投票通过时刻来重测本族。
- 文件：`output/research_hardfork_upgrade_event_1h.csv`（主网格 + 安慰剂 + 分币，17,920 行）、`output/research_hardfork_upgrade_event_1h_supp.csv`（7 个关键格逐事件明细，2,940 行）、`output/hardfork_events_official.csv`（官方事件表）；脚本 `scratch/hardfork1h/{blocktimes,events,prereg,fetch,run,analyze,supp}.py`（研究脚本不推送）。纸面 8788 / 8789 / 8792 未改动。
- 下一轮（长线）：EIA 官方 Henry Hub 天然气现货日度价格趋势 → 4h 默认书入场闸门（此前列为指针、尚未测；先查重 us_rates_oil_trend、eia_wpsr_crude、ercot_power_price_spike 与非加密 sleeve 节）。
