<!-- Sidecar for docs/STRATEGY_FORMULAS.md (main file exceeds the GitHub connector 1MB push cap). A 2-line pointer was appended to the local STRATEGY_FORMULAS.md. -->

## 短线新族：官方以太坊主网闪电贷（Aave V2 / Aave V3 / Balancer V2 `FlashLoan`）1h 突发 → 8 币永续篮子（1h，2026-11-21 ~11:25 PST，研究，不改默认；否决）

- 查重：文档、`output/research_*.csv` 与记忆里都没有闪电贷事件族。已否决的 Aave V3 `LiquidationCall` 清算冲击、Curve 3pool 失衡、Uniswap 冲击、WETH9 包装/解包冲击都是别的事件。网格在看任何收益之前锁在 `scratch/flashloan1h/PRE_REGISTER.json`（2026-11-21 11:10 PST，216 格，sha256 `5b849c712a6213041cf4253521becd4ed0056ac972381219541af25d270eaaf9`；格清单另存 `output/research_flashloan_burst_event_1h_prereg.csv`）。
- 数据（只用官方合约在公共 RPC 上的 `eth_getLogs`，不用 subgraph / Dune / DefiLlama，不用美元金额，不编造、不回补）：
  - 官方合约（`eth_getCode` 均非空）：Aave V2 LendingPool `0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9`；Aave V3 Pool `0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`；Balancer V2 Vault `0xBA12222222228d8Ba445958a75a0704d566BF2C8`。
  - 官方事件与 topic0（本地 keccak256 规范签名算出并断言；在每个合约上抽取链上日志按 ABI 解码一致）：
    - Aave V2 `FlashLoan(address indexed target, address indexed initiator, address indexed asset, uint256 amount, uint256 premium, uint16 referralCode)` → `0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac`
    - Aave V3 `FlashLoan(address indexed target, address initiator, address indexed asset, uint256 amount, uint8 interestRateMode, uint256 premium, uint16 indexed referralCode)` → `0xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0`（样本：topic1 target、topic2 WETH、topic3 referral；data = initiator / amount / mode / premium）
    - Balancer V2 `FlashLoan(address indexed recipient, address indexed token, uint256 amount, uint256 feeAmount)` → `0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0`（样本：topic1 recipient、topic2 USDT；data = amount / fee）
  - 第一条官方 Aave V2 FlashLoan：块 11,375,154，2020-12-02 19:59:55 UTC。从该小时第一个块开始扫，首小时完整。Balancer V2 首笔闪电贷在 2021-10-26 21:00 UTC 小时，Aave V3 首笔在 2023-01-27 12:00 UTC 小时；之前的零是真实零（合约无此事件）。12 个分片、多路公共 RPC（tenderly / 0xrpc / pocket 为主，mevblocker / drpc 后备）带检查点抓取，`(tx, logIndex)` 去重。
  - 官方 1h 序列：52,320 根完整小时，2020-12-02 19:00 → 2026-11-21 18:00 UTC，日历缺口 0，游离小时 0，NaN 0；不完整的当前 UTC 小时丢弃。合计 1,347,192 条 FlashLoan（分片计数与 CSV 求和一致）：Aave V2 48,138、Aave V3 185,965、Balancer V2 1,113,089；去重交易 1,282,510。零事件小时 4,176 根。post 段（2026-03-05 起）每小时中位数 47 条；最大小时 2026-03-22 03:00 UTC 6,843 条。
  - 校验：第二路官方 RPC（`https://eth.drpc.org`）重拉最近 7 个完整日（168 小时，块 26,415,174–26,465,427，8,745 条），`n_total / n_aave / n_bal / n_tx / n_init` 逐小时完全一致。
  - 序列：`n_total = n_v2 + n_v3 + n_bal`（每个借出资产一条事件），`n_aave = n_v2 + n_v3`，`n_bal`；另记录但不计分：`n_v2`、`n_v3`、`n_tx`（去重交易数）、`n_init`（去重发起方：V2 topic2 initiator、V3 data initiator、Balancer recipient）。
- 公式（预注册，216 格）：x = `log1p(序列)`；`z_t = (x_t − mean(x_{t−L..t−1})) / sd(x_{t−L..t−1})`，滚动 L 小时向后移 1，`min_periods = L/2`，sd=0 记 NaN。小时 h 的数据从 h+1 开盘起才可用：信号小时收盘后在下一根 1h 永续开盘进场，持有 H 小时，不重叠。序列 {n_total, n_aave, n_bal} × L {96, 168} 小时（4 / 7 天）× k {2, 3, 4} × 触发 {burst: z≥k；twosided: |z|≥k} × 模式 {mom, contra} × H {12, 24, 48}。burst：mom = 做多篮子、contra = 做空；twosided：方向 = sign(z) × (mom +1 / contra −1)。
  - 锁定的经济先验：闪电贷突发 = 套利 / 清算 / 攻击活动、DeFi 压力 → **做空** 8 币篮子。先验格 `log_n_total_L168_k3_burst_contra_H24`；后备格 `log_n_aave_L168_k3_burst_contra_H24`。
  - 回测（与 aaveliq1h / eigenlayer1h 同一套脚本）：OKX 官方 1h 永续 d8（BTC ETH BNB SOL XRP ADA DOGE AVAX）、未调参 OKX new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）、Gate 官方 1h d8；真实吃单费 5.1 bps/边，压力 15.1 bps/边，计入官方资金费。切分：train（深度未见，序列起点 → 2024-10-21）、test（→ 2026-03-05）、post（2026-03-05 → 末尾）、gate_window（2025-09-28 → 末尾）。8 段计分（OKX d8 三段、new8 三段、Gate post / gate_window），可用 8/8 要求 8 段均值都 > 0 且 OKX d8 笔数 train ≥ 10、test ≥ 8、post ≥ 8。安慰剂：z 平移 ±720h（全网格），先验 / 后备另加 ±168 / ±336 / ±2160h 与邻域（k 2.5 / 3.5，L 120 / 336 / 720，H 18 / 36）。
