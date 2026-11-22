# 官方 NY Fed 一级交易商统计（国债结算失败 / 交易商国债净头寸）4h 入场闸门（否决）

## 长线新族：纽约联储官方 Primary Dealer Statistics 周度——国债结算失败（fails to deliver + fails to receive）与一级交易商美国国债（除 TIPS）净头寸 → 4h 默认书 #1 入场闸门（2026-11-22 ~01:20 PST，研究，不改默认；否决）

- 查重：文档 / output / 记忆中无 primary dealer / 交易商头寸 / 结算失败条目。相邻已否决族（不在此重测）：联储净流动性（WALCL/RRP/TGA）、SOFR−IORB、H.4.1 托管、H.6/H.8 货基与存款、信用利差 / NFCI / STLFSI、MOVE / 美债收益率波动、国债发行 / 拍卖、SLOOS。本轮机制：交易商中介能力 / 国债库存过剩与结算失败作为融资压力信号。
- 数据（只用官方 `markets.newyorkfed.org/api/pd`）：`/api/pd/list/timeseries.json`（1,539 个 keyid）；`/api/pd/get/<keyid>.json` 与按断点 `/api/pd/get/<SBN20xx>/timeseries/<keyid>.json` 逐段下载，四段（SBN2013 2013-04-03→2014-12-31、SBN2015 2015-01-07→2021-12-29、SBN2022 2022-01-05→2024-06-26、SBN2024 2024-07-03→）与合并 keyid **逐值完全一致**。所用 keyid：
  - `PDFTD-USTET` 国债（除 TIPS）交易商 fails to deliver；`PDFTR-USTET` fails to receive（$mn）。
  - `PDPOSGST-TOT` 国债（除 TIPS）交易商净头寸（多 − 空，$mn），2013→2026 最小 7,823、最大 557,087，无负值。
  - 回购融资 `PDSORA-UTSETTOT` / `PDSIRRA-UTSETTOT`：2022 后分别有 105 / 96 周被官方以 `*` 抑制 → **不用**（不补缺）。
  - 历史深度：API 中这些 keyid 只从 2013-04-03 起（SBP2013 段对这些 keyid 为空，1998–2013 旧表 keyid 不同，不拼接）。2013-04-03→2026-11-11 共 711 周，0 缺口。断点处水平连续（pos 112,641→112,141（2022-01）、296,491→312,736（2024-07）；fails 量级相同），但**跨断点的 1 周 / 4 周差分一律置 NaN**；滚动 z 允许 N−8 个有效值。交易回测从 2022-04 起，深度未见段覆盖 2022-07→2024-10-21（52 周 z 从 2014 年起即可算）。
  - 官方周表 `output/nyfed_primary_dealer_official_weekly.csv`（不入库，3,555 行：obs_date / keyid / seriesbreak / value_musd / suppressed / release_date_est / known_from_utc）。
