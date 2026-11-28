# 长线新族：以太坊信标链官方 DepositContract 质押存入需求 → 4h 默认书 #1 入场闸门（2026-11-27 ~19:40 PST，否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 已超过 GitHub 连接器写入上限，只在本地追加）。

## 0. 原定题目：日本财务省外汇干预（数据过稀，不做闸门回测）
- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、scratch/ROTATION_LOCK.txt 中 intervention / 干预 / 介入 / feio 只有 `fed_custody_gate_4h` 的机制注释与上一轮「下一轮（长线）」指针，从未测过。已否决的相近族（JPY/CNY 汇率趋势、JGB 10 年收益率、JGB 拍卖、JPX 外资流、财务省居民对外债券流 mof_gate〔8798 观察〕）均不是干预实绩本身。
- 官方数据：财务省 `https://www.mof.go.jp/english/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv`（CP932 → UTF-8，存 `output/mof_fx_intervention_official_daily.csv`，不入库）。**2015 年以来只有 12 个干预日、6 个簇**：2022-09-22、2022-10-21、2024-04-29 / 05-01、2024-07-11 / 12、2026-04-30 / 05-04 / 05-06、2026-07-30 / 31 / 08-03（全部为卖美元买日元）。逐日明细只在季末公布（月度合计月末公布），实时可用性更差。
- 结论：作为 4h 闸门只有 6 个独立事件，任何格子都只是在 6 次之间开关，无统计意义 → **不回测、不进观察**（PRE_REGISTER 文本写「13 天」为初扫笔误，以 CSV 解析的 12 天为准）。按任务规则换成下面这个从未测过的长线机制。

