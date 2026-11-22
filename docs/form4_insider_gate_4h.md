# 长线新族：SEC EDGAR 官方 Form 4 加密敞口美股内部人公开市场买卖 → 4h 默认书入场闸门（2026-11-22 ~10:05–10:25 PST，研究，不改默认；否决）

状态：**否决**。不改默认、不加可选代码、不加纸面实例 / shadow；纸面 8788/8789/8792/8793/8794/8795/8796 照常运行，8790/8791 未触碰。

## 选题与查重（中英双语）

- rg `Form 4 / form4 / insider / 内部人 / 高管减持 / 董事` 于 `docs/STRATEGY_FORMULAS.md`（含轮换表）、`docs/*.md`、`output/research_*.csv` 文件名、记忆：**0 条已测**。
- 不同于 `edgar_crypto_mentions_gate_4h`（申报文本里的加密关键词命中）、`edgar_crypto_etf_s1_event_1h`（单币 ETF S-1 事件）、`us_ipo_issuance_gate_4h`（form.idx S-1/424B/Form D 计数）、`us_megacap_earnings_8k_event_1h`（8-K 财报时点）、`crypto_equity_relstrength_gate_4h`（加密股价格相对强弱）。
- 机制：加密敞口公司的内部人在加密狂热时公开市场卖出（Form 4 非衍生交易代码 S）；30/60 日内部人卖出重 / 上升 = 加密顶部 / 风险偏好下降 → 拦新多（或倾斜：卖出重拦新多、卖出轻拦新空）。只拦新开仓，持仓 / 止损 / 出场不动。

## 公司清单（看任何 Form 4 数据和 PnL 之前锁定，`scratch/form4insider4h/COMPANIES.json`）

COIN 1679788、MSTR 1050446、MARA 1507605、RIOT 1167419、CLSK 827876、HUT 1964789（新 Hut 8 Corp）、CIFR 1819989、BTBT 1710350、HOOD 1783879、GLXY 1859392、WULF 1083301、CORZ 1839341。规则：美股上市、境内申报人（内部人须报 Form 4）、主业为加密交易所 / 券商、BTC 金库或美股上市矿企 / 托管。排除 IREN / BTDR / HIVE / BITF（外国私人发行人，内部人不报 Form 4）与 XYZ（Block，加密占毛利比例小）。

## 数据（只用官方，不补缺、不插值）

- `https://data.sec.gov/submissions/CIK##########.json`（含 `files` 旧页）列出 form "4"（4/A 剔除，避免重复计数），acceptanceDateTime ≥ 2020-01-01；逐份从 `https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}` 取 Form 4 XML，≤ 7 req/s，断点续传。
- 3,591 份索引 → 4/A 60 份剔除、issuerCik 不符 34 份剔除（HOOD 页下 issuer 为 CIK 2085091 的申报），**3,497 份解析**；0 份 404 / 解析失败。时间 2020-02-06 → 2026-11-20 21:05 UTC。含 ≥1 笔公开市场 S 的申报 1,418 份（S 交易 7,400 笔，约 137.5 亿美元）；含 P 的 140 份（约 2.66 亿美元）。各家：COIN 686（S 438）、HOOD 731（300）、MSTR 420（302）、CIFR 261（82）、MARA 254（95）、WULF 362（21）、RIOT 226（50）、CLSK 217（32）、CORZ 161（55）、HUT 79（20）、GLXY 71（22）、BTBT 29（1）。
- 时区：data.sec.gov 的 acceptanceDateTime 已是 UTC（核对 CORZ 0001209191-22-033325 SGML 头 ACCEPTANCE-DATETIME 20220601205243 ET = 2022-06-02T00:52:43Z）。可用时刻 = 受理之后的第一根 4h bar 开盘（滚动和只计 [t − 窗口, t) 内受理的申报）。
- 官方日表 `output/form4_insider_official_daily.csv`（UTC 受理日 2,480 个日历日 2020-02-06 → 2026-11-20，1,029 日有申报，其余为 0 = 当日无申报；不入库）。
- 已知偏差：公司集合随时间扩大（HOOD 2021-07 上市、CIFR / CORZ SPAC、HUT 新 CIK 2023-12、GLXY 2025-05），水平值有上升趋势；trend / chg / z 形式部分抵消。10b5-1 计划卖出未剔除（全部公开市场 S）。

## 预注册（`scratch/form4insider4h/PRE_REGISTER.json`，2026-11-22 10:11 PST 锁定，sha256 `baf4c755…fe977`，先于任何 PnL）

- 序列：`scnt` = log1p(30 日含 S 的 Form 4 份数)；`susd` = log1p(30 日 S 美元额)；`net` = 60 日（含 S 份数 − 含 P 份数）。flag = 1 = 内部人卖出重 / 上升。
- 形式 8 种：trend（s > SMA_n，n = 20 / 60 / 120 日）、chg（s − s_{−n} > 0，n = 20 / 60）、z（(s − SMA252d) / STD252d > k，k = −0.5 / 0 / 0.5）。侧 5 种：long_off、short_off、both、contra_both、cap_long_off。3 × 8 × 5 = **120 格** + 同脚本基线。
- 先验侧 cap_long_off / contra_both（精确匹配）；回退 `susd_trend_n60_cap_long_off`。
- harness 与 `scratch/us_ipo_issuance4h/run.py` 完全相同（只换数据块，日 → 4h bar 换算 ×6）：官方 OKX / Gate 永续 + 现货 4h、官方资金费；OKX d8（2023-02-01）、Gate d8（2022-07-01）、OKX d7 去 BNB（2022-04-01）；深未见 → 2024-10-21，调参 → 2026-03-05，post → 2026-11-14（磁盘上最新官方 4h K 线）；费用 taker 5.1 / maker 2 bps（压力 15.1 / 现货 20）；评分 = 3 组 × 3 段日 Sharpe 胜基线（9 分制）。