- 时滞：NY Fed 官方说明“每周四约 16:15 ET 更新上周（周三截止）数据”，即周三 W 的数据在 W+8 周四 16:15 ET（≤21:15 UTC）发布；若周四为联储休市日（感恩节、7/4、6/19(2022+)、11/11、12/25、1/1）顺延到下一工作日。可用 = 发布日 + 1 天 00:00 UTC（发布后第一根 4h 棒；比“W+8 00:00 UTC”更保守，后者早于实际发布）。不回填，只持有最近一次发布的值。
- 公式（看 PnL 前锁定 `scratch/nyfedpd4h/PRE_REGISTER.csv`，sha256 c015610f…b563，2026-11-22 00:52 PST，128 格）：`fail` = log(FTD + FTR)，`pos` = 净头寸（$bn）。`d1z` / `d4z` = 1 周 / 4 周变化对过去 N 周（26 / 52 / 104）的 z > k（1 / 2）；`trend` = 水平 > SMA(N 周)（13 / 26 / 52 / 104）。flag=1 = 压力（失败激增 / 库存过剩）。旗标按观测顺序计算，挂到可用时刻，前向填充到 4h 棒。侧：long_off（flag=1 拦新多）、short_off（flag=0 拦新空）、both、contra_both；只拦新开仓，已有同向仓保留。2 序列 × 16 形式 × 4 侧 = 128 格。**先验** `fail_d4z_n52_gt1_long_off`；**回退** `pos_d4z_n52_gt1_long_off`。锁定前只看过旗标占比（非 PnL）。
- 交易与评价（复用 mmfh8_4h 模板，默认书 #1 双均线 50/150，同脚本基线）：官方 OKX / Gate 4h 现货 + 永续、官方资金费；OKX d8（2023-02-01 起）、Gate d8（2022-07-01 起）、OKX d7_noBNB（2022-04-01 起）× deep_unseen（→2024-10-21）/ tune_pre（→2026-03-05）/ post（→2026-11-14）= 9 段日 Sharpe；真实费率现货 10 / 永续 taker 5.1 bps，压力 20 / 15.1 bps；安慰剂平移 ±7 / ±14 / ±30 / +180 / +365 天；邻域 k 0.5/1.5/2.5、N 39/78、d1z↔d4z、trend N 8/20/39/78；未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI，两所最近 4500 根）。
- 同脚本基线：OKX d8 deep +35.14% / 0.71，tune +85.08 / 1.47，post +59.90 / 2.23；Gate d8 deep −3.63 / 0.09，tune +84.25 / 1.46，post +60.32 / 2.25；OKX d7 deep 0.75 / tune 1.56 / post +50.76 / 2.10。new8 pre / post Sharpe：OKX 1.01 / 0.28，Gate 0.99 / 1.00。
- 结果（`output/research_nyfed_primary_dealer_gate_4h.csv` 480 行；`_new8.csv`；补充邻域 / 安慰剂 `_supp.csv`、压力 `_supp_stress.csv`）：
  - **先验** `fail_d4z_n52_gt1_long_off`：**4/9**。只赢 deep（OKX 0.79 vs 0.71，Gate 0.15 vs 0.09，d7 0.81 vs 0.75）+ 一段 tune 微差；**post 与基线完全相同**（月份 0/0）。压力费 tune 持平 / 略输。new8 pre 1.04 / 1.02 略好，post 同基线。邻域 N39/N78/k1.5 4/9，k0.5/k2.5 0/9。安慰剂 −14d 6/9、−7d 3/9、+7d 4/9 → 不比真实差。
  - **回退** `pos_d4z_n52_gt1_long_off`：6/9（deep + tune 全赢：OKX 0.79 / 1.51，Gate 0.29 / 1.49），但 2026-03 后旗标 0 次触发，**post 与基线相同，月份 0/0**；安慰剂 −7d 6/9、+14d / +30d 5/9 → 无特异性；new8 pre 0.99 / 0.98 略输。
  - 全格最好（非先验）`fail_trend_n26_long_off`（失败额高于 26 周均线时拦新多）8/9：deep / tune 六段全赢（OKX deep +53.71 / 0.99、tune +96.39 / 1.61；Gate +18.34 / 0.39、+94.09 / 1.59），压力费同向（OKX 0.84 / 1.50 vs 0.56 / 1.35，Gate 0.24 / 1.48 vs −0.07 / 1.34）；邻域 N20 / N39 / N52 8/9、N78 7/9、N104 6/9、N13 5/9、N8 5/9（稳定）；安慰剂 −30d 6/9，其余 0–3/9；new8 pre 1.22 / 1.21 vs 1.01 / 0.99、post 0.68 / 1.36 vs 0.28 / 1.00（月份 3/1）。**但 post 收益落后**：OKX +57.01 / 2.26 vs +59.90 / 2.23，Gate +57.46 / 2.28 vs +60.32 / 2.25，2026-03 后月份只 2 好 / 2 差（两所），不满足 ≥6/9；且为看过全格后的非先验。
  - `fail_trend_n104_both` 6/9：post 最好（OKX +63.17 / 2.44，Gate +63.65 / 2.45，月份 4/4），new8 post 1.59 / 1.82，但 deep 被打穿（OKX +3.40 / 0.20，Gate −12.96 / −0.13），邻域 N78 / N8 4/9、N20 / N39 0/9 → 崩塌。
  - pos trend / short_off / contra_both 各格：tune 或 post 大幅变差（如 `pos_trend_n52_short_off` post +33.10 / 1.52）。
- 结论：**否决**（默认不变、无代码改动、仅文档）。先验 4/9 且 2026-03 后完全不触发；回退 post 不触发、安慰剂同样好；唯一稳健的 `fail` 水平 > 均线 long_off 系列在 2022–2026-03 改善 Sharpe，但 2026-03 后收益落后基线、月份 2/2，达不到默认门槛，也不是先验。
- **勿再测**：不得通过改 n / N、改侧、改 z 阈值 k、改 1 周↔4 周↔水平均线，或换序列（fails 交付 / 接收 / 合计、头寸 总额 / 票息 / 期限桶 / 短债、融资 回购 / 逆回购 / 净融资、公司债 / 机构债 / MBS 科目）来重测同一机制。
- 文件：`output/research_nyfed_primary_dealer_gate_4h.csv`、`_new8.csv`、`_supp.csv`、`_supp_stress.csv`、`output/nyfed_primary_dealer_official_weekly.csv`（均不入库）；脚本 `scratch/nyfedpd4h/{build,prereg,run,new8,supp,supp_stress}.py`、`PRE_REGISTER.csv(.sha256)`（未推送）。默认策略与纸面实例未改动。
- 下一轮做短线，先查重。
