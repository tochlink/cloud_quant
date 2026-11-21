# 短线新族：Uniswap v3 ETH/USDC 官方 LP 流动性增减（Mint / Burn）冲击 → 8 币永续篮子（1h）

> 侧记（2026-11-21 ~13:40 PST）。研究，不改默认；**否决**。

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、`output/research_*.csv`（1,229 个文件）、记忆中无 Uniswap LP 流动性 Mint / Burn、IncreaseLiquidity / DecreaseLiquidity、LP 撤出条目。已否决的 Uniswap v3 ETH/USDC 族测的是 **Swap 成交额 / 手续费（需求侧）**，其「勿重测」限制换 L/k/H/方向、vol↔fee、单费率档、其它池、v2/其它 DEX 成交；本轮是 **LP 集中流动性供给侧**（做市商加 / 撤流动性），是新机制。也不是 Curve 3pool 稳定币池构成（其勿重测里的「LP 增减」指 Curve 稳定币池）、DefiLlama TVL 闸门、gas / MEV / Lido / WETH9。任务候选里的 ETH base-fee/gas、Lido WithdrawalQueue、Uniswap v3 大额 Swap、BTC 出块间隔 / 手续费 四个都已测过（eth_gas_fullness / eth_blob_basefee、lido_wq_burst、uniswap_v3_ethusdc_shock、btc_block_interval_empty / btc_onchain_fee_shock），故改测本族。
- 数据（只用官方以太坊主网链上，不用 subgraph / Dune / DefiLlama，不编造、不插值、不回补）：官方工厂 `0x1F98431c…F984` 的 `getPool(USDC, WETH, fee)` + PoolCreated 核对过的两池：0.05% `0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640`、0.3% `0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8`（token0 USDC 6 位，token1 WETH 18 位）。公共 RPC（tenderly / pocket / mevblocker）`eth_getLogs` 抓官方 `Mint(address,address,int24,int24,uint128,uint256,uint256)` topic0 `0x7a53080b…` 与 `Burn(address,int24,int24,uint128,uint256,uint256)` topic0 `0x0c396cd9…`，时间用日志 blockTimestamp。区块 12,370,624 → 头块 −64 全覆盖（282 段、无缺段），715,734 条日志（Burn 380,390 / Mint 335,344）。
  - 预注册过滤：流动性为 0 的 Burn（NonfungiblePositionManager collect 前的手续费结算「戳」）剔除 100,289 条；同一 (区块, owner, tickLower, tickUpper) 既 Mint 又 Burn 的即时（JIT）MEV 流动性两侧都剔除 190,989 条（占原始 USDC 腿 96.5%）。
  - 估值（全链上）：区间内的 Mint / Burn 可精确反推池价：√Pc = amount1_raw / L + 1.0001^(tickLower/2)，ETH 美元价 = 1e12 / Pc；每小时取中位数，无观测小时沿用上一已知价（只用于估值，因果）。USD = amount0/1e6 + amount1/1e18 × P_h。与 OKX ETH 永续 1h 收盘对比：42,161 小时绝对偏差中位数 0.18%、99 分位 1.9%。
  - 小时序列 `output/univ3_lp_official_1h.csv`：2021-05-05 00:00 → 2026-11-21 20:00 UTC 共 48,645 小时，0 日历缺口，2 无效（首个价格观测前）；无 Mint/Burn 的 2,085 小时 = 真实零。当前未完成小时丢弃。
- 公式：net_burn = asinh((burn_usd − mint_usd)/1e6)（正 = LP 净撤出）；log_burn = log1p(burn_usd)；log_mint = log1p(mint_usd)。z：L=1 为 (x−μ)/σ，L>1 为 (Σ_L x − Lμ)/(σ√L)，μ/σ 为截至 h−1 的 168h 滚动（min 84）。信号小时收盘后**下一根 1h 永续开盘入场**，持有 H 根，不重叠，8 币等权；成本 taker 5.1 bps/边（压力 15.1）+ 官方资金费（与 curve3pool1h / eigenlayer1h 同一框架）。
- 预注册（`scratch/univ3lp1h/PRE_REGISTER.json`，sha256 `f3a7f697e2a2d2d6…`，任何 PnL 前锁定 432 格）：metric {net_burn, log_burn, log_mint} × L {1,4,8} × k {3,4,5} × {high z≥k, low z≤−k} × {long, short} × H {6,12,24,48}。**先验** `net_burn_L4_k3_high_short_H24`（4h LP 集中净撤出 = 老练做市商在逆向波动前降风险 → 次日做空篮子）；**回退** `log_burn_L1_k3_high_short_H24`。切分 train 2022-02-15 → 2024-10-21（深度未见段）、test → 2026-03-05、post → 今；Gate 自 2025-09-28；OKX new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI）未调参；安慰剂 z 平移 ±720h；post 月份对照同脚本每小时做空 H24 基线。
- 结果（真实费，每笔净 bps；`output/research_univ3_lp_liquidity_shock_event_1h.csv` 17,280 行；352 格有事件）：

