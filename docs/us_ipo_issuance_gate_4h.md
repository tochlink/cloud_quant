# 长线新族：SEC EDGAR 官方美股发行窗口（S-1/F-1 新注册、424B4/424B1 定价招股书、Form D 私募）→ 4h 默认书入场闸门（2026-11-22 ~07:55–08:30 PST，研究，不改默认；否决）

状态：**否决**。不改默认、不加可选代码、不加纸面实例 / shadow；纸面 8788/8789/8792（及 8793/8794/8795）照常运行，8790 未触碰。

## 选题与查重（中英双语）

- 候选 1「OKX 官方交割（季度 / 次季）合约年化基差期限结构」：**重复**。`docs/STRATEGY_FORMULAS.md` 2026-11-10「期货期限结构（季度交割合约年化基差）」已测（z 顺势 / 反向、基差动量、**远近月斜率**、绝对水平，`output/research_futures_term_structure_gate.csv`，否决）；CME 基差版本在 `npm_crypto_dev_downloads_gate_4h.md` 因同机制 + 无免费官方历史放弃。同机制，跳过。
- 候选 2「Deribit 期权隐含偏斜（25d RR / 认沽认购 IV 偏斜）」：**重复**。2026-11-14「长线新族：Deribit 期权偏斜 / 看跌看涨成交比 / 主动买看跌净需求 4h 闸门」已否决（history.deribit.com 官方逐笔，OTM 认沽 − 认购量加权 IV，`output/research_deribit_options_skew_flow_regime_gate_4h_{BTC,ETH}.csv`）；`skew_follow / skew_contra` 是币自身收益偏度闸门（另一族）。跳过。
- 候选 3（自选）排除：NAAIM Exposure Index（2026-08-01 起改订阅制，无免费官方历史）、AAII 情绪（官方 xls 403 Incapsula）、OKX 风险准备金 / 保险基金（官方接口无历史，只有分钟级 regular_update）、BitMEX 保险基金（403 地域封禁）、Uniswap PairCreated 4h（与已否决 univ2_paircreated 1h 同机制，有勿重测条款）。
- 选定：美股发行窗口。rg `IPO / S-1 / F-1 / 424B / Form D / issuance window / 发行窗口 / 新股 / 首发 / form.idx` 于 `docs/STRATEGY_FORMULAS.md`（含轮换表）、`docs/*.md`、`output/research_*.csv` 文件名、记忆：0 条已测。不同于 `edgar_crypto_mentions_gate_4h`（文件里的加密关键词命中）、`edgar_crypto_etf_s1_event_1h`（单币 ETF S-1 事件）、`us_debt_issuance_gate_4h`（国债发行）、FINRA 融资余额 / CFTC COT（持仓）。宏观排除清单（TGA/RRP/SOFR/VIX/MOVE/NFCI/DXY/breakeven/yen/gold/copper/CNH/KRW/IBIT/HKMA/H.4.1/put-call/MSTR）均未使用。
- 机制：美股 IPO 注册（S-1/F-1）、定价招股书（424B4/424B1）、私募募资（Form D）= 资本市场供给侧风险偏好周期。发行窗口火热 = risk-on 允许新多；冷 = 拦新多。只拦新开仓，持仓 / 止损 / 出场不动。

## 数据（只用官方，不补缺、不插值）

- SEC EDGAR 季度总索引 `https://www.sec.gov/Archives/edgar/full-index/{YYYY}/QTR{q}/form.idx`，2018Q1 → 2026Q4（Last Data Received: November 21, 2026），按 Form Type + Date Filed 逐条计数。
- 2,262 个申报营业日 2018-01-02 → 2026-11-20；8 个零星周末日期（1–13 笔）剔除；缺失工作日全部为联邦假日 / 闭馆日（无其他缺口）。官方日计数 `output/us_ipo_issuance_official_daily.csv`（不入库）。
- 序列（20 营业日滚动计数的 log1p）：`s1` = S-1 + F-1；`px` = 424B4 + 424B1；`formd` = Form D。最新 20 日计数（截至 2026-11-20）：s1 82、px 31、formd 3,382。
- 可用时刻：Date Filed = D（美东）的申报 **D+1 04:00 UTC** 起使用（EDGAR 受理截至 22:00 ET）；按 4h 开盘前向填充。

## 预注册（`scratch/us_ipo_issuance4h/PRE_REGISTER.json`，2026-11-22 08:05 PST 锁定，sha256 `35f1863a…0fdaa`，先于任何 PnL）

- 形式 8 种：trend（s > SMA_n，n = 20 / 60 / 120 营业日）、chg（s − s_{−n} > 0，n = 20 / 60）、z（(s − SMA252) / STD252 > k，k = −0.5 / 0 / 0.5）。
- 侧 5 种（flag = 1 = 发行火热）：long_off、short_off、both、contra_both、cap_long_off。3 × 8 × 5 = **120 格** + 同脚本基线。
- 先验侧 long_off / both（精确匹配）；回退 `px_trend_n60_long_off`。
- harness 与 hkmaliq4h / cryptoeq4h 相同：官方 OKX / Gate 永续 + 现货 4h、官方资金费；OKX d8（2023-02-01）、Gate d8（2022-07-01）、OKX d7 去 BNB（2022-04-01）；深未见 → 2024-10-21，调参 → 2026-03-05，post → 2026-11-14；费用 taker 5.1 / maker 2 bps（压力 15.1 / 现货 20）；评分 = 3 组 × 3 段日 Sharpe 胜基线（9 分制）。

## 结果（收益 % / 日 Sharpe；`output/research_us_ipo_issuance_gate_4h.csv` 450 行）

