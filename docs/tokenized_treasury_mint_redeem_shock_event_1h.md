# 短线：代币化美债基金（BUIDL / OUSG / USYC / USTB / BENJI）链上申购 / 赎回突发 1h 事件 → 8 永续篮子（2026-11-22 23:55 – 2026-11-23 00:10 PST，否决）

## 想法
以太坊上的代币化美债基金份额（贝莱德 BUIDL、Ondo OUSG、Hashnote/Circle USYC、Superstate USTB、富兰克林 BENJI）是加密原生机构（Ethena USDtb、DAO 金库、基金、做市商）在链上停放闲置美元的地方。某小时赎回（burn）异常放大 = 链上机构现金离开美债、准备投入加密风险资产 → 先验做多 8 永续篮子；申购（mint）突发 = 转入美债避险 → 回退做空。按突发触发、不重叠持有 24/48h，交易频率低（每格每段几十到两百笔），不是费用受限的逐小时吃单族。

去重（2026-11-22 23:55 PST）：`docs/STRATEGY_FORMULAS.md`（10,678 行）、`docs/*.md`、`output/research_*.csv`（1,246 个）、`/workspace/scratch/*`、记忆上下文中检索 BUIDL / OUSG / USYC / USTB / BENJI / Ondo / Superstate / tokenized treasury / 代币化国债 / RWA：0 条测试。本轮先排除的候选（已测或被禁）：信标链罚没（已并入信标自愿退出族，禁止换罚没重测）、以太坊满块率 / gas 使用量（`research_eth_gas_fullness_burst_event_1h.csv`）、基础费 / blob（`research_eth_blob_basefee_shock_event_1h.csv`）、期权到期（Deribit / Gate / CME / IBIT 均已测）、Base / OP 官方桥（CCTP 文档禁止换其他跨链桥）、BoJ 决议（ECB/BoE 文档禁止换其他央行）、泡菜溢价、BTC CDD 休眠、加密股财报、地磁 / 月相、USGS 地震（无经济机制，未选）。与已否决的稳定币铸造 / 供给（DefiLlama、USDe、CCTP、Curve 3pool、Maker PSM、黑名单、交易所稳定币流）不同：这里是**生息美债基金份额**的申赎，不是稳定币。

## 数据（仅官方）
- 官方以太坊主网 `eth_getLogs`（主 RPC gateway.tenderly.co 公共节点，地址 + topic 过滤 `Transfer(from=0x0)` / `Transfer(to=0x0)`），不用 Etherscan / Dune / 子图 / RWA.xyz。
- 合约（eth_call `symbol()` 实测）：BUIDL `0x7712c34205737192402172409a8F7ccef8aA2AEc`、OUSG `0x1B19C19393e2d034D8Ff31ff34c81252FcBbee92`、USYC `0x136471a34f6ef19fE571EFFC1CA711fdb8E49f2b`、USTB `0x43415eB6ff9DB7E26A15b704e7A3eDCe97d31C4e`、BENJI `0x3DDc84940Ab509C11B20B76B466933f40b750dc9`。
- 事件：BUIDL mint 14,131（705 笔交易，月度分红为批量 mint，故按去重交易数计）/ burn 227；OUSG 666 / 746；USYC 9,629 / 5,540；USTB 3,865 / 12,360；BENJI 1,966 / 12。
- 校验：按 mint − burn 累加重建的 5 个代币供给与链上 `totalSupply()` 逐位一致（BUIDL 170,389,165.18、OUSG 1,093,814.20、USYC 28,837,324.34、USTB 41,871,996.84、BENJI 16,107,474.15）；12 个随机 9,000 块窗口 + 最新 ~13,000 块在独立 RPC（rpc.mevblocker.io / eth.api.pocket.network）条数 13/13 一致。
- 1h 序列 `output/tokenized_treasury_mintburn_official_1h.csv`：33,517 个完整 UTC 小时，2023-01-26 18:00 → 2026-11-23 06:00 UTC，0 缺口；零为真零。小时 t 的值在 t 收盘后才用，t+1 开盘入场。
- 价格：官方 OKX 1h 永续（2022-01-29 → 2026-11-23 06:00 UTC，默认 8 币 + 未调参 new8），官方 Gate 1h 永续（2025-09-24 起），含官方资金费。

## 公式与网格（PRE_REGISTER.json，sha256 736194ecbeab…1d301，任何 PnL 之前锁定）
- 序列：`log_n_burn` = log1p(小时赎回交易数)；`log_n_mint` = log1p(小时申购交易数)；`log_redeem_bps` = log1p(Σ 每笔赎回份额 / 该代币赎回前供给，bps)。
- z_t = (x_t − 过去 L 小时均值) / 过去 L 小时标准差（不含 t，最少 L/2 样本）；z_t ≥ k → t+1 开盘入场，持有 H 小时，不重叠。
- L ∈ {168, 720}；k ∈ {2, 3, 4}；方向 多/空；H ∈ {24, 48}；3 序列共 72 格。
- 先验 `log_redeem_bps_L720_k3_long_H48`；回退 `log_n_mint_L720_k3_short_H24`。
- 费用：吃单 5.1 bps/边（压力 15.1 bps/边）+ 官方资金费。分段：train（深度未见）序列起点 2023-01-26 → 2024-10-21，test → 2026-03-05，post 之后；Gate 窗口 2025-09-28 起。8 项检查 = OKX d8 train/test/post、new8 train/test/post、Gate post、Gate 窗口 均值 > 0。安慰剂：z 平移 ±720h；每段 200 次同笔数随机入场。

