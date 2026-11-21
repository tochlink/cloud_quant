<!-- Sidecar for docs/STRATEGY_FORMULAS.md (main file exceeds the GitHub connector 1MB push cap). A 2-line pointer was appended to the local STRATEGY_FORMULAS.md. -->

## 短线新族：官方 Aave V3 以太坊 Pool `LiquidationCall` 清算 1h 冲击 → 8 币永续篮子（1h，2026-11-20 ~21:55 PST，研究，不改默认；否决）

- 查重：文档、`output/research_*.csv` 与记忆里都没有搜到已完成的 Aave V3 清算事件族。已否决的「Aave V3 借款年化 4h 闸门」测的是利率，不是清算事件。已否决的 OKX 交易所强平 / OI / 主动买卖失衡 1h 微观结构是另一个场所。本族看的是链上 DeFi 借贷的强制清算：抵押品被强卖到 DEX。网格在看任何收益之前锁在 `scratch/aaveliq1h/PRE_REGISTER.json`（2026-11-20 21:40 PST，108 格）。
- 数据（只用官方合约在公共 RPC 上的 `eth_getLogs`，不用 subgraph / Dune / DefiLlama 等第三方聚合，不用美元金额，不编造、不回补）：
  - 官方合约：Aave V3 Ethereum Pool 代理 `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`（bgd-labs/aave-address-book `AaveV3Ethereum.sol` 的 `POOL`；`eth_getCode` 非空）。WETH `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`、wstETH `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` 取自同一地址簿。
  - 官方事件：`LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)`，ABI 取自 aave-dao/aave-v3-origin `IPool.sol`。topic0 本地 keccak 算出为 `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286`，与链上日志一致。
  - 第一条官方 LiquidationCall：块 16,521,648，2023-01-30 19:11:47 UTC（tx `0xf89d6869…`）。从该小时第一个块开始扫，首小时完整。用 6 个分片、多路公共 RPC 抓取，带检查点：pocket / tenderly / 0xrpc 为主，mevblocker / drpc 只作后备。研究用官方 1h 序列共 33,370 根完整小时，2023-01-30 19:00 → 2026-11-21 04:00 UTC。日历缺口 0，NaN 0，无游离小时。合计 29,008 笔清算（分片计数与 CSV 求和一致），零事件小时 29,247 根。某小时没有官方事件时记为真实零，不插值；不完整的当前 UTC 小时丢弃。
  - 序列：`n_liq`（清算笔数）、`n_users`（被清算的去重 user 数，合计 27,459）、`n_eth_coll`（抵押品为 WETH 或 wstETH 的清算笔数，合计 18,178 = WETH 16,314 + wstETH 1,864）。最大的几个小时：2026-02-05 15:00 UTC 683 笔，2025-04-07 06:00 UTC 653 笔，2024-08-05 01:00 UTC 531 笔。
  - 校验：用第二路官方 RPC（`https://eth.drpc.org`）重拉最近 7 个完整日（168 小时，块 26,410,989–26,461,242，478 笔），三个序列逐小时完全一致。另在 tenderly 上抽查历史小时（随机抽 + 最活跃小时，包括 2024-08-05 01:00 UTC：531 / 375 / 408），写文时已比对的 15 个小时全部一致、0 个不一致；剩余抽查仍在后台运行，结果写入 `scratch/aaveliq1h/spotcheck.log`。