- 结果：结果 CSV 6,912 行。216 格中 8/8 只有 1 格且**不是先验**。
  - **先验格** `log_n_total_L168_k3_burst_contra_H24` 只有 5/8（真实费下每笔平均净 bps / t / 笔数 / 中位数）：
    - OKX d8：train −36.0 / t=−0.64 / n=61 / −31.3；test +5.3 / 0.09 / 41 / +77.4；post +11.4 / 0.29 / 26 / +31.8。
    - OKX new8：train −27.0；test +27.2；post −0.0。
    - Gate d8：post +11.1 / t=0.28 / 26；gate_window +58.0 / t=1.31 / 36。
    - 压力费：OKX d8 train −56.0、test −14.7、post −8.6；Gate post −8.9。
    - post 月度（每月净收益合计 > 0 才算赢）：OKX 5/9、Gate 5/9（3、4、6、7、11 月为正，5、8、9、10 月为负）。
    - 安慰剂：+720h train/test/post = −0.6 / −49.3 / +18.1（post 高于真格）；−2160h 的 post +40.9、gate_window +141.7，都高于真格。
    - 邻域：L120 post +48.1、H36 +43.5、k3.5 +31.7，但 train 全部为负（−48 ~ −63），k2.5 / L336 / L720 post 为负。深度未见段整片无边。
  - **后备格** `log_n_aave_L168_k3_burst_contra_H24` 4/8：train +66.3 / t=1.31 / 73，test +75.6 / 0.88 / 19，但 post −164.8 / t=−1.27 / 10，new8 post −195.6，Gate post −165.7；月度 2/9。
  - 唯一可用 8/8（非先验）`log_n_bal_L96_k3_twosided_contra_H48`：OKX d8 train +21.5 / t=0.5 / 130，test +10.0 / 0.2 / 77，post +27.7 / 0.5 / 34（中位数 +32.5）；new8 +15.2 / +18.2 / +14.8；Gate post +27.2 / t=0.54，gate_window +94.0 / 54。post 月度 4/9（OKX、Gate 同）。压力费下 OKX test −10.0、new8 三段全负。−720h 安慰剂 train/test/post = +81.8 / +22.6 / +40.6，全部高于真格。连观察名单都不够。
  - 网格整体：真格 OKX d8 三段全正 6/216；安慰剂 +720h 有 20 格、−720h 有 22 格，比真格还多。信号整体不比时间平移的假信号好。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例与应用代码。先验格深度未见为负、post t 仅 0.29、月度 5/9 未过 ≥6/9，被安慰剂超过；后备格 post 大幅为负；唯一 8/8 非先验格 t 全 < 0.6、月度 4/9、打不过 −720h 安慰剂。
- 勿重测：不要用换 L、k、H、触发方式（burst / twosided）、方向（mom / contra）的方式重测本族，也不要在 `n_total` / `n_aave` / `n_bal` / `n_v2` / `n_v3` / `n_tx` / `n_init` 之间对调，改换协议（只用 Aave、只用 Balancer、加 Uniswap flash swap / dYdX / Maker flash mint / Morpho 等），改用美元金额或手续费，或改成 4h 闸门来绕过本条。
- 现场记录：`scratch/flashloan1h/record.py` 只读这三个官方合约的 FlashLoan 日志，每过一个完整 UTC 小时追加到 `output/flashloan_official_1h.csv` 与 `scratch/flashloan1h/flashloan_official_1h.csv`（pid / 日志在 `scratch/flashloan1h/record.{pid,log}`）；不回补、不改写已有小时、丢弃当前未完成小时。
- CSV（不入库）：`output/research_flashloan_burst_event_1h.csv`（216 格 × 3 宇宙 × 真实 / 压力费 + ±720h 安慰剂）、`output/research_flashloan_burst_event_1h_prereg.csv`、`output/research_flashloan_burst_event_1h_nbhd_placebo.csv`；官方 1h 序列 `output/flashloan_official_1h.csv`（研究当时 52,320 小时）。脚本在 `scratch/flashloan1h/{fetch,run,analyze,extra,record,prereg}.py`。
