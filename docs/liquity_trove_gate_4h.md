# Liquity v1 官方系统债务 / LTV → 4h 默认书入场闸门（2026-11-21，否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（远端 STRATEGY_FORMULAS.md 与本地分叉时以此为准）。


- 背景：上节「下一轮（长线）」所列。机制 = 链上 ETH 抵押借贷杠杆需求（LUSD 债务扩张 / 系统 LTV 上升 = 加杠杆做多 ETH）；经济先验「过热拦新多」。只拦新开仓，出场 / 止损 / 已有同向仓不动。本地与远端文档、output 中此前 Liquity / LUSD / Trove 0 条，不是重复。
- 数据（全部官方链上，`output/liquity_official_daily.csv`）：TroveManager `0xA39739EF8b0231DbFA0DcdA07d7e29faAbCf4bb2`；ActivePool `0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F`、DefaultPool `0x896a3F03176f05CFbb4f006BfCd8723F2B0D741C`、StabilityPool `0x66017D22b0f8556afdd19FC67041899Eb65a21bb`、LUSD `0x5f98805A4E8be255a32880FDeC7F6728C6568bA0`、PriceFeed `0x4c517D4e2C851CA76d7eC94B805269Df0f2201De`（均由 TroveManager getter 链上取得，并与 liquity/dev 官方 mainnet.json 部署清单一致）。每个 UTC 日终块（时间戳 ≤ D 23:59:59 UTC 的最后一块）archive `eth_call`：getEntireSystemColl/Debt、ActivePool/DefaultPool getETH/getLUSDDebt、PriceFeed.lastGoodPrice、StabilityPool 存款、LUSD totalSupply、trove 数。价格用 Liquity 官方 lastGoodPrice，不用交易所价。
  - **完整 UTC 日 2021-04-05 → 2026-11-20 共 2,056 天，0 缺口，0 重复，0 NaN，不插值不回补**。
  - 校验：ActivePool + DefaultPool = TroveManager.getEntireSystemColl/Debt **2,056/2,056 天逐 wei 一致**；7 个日终（6 随机 + 最后一天）× 4 个 RPC 独立重拉 **112/112 一致**；最新块 26,464,145 在 drpc 与 mevblocker 两个 RPC 上 TM = AP + DP 逐 wei 成立（抵押 71,261.02 ETH、债务 26,382,911 LUSD、TCR 4.55）；ActivePool 官方事件 `ActivePoolETHBalanceUpdated` / `ActivePoolLUSDDebtUpdated` 最后值与日终状态 3/3 一致（1 个抽样日窗口内无事件）。
  - 量级：债务峰值 15.58 亿 LUSD（2021-05-14），2026-11-20 只剩 2,669 万 LUSD、抵押 71,453.76 ETH、TCR 4.33、稳定池覆盖 0.231、63 个 trove（Liquity v2 上线后 v1 持续去杠杆）。
  - 时滞：D 日值 D+1 01:00 UTC 才使用，前向填充到 4h 根。
- 公式（`scratch/liquity4h/PRE_REGISTER.json` sha256 `fc28cf7a…b659`，看任何 PnL 前锁定，结果后复核未改；安慰剂补充 `PLACEBO_ADDENDUM.txt`，亦在 PnL 前写）：
  - 序列：debt = getEntireSystemDebt（LUSD）；ltv = debt /（coll_eth × lastGoodPrice）= 1/TCR；sp_cov = 稳定池 LUSD / debt（非先验探索）。
  - 形式：trend（值 > SMA n，n∈{30,90,180}）、chg（n 日变化 > 0，n∈{30,90}）、z365 > k（k∈{1,1.5,2}）；方向 long_off / short_off / both / contra_both / cap_short_off。3 × 8 × 5 = **120 格** + 同脚本基线（当前 S.DEFAULTS 4h 默认书）。
  - **先验 `debt_trend_n90_long_off`**，回退 `ltv_trend_n30_long_off`。
  - 评分：9 个 Sharpe 片（OKX d8、Gate d8、OKX d7_noBNB × 深未见 < 2024-10-21 / tune_pre / post ≥ 2026-03-05，回测止于 2026-11-14）；post 月度 ≥ 6/9 两所都更好；post 收益两所不差；新 8 币未调参；邻域；时移安慰剂 ±7/±14/+180/−120/+365/−119 天；30 天块打乱安慰剂（种子 1/2/3）。真实费用：永续 taker 5.1 bps / maker 2 bps + 官方资金费；压力永续 taker 15.1 bps。
