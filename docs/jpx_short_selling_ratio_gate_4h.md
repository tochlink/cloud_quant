# 长线新族：东证（JPX）官方月度「空売り集計」空卖比率 → 4h 默认书 #1 入场闸门（2026-11-27 ~21:25–21:40 PST，研究，不改默认；否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 已超过 GitHub 连接器写入上限，只在本地追加）。

- 换题：上一轮指针「JSDA 按投资者类别的公社债店头売買高 → 外国人净买入日债（JGB）」**不跑，属重复**：`docs/mof_resident_foreign_bond_flow_gate_4h.md` 的勿重测明确禁止「改用……非居民买日债 / 日股」，而财务省 week.csv 本身就带有非居民买日本中长期债的同一资金流；JSDA 只是另一个统计口径。
- 查重（替代题）：`docs/STRATEGY_FORMULAS.md`、全部 `docs/*.md`、`output/research_*.csv`（约 1,390 个）、`scratch/` 目录名、`scratch/ROTATION_LOCK.txt` 检索 空売り / short-selling ratio / 空卖比率 / 卖空比率：0 命中。不同于 `finra_short_volume`（美股加密代理股场外卖空成交，勿重测只覆盖美股篮子）、`cn_margin_financing`（其勿重测禁的是日本**信用取引残高**，是另一张 JPX 表）、`jpx_foreign_investor_flow`（按投资者类别净买入）。
- 机制：东证全市场空卖比率 = 现货成交中空卖（含信用卖空）所占比例。偏高 / 上升 = 亚洲最大发达股市的对冲 / 看空仓位增加 = 全球 risk-off → 经济先验「不新开多」（long_off / both）；`cap_short_off` / `contra_both` 检验反向（空头回补）说法。
- 数据（只用官方，不编造、不插值、不回补）：JPX「空売り集計（月間）」PDF（`jpx.co.jp/markets/statistics-equities/short-selling/01.html` 及 `01-archives-01..05.html`），官方只回溯到 **2021-01**，2021-01 → 2026-10 共 **70 个月，0 缺口**；每份 PDF 一行：实注文 a、空売り（价格规制あり）b、（价格规制なし）c、合计 d（百万日元），a+b+c=d 全部核对通过。`ss = (b+c)/d`，`nr = c/d`。最新 2026-10：ss 40.11%、nr 7.15%。日度 PDF 只保留约 13 个月，不用。
- 可用时点：每份 PDF 抬头印有发布日（M+1 月第 4~11 天），M 月值自 **发布日 + 1 天 00:00 UTC** 起才用。官方表 `output/jpx_short_selling_official_monthly.csv`（不入库）。
- 公式（看 PnL 前锁定 `scratch/jpxshort4h/PRE_REGISTER.json`，sha256 `afd31ed0…099ec`，2026-11-27 21:27 PST，50 格）：x = 序列的 3 个月均值；flag = 1 表示空卖比率偏高 / 上升：
  `trend_n{12,6}`：x > 该序列近 N 月均值；`chg_n{3,1}`：x − x(N 月前) > 0；`z_k1`：x 的 24 个月 z > 1。2 序列 × 5 形式 × 5 侧（long_off / short_off / both / contra_both / cap_short_off），只拦新开仓，已有同向仓位不动。
  先验 `ss_trend_n12_long_off`，回退 `ss_chg_n3_long_off`；安慰剂 = 先验 + 回退各 8 个时移（±30 / ±90 / +180 / −120 / +365 / −119 天）。
  - 预注册缺陷（如实记录）：x 是 3 个月均值时，`trend_n6`（x > 6 月均值）与 `chg_n3`（x > x(3 月前)）在数学上等价，所以 50 格里有 10 对完全相同，独立格只有 40 个。
- 回测：同脚本默认 #1（双均线 50/150，8 币 perp_both，官方资金费），官方 OKX / Gate 4h 深缓存；真实费 maker 2 / taker 5.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根 4h，2024-12 →），含压力费 perp 15.1 / spot 20 bps。
- 触发占比（月）：`ss_trend_n12` 深未见 9.5%、调参 12.5%、post 67%；`ss_z_k1` 2023-02 之后几乎不触发（post 1 个月）。

## 结果（`output/research_jpx_short_selling_ratio_gate_4h.csv` 264 行；`_new8.csv` 20 行）

收益 % / Sharpe；9 段 = 3 套 ×（深未见 / 调参 / post）Sharpe 胜基线次数。

| 格子 | 9 段 | OKX d8 深未见 / 调参 / post | Gate d8 深未见 / 调参 / post | post 月 好/差（OKX、Gate） |
|---|---|---|---|---|
| 基线 默认 #1 | — | +35.14/0.71、+85.08/1.47、+59.90/2.23 | −3.63/0.09、+84.25/1.46、+60.32/2.25 | — |
| 先验 ss_trend_n12_long_off | 1/9 | +32.67/0.68、+55.34/1.10、+55.89/2.21 | +3.93/0.20、+54.17/1.09、+56.48/2.23 | 1/2、1/2 |
| 回退 ss_chg_n3_long_off | 0/9 | +27.05/0.63、+55.34/1.10、+59.90/2.23 | −3.13/0.09、+54.17/1.09、+60.32/2.25 | 0/0（post 从未拦到新多） |
| 最好非先验 ss_chg_n1_short_off | 6/9 | +12.96/0.39、+101.01/1.75、+61.70/2.35 | −11.67/−0.07、+98.62/1.72、+62.96/2.39 | 2/5、3/4 |
| 非先验 ss_trend_n12_short_off | 5/9 | +12.52/0.42、+58.78/1.50、+72.12/2.68 | −9.60/−0.10、+59.80/1.51、+72.98/2.71 | 4/3、6/1 |

