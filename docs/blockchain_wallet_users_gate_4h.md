# Blockchain.com 官方钱包用户数（my-wallet-n-users）新增注册节奏 → 4h 默认书入场闸门（否决；不改默认、不入纸面）

## 长线新族：散户钱包注册节奏作为 4h 默认书入场闸门（2026-11-22 ~22:50–23:10 PST，研究，不改默认；否决）

- 查重 / 换题：原建议的日本央行《営業毎旬報告》总资产 / 当座預金 **不测**：`BoJ 当座預金` 已明确写进 SNB 活期存款闸门的勿重测范围（`docs/snb_sight_deposits_gate_4h.md`），BoJ 总资产与已否决的 ECB Eurosystem 总资产（`docs/ecb_eurosystem_balance_sheet_gate_4h.md`）、联储净流动性 / H.4.1 属同一「央行资产负债表趋势」族；AAII 情绪 `sentiment.xls` 仍 403（不绕过）；美国 CP 利差在多个勿重测条目里归入「其他美国宏观」。`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（约 200 个 4h 闸门）、`scratch/` 与记忆检索 `my-wallet / wallet users / 钱包用户` 0 命中。它不是已否决的链上活跃地址 / 交易笔数（`btc_onchain_activity_gate_4h`，链上地址）、交易所成交额、TSA / Wikipedia / npm 注意力族——这里是单一托管 / 非托管钱包产品的**新注册用户**（散户入场）。
- 机制（看 PnL 前锁定）：新钱包注册上升 / 偏高 = 散户入场 = risk-on → flag=1 拦新空（cap_short_off），contra_both 同时在 flag=0 时拦新多。只拦新开仓，已有持仓、止损、离场不变。默认 4h 书（#1 双均线 50/150，8 个永续）。
- 数据（只用官方，不编造、不回补）：Blockchain.com 官方图表 API `https://api.blockchain.info/charts/my-wallet-n-users?timespan=all&format=json&sampled=false`（"Blockchain Wallet Users"，累计用户数，小时点）。原始快照 `scratch/bcwallet4h/raw/my_wallet_n_users_all.json`（74,644 点，2011-11-29 → 2026-10-28 08:54 UTC）；日值 = 当日 UTC 最后一个官方点，5,424 天，日历缺口仅 3 处（2017-07-13→08-01、2017-09-15→09-20、2018-04-27→04-30），因此只用 2018-05-01 之后（3,103 天，0 缺口）。另有两段官方计数停更（2021-06-15 起 12 天、2022-07-25 起 15 天，按官方原值保留为 0 新增）。**发布方自 2026-10-28 起停止更新**，序列不外推，闸门在此后保持最后已知值。2025-08 至 2026-02 有几次单周 +0.4M~+2.0M 的跳增（官方原值，未清洗）。最后一天累计 101,159,104，近 28 天新增 39,376。
- 滞后：日 D 的值仅于 D+1 01:00 UTC 起使用，前向填充到 4h K 线。修订风险：官方不提供历史版本，本研究用 2026-11-22 当前版本；已起实时记录器保存后续版本。
- 公式（看 PnL 前写入 `scratch/bcwallet4h/PRE_REGISTER.json` 锁定，2026-11-22 22:54 PST，sha256 `PRE_REGISTER.sha256` 同目录另记 run.py / build.py / 原始 JSON / 日度 CSV 的 sha；锁定前只打印过 flag 占比，没有改网格；共 120 格）：
  - 序列：`w7 = log1p(近 7 天新增钱包)`、`w28 = log1p(近 28 天新增钱包)`、`g365 = log(用户数 / 365 天前)`。
  - 形式：`chgN`：s − s.shift(N 天) > 0，N 7 / 28 / 91；`trendN`：s > SMA(N 天)，N 28 / 91 / 182；`z365gtK`：(s − SMA365) / STD365 > K，K 0.5 / 1。
  - 侧：long_off（flag=0 拦新多）/ short_off（flag=0 拦新空）/ both / contra_both / cap_short_off（flag=1 拦新空）。3 × 8 × 5 = 120 格 + 同脚本基线。
  - 锁定先验格：`w28_trend91_cap_short_off`（28 天新增高于 91 天均线 → 拦新空），兼作安慰剂锚；回退 `w28_chg28_cap_short_off`；经济侧 = cap_short_off / contra_both。
- 验证：与 MoF / ECB / SNB 闸门同一框架（OKX d8 2023-02→ / Gate d8 2022-07→ / OKX d7_noBNB 2022-04→，官方永续 + 现货 4h、官方资金费；真实费率永续 maker 2 / taker 5.1 bps，压力永续 15.1 / 现货 20 bps；深未见 →2024-10-21、调参段 →2026-03-05、post →2026-11-14；平移安慰剂 ±7 / ±14 / +180 / −120 / +365 / −119 天；邻域；new8 未调参 LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI 最近 4500 根 4h）。9 个检查 = 3 套账本 × {深未见, 调参段, post} Sharpe 胜基线。默认门槛：深未见 + post 都成立，且 post 两所 ≥ 6/9 月更好。
- 结果（`output/research_blockchain_wallet_users_gate_4h.csv` 444 行 + 表头；收益 % / Sharpe，真实费率）：

