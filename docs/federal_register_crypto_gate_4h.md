# 长线：美国联邦公报（Federal Register）涉加密文件数 → 默认 4h 书入场闸门（2026-11-23 ~01:05–01:35 PST，否决；非先验弱观察，不进模拟盘）

## 查重
- `docs/*.md`、`docs/STRATEGY_FORMULAS.md`、`ls output/research_*.csv`、`/workspace/scratch` 检索 `Federal Register` / `federalregister` / `联邦公报` / `联邦纪事` / 监管文件计数：0 命中。
- 不是已否决的 `edgar_crypto_mentions`（上市公司 SEC 申报文本提及加密）、`edgar_crypto_etf_s1`（1h S-1 事件）、`stablecoin_blacklist` / OFAC / Tornado、EPU / GPR 新闻指数、Wikipedia / Google Trends 注意力、美股 IPO / 发债窗口。机制是**联邦监管机构正式刊登的涉加密文件流量**（SEC 交易所规则变更通知 / 命令、FinCEN / IRS / 财政部 / CFTC / 美联储等规则与通知）。

## 数据（官方，未编造、未回补）
- FederalRegister.gov 官方 API v1 `GET /api/v1/documents/facets/daily`（免密钥），按**刊登日**计数，全文检索词：`cryptocurrency | bitcoin | "digital asset" | "digital assets" | "virtual currency" | blockchain | stablecoin`。
- 三条序列：`all`（全部机构）、`sec`（agency = securities-and-exchange-commission）、`nonsec` = all − sec；另存全部文件日计数作参考。
- 覆盖 2015-01-01 → 2026-11-23，共 4,345 个日历日（无文件的日子计 0）；涉加密文件合计 1,263 份（SEC 858 / 非 SEC 405）。年度：2021 87、2022 81、2023 122、2024 203、2025 347、2026（至 11-23）244；SEC 2024 136、2025 310。
- 发布时滞：刊登日 D 的计数仅于 **D+1 12:00 UTC** 起使用（官方 D 日 06:00 ET 刊登，保守多等约 1 天）。联邦公报不修订（更正为新文件）。前向填充到 4h K 线。
- 本地 `output/federal_register_crypto_official_daily.csv`（4,345 行，含 `known_from_utc`）。

## 公式与预注册（看任何 PnL 前锁定，`PRE_REGISTER.json` / `PRE_REGISTER.csv` 2026-11-23 01:09:58 PST，sha256 b986ce37…584ad）
- 日计数 c。形式（flag=1 = 涉加密监管文件活跃）：`rA_gtB` mean(c,A) > mean(c,B)，(30,365)/(90,365)/(30,90)；`chgW` W 日合计 > W 日前的 W 日合计，W∈{30,90}；`zWgtK` W 日合计相对过去 365 天均值/标准差的 z > K，(30,1)/(90,1)/(90,0)。
- 五侧：long_off（flag=1 拦新多）/ short_off（flag=0 拦新空）/ both / contra_both / cap_short_off（flag=1 拦新空）；已有同向仓保留。3×8×5 = **120 格** + 同脚本基线（默认 #1 MA50/150）。
- 经济先验（锁定）：SEC 涉加密文件（主要是交易所加密 ETP 上市规则变更）90 天速率高于一年均速 = ETF / 机构化管道活跃 = risk-on → 不开新空。先验 `sec_r90gt365_cap_short_off`；回退 `all_r90gt365_cap_short_off`。
- 验证：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续+现货、官方资金费；真实费（永续 maker 2 / taker 5.1 bps，现货 10）、压力费（永续 15.1 / 现货 20）；深度未见 →2024-10-21 / 调参 →2026-03-05 / post →2026-11-14；9 片 Sharpe 胜场；post 月份胜负；邻域；可用时间平移安慰剂 ±7/±14/±60/+180/−120/+365/−119 天；未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI，最近 4500 根，OKX+Gate）。

## 结果（`output/research_federal_register_crypto_gate_4h.csv` 567 行；`_best_placebo_nbhd.csv`；`_new8.csv`）
- 基线：OKX d8 深度 +35.14%/0.71、调参 +85.08%/1.47、post +59.90%/2.23；Gate d8 深度 −3.63%/0.09、调参 +84.25%/1.46、post +60.32%/2.25；OKX d7 深度 0.75 / 调参 1.56 / post +50.76%/2.10。
- 120 格 9 片胜场分布：0:31，1:8，2:20，3:41，4:7，5:4，6:9；无 7/9 以上。