- 50 格分布：6/9 4 格、5/9 2、3/9 14、2/9 6、1/9 4、0/9 20；**没有 7/9 以上**。另两个 6/9（`nr_trend_n12_cap_short_off`、`nr_trend_n12_contra_both`）与 `nr_chg_n1_cap_short_off` post 都比基线差 20~48 pp。
- OKX d7（无 BNB）：基线 +54.92/0.75、+92.93/1.56、+50.76/2.10；先验 +52.75/0.73、+57.44/1.14、+46.31/2.03。
- 安慰剂：16 个时移最高 **6/9**（先验 +365 天、+90 天、−120 / −119 天；回退 −90 / −120 / −119 天），都高于真实先验 1/9。
- `ss_chg_n1_short_off`（拦新空，除非空卖比率上月上升）：深未见两所都明显差（OKX Sharpe 0.39 vs 0.71，Gate −0.07 vs 0.09），post 只多 +1.8 / +2.6 pp，逐月 2/5、3/4；压力费 post OKX +58.74/2.26（基线 +55.94/2.12）、Gate +59.85/2.30（基线 +56.78/2.15），深未见仍差。邻域：n2 6/9（post +74 / +75，月 4/4、5/3），n4 崩溃（post +21%），n6 3/9。未调参 new8 pre 大幅变差（OKX Sharpe 0.22 vs 0.72，Gate 0.18 vs 0.69）。
- `ss_trend_n12_short_off`：post 两所约 +12 pp、Gate 月 6/1，但深未见、调参窗都输；new8 post 好（OKX +11.85/0.99 vs +3.26/0.28，Gate +26.47/1.69 vs +16.36/1.00，月 6/0、7/0），pre 却大幅变差（OKX 0.15 vs 0.72，Gate 0.18 vs 0.69）。只在 post 有效，和先验方向相反，不算观察。
- 未调参 new8 先验：pre OKX +33.83/0.84（基线 +29.85/0.72），post +7.38/0.56（基线 +3.26/0.28），月 3/0；Gate pre 0.81 vs 0.69，post 1.24 vs 1.00；压力费同向。new8 支持先验，但 d8 三套主样本都不支持。

## 结论

**否决**，不实现、不进观察名单、不改默认、不加纸面盘，无代码改动。先验 1/9：调参窗两所都少约 30 pp、post 少约 4 pp、逐月 1/2；回退 0/9（post 从未触发）；安慰剂最高 6/9 高于先验；最高的 6/9 格（`ss_chg_n1_short_off`）深未见差、post 逐月 2/5 和 3/4、邻域 n4 崩、new8 pre 差。日股空卖比率月度体制对默认书新开仓没有稳定增量。另外，官方月度历史只有 70 个月，样本本身就薄。

## 勿重测（never retest by…）

不要通过改 n / 均值窗口（3 个月均值 ↔ 单月 / 6 个月）/ z 窗口 / k / 侧 / 方向 / 滞后来重测本族；不要在总空卖比率、有价格规制 / 无价格规制空卖占比、空卖金额、实注文占比之间换序列；不要改用 JPX 日度空卖比率（仅约 13 个月）、按行业的空卖比率、个股空卖余额报告（残高報告）、信用取引残高 / 贷借取引（已被 `cn_margin_financing` 禁）；也不要换成港交所 / 台湾 / 韩国 / 美国（FINRA / Reg SHO）等其他市场的全市场空卖比率，或做成 1h「JPX 月度 / 日度空卖集计发布」事件来绕过本条。JSDA 外国人净买日债属于 `mof_resident_foreign_bond_flow` 勿重测范围，也不要再提。

## 文件
- `output/research_jpx_short_selling_ratio_gate_4h.csv`、`_new8.csv`、`output/jpx_short_selling_official_monthly.csv`（均不入库）。
- 脚本：`scratch/jpxshort4h/{build,run,new8}.py`、`PRE_REGISTER.json(.sha256)`、原始 PDF `raw/YYMM.pdf`（70 份）及年页 HTML；日志 `run.log` / `new8.log` / `zhanji.out`。
- 下一轮（短线）：OPEC / OPEC+ 官方部长级会议（ONOMM / JMMC）新闻稿发布 → 8 币永续篮子 1h 顺势 / 逆势事件（opec.org 官方 Press Releases 的日期与时间，按发布时刻后下一根 1h 入场）。docs / output 中 OPEC 0 命中；开跑前须核对 `eia_wpsr_crude_event_1h`、`eia_petroleum_stocks_gate_4h`、`us_rates_oil_trend`、`henryhub_natgas` 的勿重测范围（它们禁的是库存 / 价格序列，不是产量政策决议事件），若判同机制就换题。
