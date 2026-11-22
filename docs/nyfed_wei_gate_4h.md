# 长线新族：纽约联储官方 Weekly Economic Index（WEI，ALFRED 实时 vintage）→ 4h 默认书入场闸门（2026-11-22 ~08:45–09:05 PST，研究，不改默认；否决）

状态：**否决**。不改默认、不加可选代码、不加纸面实例 / shadow；纸面 8788/8789/8792/8793/8794/8795/8796 照常运行（只纸面、live 关），8790 未触碰。

## 选题与查重

- 任务候选（a）BTC 哈希带 / 难度：已测（`output/research_btc_hash_ribbon_gate_4h.csv`、`research_btc_difficulty_adj_event_1h.csv`）；（b）T10Y2Y：2026-11-14「美债 10Y / 2s10s / WTI 均线趋势门控」已否决；（c）M2：`research_m2_money_supply_regime_gate_4h.csv`；（d）DEXJPUS：`research_fx_jpy_cny_trend_gate_4h.csv`；（e）BAMLH0A0HYM2：`research_financial_stress_credit_gate_4h.csv`。全部重复，跳过。
- 选定：纽约联储 WEI。rg `Weekly Economic Index / WEI / 纽约联储 WEI` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,182 个）：只在 WBTC 节前作为「下一轮」指针出现，无测试。不同于已否决的 GDPNow（季度 GDP 即时预测）、初请失业金、密歇根信心 / 零售 / 工业产出、NFCI / STLFSI / 信用利差、M2、政策利率 / 失业率、按揭 / 营建、TSA 出行。
- 机制：WEI 是 10 个周度实体活动指标的合成，按 4 季度 GDP 增速标定。活动改善 / 高于趋势 = 宏观 risk-on → 允许新多；走弱 → 拦新多。只拦新开仓，持仓 / 止损 / 出场不动。

## 数据（只用官方，不补缺、不插值、无修订前视）

- ALFRED（圣路易斯联储官方 vintage 存档）`alfredgraph.csv?id=WEI&vintage_date=周五`，2021-06-04 → 2026-11-20 共 **286 个周五 vintage**，每个 vintage 都包含当时可见的完整历史（2008 起）。每个 vintage 只用自身序列计算特征（实时，不用后来修订值）。
- 发布滞后：WEI 每周四发布；vintage 日 D（周五）的数据 **D+1 00:00 UTC** 起使用（保守 ~1.5 天），前向填充到 4h 开盘。vintage 末观测日与 vintage 日固定相差 6 天（一次 13 天：2026-11-20 vintage 未更新，沿用 11-07 观测），无缺口。
- 最新（2026-11-20 vintage）：WEI 3.29（周截至 2026-11-07）。官方周表 `output/nyfed_wei_realtime_official_weekly.csv`（不入库）。

## 预注册（`scratch/nyfed_wei4h/PRE_REGISTER.json`，2026-11-22 ~08:47 PST 锁定，sha256 `3a602073…b0ed`，先于任何 PnL）

- 形式 13 种：trend（WEI > 最近 n 周均值，n = 4 / 13 / 26 / 52）、chg（WEI > n 周前，n = 4 / 13 / 26）、z52（(WEI − 52 周均值) / 52 周标准差 > k，k = −0.5 / 0 / 0.5）、lvl（WEI > k%，k = 1 / 2 / 3）。
- 侧 5 种（flag = 1 = 经济改善）：long_off、short_off、both、contra_both、cap_long_off。13 × 5 = **65 格** + 同脚本基线。
- 先验侧 long_off / both；回退 `wei_trend_n13_long_off`。
- harness 与 cryptoeq4h / us_ipo_issuance4h 相同：官方 OKX / Gate 永续 + 现货 4h、官方资金费；OKX d8（2023-02-01）、Gate d8（2022-07-01）、OKX d7 去 BNB（2022-04-01）；深未见 → 2024-10-21，调参 → 2026-03-05，post → 2026-11-14；费用 taker 5.1 / maker 2 bps（压力 15.1 / 现货 20）；评分 = 3 组 × 3 段日 Sharpe 胜基线（9 分制）。基线与前几轮逐位一致（OKX d8 +35.14 / 0.71、+85.08 / 1.47、+59.90 / 2.23）。

## 结果（收益 % / 日 Sharpe；`output/research_nyfed_wei_gate_4h.csv` 252 行）

