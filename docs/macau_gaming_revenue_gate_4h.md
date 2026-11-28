# 长线新族：澳门博彩监察协调局（DICJ）官方月度幸运博彩毛收入（GGR）→ 4h 默认书 #1 入场闸门（2026-11-27 ~21:05 PST，研究，不改默认；否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 已超过 GitHub 连接器写入上限，只在本地追加）。

- 查重：`docs/STRATEGY_FORMULAS.md`（全部轮换记录）、`docs/*.md`、`output/research_*.csv`、`scratch/` 目录名、`scratch/ROTATION_LOCK.txt` 检索 Macau / 澳门 / 博彩 / gaming revenue / GGR / DICJ / casino / lottery：只有子串误命中（aggregate 等），从未测过。不同于 `cn_margin_financing`（A 股两融杠杆）、`korea_retail_volume_share`、`pboc_*`（政策 / 信贷）、`hkma_interbank_liquidity`（香港银行间流动性）、`safe_fx_settlement`（居民结售汇）、美国实体 / 消费类闸门。本轮另排除（查重命中）：全球央行政策利率加 / 降息广度（与已否决的 Fed 政策利率周期同机制）、TIC（`mof_resident_foreign_bond_flow` 勿重测已点名）、Philly Fed ADS（`nyfed_wei` 勿重测已点名）、DTS 预扣税（与已否决财政部月度税收入库同机制）、Gate / OKX 爆仓（官方历史只有约 180 天）。
- 机制：澳门博彩毛收入 = 内地高净值 / 中场客的可支配投机性消费（含贵宾厅信贷）。GGR 相对自身趋势走弱 = 华人投机风险偏好 / 财富效应下降 → 经济先验「不新开多」（long_off / both）；`cap_short_off` 检验相反说法。
- 数据（只用官方，不编造、不插值、不回补）：DICJ「Monthly Gross Revenue from Games of Fortune」`dicj.gov.mo/web/en/information/DadosEstat_mensal/{2010..2026}/report_en.xml`（MOP 百万），2009-01 → 2026-10 共 **214 个月，0 个日历缺口**；每年文件的「上年同月」列与上一年文件的当年值逐月比对 **0 处修订**。最新 2026-10 = 21,680。可用时点：M 月值自 **M+1 月 3 日 00:00 UTC** 起使用（DICJ 通常 M+1 月 1 日公布，保守 +2 天）。官方表 `output/macau_ggr_official_monthly.csv`。
- 公式（看 PnL 前锁定 `scratch/macauggr4h/PRE_REGISTER.json`，sha256 `81d903c6…1b98`，2026-11-27 20:51 PST，50 格）：s = ln(GGR)。`lvl`：x = s 的 3 个月均值；`yoy`：x = (s − s(12 个月前)) 的 3 个月均值。flag = 1 表示博彩走弱：
  `trend_n{12,24}`：x < 该序列近 N 月均值；`chg_n{3,6}`：x − x(N 月前) < 0；`z_k1`：x 的 36 个月 z < −1；`neg`（仅 yoy）：x < 0。10 形式 × 5 侧（long_off / short_off / both / contra_both / cap_short_off），只拦新开仓，已有同向仓位不动。
  先验 `lvl_trend_n12_long_off`，回退 `yoy_chg_n3_long_off`；安慰剂 = 先验 + 回退各 8 个时移（±30 / ±90 / +180 / −120 / +365 / −119 天）。
- 回测：同脚本默认 #1（双均线 50/150，8 币 perp_both，官方资金费），官方 OKX / Gate 4h 深缓存；真实费 maker 2 / taker 5.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根 4h，2024-12 →），含压力费 perp 15.1 / spot 20 bps。
- 注意：`z_k1` 两条在 2023-02 之后从未触发（36 个月窗口含疫情塌陷），只在 Gate 2022 段有影响；post 段 `lvl_trend_n12` 有 75% 的月份处于 flag = 1。

## 结果（`output/research_macau_gaming_revenue_gate_4h.csv` 201 行；`_supp.csv` 邻域 24 行；`_new8.csv` 20 行）

收益 % / Sharpe；9 段 = 3 套 × (深未见 / 调参 / post) Sharpe 胜基线次数。

