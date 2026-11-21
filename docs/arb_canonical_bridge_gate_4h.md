# 长线新族：官方 Arbitrum One 以太坊主网规范桥净 ETH 入金与官方延迟收件箱 / L1 网关流量 → 4h 默认书入场闸门（2026-11-20 ~18:50 PST，研究，不改默认；否决）

主文件 docs/STRATEGY_FORMULAS.md 已超过 GitHub 连接器 1MB 推送上限，本页是本轮完整记录。本地主文件末尾有同名短指针。

- 查重：文档 / output/research_*.csv / 记忆中无完成的 Arbitrum One 规范桥 / Delayed Inbox / 官方 L1 网关 4h 闸门。这是 L1→L2 官方桥需求，不是已否决的 WETH9 包装/拆包冲击、ENS 注册热度、LST 供给/年化、MEV-Boost 集中度、Aave 借款年化或稳定币供给。
- 机制（看任何 PnL 之前锁定，回测中不增格、不改公式、不翻转先验）：官方以太坊主网 Arbitrum One 规范桥净 ETH 入金，以及官方 Delayed Inbox / 三个 L1 网关用户流次数，作为 4h 默认书入场闸门（只拦新开仓，已有同向仓保留）。官方日 D 的值于 D+1 01:00 UTC 才使用，不前视。无事件日 / 零净流入记 0，不插值、不回补。
- 官方合约（docs.arbitrum.io contract-addresses；Classic Old Bridge 是 Nitro 之前同一延迟收件箱的官方 ETH 托管，Nitro 迁移时余额进入文档中的 Nitro Bridge，合并托管连续，迁移不是用户流）：
  - Delayed Inbox 0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f
  - Nitro Bridge 0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a
  - Classic Old Bridge 0x011B6E24FfB0B5f5fCc564cf4183C5BBBc96D515
  - L1 ERC20 Gateway 0xa3A7B6F88361F48403514059F1F16C8E78d60EeC
  - L1 Custom Gateway 0xcEe284F754E854890e311e3280b767F80797180d
  - L1 WETH Gateway 0xd92023E9d9911199a6711321D1277285e6d4e2db
- 预注册序列（最多 3 条主序列，120 格）：
  - eth_net：官方当日合并托管（Old Bridge ETH + Nitro Bridge ETH）相对前一 UTC EOD 的差额，单位 ETH。首个完整日需要前一日 EOD 作基数。
  - n_inbox：官方当日 Delayed Inbox InboxMessageDelivered 次数。
  - n_gw：官方当日三个 L1 网关 DepositInitiated + WithdrawalFinalized 次数（不计代币金额，不编汇率）。
  - 额外 CSV 列（不是主序列）：Nitro 风格 52 字节 inbox ETH 存款笔数/数量、EOD 托管水平、网关存/取分项。Classic 载荷不是 52 字节 Nitro 式 ETH 存款，故不把毛 ETH 入金当作主序列。
