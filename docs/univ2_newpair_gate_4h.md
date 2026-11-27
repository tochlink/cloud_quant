# 长线新族：Uniswap V2 官方工厂新交易对创建（PairCreated，新币上线 / 投机狂热温度计）日度计数 → 4h 默认书入场闸门（2026-11-27 ~12:55–13:10 PST，研究，不改默认；否决）

## 查重
- `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,325 个）检索 paircreated / new pair / token launch / memecoin / meme：唯一先例是**短线 1h 突发事件** `output/research_univ2_paircreated_burst_event_1h.csv`（2026-11-21 否决），其勿重测条款覆盖 1h 突发的 L / k / H / 方向 / 配对口径 / 其他工厂；从未把新交易对创建作为 4h 默认书的慢体制入场闸门。
- 不同于已否决的 Safe ProxyCreation 4h 闸门（新建多签 = 机构入场）、ERC-4337 EntryPoint、ENS 注册、Arbitrum 规范桥、稳定币供给、ETH 满块率 / gas。
- 本轮另外检索并排除了（均已测或被勿重测覆盖）：EM 外汇（H.10 美元族勿重测）、费城联储 ADS（WEI 勿重测覆盖）、台湾三大法人（JPX 勿重测）、金银比 / 铜银比（铜金比勿重测、无免费官方日频白银）、Daniel–Moskowitz、摆动结构、MFE / 回吐 / 吊灯离场、均线收敛离场、CP 利差等。

## 数据（只用官方，不编造、不插值、不回补）
- 以太坊主网 Uniswap V2 Factory `0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f`，`PairCreated` 日志（`eth_getLogs`，块 10000835 起）：历史段（scratch/stablemint1h 抓取，至块 26462839）+ 实时记录器（同目录 record.py，至块 26508976 = 2026-11-27 20:35:35 UTC）。
- 完整性：合并后 528,873 条日志，allPairs 下标 1..528,873 连续，且等于块 26508976 上官方 `allPairsLength()` = 528,873。
- D 日计数 = 区块时间戳落在 UTC D 日的 PairCreated 数；只用完整 UTC 日：2020-05-06 → 2026-11-26 共 2,396 天，0 缺日，8 个真实 0 日（2020 年初）。最大 838 / 日；2026-11-24/25/26 = 73 / 63 / 112。
- 可用时刻：D 日值 D+1 01:00 UTC 才用，前向填充到 4h K 线。存 `output/univ2_paircreated_official_daily.csv`（不入库）。
- 交易数据：官方 OKX / Gate 4h（scratch/deep，回测到 2026-11-14），官方资金费；真实费（永续 taker 5.1 bps / maker 2 bps）+ 压力费（永续 taker 15.1 bps、现货 20 bps）。

## 公式与预注册
- 序列：cnt（日新交易对数）、ma7（7 日均值，需 7 天齐全）、ma28（28 日均值，需 28 天齐全）。
- 形式：trend = 值 > SMA(n)，n ∈ {30, 90, 180}；chg = n 日变化 > 0，n ∈ {30, 90}；z365 = (值 − SMA365) / STD365 > k，k ∈ {1, 1.5, 2}。flag=1 = 新币上线偏多 / 上升。
- 侧：long_off（flag=1 拦新多）、short_off（flag=0 拦新空）、both、contra_both（flag=0 拦多、flag=1 拦空）、cap_short_off（flag=1 拦新空）。只拦新开 / 反手，已有同向仓、止损、离场不变；NaN 不拦。
- 3 × 8 × 5 = 120 格 + 同脚本基线（S.DEFAULTS 双均线 50/150 4h 8 币）。经济先验（看结果前锁定）：投机狂热 = risk-on → cap_short_off / contra_both。
- 先验格 `ma7_trend_n90_cap_short_off`，回退 `ma28_trend_n180_cap_short_off`。PRE_REGISTER.json sha256 `a496d77668c17d6b52ae3274ce141c34579a94abf1e2da9d4d7eb4af3ad8ff19`（任何 PnL 之前锁定）。
- 评分：9 个 Sharpe 切片（OKX d8 2023-02-01 起、Gate d8 2022-07-01 起、OKX d7 去 BNB 2022-04-01 起 × 深未见 <2024-10-21 / 调参前段 / post ≥2026-03-05）。

## 结果（收益 %，Sharpe 为日 Sharpe 年化；post = 2026-03-05 → 2026-11-14）
| 样本 | 变体 | 深未见 收益 / Sh | 调参前段 收益 / Sh | post 收益 / 回撤 / Sh | post 月 好 / 差 |
| --- | --- | --- | --- | --- | --- |
| OKX d8 | 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / −10.61 / 2.23 | — |
| OKX d8 | 先验 ma7_trend_n90_cap_short_off | −18.59 / −0.30 | +105.30 / 1.72 | +36.21 / −12.95 / 1.54 | 1 / 7 |
| OKX d8 | 回退 ma28_trend_n180_cap_short_off | −1.95 / 0.07 | +49.09 / 1.04 | +24.17 / −13.10 / 1.37 | 3 / 5 |
| OKX d8 | 非先验 9/9 ma28_trend_n90_short_off | +41.38 / 0.84 | +91.29 / 1.58 | +71.01 / −10.61 / 2.64 | 3 / 4 |
| Gate d8 | 基线 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / −10.55 / 2.25 | — |
| Gate d8 | 先验 | −36.10 / −0.60 | +105.17 / 1.72 | +36.25 / −12.92 / 1.54 | 1 / 7 |
| Gate d8 | 回退 | −25.38 / −0.43 | +43.96 / 0.98 | +24.88 / −13.01 / 1.40 | 4 / 4 |
| Gate d8 | 非先验 9/9 | +4.40 / 0.21 | +97.80 / 1.64 | +71.80 / −10.55 / 2.67 | 4 / 3 |
| OKX d7 去 BNB | 基线 | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / −10.05 / 2.10 | — |
| OKX d7 去 BNB | 先验 | −5.81 / 0.03 | +103.59 / 1.73 | +28.43 / −12.61 / 1.33 | 2 / 6 |
| OKX d7 去 BNB | 回退 | +16.53 / 0.38 | +54.41 / 1.12 | +16.00 / −12.67 / 1.07 | 2 / 6 |
| OKX d7 去 BNB | 非先验 9/9 | +57.58 / 0.82 | +93.12 / 1.62 | +61.92 / −10.05 / 2.55 | 3 / 4 |

- 先验 3/9（只赢调参前段），post OKX −23.7 pp、Gate −24.1 pp；回退 0/9，post −35.7 / −35.4 pp。
- 全部 120 格：唯一 9/9 是非先验 `ma28_trend_n90_short_off`（只在新币上线高于 90 日均线时才允许开新空 = 反经济方向）；8/9 两个非先验 `cnt_chg_n90_both`、`cnt_trend_n180_both`（post 月份 4/3、5/2、4/4）。
- 压力费下 9/9 格 post OKX +68.21 / 2.57（基线 +55.94 / 2.12），Gate +69.19 / 2.60（+56.78 / 2.15）。
- 安慰剂（30 日块打乱 flag，种子 1–3）：先验 post OKX +27.3 / +53.8 / +43.3（真实 +36.2），回退 +57.1 / +63.1 / +53.6 全部好于真实（+24.2）→ 先验 / 回退无信息。先验时间平移最好 +180d 6/9 > 真实 3/9。
- 9/9 格（事后标注）时间平移：+14d post OKX +79.05 / Gate +79.52 高于真实 +71.01 / +71.80；±7d ≈ 真实；+180 / −120 / +365 / −119d post 降到 +33 ~ +46。
- 邻域（ma28_trend_n?_short_off，OKX d8 post）：n60 +39.10、n75 +60.89、n90 +71.01、n105 +73.81、n120 +69.33、n150 +40.28 → 两端崩塌（低于基线 +59.90 约 20 pp）。
- new8 未调币（OKX / Gate 官方 4h 最后 4500 根，2024-12-03 起；pre = 2026-03-05 前）：9/9 格 pre +8.15 / +6.65（基线 +33.92 / +31.70，大幅落后），post +12.70 / +27.06（基线 +3.26 / +16.36），月份 4/4、4/4；先验 pre ≈ 基线、post OKX +6.77 / Gate +6.42（Gate 基线 +16.36）；回退 pre / post 全输。

## 结论
**否决**，不改默认、不实现、不加纸面实例、无代码改动。先验 / 回退被安慰剂击败；唯一 9/9 是反经济方向的非先验格，post 逐月只有 3/4、4/3（未达 ≥6/9），邻域 n60 / n150 崩塌，new8 未调币 pre 段大幅落后，+14d 平移安慰剂 post 更好。

**勿重测**：不要以改 n / k / z 窗口 / 形式（trend / chg / z）/ 侧或方向、在 cnt / ma7 / ma28 / WETH 配对 / 稳定币配对 / 非 WETH 配对之间互换、改用 Uniswap V3 PoolCreated / V4 Initialize / Sushiswap / PancakeSwap / Base / Solana pump.fun 等其他工厂或链的新池 / 新币数、ERC-20 合约部署数、改发布滞后或换更早起点的方式重测本族（4h 闸门与已否决的 1h 突发合起来，新币上线节奏这一机制在两个周期都已覆盖）。

## 文件
- CSV（不入库）：`output/research_univ2_newpair_gate_4h.csv`（441 行，含邻域 / 安慰剂 / 压力费）、`_shuffle.csv`、`_posthoc_placebo.csv`、`_new8.csv`；官方日度 `output/univ2_paircreated_official_daily.csv`。
- 脚本（未推送）：scratch/univ2pair4h/{build,run,supp,supp2,new8}.py、PRE_REGISTER.json(.sha256)；模板 scratch/safe4h。
