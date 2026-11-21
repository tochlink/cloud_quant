# Tornado Cash 官方 ETH 池 Deposit / Withdrawal 1h 突发 → 8 币永续篮子（研究记录，否决）

> 侧车文档：本地与远端 STRATEGY_FORMULAS.md 已分叉；本节同时追加到远端 STRATEGY_FORMULAS.md 末尾。
## 短线：Tornado Cash 以太坊主网官方 ETH 池 Deposit / Withdrawal 1h 突发 → 8 币永续篮子（2026-11-21，否决）

- 背景：上节「下一轮（短线）」所列。机制 = 黑客 / 洗钱资金进出混币器（攻击后集中存入、随后提出砸盘）= 安全事件资金流。本地与远端文档、output 中此前 Tornado 0 条，不是重复。
- 数据（全部官方链上，`output/tornado_cash_official_1h.csv`）：tornadocash/tornado-cli `config.js` netId1 的 4 个 ETH 实例——0.1 ETH `0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc`（部署块 9,116,966）、1 ETH `0x47CE0C6eD5B0Ce3d3A51fdb1C52DC66a7c3c2936`（9,117,609）、10 ETH `0x910Cbd523D972eb0a6f4cAe4618aD62622b39DbF`（9,117,720）、100 ETH `0xA160cdAB225685dA1d56aa342Ad8841c3b53f291`（9,161,895）；链上校验：`denomination()` = 0.1/1/10/100 ETH（3 个 RPC 一致；tenderly 对制裁地址拒绝 eth_call 但 getLogs 正常），部署块前无代码。事件 `Deposit(bytes32 indexed,uint32,uint256)` topic0 `0xa945e51e…f196`、`Withdrawal(address,bytes32,address indexed,uint256)` topic0 `0xe9e508ba…4931`（本地 keccak，链上命中）。公共 RPC `eth_getLogs`（tenderly / mevblocker / blockpi / 0xrpc）全量重建区块 9,116,966–26,463,893，50k 块分片检查点 `scratch/tornado1h/ck/`。
  - 596,959 条日志 = 306,514 Deposit + 290,445 Withdrawal。**完整性**：4 个池 leafIndex 均严格 0..N−1 连续（0.1: 77,427；1: 98,286；10: 80,298；100: 50,503）；终点块 `eth_getBalance` = 面额 ×(存−取) 逐池 **差 0 wei**（659.4 / 4,279 / 23,740 / 282,200 ETH）；随机 12 小时用 blockpi 按时间二分区块独立重拉 **12/12 一致**。
  - 完整 UTC 小时 **2019-12-16 20:00 → 2026-11-21 12:00 共 60,761 小时，0 缺口，不补值**（无事件小时为真实 0；当前未完成小时丢弃）。
  - 事件量（存款笔数 / 存款 ETH）：2020 25,454 / 57.6 万；2021 73,631 / 178.8 万；2022 55,813 / 123.3 万；2023 16,582 / 34.2 万；2024 17,210 / 50.6 万；2025 43,211 / 71.0 万；2026（至 11-21）73,120 / 80.1 万。2022-08 OFAC 制裁后 2023–24 降到约 1/4（零存款小时约 50%），但 2025–26 已回升到接近 2021 水平；**事件数充足**（先验格 OKX train/test/post 触发 173/88/37 次）。
  - 时滞：小时 h 的链上值在 h 收盘后才用，h+1 根 1h 永续开盘入场。
- 公式（`scratch/tornado1h/PRE_REGISTER.csv` sha256 `b0ae5795…943de`，看任何 PnL 前、拉数尚未完成时锁定 216 格；副本 `output/research_tornado_cash_burst_event_1h_prereg.csv`）：
  - 序列：log_dep_eth = log1p(本小时 4 池存入 ETH)；log_wd_eth = log1p(本小时 4 池提出 ETH，按面额毛额)；log_dep_big = log1p(本小时 10 + 100 ETH 池存入 ETH，攻击赃款量级)。
  - z：W = 168h 滚动均值 / 标准差截至 t−1（min 84）；L=1 时 z=(x−μ)/σ，L>1 时 z=(Σ_L x − Lμ)/(σ√L)；z ≥ k 触发，下一根 1h 开盘入场，持有 H，不重叠。
  - 网格：3 序列 × L{1,4,8} × k{3,4,5} × 方向{long, short} × H{6,12,24,48} = 216 格（只做高侧突发）。short = 顺势（安全事件 → 风险厌恶、赃款后续砸盘），long = 逆势。
  - **唯一先验 `log_dep_big_L4_k3_high_short_H24`**；回退 `log_wd_eth_L4_k3_high_short_H24`。
  - harness 与 curve3pool1h / aaveliq1h 相同：OKX d8 深历史 1h（train 2022-02-15→2024-10-21 = 深未见；test →2026-03-05；post →末尾）、Gate d8 官方 1h（post + gate_window 2025-09-28→）、未调参 OKX new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）；真实永续 taker 5.1 bps/边（不假设 maker 2 bps），压力 15.1 bps/边；官方资金费；±720h 时移安慰剂（OKX + Gate）；额外 ±168/±336/±2160h 安慰剂与邻域（k 2.5/3.5、W 336/720、L 2/6、H 18/36）；同脚本逐小时基线（同方向同 H）。2019-12→2022-02 只作 z 预热（无官方 1h 永续）。