## 结果（真实费用；每笔均值 bps / t / n；括号为段内累计收益 %）
| 格 | OKX train | OKX test | OKX post | new8 post | Gate post | Gate 窗口 | 8 项 | post 月份 OKX/Gate | ±720h 平移 post | 随机分位 post |
|---|---|---|---|---|---|---|---|---|---|---|
| 先验 redeem_bps L720 k3 多 H48 | +37.2 / 1.07 / 133（+49.5%） | +5.2 / 0.11 / 133（+7.0%） | −46.9 / −0.87 / 65（−30.5%） | −7.7 | −45.6 | −102.7 | 3/8 | 3/9、3/9 | −50.7 / −7.3 | 30.5 |
| 回退 n_mint L720 k3 空 H24 | −39.5 / −2.06 / 257（−101%） | −97.3 / −2.81 / 108 | −20.1 / −0.47 / 42 | −48.5 | −21.0 | −11.8 | 0/8 | 4/9、4/9 | −13.1 / −3.2 | 19.5 |
| 非先验 n_burn L168 k4 多 H24 | +11.8 / 0.48 / 182 | +74.5 / 1.22 / 49 | +49.1 / 0.97 / 12（+5.9%） | +108.2 | +49.6 | +11.1 | 8/8 | 5/9、5/9 | −123.7 / +11.1 | 83 |
| 非先验 n_mint L168 k3 多 H48 | +73.4 / 2.67 / 176 | +37.5 / 0.67 / 90 | +29.2 / 0.36 / 36 | +1.5 | +30.6 | +22.1 | 8/8 | 4/9、4/9 | −18.2 / **+66.7** | 83 |
- 同期随机入场基线（做多，OKX d8）：train +4.9、test +1.4、post −21.8 bps；压力费 post：先验 −66.9、n_burn L168 k4 +29.1、n_mint L168 k3 H48 +9.2（new8 −18.5）。
- 分布：72 格中 8/8 两格、7/8 一格、6/8 四格、5/8 四格；0–4/8 共 61 格。
- 先验邻域（redeem_bps 做多 12 格）post 全负（−13.7 ~ −109.7），Gate post 全负。
- n_burn 做多邻域：只有 L168 k4 H24 与 L720 k4 H24 post 为正（各 11–12 笔），k2 / k3 与所有 H48 post 为负（L168 k4 H48 −54.6）——单点；Gate test 仅 6 笔 −66.1。
- n_mint L168 k3 H48：−720h 平移安慰剂 post +66.7 好于真格 +29.2，new8 post ≈ 0，月份 4/9。

## 结论
**否决，不进观察名单。** 先验（赎回强度突发 → 做多）test 近零、post 两所约 −46 bps、邻域 post 全负；回退（申购突发 → 做空）0/8。两个 usable 8/8 都是非先验做多格：一个 post 只有 12 笔、t < 1、月份 5/9、邻域单点；另一个被 −720h 平移安慰剂超过、new8 post 归零。均不满足 post ≥ 6/9 月份两所与安慰剂门槛。默认、纸面盘、应用代码均不变。数据史够长（深未见段覆盖 2023-01 起），未另起实时记录器。

## 勿重测（never retest by…）
- 换 L / k / H / 方向，或把镜像格 / 最佳格包装成新发现；
- 换序列：申购 / 赎回交易数 ↔ 事件数 ↔ 份额 ↔ 美元额（按 NAV 折算）↔ 占供给 bps ↔ 净申赎 ↔ 唯一地址数 ↔ 大额单笔 ↔ 总供给 / AUM 变化；
- 只用单一基金（只 BUIDL / 只 OUSG 等），或加入其他代币化美债 / 货币基金（WisdomTree、Spiko、OpenEden TBILL、Backed bIB01、Mountain USDM、Ondo USDY、Securitize sToken、Circle USYC 其他链版本）、其他链（Solana / Arbitrum / Base / Polygon / Avalanche / Stellar 上的 BUIDL / BENJI / USDY）；
- 换 Ethena USDtb 铸造 / 赎回，或改成 4h 日度闸门 / 单币反应来重测同一「链上代币化美债申赎」机制；
- 只能用前向新数据复核，至少攒够 post 之后新的 ≥ 20 笔事件再按新预注册单独复审。

## 文件
- 结果 CSV（不入库）：`output/research_tokenized_treasury_mint_redeem_shock_event_1h.csv`（2,520 行，含真实 / 压力费、±720h 平移、随机 200 次安慰剂）；官方 1h 序列 `output/tokenized_treasury_mintburn_official_1h.csv`。
- 脚本（不推送）：`scratch/tbillmint1h/{fetch.py,build.py,run.py,analyze.py,plog.py}`、`PRE_REGISTER.json`、`analyze_wide.csv`、`tbill_mintburn_events_official.csv`。

下一轮（长线）：德国 ifo 商业景气 / ZEW 经济景气指数（官方月度，非美宏观）→ 4h 默认书入场闸门；先查重（含 OECD CLI、中国 PMI、美国宏观、韩国出口等已否决族）并确认官方历史可免费下载。