| 组 | 段 | 基线 | 先验最佳 `s1_chg_n60_both`（6/9） | 回退 `px_trend_n60_long_off`（2/9） | 非先验 `formd_chg_n60_contra_both`（9/9） | 非先验 `s1_chg_n20_short_off`（9/9） |
| --- | --- | --- | --- | --- | --- | --- |
| OKX d8 | 深未见 | +35.14 / 0.71 | +55.79 / 1.06 | +34.26 / 0.71 | +69.44 / 1.17 | +45.14 / 0.87 |
| OKX d8 | 调参 | +85.08 / 1.47 | **+53.46 / 1.15** | +76.09 / 1.42 | +80.40 / 1.51 | +145.01 / 2.04 |
| OKX d8 | post | +59.90 / 2.23 | +66.28 / 2.51（月 4/3） | +39.53 / 1.86（1/3） | +58.88 / 2.27（4/5） | +63.11 / 2.31（4/4） |
| Gate d8 | 深未见 | −3.63 / 0.09 | +25.30 / 0.49 | −1.47 / 0.11 | +38.98 / 0.66 | −1.91 / 0.10 |
| Gate d8 | 调参 | +84.25 / 1.46 | **+54.69 / 1.17** | +74.44 / 1.40 | +77.05 / 1.46 | +145.88 / 2.04 |
| Gate d8 | post | +60.32 / 2.25 | +66.52 / 2.53（4/3） | +39.78 / 1.87（1/3） | +59.65 / 2.29（4/5） | +64.02 / 2.34（3/5） |
| OKX d7 去 BNB | 深未见 | +54.92 / 0.75 | +64.77 / 0.93 | +50.45 / 0.72 | +96.11 / 1.20 | +52.42 / 0.75 |
| OKX d7 去 BNB | 调参 | +92.93 / 1.56 | **+49.58 / 1.12** | +97.11 / 1.67 | +87.75 / 1.60 | +145.77 / 2.09 |
| OKX d7 去 BNB | post | +50.76 / 2.10 | +59.26 / 2.42（2/4） | +38.08 / 1.84（1/3） | +55.21 / 2.28（5/4） | +53.92 / 2.18（4/4） |

- 分布（120 格）：0/9 27、1/9 17、2/9 11、3/9 36、4/9 5、5/9 6、6/9 13、7/9 1、8/9 2、9/9 2。两个 9/9 都**不是**先验侧。
- **先验**：最佳只有 6/9（`s1_chg_n60_both`、`s1_chg_n60_long_off`、`px_chg_n60_*`、`formd_z252gt-0.5_long_off` 等），6/9 格都输在调参段；安慰剂锚点 `s1_chg_n60_both` 三组调参段落后 −30 ~ −43 pp。压力费同向（调参 OKX +47.49 对 +75.18）。时间平移安慰剂：**+180d 8/9 强于真实 6/9**，+365d 5/9，±7d 3/9，其余 0–2/9。邻域（同侧改 n）：n10 2/9、n15 5/9、n30 3/9（post 三组 −12 ~ −16%）、n40 2/9、n80 7/9、n100 5/9、n150 1/9、n200 0/9 → 不稳。先验否决。
- **回退** `px_trend_n60_long_off` 2/9，post 三组 −20 pp。否决。
- **非先验 9/9（事后，不能晋升）**：
  - `formd_chg_n60_contra_both`（Form D 60 日上升 → 拦新多、下降 → 拦新空，反向用法）：深未见三组 +34 ~ +42 pp，但 post 收益 OKX −1.0 / Gate −0.7 / d7 +4.5 pp、逐月 4/5、4/5、5/4（达不到 ≥ 6/9）；补充安慰剂（`_supp.csv`）最多 6/9（+14d），邻域 n30 3/9、n40 4/9、n80 / n100 5/9 → 只在 n=60 成立。未调参 new8：OKX pre +44.30 → +53.32、post +3.26 → +22.73，Gate pre +41.55 → +51.66、post +16.36 → +22.59（逐月 5/4）。
  - `s1_chg_n20_short_off`（S-1 20 日上升 → 拦新空）：收益几乎全来自调参段（+60 pp），Gate 深未见只 +1.7 pp，压力费下 d7 深未见反而更差（+40.41 对 +41.68）；post 逐月 4/4、3/5、4/4；邻域 n10 4/9、n15 7/9、n30 6/9（post 逐月 0/8）、n40 3/9。
- 结论：**否决**，不改默认、不实现、不列观察、不加纸面。先验（发行窗口冷 → 拦新多）在调参段三组全面变差，且被 +180d 安慰剂超越；回退 2/9；两个非先验 9/9 post 逐月都不过半，邻域只在单点成立。

**勿以改 n / 形式（trend / chg / z）/ 方向、换 S-1 ↔ F-1 ↔ 424B4 ↔ 424B1 ↔ Form D ↔ S-1/A ↔ EFFECT ↔ RW（撤回）、改滚动窗口（20 日以外）、改用金额（发行规模）、换 SPAC / 单只 IPO 首日表现、或换更早起点的方式在现有历史上重测本族。**

- 文件（不入库）：`output/research_us_ipo_issuance_gate_4h.csv`（主网格 + 安慰剂 + 邻域 + 压力费）、`_supp.csv`（非先验 9/9 的安慰剂 / 邻域）、`_new8.csv`；官方日计数 `output/us_ipo_issuance_official_daily.csv`；脚本 `scratch/us_ipo_issuance4h/{fetch,build,run,supp,new8}.py`、`PRE_REGISTER.json`。
- 下一轮（长线）：选一个未测过、官方日度历史覆盖 2021–2026 的 4h 默认书入场闸门族；先查重 docs / 侧文档 / output / 记忆（NAAIM / AAII 无免费官方历史，勿再选）。