## 结果（收益 % / 日 Sharpe；`output/research_form4_insider_gate_4h.csv` 441 行）

| 组 | 段 | 基线 | 先验最佳 `scnt_z252gt0_contra_both`（7/9） | 回退 `susd_trend_n60_cap_long_off`（3/9） | 先验 `net_z252gt0_contra_both`（6/9） | 非先验 `susd_trend_n20_short_off`（7/9） |
| --- | --- | --- | --- | --- | --- | --- |
| OKX d8 | 深未见 | +35.14 / 0.71 | +37.93 / 0.84 | +61.24 / 1.07 | +52.83 / 1.10 | +37.40 / 0.77 |
| OKX d8 | 调参 | +85.08 / 1.47 | +81.12 / 1.52 | **+12.29 / 0.42** | **+26.00 / 0.80** | +100.17 / 1.68 |
| OKX d8 | post | +59.90 / 2.23 | +57.14 / 2.30（月 3/3） | +59.90 / 2.23（0/0） | +69.10 / 2.58（4/2） | +56.79 / 2.24（6/3） |
| Gate d8 | 深未见 | −3.63 / 0.09 | +19.09 / 0.41 | +12.09 / 0.31 | +27.63 / 0.56 | −9.34 / −0.03 |
| Gate d8 | 调参 | +84.25 / 1.46 | +82.33 / 1.53 | **+11.32 / 0.40** | **+20.90 / 0.69** | +99.32 / 1.67 |
| Gate d8 | post | +60.32 / 2.25 | +57.66 / 2.32（3/3） | +60.32 / 2.25（0/0） | +69.90 / 2.61（5/1） | +57.43 / 2.26（6/3） |
| OKX d7 去 BNB | 深未见 | +54.92 / 0.75 | +43.14 / 0.72 | +66.21 / 0.88 | +50.27 / 0.88 | +39.44 / 0.63 |
| OKX d7 去 BNB | 调参 | +92.93 / 1.56 | +80.89 / 1.54 | +22.14 / 0.62 | +25.40 / 0.79 | +104.20 / 1.74 |
| OKX d7 去 BNB | post | +50.76 / 2.10 | +51.45 / 2.25（4/2） | +50.76 / 2.10（0/0） | +61.83 / 2.55（5/1） | +50.06 / 2.15（6/3） |

- 分布（120 格）：0/9 28、1/9 10、2/9 14、3/9 51、4/9 4、5/9 2、6/9 9、7/9 2、8/9 0、9/9 0。**无 8/9、无 9/9**。
- **先验最佳** `scnt_z252gt0_contra_both`（7/9）：d7 深未见 / 调参落后；post 收益三组里两组低于基线（OKX −2.8、Gate −2.7 pp），逐月 3/3、3/3、4/2（远达不到 ≥ 6/9）。时间平移安慰剂：+7d 5/9、−7d 4/9、−14d 3/9、+180d 3/9、+365d 3/9、+14d 2/9、−120d 0/9、−119d 0/9（真实值高于安慰剂）。邻域（事后补充，`_supp.csv`，同侧改 k）：k −0.5 5/9、−0.25 6/9、**0 7/9**、0.25 3/9、0.5 1/9、0.75 0/9、1.0 1/9 → 只在 k ≤ 0 附近成立，k > 0 崩塌（post −15 pp）。压力费同向（post 逐月不变）。未调参 new8：OKX pre +44.30 → +31.34、post +3.26 → +5.52（5/1）；Gate pre +41.55 → +31.07、post +16.36 → +18.94（5/1）——pre 段变差。先验否决。
- **回退** `susd_trend_n60_cap_long_off` 3/9：调参段三组 −70 pp，post 与基线完全相同（post 期内未拦到新多）。否决。
- 先验侧 `net_z252gt0_contra_both`（6/9）：post 最强（+9 ~ +11 pp，逐月 4/2、5/1、5/1，仍未达 ≥ 6），但调参段三组 −59 ~ −68 pp，邻域 k −0.25 6/9、0.25 1/9、0.75 1/9、1.25 4/9、1.5 3/9 → 不稳。new8 pre 段 −24 pp。否决。
- 非先验 `susd_trend_n20_short_off`（7/9，事后，不能晋升）：post 收益三组都低于基线，Gate 深未见 −5.7 pp。
- 结论：**否决**，不改默认、不实现、不列观察、不加纸面。先验（内部人卖出重 → 拦新多 / 倾斜）虽胜过时间平移安慰剂，但 post 三组收益不增、逐月 3/3，邻域 k > 0 崩塌；回退与 net 版本调参段大幅落后。

**勿以改 n / k / 形式（trend / chg / z）/ 方向、换 scnt ↔ susd ↔ net ↔ 只算 P 买入、改滚动窗口（30 / 60 日以外）、剔除 / 只用 10b5-1、加减公司（含 Block / 外国矿企 / 新上市加密股）、换衍生交易（期权行权 M / 赠与 G / 扣税 F）、或换更早起点的方式在现有历史上重测本族。**

- 文件（不入库）：`output/research_form4_insider_gate_4h.csv`（主网格 + 安慰剂 + 邻域 + 压力费）、`_supp.csv`（先验最佳的邻域）、`_new8.csv`；官方日表 `output/form4_insider_official_daily.csv`；脚本 `scratch/form4insider4h/{fetch,build,run,supp,new8}.py`、`COMPANIES.json`、`PRE_REGISTER.json`。