| 格 | OKX d8 train（深未见） | OKX d8 test | OKX d8 post | OKX new8 train / test / post | Gate d8 post / gate_window | 安慰剂 OKX post +720h / −720h | 压力费 OKX post |
|---|---|---|---|---|---|---|---|
| 先验 net_burn L4 k3 high short H24 | −2.4（n=72，t −0.06） | **−95.3**（n=57，t −1.95） | +18.1（n=31，t 0.35） | +18.7 / −82.7 / +4.0 | +17.0（t 0.33）/ −25.9 | −13.5 / **+35.6** | −1.9 |
| 回退 log_burn L1 k3 high short H24 | 0 笔 | 0 笔 | 0 笔 | 0 / 0 / 0 | 0 / 0 | — | — |
| 最好非先验 net_burn L4 k4 low long H48 | +110.9（n=12，t 1.29） | +128.8（n=28，t 1.58） | +133.4（n=20，t 0.92） | +53.8 / +101.4 / +154.1 | +134.7（t 0.93）/ +127.1 | −61.9 / −8.5 | +113.4 |

  - 先验 4/8：test 两所都大亏（OKX −95.3、Gate −92.5、new8 −82.7），post 仅 +18 且 t 0.35；post 月份正 6/9，但事件均值好于同脚本做空基线只有 **5/9**（两所相同）；−720h 安慰剂 post +35.6 好于真实；压力费 post 转负；邻域 L4k5 −71.6、L8k4 −92.0、L8k5 −133.6。否决。
  - 回退：log1p 后 13.9% 零 Burn 小时把上尾压扁，L=1 的 z 全样本最大 3.14、≥3 只有 2 次（均在 2022-02 前），train/test/post **0 笔**，不可测即失败（按规则不换格）。
  - 全网格 usable 8/8 = 8（都非先验，7 个做多），post t 全部 ≤ 1.0。最好 `net_burn_L4_k4_low_long_H48`（LP 净加流动性突发 → 做多）：train 只有 12 笔；邻域不稳（同侧 H=24 post −0.1、L4k3 H24 −35.7、L1k3 H24 −33.6、L8k4 H24 −86.5，只在 H48 / 部分 H6 为正）。安慰剂：真实 352 格中 35 格（9.9%）在 OKX/Gate 五段全正，±720h 平移 704 格中 39 格（5.5%），超额有限。
- 结论：**否决**，不实现、不进观察名单、不加纸面影子子书、不改默认、无代码改动，仅文档。LP 撤出 → 做空的先验在 2024-10 后（test）显著反向、post 接近零且不如安慰剂；能 8/8 的格子都是「LP 净加 → 做多」的长持有，post t < 1、邻域在 H 上断开，更像偏多行情里的方向暴露。
- 勿重测（never retest）：不要用换 L / k / H / 方向 / high↔low、对调 net_burn / log_burn / log_mint、改笔数或流动性单位 L、改 JIT 过滤或保留 JIT、只用单一费率档、换 Uniswap 其它池（WBTC/ETH、稳定币池、L2 池）、换 v4 / Sushi / 其它 DEX 的 LP 增减、换 tick 区间宽度 / 区间内流动性、更早起点的方式重测本族。
- 文件：`output/research_univ3_lp_liquidity_shock_event_1h.csv`、`output/univ3_lp_official_1h.csv`（不入库）；脚本 `scratch/univ3lp1h/{fetch,build,run,analyze,baseline}.py`、PRE_REGISTER.json（研究脚本未推送）。官方历史已 5.5 年，未另起实时记录器。
- 纸面：8788/8789/8792/8793 /api/health 全 OK；2026-11-21 13:21 PST 以来四本均无新成交，与回测预期一致（无信号翻转）。
- 下一轮（长线）：NAAIM 官方每周 Exposure Index（naaim.org，2006 起，每周三公布）水平 / z / 趋势 → 4h 默认书入场闸门（经理满仓 → 拦新多），按公布次日滞后入场；docs / output 中 0 条已完成测试（若官方免费历史不全，改 AAII 每周情绪调查）。
