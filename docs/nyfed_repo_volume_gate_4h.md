# 长线新族：纽约联储官方回购成交量（SOFR 总成交量 / TGCR 三方回购成交量 / FICC 清算 DVP 占比）→ 4h 默认书 #1 入场闸门（2026-11-27 ~23:00 PST，研究；否决，仅文档，不改默认、无纸面变更）

- 查重：本轮原计划「PBoC 社融存量或 G.19 消费信贷」——两者**都已测过并否决**（`docs/pboc_tsf_credit_gate_4h.md`、`docs/fed_g19_consumer_credit_gate_4h.md`，2026-11-27），且 G.19 勿重测已覆盖 H.8 消费贷款 / Z.1 家庭负债 / HHDC 等替身，M2、SLOOS、FINRA 融资余额也已否决，因此换题。rg `SOFR volume / volumeInBillions / repo volume / 回购成交量 / EFFR volume` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`：0 条。最接近的已否决族：`sofr_iorb_gate_4h`（SOFR − IORB **利差** = 资金压力的**价格**；其勿重测只禁换 SOFR 分位、TGCR / BGCR / EFFR / OBFR、RRP **利率**），美联储净流动性（WALCL / TGA / RRP）、NFCI / 金融压力、一级交易商头寸、MMF / H.8。回购融资的**数量**（美债杠杆 / 基差交易规模）从未测过，按新机制处理。
- 数据（只用官方，不编造、不插值、不回补）：NY Fed Markets API `https://markets.newyorkfed.org/api/rates/secured/{sofr,tgcr}/search.json` 官方 `volumeInBillions`，2018-04-02 → 2026-11-25 共 2,161 个营业日，成交量 0 缺失，最大间隔 4 个日历日。序列：`sofr_vol = ln(SOFR 成交量)`（全部隔夜美债回购）、`tgcr_vol = ln(TGCR 成交量)`（三方 GC 回购）、`dvp_share = (SOFR − TGCR)/SOFR`（FICC 清算 DVP / GCF 占比，近似对冲基金 sponsored repo 杠杆）。时滞：D 日数据于下一官方营业日 ~08:00 ET 发布 → 从该营业日 13:00 UTC 起才使用，再前向填充到 4h 棒。最新（2026-11-25）：SOFR 成交量 3,145 bn、TGCR 1,214 bn、DVP 占比 61.4%。官方日表 `output/nyfed_repo_volume_official_daily.csv`（不入库）。
- 公式（看 PnL 前锁定 `scratch/sofrvol4h/PRE_REGISTER.json`，sha256 `85298ef2…`，run.py sha256 `b8fcc289…`，120 格）：flag = 1 表示**回购融资量收缩**：trend（x < SMA n，n 30 / 90 个营业日观测）、chg（x − x[−n] < 0，n 20 / 60）、z（252 观测 z < −k，k 0.5 / 1 / 1.5 / 2）；侧 long_off（收缩 → 不新开多）、short_off（不收缩 → 不新开空）、both、contra_both、cap_short_off（收缩 → 不新开空）。闸门只拦新开仓，已有同向仓保留。经济先验：回购量收缩 = 杠杆去化 / 美元抵押流动性收紧 = risk-off。**先验 sofr_vol_trend_n90_long_off，回退 dvp_share_chg_n60_long_off**，安慰剂锚 = 先验（±30 / ±90 / +180 / −120 / +365 / −119 天平移）。
- 回测：同脚本默认 #1（双均线 50/150、perp_both 10×、官方资金费；结构同 `scratch/g19cc4h/run.py`），真实费 maker 2 / taker 5.1 bps，压力费 spot 20 / perp 15.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14（官方 4h 深缓存终点）；未调参 new8（OKX + Gate 最近 4500 根）。

## 结果（`output/research_nyfed_repo_volume_gate_4h.csv` 444 行；`_new8.csv` 16 行）

**没有 7/9、8/9 或 9/9。**

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | OKX post 收益 / Sharpe | Gate d8 深未见 / 调参 | Gate post | post 月胜 / 负（OKX、Gate） | new8 post Sharpe（OKX、Gate） |
|---|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | +59.90% / 2.23 | 0.09 / 1.46 | +60.32% / 2.25 | — | 0.28、1.00 |
| **先验 sofr_vol_trend_n90_long_off** | 2/9 | 0.75 / 1.45 | +39.55% / 1.82 | 0.00 / 1.44 | +39.55% / 1.82 | 1/3、1/3 | −0.03、0.76 |
| **回退 dvp_share_chg_n60_long_off** | 0/9 | 0.20 / 1.23 | +48.36% / 1.93 | 0.02 / 1.22 | +48.91% / 1.95 | 1/3、1/3 | 0.96、1.58（pre 0.52 / 0.50 vs 0.72 / 0.69） |
| 9 段最高 dvp_share_trend_n30_short_off | 6/9 | 0.34 / 1.63 | +61.64% / 2.29 | −0.22 / 1.68 | +62.17% / 2.31 | 3/6、4/5 | 0.70、1.37 |
| tgcr_vol_chg_n20_cap_short_off（post 最高之一） | 4/9 | 0.51 / 1.48 | +66.73% / 2.51 | −0.08 / 1.42 | +67.72% / 2.54 | 4/4、4/4 | — |