| 格 | OKX post 收益/Sharpe | Gate post 收益/Sharpe | post 好/差月（OKX, Gate） | 深度未见 Sharpe OKX / Gate / d7 | 调参 Sharpe OKX / Gate | 9 片 | new8 post Sharpe OKX / Gate（基线 0.28 / 1.00） |
|---|---|---|---|---|---|---|---|
| 基线 | +59.90% / 2.23 | +60.32% / 2.25 | – | 0.71 / 0.09 / 0.75 | 1.47 / 1.46 | – | 0.28 / 1.00（pre 0.99 / 0.96） |
| 先验 sec_r90gt365_cap_short_off | +54.41% / 2.13 | +55.03% / 2.15 | 2/1, 2/1 | 0.17 / −0.37 / −0.15 | 1.66 / 1.71 | 3/9 | 0.85 / 1.49（pre 0.78 / 0.76） |
| 回退 all_r90gt365_cap_short_off | +34.83% / 1.59 | +35.34% / 1.61 | 4/4, 5/3 | 0.33 / −0.29 / −0.05 | 1.66 / 1.71 | 3/9 | 0.08 / 0.93 |
| 最佳非先验 all_r90gt365_short_off | +66.41% / 2.57 | +66.24% / 2.65 | **6/2, 6/2** | 0.87 / 0.35 / 1.29 | 1.23 / 1.15 | 6/9 | 0.50 / 0.51（pre 0.57 / 0.56） |
| 非先验 sec_chg90_short_off | +72.43% / 2.63 | +73.20% / 2.66 | 5/1, 5/1 | 0.96 / 0.42 / 0.84 | 1.17 / 1.19 | 6/9 | 0.56 / 1.20（pre 0.57 / 0.56） |

- 先验：深度未见三片全输、post 双所跑输（−5.5 pp），3/9 → 否决；先验安慰剂 −14d 反而 6/9 / post +62%。回退：post −25 pp → 否决。
- `all_r90gt365_short_off`（全部机构涉加密文件 90 天速率**低于**一年均速 = 监管安静 → 拦新空）：深度未见三片全胜、post 三片全胜、post 月份双所 6 好 2 差（满足 ≥6/9），压力费仍胜（OKX post +63.4%/2.48 vs +55.9%/2.12，7/2 月；Gate +63.4%/2.57 vs +56.8%/2.15，6/2 月）。**但**：调参期三片全输（OKX 1.23 vs 1.47，Gate 1.15 vs 1.46，−30 pp）；安慰剂 −7d post 更好（OKX +69.2%/2.62，Gate +69.9%/2.64）、−14d 也 +62%，+7d 降到 +57.7%（< 基线）、+14d 崩到 +40%、+60d +33% → 无时点特异性且对小平移脆弱；邻域 r30 +57.8%、r21 +47%、r14 +52%、r120 +22.9%、长窗 540 +45.6%，仅 45–90 / 180–365 窄带成立；new8 pre 0.57/0.56 远差于基线 0.99/0.96，Gate post 0.51 vs 1.00 也输，月份 3/4。
- `sec_chg90_short_off`：post 最高但月份只有 5 个不同（<6），安慰剂 −7d post 同样 +70%，邻域 chg14/21/30 崩到 +6~27%，new8 pre 也更差。
- 两个 short_off 格本质相同：多数时间"监管冷清"即禁新空，post 收益来自 2026 年少做空，不是监管信息。

## 结论
**否决**（先验 / 回退均否决）。`all_r90gt365_short_off` 仅记为**非先验弱观察**（满足深度未见 + post 月份 6/9，但调参全输、平移安慰剂同样有效、邻域窄、new8 更差，未达到默认门槛中的"安慰剂 / 邻域支持"），**不实现、不改默认、不加模拟盘**。
勿重测：换窗口 A/B/W / z 阈值 / 侧，换检索词（加减 crypto / token / DeFi / NFT 等）、换机构（SEC↔CFTC↔FinCEN↔IRS↔OCC↔美联储）、换文件类型（规则 / 拟议规则 / 通知 / 总统文件）、用占全部文件比例、用 public-inspection 提前一日、用 Regulations.gov 意见数 / 国会法案数等同类"监管文本流量"替身。

## 文件
- 结果 CSV（不入库）：`output/research_federal_register_crypto_gate_4h.csv`、`output/research_federal_register_crypto_gate_4h_best_placebo_nbhd.csv`、`output/research_federal_register_crypto_gate_4h_new8.csv`；官方日度 `output/federal_register_crypto_official_daily.csv`。
- 脚本（不推送）：`scratch/fedreg4h/{fetch.py,run.py,prereg.py,supp.py,new8.py,stress2.py}`、`PRE_REGISTER.{json,csv,sha256}`、`run.log`。

下一轮（短线）：美股交易所官方停牌（Nasdaq Trader 官方 Trading Halts / LULD 暂停，含 halt 时刻与原因代码）日内爆发 → 8 币永续篮子 1h 事件（顺势 / 逆势）；已查 halt / LULD / 停牌（作为信号）0 条（不同于已否决的 VIX / Cboe 跨资产波动、日经开盘跳空、交易所状态事故），需先确认官方历史可免费下载、时间戳精确到秒。