| 账本 | 格 | 深未见 | 调参段 | post | post 月 好/差 |
|---|---|---|---|---|---|
| OKX d8 | 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | — |
| OKX d8 | 先验 w28_trend91_cap_short_off（3/9） | +13.39 / 0.39 | +35.17 / 0.90 | +69.44 / 2.53 | 4/2 |
| OKX d8 | 回退 w28_chg28_cap_short_off（3/9） | −13.90 / −0.21 | +50.81 / 1.13 | +63.78 / 2.37 | 2/4 |
| OKX d8 | 最佳非先验 6/9 w7_trend91_contra_both | +32.29 / 0.73 | −4.64 / 0.06 | +64.49 / 2.53 | 3/3 |
| OKX d8 | 安慰剂 先验 +180d（8/9） | +67.90 / 1.17 | +94.48 / 1.65 | +67.15 / 2.54 | 4/4 |
| Gate d8 | 基线 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / 2.25 | — |
| Gate d8 | 先验 | −20.40 / −0.22 | +29.87 / 0.81 | +69.90 / 2.55 | 4/2 |
| Gate d8 | 回退 | −39.07 / −0.72 | +45.62 / 1.06 | +64.48 / 2.40 | 3/3 |
| Gate d8 | w7_trend91_contra_both | +6.37 / 0.22 | −7.94 / −0.04 | +65.04 / 2.55 | 3/3 |
| Gate d8 | 安慰剂 +180d | +18.54 / 0.39 | +90.56 / 1.61 | +68.35 / 2.58 | 5/3 |
| OKX d7_noBNB | 基线 | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / 2.10 | — |
| OKX d7_noBNB | 先验 | +29.97 / 0.52 | +39.10 / 0.98 | +59.70 / 2.43 | 4/2 |
| OKX d7_noBNB | w7_trend91_contra_both | +47.66 / 0.76 | +2.47 / 0.23 | +53.29 / 2.34 | 2/4 |

  - 9 切片 Sharpe 胜数：**最高 6/9，没有 7/9 / 8/9 / 9/9**（14 格 6/9）。6/9 格要么调参段大输（w7_trend91_contra_both 调参段 −90 pp），要么 post 几乎不触发（z365 / g365 cap_short_off post 月 0/1、1/0），要么 post 崩盘（w28_chg28_short_off / both post −0 ~ −6%）。
  - **锁定先验 3/9**：只赢 post（+9.5 pp / Sharpe +0.30，月 4/2，< 6/9），深未见三套全输（OKX −22 pp、Gate −17 pp），调参段 −50 pp。回退 3/9 同形态且深未见更差。
  - 安慰剂（先验锚平移）：+180d **8/9**、−7d 5/9、+14d 4/9，均 ≥ 真实先验 3/9；post 段平移版同样 +7 ~ +9 pp → post 的增量来自「post 期少开空单」的体制，而不是钱包注册的时点信息。
  - 邻域（锚 w7_trend91_contra_both，trend n = 14 / 28 / 56 / 120 / 182 / 365）：胜数 3 / 5 / 6 / 3 / 3 / 0，n=365 post 掉到 +40%，无稳定平台。
  - 压力费率（永续 taker 15.1 / 现货 20 bps）：基线 OKX 深未见 +24.67/0.56、调参段 +75.18/1.35、post +55.94/2.12；先验 +5.34/0.25、+28.44/0.78、+66.32/2.45；Gate 先验深未见 −27.90/−0.37；结论不变。
  - new8 未调参（2024-11-28 →）：先验 OKX pre +10.97/0.39 vs 基线 +47.16/0.98、post +7.73/0.60 vs +3.26/0.28（4/2）；Gate pre +10.72/0.38 vs +44.50/0.96、post +20.74/1.26 vs +16.36/1.00（4/2）。w7_trend91_contra_both OKX pre −10.16 vs +47.16、post +15.97（4/3）；Gate pre −9.24、post +30.67（4/3）。+180d 平移安慰剂 post 同样胜（+6.73 / +20.83）。new8 同样 pre 大输、post 胜但安慰剂也胜。
- 当前信号（数据到 2026-10-28，2026-10-29 01:00 UTC 起保持）：w28 新增 39,376 > 91 天均值约 36,820 → 先验 flag=1（会拦新空）；w28_chg28 flag=1；w7_trend91 flag=0。仅供记录，不进纸面（且官方序列已停更 3.5 周，无法实时使用）。
- 结论：**否决**（不改默认、不入纸面、不加代码）。唯一的正面是 post 段「拦新空」带来的 +5 ~ +10 pp，但它在深未见、调参段、new8 pre 段都大幅亏损，且 +180 天平移安慰剂 8/9 远强于真实先验 3/9，说明不是钱包注册信息本身；post 月份最高 4/2，未达 6/9；发布方 2026-10-28 起停更，也不具备实盘可用性。
- 勿重测：不要通过改 N（3~365 天）、z 窗口 / K、方向 / 侧、滞后（D+0 / D+1 / D+2），换 7 / 14 / 28 / 91 天新增、累计水平、同比增速、加速度，换 Blockchain.com 其他产品指标（钱包数、交易所用户、my-wallet-transaction-volume 等），或换成 Coinbase / Robinhood / Binance 等交易所披露的用户数 / MAU、App 下载排名、Google Trends 等散户入场代理来重开本族。
- CSV：`output/research_blockchain_wallet_users_gate_4h.csv`（主网格 + 安慰剂 + 邻域 + STRESS，444 行）、`output/research_blockchain_wallet_users_gate_4h_new8.csv`（new8 未调参，20 行）、官方日度 `output/blockchain_wallet_users_official_daily.csv`（5,424 天，不入库）；脚本 `scratch/bcwallet4h/{build,run,new8,record,plog}.py`；官方实时记录器 `scratch/bcwallet4h/record.py`（每 6 小时拉近 30 天，新版本存 `scratch/bcwallet4h/vintages/`）。
- 下一轮（短线）：选一个未测过、官方历史足够覆盖 2024-10-21 / 2026-03-05 切分的 1h 事件族；先查重。备选长线：德国 ifo 商业景气 / ZEW 景气（官方月度，非美宏观，docs 0 条），需先确认官方历史文件可免费下载。