| 格子 | 9 段 | OKX d8 深未见 / 调参 / post | Gate d8 深未见 / 调参 / post | post 月 好/差（OKX、Gate） |
|---|---|---|---|---|
| 基线 默认 #1 | — | +35.14/0.71、+85.08/1.47、+59.90/2.23 | −3.63/0.09、+84.25/1.46、+60.32/2.25 | — |
| 先验 lvl_trend_n12_long_off | 4/9 | +31.30/0.66、+98.99/1.60、+39.53/1.86 | +9.87/0.28、+97.51/1.58、+39.78/1.87 | 1/3、1/3 |
| 回退 yoy_chg_n3_long_off | 2/9 | +31.74/0.71、+47.70/1.02、+39.53/1.86 | +13.70/0.33、+46.44/1.01、+39.78/1.87 | 1/3、1/3 |
| 最好非先验 lvl_chg_n3_long_off | 6/9 | +52.09/0.96、+98.72/1.60、+39.53/1.86 | +21.23/0.42、+97.22/1.58、+39.78/1.87 | 1/3、1/3 |
| 最好非先验 yoy_neg_long_off | 6/9 | +42.38/0.82、+95.79/1.58、+39.53/1.86 | +16.03/0.36、+94.81/1.57、+39.78/1.87 | 1/3、1/3 |

- 50 格分布：6/9 2 格、5/9 1、4/9 6、3/9 8、2/9 20、1/9 7、0/9 6；**没有 7/9 以上**。8 个会触发的 long_off 格中 7 个 post 都是 OKX +39.53 / Gate +39.78（约 −20 pp，拦掉了 2026-03 之后同一段关键新多），`lvl_trend_n24_long_off` 也是 −4 pp；post 更好的只有 short_off 侧（如 `lvl_trend_n12_short_off` post +65.63 / +66.02，月 5/2，但深未见 OKX +4.97、Gate −22.34，3/9）。
- OKX d7（无 BNB）：基线 +54.92/0.75、+92.93/1.56、+50.76/2.10；先验 +50.48/0.71、+102.94/1.65、+38.08/1.84。
- 安慰剂：16 个时移最高 **6/9（先验 +90 天）**，高于真实先验 4/9；+180 / +365 天 post 与基线相同（3/9）。
- 邻域（事后，不改结论）：先验 n6 / n9 / n18 全部 post −20 pp、月 1/3，n36 = 基线；`lvl_chg_n{1,2,4}`：n1 post −4 pp，n2 / n4 post −20 pp。
- 未调参 new8（pre 2024-12→2026-03 / post，基线 OKX +29.85/0.72、+3.26/0.28；Gate +27.68/0.69、+16.36/1.00）：先验 OKX +43.81/1.00、+5.05/0.41，Gate +41.20/0.98、+18.82/1.15，post 月 3/1；压力费同向。new8 好看，但 d8 post 两所都大幅变差。
- 压力费：没有任何真实格满足「≥ 6/9 且 post 不差于基线」，按预注册规则未跑主网格压力费。

## 结论

**否决**，不实现、不进观察名单、不改默认、不加纸面盘，无代码改动。先验 4/9：调参窗更好，但 OKX 深未见更差、post 两所都 −20 pp、逐月 1/3；回退 2/9；最高的两个 6/9 也是 post −20 pp、月 1/3；时移 +90 天的安慰剂（6/9）比真实先验还好；只有未调参 new8 支持。澳门博彩月度强弱对默认书新开仓没有稳定增量。

## 勿重测（never retest by…）

不要通过改 n / 均值窗口（3 个月均值 ↔ 单月 / 6 个月）/ z 窗口 / k / 侧 / 方向 / 滞后（M+1 月 1 日 / 3 日 / 15 日）重测本族；不要在水平 / 同比 / 环比 / 累计 / 季调之间换序列，不要换港币计价、贵宾厅 / 中场分项（季度）、按博彩游戏分项（百家乐 / 角子机）、按运营商（6 家持牌公司季报）、访澳旅客数 / 酒店入住率、新加坡 / 拉斯维加斯（内华达 Gaming Win）/ 菲律宾等其他博彩辖区收入，也不要改用澳门日度 / 周度非官方估算或做成 1h「DICJ 月初公布」事件来绕过本条。

## 文件
- `output/research_macau_gaming_revenue_gate_4h.csv`、`_supp.csv`、`_new8.csv`、`output/macau_ggr_official_monthly.csv`（均不入库）。
- 脚本：`scratch/macauggr4h/{build,run,supp,new8}.py`、`PRE_REGISTER.json(.sha256)`、原始 XML `raw_2010..2026.xml`；日志 `run.log` / `supp.log` / `new8.log` / `pytest_full.log`。
- 下一轮（短线）：选一个未测过、官方逐小时数据覆盖 2022–2026 的 1h 事件族（先查重 docs / 侧文档 / output / 记忆）。