- **先验（SOFR 成交量跌破 90 日均线 → 不新开多）**：2026-03 后美债回购量见顶回落，flag 在 post 占 78%（深未见 12%、调参窗 5%），大量拦多：post 两家都 −20 pp（+39.55% vs +59.90% / +60.32%），月份 1/3；深未见只在 OKX 小胜（0.75 vs 0.71），Gate 输 → 2/9。安慰剂平移 +30d / +90d 有 5/9，比真实更好；压力费同向（OKX post +36.55% vs +55.94%）→ 否决。
- **回退（DVP 占比 60 日下降 → 不新开多）**：九段全输（深未见 OKX 0.20 vs 0.71）→ 0/9。new8 post 虽高（OKX 0.96 vs 0.28），但 new8 pre 更差（0.52 / 0.50 vs 0.72 / 0.69），不算未见成立。
- 9 段最高 dvp_share_trend_n30_short_off（DVP 占比不低于 30 日均线 → 不新开空）是非先验侧；6 胜来自调参窗 + post，深未见三处大输（OKX 0.34 vs 0.71、Gate −0.22 vs 0.09，压力费 Gate −0.36 vs −0.07）；post 只多 +1.7 / +1.9 pp，月份 3/6、4/5 远低于 6/9；邻域 n20 / 45 / 60 / 120 / 180 / 250 全部只有 0–2/9、post 都不高于基线 → 塌陷，否决。
- tgcr_vol_chg_n20_cap_short_off post +6.8 / +7.4 pp，但深未见与调参窗输、月份 4/4，且同序列 chg_n20_both post 为 −9%（侧一换即崩），属单段巧合。z 类格在深未见 / 调参窗从不触发（回购量 2018 → 2026 结构性上升，z<−k 只在 2026 出现）。
- 结论：**否决**，不实现、不进观察名单、不改默认、无纸面变更、无代码改动。美债回购成交量是随美债供给结构性增长的慢变量，2026-03 后的回落与币价走势只在 post 单段重叠；没有格同时在深未见、调参窗和 post 成立，安慰剂不弱于真实。
- 勿重测（never retest via）：不要换 n / z 窗 / 阈值 / 侧 / 滞后重测本族；不要在 SOFR / TGCR / BGCR 成交量、DVP 占比、GCF 量、水平 / 同比 / 变动之间换序列；不要改用 OFR 回购市场监测（DVP / GCF / 三方分项量）、FICC sponsored repo 量、EFFR / OBFR 成交量、美联储 ON RRP 使用量、一级交易商融资（FR 2004 financing）或 CFTC 美债期货杠杆基金空头（基差交易代理）这类「美元回购 / 货币市场**数量**」替身重测；连同 SOFR−IORB 利差族，**美国货币市场管道（价格与数量）类 4h 闸门视为全部覆盖**。
- 文件：`output/research_nyfed_repo_volume_gate_4h.csv`、`_new8.csv`、`output/nyfed_repo_volume_official_daily.csv`（均不入库）；脚本 `scratch/sofrvol4h/{build,run,new8}.py`、`{sofr,tgcr,bgcr}.json`、`PRE_REGISTER.json(.sha256)`（不推送）。因 `docs/STRATEGY_FORMULAS.md` 超过 GitHub 连接器写入上限，本段写在本 sidecar（本地 STRATEGY_FORMULAS.md 同步追加一行轮换记录）。
- 下一轮（短线）：以太坊主网官方新合约部署数（官方 `eth_getBlockReceipts` 中 `contractAddress` 非空的交易笔数，按块头时间归整点小时，2022 起）1h 突发（L 小时 z）→ 8 币永续篮子 1h 顺势 / 逆势事件（下一根 1h 入场）。查重：docs / `output/research_*.csv` 无合约部署计数条目（Coinbase 溢价 1h、Kraken 欧元溢价、OKX 保险基金、信标参与率 / 漏槽、难度调整都已测或被勿重测覆盖，不选）；须先确认不被 `univ2_newpair_gate_4h`（只禁 DEX 交易对 / 池创建）与 `eth_onchain_demand_gate_4h`（gas / 燃烧 / 笔数）勿重测覆盖，若 RPC 回填超过一轮时长就换题。