- 结果（真实费，每笔篮子净 bps）：
  - 216 格无一可用 8/8（0 usable；仅 2 格 8/8 但 post 只有 1 笔）；log_wd_eth L1 k5 全期 0 触发。所有 short 格 OKX 平均 train −12.3 / test −33.4 / post −13.0，long 格 −8.1 / +13.0 / −7.4。
  - **先验** log_dep_big L4 k3 short H24：0/8。OKX train −11.3（t −0.40，n 173）/ test −41.2（t −1.08，n 88）/ post −17.8（t −0.37，n 37，中位 −53）；Gate post −18.3、gate_window −66.2；new8 −4.2 / −16.8 / −59.6；压力费 OKX −31 / −61 / −38。同脚本基线（逐小时 short H24）train −15.7 / test −14.8 / post −0.8：test、post 均劣于基线。post 逐月：事件均值 > 基线 5/9（两所相同），月和 >0 7/9 但被 2026-09 单月 −2,215 bps 吞掉。±720h 安慰剂 post +4.8 / +17.0（都比先验好）。邻域乱：k3.5 post −24、L6 +18.7、H18 −51.7、W336 −9.8。
  - **回退** log_wd_eth L4 k3 short H24：6/8。OKX train −30.5（t −0.91，n 126，劣于基线 −15.7）/ test +12.9（t 0.22，n 57）/ post +74.6（t 1.75，n 22，中位 +38）；Gate post +73.6（t 1.73）、gate_window +67.9；new8 −11.8 / +31.4 / +34.4；压力费 post +54.6。post 逐月：事件均值 > 基线 6/9（两所），但月和 >0 仅 5/9（11 月无交易）。安慰剂 −168h post +122.8、−2160h +84.4、−336h +43.8 —— post 优势并非事件特有；深未见为负；邻域 H18 +10、W720 +4.7、k2.5 +38 断崖。
  - 最好的非先验 7/8（log_dep_big L4 k4 short H24/H48）post 只有 9 笔、test 为负；log_dep_big L8 k3 short H48 post +93（t 1.5，n 32）但 test −45。每笔优势不够结构性大，1h taker 族典型形态。
- 结论：**否决**。先验三段全负且劣于同脚本基线与安慰剂；回退深未见为负、post 优势被时移安慰剂复现；无可用 8/8。不改默认、不动纸面盘、不改代码。**勿以改 L / k / H / W / 方向、换序列（笔数 / 净流 / 只 100 ETH 池 / 只 0.1 池 / relayer 费 / 唯一提款地址）、加入 DAI / USDC / WBTC 等 ERC20 实例或其他链 Tornado、或改用 USD 计价的方式在现有历史上重测本族。**
- 文件：`output/tornado_cash_official_1h.csv`、`output/research_tornado_cash_burst_event_1h.csv`、`_prereg.csv`、`_nbhd_placebo.csv`（new8 已在主表 universe=okx_new8 内；均不入库）；脚本 `scratch/tornado1h/{fetch,build,verify,prereg,run,analyze,baseline,extra}.py`（未推送）。
- 下一轮（长线）：Liquity v1 以太坊主网官方合约（TroveManager / ActivePool / StabilityPool）日度系统抵押 ETH、LUSD 债务与系统抵押率 TCR → 4h 默认书入场闸门。机制 = 链上 ETH 抵押借贷杠杆需求（TCR 下降 / 债务扩张 = 加杠杆做多 ETH，过热拦新多）；不是已否决的 Aave V3 借款 APR 闸门、Sky SSR/DSR、稳定币供给或交易所融资余额；文档 / output 中 Liquity / LUSD / Trove 0 条。数据只用官方事件 + archive eth_call，2021-04 起。