- 结果（`output/research_liquity_trove_gate_4h.csv`）：
  - 基线：OKX d8 深未见 +35.14% / Sharpe 0.71，tune +85.08% / 1.47，post +59.90% / 2.23；Gate d8 −3.63% / 0.09，+84.25% / 1.46，+60.32% / 2.25。
  - 占用率（flag=1 比例）：debt_trend_n90 深未见 0.347、tune 0.024、**post 0.000**；debt 各格 2024-10 之后基本全 0（v1 债务单边收缩）。
  - **先验 debt_trend_n90_long_off = 6/9，但只赢深未见 + tune**：OKX 深未见 +50.25% / 0.93、tune +93.04% / 1.56，Gate +6.18% / 0.23、+91.04% / 1.53；**post 与基线逐笔相同**（OKX +59.90% / 2.23、Gate +60.32% / 2.25，月度 0/0），达不到 post ≥ 6/9 月份更好。压力费下同形（OKX 深未见 0.80 vs 0.56，post 相同）。新 8 币（2024-11-26 起）flag 全 0，与基线完全相同（OKX post +3.26% / 0.28，Gate +16.36% / 1.00，月度 0/0）。
  - **安慰剂复现深未见优势**：+7 天时移 6/9（OKX 深未见同为 +50.25%），−119 天 6/9，−120 天 4/9，其余 ≤ 3/9；30 天块打乱 3 个种子深未见 Sharpe OKX 0.98 / 0.86 / 0.96、Gate 0.29 / 0.20 / 0.27，与先验（0.93 / 0.23）同级 → 深未见增益是「2021–22 熊市少开多」的慢变量体制效应，不是本序列信息。
  - 邻域 n 60/75/105/120/150 各 3/9（只赢深未见；n60/n75 tune 劣于基线），post 全部等于基线。
  - 回退 ltv_trend_n30_long_off = 3/9：OKX tune +71.02% / 1.35、post +58.39% / 2.19（月度 1/2），Gate tune +70.32% / 1.34、post +58.51% / 2.20（月度 0/3），均劣于基线；新 8 币 post 略好（OKX +4.39% vs +3.26%，Gate +17.61% vs +16.36%，月度 2/0）但仅 2 个月有差异。
  - 120 格分布：无 8/9 或 9/9；唯一 7/9 为非先验 sp_cov_trend_n30_both，post 收益两所都更差（OKX +55.53% vs +59.90%，Gate +56.11% vs +60.32%，月度 3/5）；13 个 6/9 无一满足 post 月度 ≥ 6/9。ltv_chg_n30_both post 最强（OKX +70.25% / 2.59、Gate +70.73% / 2.60，月度 5/4、7/2）但 tune 崩（0.44 / 0.36 vs 1.47 / 1.46），5/9。
- 结论：**否决**。先验 post 零占用（与基线相同）、深未见增益被时移 / 打乱安慰剂复现，回退劣于基线，无格同时过深未见与 post 两所 ≥ 6/9 月份。不改默认、不动纸面盘、不改代码。**勿以改 n / k / 方向、换序列（抵押 ETH / TCR / 稳定池覆盖 / LUSD 供给 / trove 数 / 赎回 / 清算量）、换 Liquity v2（BOLD）或其他 CDP（Maker vault、crvUSD、Prisma、Felix 等）的方式在现有历史上重测本族。**
- 文件：`output/liquity_official_daily.csv`、`output/research_liquity_trove_gate_4h.csv`、`_new8.csv`、`_shuffle.csv`（均不入库）；sidecar `docs/liquity_trove_gate_4h.md`；脚本 `scratch/liquity4h/{fetch,verify,run,new8,supp,record}.py`（未推送）。官方日度记录器 `scratch/liquity4h/record.py` 已后台运行（30 分钟一轮，只追加新完成 UTC 日，不重写）。
- 下一轮（短线）：Hyperliquid 官方 Arbitrum 存款桥 Bridge2（`0x2Df1c51E09aECF9cacB7bc98cB1742757f163dF7`，原生 USDC `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`）USDC 存入 / 验证者提出 1h 突发 → 8 币永续篮子顺势 / 逆势。机制 = 链上永续 DEX 保证金新钱进出（投机杠杆资金入场 / 撤离），不是已否决的 Arbitrum 官方桥 ETH 净流（长线、L1↔L2 桥）、稳定币供给、Curve 3pool、WETH9、Tornado、交易所资金费或 OI；文档 / output 中 Hyperliquid 0 条。数据只用 Arbitrum 官方链上日志（USDC Transfer to/from Bridge2 + Bridge2 自身事件），约 2023-12 起；需先确认 CCTP 迁移后 2025–26 流量是否仍足够（官方文档已把该桥标为 legacy）。

## 复现

```
cd /workspace/scratch/liquity4h
python fetch.py      # 官方 archive eth_call 日终状态 → output/liquity_official_daily.csv
python verify.py     # 组件逐 wei / 跨 RPC / 最新块 / 官方事件校验
python run.py        # 120 格 + 基线 + 时移安慰剂 + 邻域 + 压力费
python new8.py debt_trend_n90_long_off ltv_trend_n30_long_off sp_cov_trend_n30_both PLC_debt_trend_n90_long_off_shift7d PLC_debt_trend_n90_long_off_shift-7d
python supp.py       # 30 天块打乱安慰剂
```