| 组 | 段 | 基线 | 先验最佳 `wei_chg_n4_long_off`（7/9） | 回退 `wei_trend_n13_long_off`（3/9） |
| --- | --- | --- | --- | --- |
| OKX d8 | 深未见 | +35.14 / 0.71 | **+22.64 / 0.54** | +38.75 / 0.78 |
| OKX d8 | 调参 | +85.08 / 1.47 | +91.72 / 1.56 | +77.68 / 1.43 |
| OKX d8 | post | +59.90 / 2.23 | +59.74 / 2.24（月 3/1） | +47.55 / 1.96（2/2） |
| Gate d8 | 深未见 | −3.63 / 0.09 | +3.58 / 0.19 | +15.57 / 0.35 |
| Gate d8 | 调参 | +84.25 / 1.46 | +88.24 / 1.53 | +76.81 / 1.42 |
| Gate d8 | post | +60.32 / 2.25 | +60.64 / 2.27（4/0） | +47.69 / 1.97（2/2） |
| OKX d7 去 BNB | 深未见 | +54.92 / 0.75 | **+42.13 / 0.63** | +63.64 / 0.83 |
| OKX d7 去 BNB | 调参 | +92.93 / 1.56 | +96.62 / 1.62 | +81.72 / 1.49 |
| OKX d7 去 BNB | post | +50.76 / 2.10 | +51.07 / 2.11（2/2） | +41.77 / 1.83（2/2） |

- 分布（65 格）：0/9 24、1/9 7、2/9 6、3/9 16、4/9 3、5/9 3、6/9 5、7/9 1、8/9 0、9/9 0。没有 8/9 或 9/9。
- **先验** `wei_chg_n4_long_off` 7/9，但深未见 3 组输 2（OKX d8 −12.5 pp、d7 −12.8 pp）；post 只差 −0.2 / +0.3 / +0.3 pp，逐月 3/1、4/0、2/2（只拦了极少几笔新多，远达不到 ≥ 6/9 月）。压力费同向（深未见 OKX +13.31 对 +24.67，post +56.01 对 +55.94）。
- 时间平移安慰剂（±7 / ±14 / +180 / −120 / +365 / −119 天）：最高 5/9（−14d），+180d 0/9；真实 7/9 只高于安慰剂 2 分，且来自调参段。
- 邻域（chg 换 n）：n2 3/9、n3 5/9（post −14 pp）、n6 6/9（Gate 深未见 −19.65%）、n8 3/9、n10 3/9、n17 2/9、n20 3/9 → 只在 n=4 单点成立。
- 未调参 new8（`_new8.csv`）：先验 OKX pre +44.30 → +67.12、post +3.26 → +10.84；Gate pre +41.55 → +64.38、post +16.36 → +25.70（逐月 3/1）；回退 pre 两所都更差（+22.63 / +20.55）。new8 好看，但 d8 深未见失败、逐月样本极少。
- 其余 6/9（`wei_z52gt0.5_long_off`、`wei_chg_n26_long_off`）调参段三组大幅落后（−20 ~ −35 pp）；`contra_both` 6/9 两格 post −40 ~ −50 pp。

## 结论

**否决**，不改默认、不实现、不列观察、不加纸面。WEI 周度实体经济改善 / 走弱对默认书新开仓没有稳定增量：先验最佳在深未见三组输两组，post 几乎不变且逐月不过半，邻域只在 n=4 成立，回退 3/9 且 post −12 pp。

**勿以改 n / 形式（trend / chg / z / lvl）/ 方向 / 阈值、换最新修订值代替实时 vintage、改发布滞后、换 WEI 的单个分项（初请、续请、零售同店、钢产量、燃料销售、铁路运量、税收、电力、Rasmussen 信心）、换 Lewis-Mertens-Stock 其它版本或改用 Dallas / 费城联储周度活动指数、或换更早起点的方式在现有历史上重测本族。**

- 文件（不入库）：`output/research_nyfed_wei_gate_4h.csv`（主网格 + 安慰剂 + 邻域 + 压力费）、`_new8.csv`；官方周表 `output/nyfed_wei_realtime_official_weekly.csv`；脚本 `scratch/nyfed_wei4h/{fetch,build,run,stress,new8}.py`、`PRE_REGISTER.json`。
- 下一轮（短线）：选一个未测过、官方逐小时数据覆盖 2022–2026 的 1h 事件族（先查重 docs / 侧文档 / output / 记忆），例如以太坊官方 Beacon 链 sync committee 参与率骤降 / 区块重组（reorg）1h 突发 → 8 币永续篮子（须先确认不同于已否决的 missed slot 1h 突发 `research_eth_missed_slot_burst_event_1h.csv`）。
