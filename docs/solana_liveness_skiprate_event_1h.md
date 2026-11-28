# 短线新族：Solana 主网活性（出块跳槽率 / 槽时长）1h 突发 → SOL 永续（2026-11-28 ~03:00 PST；已否决）

- 族名：`solana_liveness_skiprate_event_1h`。预注册 `scratch/solskip1h/PRE_REGISTER.json`（任何 PnL 之前锁定，96 格，sha256 `fadb9d9fb093f170de7cd1d5471ddef34cdf7d72a98474e96c9082a3794867af`）。脚本 `scratch/solskip1h/{extend,build,run,analyze,supp}.py`（研究脚本不推送）。

## 查重
- docs/*.md、docs/STRATEGY_FORMULAS.md、`output/research_*.csv`、scratch 目录、ROTATION_LOCK 中检索 chain halt / 链停摆 / skip rate / 跳槽 / slot time / Solana 活性：0 次测试；`us_rigcount_gate_4h.md`、`henryhub_natgas_gate_4h.md` 两次把「主链出块停顿 / 链停摆冲击（Solana 官方 RPC slot→blockTime）」列为未测的下一短线指针。
- 不同于：以太坊信标漏槽 1h（ETH 信标链、交易 8 币篮子）、BTC 出块间隔 / 空块 1h（PoW）、Solana 优先费冲击（费用需求）、Solana epoch 边界（日历）。本族用 Solana 自身的出块活性，交易被点名的 SOL 永续。
- 本轮先放弃的候选：Coinbase 现货上币（STRATEGY_FORMULAS 已禁止换交易所测上币 / 下架）；指数成分调整（Grayscale GDLC 8-K + CoinDesk 20 再平衡，官方可得但 2022-04→2026-02 只有约 25 个币次，post 段约 0 个事件，无法验证）。

## 数据（只用官方，不编造、不回补）
- Solana 主网官方 RPC `api.mainnet-beta.solana.com`：每个 UTC 小时 :15 与 :45 各取一个已产出的区块（跳过的槽顺延到下一个槽）的 `slot / blockTime / blockHeight`。2023-06-01 → 2026-11-21 复用 `scratch/solprio1h/blocks_light.csv`（60,959 个样本），2026-11-22 → 2026-11-28 10:45 UTC 用同一方法补取 310 个样本（`scratch/solskip1h/extend.py`）。
- 小时序列 `output/solana_liveness_official_1h.csv`：30,634 个完整小时（2023-06-01 01:00 → 2026-11-28 10:00 UTC），0 个缺失小时。第 h 小时用 (h−1):45 → h:45 两个样本：`skip = 1 − ΔblockHeight/Δslot`（领导者跳槽率），`slow = Δt/Δslot×1000`（每槽毫秒；停摆时巨大）。h+1:00 才算已知，下一根 1h 开盘入场。
- 核对：2024-02-06 14:00 UTC 停摆（Δt 21,016 秒、slow 2,714 ms）；2024-04 拥堵期跳槽率 17%–22%。体制变化须如实标注：跳槽率 2025 年起中位数只有约 0.1%；槽时长在 2026 年下半年分步下降（月中位数 2026-08 约 416 ms → 2026-09 约 315 ms，2026-09-18 起约 267 ms，2026-10-09 起约 215 ms；属协议变化），z 用滚动 168h 窗口吸收。
- 价格：OKX 官方 SOL / BTC USDT 永续 1h（`scratch/deep1h`，至 2026-11-27 19:00 UTC）；Gate 官方 SOL / BTC 永续 1h（批量下载 + v4 API，`scratch/bnblpool1h/px`，至 2026-11-28 01:00 UTC）；篮子稳健性用 d8 八币。

## 公式（预注册）
- `z_L = (最近 L 小时 x 之和 − L·μ) / (σ·√L)`，μ/σ 为该 L 小时块之前 168 小时（≥120 个有效值）。只做突发（z ≥ k，活性变差）。同一格持仓期间不再开新仓。
- 网格：series {skip, slow} × L {1, 4} × k {3, 4} × side {short, long} × H {12, 24, 48} × hedge {none, btc（同所反向等额 BTC）} = 96 格。
- 先验 `skip_L4_k3_short_H24_btc`（持续跳槽 = 活性 / 拥堵变差 → SOL 特有去风险，BTC 对冲隔离链自身成分）；回退 `slow_L1_k3_short_H24_btc`（槽变慢 / 局部停摆）。
- 费用：吃单 5.1 bps / 边 / 腿（真实），压力 15.1 bps；资金费未计（H ≤ 48h）。切分：deep 未见（→2024-10-21）/ test（→2026-03-05）/ post（≥2026-03-05）。评分 6 槽 = {OKX, Gate} × 三段均值 > 0；可用 = 6/6 且 OKX 每段 n ≥ 8。

## 结果（`output/research_solana_liveness_skiprate_event_1h.csv`，4,608 行；均值 bps / 笔，真实费）

| 格 | 得分 | OKX deep / test / post | Gate deep / test / post | OKX n | post t | 压力费 post（OKX / Gate） |
|---|---|---|---|---|---|---|
| **先验** skip_L4_k3_short_H24_btc | 2/6 | −48.8 / +4.1 / −15.2 | −49.0 / +4.0 / −15.4 | 133/108/56 | −0.7 | −55.2 / −55.4 |
| **回退** slow_L1_k3_short_H24_btc | 4/6 | −25.9 / +10.8 / +16.5 | −26.1 / +11.3 / +17.3 | 67/50/33 | 0.7 | −23.5 / −22.7 |
| 非先验 slow_L1_k4_short_H48_none | 6/6 | +14.7 / +198.0 / +150.8 | +15.9 / +197.3 / +151.2 | 21/18/10 | 1.3 | +130.8 / — |
| 非先验 skip_L1_k4_short_H24_none | 6/6 | +7.9 / +30.4 / +29.5 | +6.8 / +29.9 / +29.2 | 42/88/48 | 0.7 | +9.5 / — |
| 非先验 skip_L1_k3_short_H24_none | 6/6 | +2.9 / +31.0 / +27.9 | +2.2 / +31.0 / +27.9 | 89/121/67 | 0.8 | +7.9 / — |
| 非先验 slow_L1_k4_short_H24_btc | 6/6 | +14.1 / +30.7 / +7.1 | +15.4 / +30.9 / +7.9 | 26/20/10 | 0.2 | −32.9 / — |
| 非先验 skip_L1_k3_short_H24_btc | 6/6 | +1.0 / +1.0 / +4.6 | +0.6 / +1.1 / +4.5 | 89/121/67 | 0.2 | −35.4 / — |

- 得分分布：0/6 31 格、1/6 2、2/6 36、4/6 21、5/6 1、6/6 5（可用 5 格，全是非先验、全是做空 SOL）。
- 同脚本基线（每 24h / 48h 无条件做空 SOL，真实费）：H24 无对冲 deep −64.7 / test −7.8 / post −5.3；H48 −118.0 / −3.1 / −0.4；H24 BTC 对冲 −52.6 / −14.0 / −20.2。
- 安慰剂（日期平移，全网格 6/6 格数）：真实 5；+168h 2、−168h 4、+720h 3、**−720h 7（多于真实）**。逐格：skip_L1_k4_short_H24_none 的 +168h post +123.5（t 2.2）、skip_L1_k3 的 +168h post +80.5，都高于真实 post；slow_L1_k4_short_H48_none 的 −720h test +249.4 高于真实 test。
- 压力费：skip 系可用格 deep 段压力费为负（−12.1 / −17.1）；对冲格压力费三段全负。
- 邻域：slow_L1_k3_short_H48_none deep −123.9、slow_L4_k4_short_H48_none deep −74.6、skip_L1_k3_short_H48_none deep −134.4 —— 换 k / L / H 就翻负。8 币篮子替代 SOL：先验 −16.3 / −13.6 / −20.9。
- OKX 与 Gate 数字几乎一样（同一标的 SOL，价格高度一致），两所不是独立证据。

## 结论
- **否决**，不进观察名单、不改默认、不加纸面 / shadow，无代码改动。先验 2/6，压力费三段全负；回退 4/6，deep 段为负。5 个 6/6 格都是非先验做空 SOL 且无对冲（或对冲后接近 0），post t ≤ 1.3，压力费不稳，邻域翻负，日期平移安慰剂在格子数（−720h 7 > 5）和逐格 post 上都追平或超过真实。Solana 跳槽率 / 槽时长突发对 SOL 没有可重复的单笔优势；2025 年后跳槽率接近 0、2026 年下半年槽时长分步变化，信号的信息量还在继续下降。

## 不要重测（never-retest）
- 不要改 L / k / H / 方向 / 对冲 / z 窗口，不要在 skip ↔ slow ↔ blockHeight 增速 ↔ 每小时槽数之间换序列，不要改用交易数 / 非投票交易数 / TPS（`getRecentPerformanceSamples`）或投票交易占比，不要改成 SOL 篮子 / Solana 生态币（JUP、JTO、BONK 等）为标的，也不要换成其他 PoS 链（Sui、Aptos、Avalanche、Near 等）的出块活性 / 停摆来重测「链活性变差 → 该链代币」这一机制。真正的长时停摆（2021–2024 年约 7 次）样本太少，不要单独挑出来重测。
- 不需要实时记录器（`scratch/solprio1h/record.py` 已在记录同一官方样本）。

## 下一轮（长线）
- 选一个未测、官方历史覆盖 2024-10-21 / 2026-03-05 切分的 4h 默认书入场闸门（先查重 docs / 侧文档 / output / 记忆；勿提其它美国宏观）。