- 公式（预注册，108 格）：x = `log1p(序列)`；`z_t = (x_t − mean(x_{t−L..t−1})) / sd(x_{t−L..t−1})`，滚动窗向后移 1，`min_periods = L/2`，sd=0 时记为 NaN。L = 168 / 720 小时，k = 2 / 3 / 4，持有 H = 12 / 24 / 48 小时，方向做多 / 做空。触发条件为已收盘小时 `z_t ≥ k`，在下一根 1h 永续开盘入场，持仓不重叠。交易标的是 OKX 默认 8 币（d8）、没调过参的另外 8 币（new8：LINK LTC DOT TRX BCH ATOM NEAR UNI），以及 Gate 默认 8 币（官方永续 1h 只从 2025-09-24 起有数据，所以 Gate 只有 post / gate_window 两段）。真实 taker 费每边 5.1 bps，压力费每边 15.1 bps，再加官方资金费。安慰剂：z 序列平移 ±720h。切分：train 为序列起点到 2024-10-21（深度未见），test 为 2024-10-21 到 2026-03-05，post 为 2026-03-05 起。计分沿用 eigenlayer1h 的 8 段口径。**锁定的经济先验**：清算突发 = 强制抛售 / 投降，之后做多篮子吃反弹。先验格为 `log_n_liq` L=720、k=3、long、H=24；做空一侧只算探索。
- 结果：CSV 共 3,456 行。8 段全为正的格有 3 个，样本都够，**全是非先验**；先验格不在其中。
  - **先验格** `log_n_liq_L720_k3_long_H24` 只有 6/8（数值为真实费下的每笔平均净 bps / t / 笔数 / 中位数 / 合计净收益）：
    - OKX d8：train +70.57 / t=2.69 / n=159 / 中位数 +49.7 / 合计 +112.2%；test +32.84 / 0.79 / 122 / +59.3 / +40.1%；post +9.45 / 0.28 / 77 / +5.1 / +7.3%。
    - OKX new8：train +62.88 / 2.26；test +33.69 / 0.71；post −1.47 / −0.05。
    - Gate d8：post +9.77 / 0.29 / 77；gate_window −1.63 / −0.05 / 111。
    - 压力费下 OKX d8 post −10.55、Gate post −10.23。
    - post 月度（OKX d8 每月净收益合计 > 0 才算赢）只有 4/9 个月：3、4、7、8 月为正，5、6、9、10、11 月为负。
    - 安慰剂：+720h 的 train 为 +38.0、test +18.3；−720h 的 test 为 +47.6，高于真格 test 的 +32.8。
    - 结论：边只在 train 明显，test / post 衰减到接近 0，打不过安慰剂。
  - 非先验的可用 8/8 格：
    - `log_n_eth_coll_L720_k4_long_H48`：OKX d8 train +86.3 / t=1.9 / n=89，test +27.2 / 0.4 / 67，post +61.9 / t=1.06 / 47 / 中位数 +10.8。Gate post +63.4 / t=1.09。post t 低于 1.5。−720h 安慰剂的 train +99.9、test +138.8、post +41.5，train 和 test 都高于真格。压力费下 test 只剩 +7.2 / t=0.11。
    - `log_n_eth_coll_L720_k4_long_H24`：post +18.6 / t=0.47，中位数 −5.5。
    - `log_n_eth_coll_L168_k4_long_H24`：train +7.1 / t=0.3，post +9.1 / t=0.29，中位数 −12.7。
  - 网格整体：真格中 OKX d8 三段全为正的有 18/108 格，全部是做多。安慰剂中，+720h 有 13 格、−720h 有 17 格三段全正，与真格相当。说明「做多三段为正」主要来自样本期篮子的多头漂移，不是清算信号本身。做空一侧最好只有 4/8，train / test 都为负。
  - 邻域（`log_n_liq` 做多，只改预注册的 L / k / H）：k=2 各档 post 都为负或接近 0（例如 L720 k2 H24 post −18.1）；L168 k3 三档 post 都为负；只有 k=4 一片 post 为正，但样本少，test 不稳（L720 k4 H24 test −3.8）。不是稳定的一片邻域。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例和应用代码。先验格 6/8，new8 post 与 Gate gate_window 为负；post t 只有 0.28；post 月度 4/9，没过 ≥6/9 的门槛；也打不过 ±720h 安慰剂。非先验的 3 个可用格 post t 都低于 1.5，中位数为负，或被安慰剂超过。每笔边远不够 1h taker 族结构上需要的大小。
- 勿重测：不要用换 L、k、H、方向的方式重测本族，也不要把 `n_liq` / `n_users` / `n_eth_coll` 对调，改用抵押品或债务资产的其它子集，改用美元金额或清算奖励，改用 Aave V2 / 其它链上的 Aave V3 Pool，或改成 4h 闸门来绕过「勿重测」。
- 现场记录：`scratch/aaveliq1h/record.py` 只读官方 Pool 的 LiquidationCall 日志，每过一个完整 UTC 小时就追加到 `output/aave_v3_liquidationcall_official_1h.csv` 与 `scratch/aaveliq1h/aave_v3_liquidationcall_official_1h.csv`（pid / 日志在 `scratch/aaveliq1h/record.{pid,log}`）。不写 `data/micro.sqlite`，不打断其它记录进程。
- CSV（不入库）：`output/research_aave_v3_liquidation_shock_event_1h.csv`（3,456 行，含 108 个预注册格 × 真实 / 压力费 × 真实 / ±720h 安慰剂）；官方 1h 序列 `output/aave_v3_liquidationcall_official_1h.csv`（研究当时 33,370 小时）。脚本在 `scratch/aaveliq1h/{fetch,run,analyze,record,spotcheck}.py`。
- 下一轮（短线）：官方以太坊主网 Morpho Blue 的 `Liquidate` 事件。若官方历史不够 2026-03-05 切分，就改用官方 Compound V3 Comet 的 `AbsorbCollateral` / `AbsorbDebt`。不过本族已经说明，「借贷清算突发 → 做多反弹」在 test / post 没有边。如果换协议重测同一机制，只能算同机制复核，不能另起一族；更好的下一轮是另选一个没测过、官方历史够长、单笔边结构上更大的短线机制。