## 1. 换题：信标链质押存入需求
- 查重：rg `validator count|staking ratio|质押率|beacon deposit|DepositContract|0x00000000219ab` 于 docs/STRATEGY_FORMULAS.md、docs/*.md（176 篇）、output/research_*.csv（1,377 个）、ROTATION_LOCK：0 命中。相近但不同：`beacon_voluntary_exit_burst_event_1h`（退出 1h 冲击；勿重测覆盖退出 / EIP-7002 / 罚没，不含存入）、EigenLayer StrategyManager 存入 1h（再质押 LST）、stETH 折价 1h、ETH gas / blob / 燃烧 1h。没有任何信标链存入 4h 闸门。
- 机制（先验）：新增 ETH 质押存入放缓 = 长期资金流入以太坊生态减弱 → 加密风险偏好下降 → **拦新开多**。flag = 1 表示存入需求走弱。
- 数据（只用官方链上日志，不编造、不插值、不回补）：以太坊主网 `eth_getLogs`，DepositContract `0x00000000219ab540356cBB839Cbe05303d7705Fa`，topic0 DepositEvent `0x649bbc62…38c5`，金额为小端 gwei 字段，时间取日志 `blockTimestamp`（官方块头）。区块 12,550,000（2021-06）→ 26,510,956，1,397 个 1 万块窗口全部取到（0 缺窗）。**2,431,860 笔存入，存入序号 163,052 → 2,594,911 连续无缺口；合约 `get_deposit_count()` 在 26,510,956 块返回 2,594,912，与日志最大序号 +1 完全一致**。去掉首尾不完整日后 2,005 个完整 UTC 日 2021-06-02 → 2026-11-27，0 日历缺口，0 个零日。最近：2026-11-27 610 笔 / 48,490 ETH。季度存入：2023Q2（Shapella 后）787.6 万 ETH 峰值，2026Q1 722.6 万，2026Q3 395.0 万。日 D 于 **D+1 00:00 UTC** 起使用。官方日表 `output/beacon_deposit_official_daily.csv`（不入库）。
- 公式（看 PnL 前锁定 `scratch/beacondep4h/PRE_REGISTER.json`，sha256 `2326af5a…7e9757`，文件 mtime 2026-11-27 19:27 PST，回测 19:29 PST 开跑；文件内 locked_at 字段误写 19:45，未改以保持 sha），**80 格**：
  序列 eth7 = log(1 + 7 日存入 ETH 和)，n7 = log(1 + 7 日存入笔数)；形式 trend_n{30,90,180}（低于 n 日均）、chg_n{30,90}（比 n 日前低）、z180lt{0.5,1,1.5}（180 日 z < −k）；侧 long_off / short_off / both / contra_both / cap_short_off（只拦新开仓）。
  先验 `eth7_trend_n90_long_off`，回退 `n7_chg_n30_long_off`；安慰剂 = 先验 8 个时移（±30 / ±90 / +180 / −120 / +365 / −119 天）。
- 回测：与 fhfahpi4h 同一脚本（默认 #1 双均线 50/150，8 币 perp_both 10×，官方资金费），官方 OKX / Gate 4h 深缓存；真实费 maker 2 / taker 5.1 bps，压力费 perp 15.1 / spot 20；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8。

## 2. 结果（`output/research_beacon_deposit_staking_demand_gate_4h.csv` 324 行；`_supp.csv` 30 行；`_new8.csv` 20 行）

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | Gate d8 深未见 / 调参 | OKX d7 深未见 / 调参 | post 收益 / Sharpe（OKX、Gate）；月份 好/差 | new8 pre Sharpe（OKX、Gate） |
|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | 0.09 / 1.46 | 0.75 / 1.56 | +59.90%/2.23、+60.32%/2.25 | 0.75、0.73 |
| **先验 eth7_trend_n90_long_off** | 5/9 | 0.91 / 1.23 | 0.26 / 1.23 | 0.65 / 1.47 | +60.36%/2.25、+60.79%/2.26；1/1、1/1 | 0.99、0.98 |
| **回退 n7_chg_n30_long_off** | 4/9 | 1.01 / 1.13 | 0.58 / 1.10 | 0.86 / 1.37 | +59.33%/2.21、+60.34%/2.24；2/2 | 0.68、0.66 |
| 唯一 9/9 n7_chg_n90_cap_short_off（非先验） | 9/9 | 0.74 / 1.56 | 0.13 / 1.62 | 0.79 / 1.65 | +58.42%/2.30、+59.22%/2.32；4/5、4/5 | 0.63、0.61（post 1.04 vs 0.28、1.70 vs 1.00，月 6/3） |
| 7/9 eth7_chg_n30_cap_short_off（非先验，唯一 post 两所都≥基线） | 7/9 | 0.71 / 1.49 | 0.09 / 1.48 | 0.88 / 1.56 | +63.71%/2.36、+64.23%/2.37；4/4、5/3 | 0.65、0.63 |

- **先验**：深未见 OKX / Gate 赢（0.91 vs 0.71、0.26 vs 0.09），但 d7 深未见输（0.65 vs 0.75），三处调参窗全输（1.23 / 1.23 / 1.47 vs 1.47 / 1.46 / 1.56）；post 只多 +0.46 pp，月份 1 好 1 差（post 段几乎没拦到新多）。8 个时移安慰剂 post 都 ≤ 真实（−30d 与基线相同），但真实格本身没有可用边。压力费 post +56.39 vs +55.94（OKX）。new8 pre 0.99 / 0.98 vs 0.75 / 0.73 更好，但主书 tune 崩。否决。
- **回退**：深未见三处都赢，调参窗全输（1.13 vs 1.47），post 持平 → 4/9。否决。
- **唯一 9/9 n7_chg_n90_cap_short_off**（存入笔数比 90 日前低 → 不新开空，与经济先验无关）：post Sharpe 略高但收益反而低（OKX −1.5 pp、Gate −1.1 pp），月份 4/5 两所，达不到 ≥6/9。事后邻域（`_supp.csv`）：n45 post +52.0%、n60 +57.7%、n120 **+8.0%**、n180 +49.2%（OKX），全部低于基线；事后时移安慰剂 **+90d post +64.41% / 2.36 高于真实**，−120d +60.08% 也高于真实 → 无时点特异性。new8 pre 0.63 / 0.61 低于基线。否决。
- **7/9 eth7_chg_n30_cap_short_off**：post +3.8 / +3.9 pp（压力费 +59.95 vs +55.94、+60.26 vs +56.78），但 OKX d8 深未见与基线持平（0.71），月份 4/4、5/3 未达 ≥6/9；预注册邻域塌陷：n14 / n21 / n45 post 仅 +10.5 / +13.6 / +14.3%，n120 +18.8%，n180 +37.3%，n60 +56.7%（均低于基线）→ 孤立峰值。new8 pre 0.65 / 0.63 低于基线。否决。
- 结论：**否决**。不实现、不进观察名单、不改默认、无纸面变更、无代码改动。

## 3. 勿重测（never retest by…）
不要通过改 n / k / z 窗 / 侧 / 滞后，在 ETH 金额 / 笔数 / 平均单笔 / 7 日 / 30 日和 / 水平 / 变化之间换序列，改用净质押（存入 − 信标链提款 / 退出）、验证者数量 / 活跃验证者 / 质押率 / 入队等待（entry queue）、Pectra 后 0x02 合并 / 追加存入拆分、按存款人 / 运营方（Lido / Coinbase / Binance 等）分组、第三方（beaconcha.in / Dune / Rated）质押统计，或把存入改成 1h 突发事件，来重测「信标链质押存入需求 → 默认 #1 入场闸门」同一机制（1h 版须另立机制并先查重）。日本财务省外汇干预：2015 年以来只有 12 个干预日 / 6 簇，在干预簇 ≥ 15 个之前不要再拿来做闸门或事件回测，也不要改用财务省月度干预合计或「口头干预」新闻代替。

## 4. 文件
- `output/research_beacon_deposit_staking_demand_gate_4h.csv`、`_supp.csv`、`_new8.csv`、`output/beacon_deposit_official_daily.csv`、`output/mof_fx_intervention_official_daily.csv`（均不入库）。
- 脚本 `scratch/beacondep4h/{probe,fetch,build,run,supp,new8}.py`、`PRE_REGISTER.json(.sha256)`、`ckpt.pkl`（官方日志原件，不推送）；`scratch/mofintv/feio.csv`（财务省原件）。

## 5. 下一轮（短线 1h）
Uniswap v4 官方 PoolManager（以太坊主网，2025-01 部署）`Swap` 事件小时成交量冲击 → 8 币永续篮子 1h 顺势 / 逆势事件。docs / output 中无 Uniswap v4 / PoolManager 条目（0 命中）；须先核对 `univ3_lp_liquidity_shock_event_1h`（LP 流动性）、`univ2_newpair_gate_4h`（新池）、`cow_settlement_burst_event_1h`、`flashloan_burst_event_1h` 勿重测范围，若判同机制（DEX 成交量 / 流动性冲击）就换题。