- 格子：trend n 取 30/90/180；chg n 取 30/90；z365 k 取 1.0/1.5/2.0；五侧 long_off / short_off / both / contra_both / cap_short_off。三序列 × 8 种 × 5 侧 = 120 格，全部在 PRE_REGISTER.json / run.py 的 VARS 中、看任何 PnL 之前锁定（2026-11-20 17:43 PST）。
- 经济先验（看结果前锁定，不翻转）：官方规范桥净 ETH 入金或官方延迟收件箱 / 代币网关流量偏高或上升 = 建设性资金部署与 L2 需求（risk-on）→ 先验侧为 cap_short_off 与 contra_both（指标“高”时拦新开空；contra_both 在高位只许新开多、低位只许新开空）。long_off / short_off / both 为非先验探索。预注册回退先验格：eth_net_trend_n90_cap_short_off。
- 数据：只用官方以太坊主网 RPC 的合约日志与 EOD eth_getBalance，无 Dune / 非官方 subgraph、无编造、无回补。1945 个完整 UTC 日 2021-07-25→2026-11-20，日历缺口 0；EOD 块均在 UTC 午夜前 180 秒内。eth_net 首个有值日 2021-07-26（地板日无前一日托管）。官方零活动日是真零不是缺失：n_inbox 10 日、n_gw 34 日、eth_net 12 日。合计官方事件：Delayed Inbox 1,986,264 条，三个 L1 网关 301,592 条。最近一日（2026-11-20）合并托管 780,921.545851 ETH（已全部在 Nitro Bridge）。二次官方 RPC 核对最近 7 个完整日：托管 wei 完全一致，n_inbox 1,675=1,675，n_gw 1,012=1,012。
- 回测：同一脚本基线，官方 OKX / Gate 永续（不用现货蜡烛替代），真实费率，切分 deep unseen / tune_pre（2024-10-21）/ post（2026-03-05→2026-11-14），三本账 okx d8、gate d8、okx d7_noBNB。9 段 Sharpe 胜场相对同脚本基线。安慰剂为同一格子日历平移 +180 / −120 / +365 / −119 以及稳健性 ±7 / ±14 日。邻域只改预注册的 n，不升主榜。压力费 spot taker 20 / perp taker 15.1 bps。
- 结果（output/research_arb_canonical_bridge_gate_4h.csv，441 行）：
  - 基线：OKX d8 post +59.90 / Sharpe 2.23 / n=439；Gate d8 post +60.32 / 2.25 / 524；OKX d7_noBNB post +50.76 / 2.10 / 521。
  - 真实 120 格：9/9 仅 1 个、8/9 仅 1 个、没有 7/9、6/9 有 7 个。达到 watch-like（至少 6/9 且 okx/gate d8 的 post 收益不低于基线）的格里，先验最高是 9/9。
  - 唯一 9/9 是先验格 eth_net_trend_n180_cap_short_off（occupancy：deep 0.613、tune 0.814、post 0.693）。OKX d8 post +60.46 vs 基线 +59.90、Sharpe 2.26 vs 2.23、月份 5/4、deep +43.19 / 0.84 vs +35.14 / 0.71、tune +112.17 / 1.71 vs +85.08 / 1.47、n=394；Gate d8 post +61.55 vs +60.32、Sharpe 2.29 vs 2.25、月份 5/4、deep +3.23 / 0.18 vs −3.63 / 0.09、tune +103.48 / 1.64 vs +84.25 / 1.46、n=477；OKX d7_noBNB post +54.55 vs +50.76、Sharpe 2.19 vs 2.10、月份 5/4、deep +54.95 / 0.79 vs +54.92 / 0.75、tune +108.35 / 1.73 vs +92.93 / 1.56、n=481。三段 Sharpe 都赢基线，但 post 边很薄（两所 d8 大约 +0.56 / +1.23 个百分点、Sharpe +0.03 / +0.04），后段月份只有 5 胜 4 负，达不到改默认所需的两所至少 6/9 个月。
  - 预注册回退格 eth_net_trend_n90_cap_short_off 是 6/9：post 与 n=180 几乎相同，但三段未见历史（deep）的 Sharpe 全输给基线（OKX d8 0.56 vs 0.71，Gate −0.07 vs 0.09，d7 0.58 vs 0.75）。不能当作“持有未见历史”的先验格。
  - 唯一 8/9 是非先验 n_gw_trend_n30_short_off：post 边同样很薄，月份 4/5，OKX d8 deep Sharpe 还略低于基线（0.70 vs 0.71）。不按非先验格改默认或进观察。
  - 其它 6/9 要么是非先验 short_off / long_off（若干 deep 绝对收益为负或低于基线），要么是先验 n_inbox_trend_n30_contra_both（tune Sharpe 从约 1.47 掉到约 1.09）。
  - z365 格占用极低（eth_net z>2.0 在 post 窗口占用 0），多数只是几乎永不触发，贴近基线。
  - 安慰剂（锚点 eth_net_trend_n180_cap_short_off）：最高只有 4/9（+365d，post Sharpe 边 −0.09；+7d 也是 4/9 且 post 边为负）。其余平移为 3/9 或 0/9，后段明显弱于真格。安慰剂没有做出 6/9。
  - 邻域（同一 eth_net trend / cap_short_off，只改 n）：n=150 也是 9/9，post 边与 n=180 相同（仍是月份 5/4、薄边）。n=60 / 75 为 6/9，薄边类似。n=105 / 120 掉到 3/9，post 收益边翻负（约 −3.4 / −4.0 个百分点）。邻域不是一整片平稳区域，中间的 n 会翻负。
  - 压力费（20 / 15.1 bps）：锚点相对同脚本压力基线仍是 9/9，但 post 边仍然很薄（OKX d8 +57.32 / 2.18 vs 压力基线 +55.94 / 2.12；Gate +58.10 / 2.20 vs +56.78 / 2.15，约 +1.3 个百分点 / Sharpe +0.05），月份仍是 5/4，挡不住“后段月份不够、边薄、邻域中间翻负”。
- 结论：否决，不实现、不进观察名单、不改默认、不进纸交易。唯一先验 9/9 在未见历史和安慰剂上站得住，但 post 边相对已经很强的基线过薄，后段月份只有 5/4，邻域在 n=105/120 翻负，回退 n=90 在三段未见历史上全输。本族勿以同一机制换 n、k、方向，或把 eth_net / n_inbox / n_gw 对调，或改用毛 ETH 入金、代币金额、净流量变体、更早起点、其它 L2 官方桥或不在文档中的桥合约再测。
- 现场记录：只读上述官方合约日志与 EOD 托管余额，写入 output/arb_canonical_bridge_official_daily.csv 与 scratch/arbbridge4h/ 下的同名文件（pid / 日志在 scratch/arbbridge4h/record.pid 与 record.log）。不写 data/micro.sqlite，不打断其它记录进程。
- CSV（不入库）：output/research_arb_canonical_bridge_gate_4h.csv（441 行，含 120 个预注册格 / 真实与压力费 / 安慰剂 / 邻域）；官方日序列 output/arb_canonical_bridge_official_daily.csv（研究当时 1,945 个完整日，不入库；现场记录会在其后追加完整日）；脚本 scratch/arbbridge4h/ 下的 fetch、shard_fetch、gw_prefetch、watch_and_finish、run、record（研究脚本未推送）。
- 下一轮（短线）：官方以太坊主网 ERC-4337 EntryPoint UserOperationEvent 1h 次数或 gas 冲击 → 8 永续篮子。这是官方账户抽象需求，不是已否决的 WETH9 存取、Uniswap v3 ETH/USDC 冲击、blob / 基础费、mempool 拥堵、Circle USDC 铸造赎回或信标存款 / 提款。先确认官方 EntryPoint 地址与完整官方历史是否够 2026-03-05 切分和未见样本；不够就换一个同样未测过、官方历史足够的短线族。勿重测已否决的短线族，也不要用改 n / k / 侧或对其它 L2 官方桥换皮的方式重测本轮已否决的规范桥族。
