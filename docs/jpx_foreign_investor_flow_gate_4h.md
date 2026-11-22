# 日本交易所（JPX）官方每周「投資部門別売買状況」海外投資家 / 個人 净买入 → 4h 默认书入场闸门（否决；不改默认、不入纸面）

## 长线新族：JPX 海外投资者 / 个人 周度净买入（东京+名古屋二市场，金额）作为 4h 默认书入场闸门（2026-11-22 ~12:35 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`（含轮换日志）、`docs/*.md`、`output/research_*.csv`（1,199 个）、`scratch/ROTATION_LOCK.txt` 检索 jpx / Japan Exchange / investor type / 投資部門別 / 海外投資家 / 外国人 / foreigners / nonresident / nikkei / topix / TWSE / 三大法人 / 外資 / foreign flow：**0 命中**。不同于已测 JGB10y 收益率闸门（利率）、日元汇率趋势、BoJ（仅作 1h 政策事件排除集）、加密股相对强弱（MSTR/COIN 价格）、美国 IPO 发行、FINRA 保证金、CFTC COT、Korea premium / 韩国散户成交占比（加密交易所数据）。本轮先试台湾证交所 BFI82U 三大法人买卖超（约 6 次请求后 IP 被限流 / 307 重定向，无法完整拉取），再试期交所 TAIFEX 三大法人（只提供约 3 年历史），均放弃，改用 JPX。
- 机制：海外投资者占东证成交额约 60–70%，是全球 risk-on/off 的边际配置者；其对日本股票的周度净买卖 = 官方跨境风险偏好流量。先验：4 周海外净卖出 = 全球去风险 → 拦新多。个人（散户）通常与海外资金反向；个人净买入（= 海外卖出）时拦新多。只拦新开仓，已有持仓、止损、离场不变。默认 4h 书（#1 双均线 50/150，8 币永续）。
- 数据（只用官方，不编造、不回补）：JPX 官网 Trading by Type of Investors 周度文件（`https://www.jpx.co.jp/english/markets/statistics-equities/investor-type/` 及 `00-00-archives-00..08.html`）：`stock_val_1_YYMMWW.xls`（2018-01 → 2026-09，表 `Tokyo & Nagoya`）与 `stock_1_w_YYYYMMDD_YYYYMMDD.xlsx`（2026-09 起，行「二市場 Tokyo & Nagoya」金額），单位千日元；取当周列，文件里「上周」列只用于没有自身文件的周（同一官方来源，34 周）；**463 周 2017-12-29 → 2026-11-13，无缺交易周**（新旧格式交界数量级一致）。最新 2026-11-13 周：海外 −0.310 万亿日元、个人 −0.361；海外 4 周 −0.575、13 周 +0.516；个人 13 周 +0.293。存 `output/jpx_investor_type_official_weekly.csv`（不入库），原始文件 `scratch/twsefi4h/jpx/`。
- 滞后：周五 F 结束的周按 **F+7 天 12:00 UTC** 才可用（JPX 于下周第 4 个营业日约 15:00 JST = 周四 06:00 UTC 发布；12/22–1/6 与 4/26–5/8 的周再 +4 天）；前向填充到 4h K 线。
- 公式（看 PnL 前写入 `scratch/twsefi4h/PRE_REGISTER.json` 锁定，sha256 `65b6b2960d30fe1afd9582d95e7e3a188d1ab23137d3f9d27d7bf948bac90b4e`，同目录 `PRE_REGISTER.sha256` 另记 run.py / parse_jpx.py / 周度 CSV 的 sha；共 100 格）：
  - 序列（flag=1 一律 = 净买入）：`fcum` = 海外投资者累计净买入（万亿日元）、`icum` = 个人累计净买入。
  - 形式：`chg`：s − s.shift(n 周) > 0（= n 周净买入），n 4 / 8 / 13 / 26；`trend`：s > SMA(n 周)，n 8 / 13 / 26；`z`：4 周净流量的 52 周 z > k，k −0.5 / 0 / 0.5。
  - 侧：long_off（flag=0 拦新多）/ short_off（flag=1 拦新空）/ both / contra_both（flag=1 拦新多、flag=0 拦新空）/ cap_long_off（flag=1 拦新多）。2 × 10 × 5 = 100 格 + 同脚本基线。
  - 先验格（锁定）：`fcum_chg_n4_long_off`（海外 4 周净卖出拦新多），兼作安慰剂锚；回退 `fcum_chg_n13_long_off`；经济先验族 = fcum long_off / both + icum cap_long_off（40 格）。
- 验证：与 SNB / HKMA / GLD 闸门同一框架（OKX d8 2023-02→ / Gate d8 2022-07→ / OKX d7_noBNB 2022-04→，官方永续 + 现货 4h、官方资金费；真实费率永续 maker 2 / taker 5.1 bps，压力永续 15.1 / 现货 20 bps；深未见 →2024-10-21、调参段 →2026-03-05、post →2026-11-14；安慰剂日历平移 +7 / −7 / +14 / −14 / +180 / −120 / +365 / −119 天；邻域 n 2…52 周；new8 未调参币 OKX + Gate 最近 4500 根 4h）。基线与以往闸门研究一致（OKX post +59.90 / 2.23）。
- 默认门槛：深未见 + 调参段 Sharpe 两所都胜，且 post（2026-03-05 后）两所 ≥ 6/9 月更好，并有安慰剂 + 邻域支持。
- 结果（`output/research_jpx_foreign_investor_flow_gate_4h.csv` 381 行；收益 % / Sharpe，真实费率）：

| 账本 | 格 | 深未见 | 调参段 | post | post 月 好/差 |
|---|---|---|---|---|---|
| OKX d8 | 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | — |
| OKX d8 | 先验 fcum_chg_n4_long_off（3/9） | +53.68 / 0.97 | +81.14 / 1.43 | +45.55 / 2.03 | 1/3 |
| OKX d8 | 回退 fcum_chg_n13_long_off（0/9） | +17.05 / 0.46 | +43.82 / 0.96 | +49.18 / 2.17 | 1/3 |
| OKX d8 | 非先验 icum_chg_n13_short_off（9/9） | +37.46 / 0.79 | +94.38 / 1.60 | +64.70 / 2.39 | 3/4 |
| OKX d8 | 非先验 fcum_trend_n13_contra_both（9/9） | +32.24 / 0.74 | +82.09 / 1.55 | +62.42 / 2.31 | 1/4 |
| Gate d8 | 基线 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / 2.25 | — |
| Gate d8 | 先验 | +22.81 / 0.44 | +78.22 / 1.40 | +45.80 / 2.05 | 1/3 |
| Gate d8 | 回退 | −6.59 / 0.02 | +42.43 / 0.94 | +49.41 / 2.18 | 1/3 |
| Gate d8 | icum_chg_n13_short_off | +10.95 / 0.29 | +92.54 / 1.58 | +65.77 / 2.42 | 6/1 |
| Gate d8 | fcum_trend_n13_contra_both | +6.16 / 0.22 | +81.26 / 1.53 | +63.31 / 2.33 | 4/1 |
| OKX d7_noBNB | 基线 | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / 2.10 | — |
| OKX d7_noBNB | 先验 | +95.55 / 1.08 | +79.32 / 1.43 | +38.68 / 1.83 | 1/3 |
| OKX d7_noBNB | 回退 | +32.69 / 0.55 | +42.65 / 0.96 | +42.11 / 1.97 | 1/3 |
| OKX d7_noBNB | icum_chg_n13_short_off | +60.80 / 0.85 | +97.22 / 1.64 | +54.68 / 2.24 | 3/3 |
| OKX d7_noBNB | fcum_trend_n13_contra_both | +58.20 / 0.87 | +95.07 / 1.71 | +53.18 / 2.18 | 2/3 |

  - 9 切片 Sharpe 胜数分布（100 格）：0/9 49、1/9 8、2/9 11、3/9 20、4/9 2、5/9 6、6/9 2、9/9 2（两个都是非先验）。经济先验族 40 格：0/9 19、1/9 1、2/9 6、3/9 12、4/9 1、6/9 1（fcum_f4z52gt−0.5_long_off：深未见三套胜，但 post −18.5 pp、月 1/3）。
  - 先验 3/9 的形态：三套深未见全胜（OKX +18.5 pp），调参段与 post 全输（post −14 pp、Sharpe −0.2，月 1/3）。回退 0/9。先验 both 更差（fcum_chg_n4_both post +13.34 / 1.00，月 2/7）。
  - 压力费率（icum_chg_n13_short_off）：OKX +27.87/0.64 vs 基线 +24.67/0.56、+84.32/1.49 vs +75.18/1.35、post +61.68/2.31 vs +55.94/2.12；Gate +0.99/0.14 vs −13.77/−0.07、+82.59/1.47 vs +74.07/1.34、+62.46/2.33 vs +56.78/2.15。
- 安慰剂（先验锚 fcum_chg_n4_long_off，9 切片胜数）：+7d 6、−7d 6、+14d 2、−14d 6、+180d 5、−120d 3、**+365d 9/9**、−119d 3 → 多个平移胜过真实 3/9，先验无时点特异性。
- 安慰剂（icum_chg_n13_short_off，`_supp.csv`）：+7d **8/9**、−7d 4、+14d 5、−14d 3、+180d 3、−120d 5、**+365d 7/9**（post +66.75 / +67.24 高于真实，d7 月 6/3）、−119d 6。
- 安慰剂（fcum_trend_n13_contra_both，`_supp2.csv`，事后补充）：**−7d 9/9**（post 边 +4.9 pp 大于真实 +2.7）、+365d 7、−14d 6、其余 0–3。
- 邻域：先验 fcum_chg n（long_off）n=2/3/6/10/17/20/39/52 胜数 6/3/5/0/1/3/3/3，post 全部 ≤ 基线。icum_chg_n13_short_off：n=2/3/6/8/10/17/20/39/52 胜数 4/5/3/6/7/2/1/3/5，n=8 post −26 pp、n=6 −29 pp、n≥17 基本不触发（= 基线），只有 n=10（7/9，月 5/4、6/3、4/5）接近 → 断续。fcum_trend contra_both：n=10/17 9/9，但 n=20 6/9（post −33 pp）、n=6 2/9、n=39/52 1/9；icum 同形 0/9。
- new8 未调参（最近 4500 根 4h，2024-11-28→）：基线 OKX pre +47.85/1.00、post +3.26/0.28；Gate pre +44.99/0.97、post +16.36/1.00。icum_chg_n13_short_off **两所 pre / post 都输**（OKX 0.85 / 0.21，Gate 0.82 / 0.65）。fcum_trend_n13_contra_both 两所都胜（OKX 1.02 / 0.63 月 5/0，Gate 1.07 / 1.30 月 5/0）。先验 pre 胜（1.30 / 1.28）post 输（0.12 / 0.89，月 1/3）；回退 pre 输、post 约平。
- 当前信号（数据到 2026-11-13 周，2026-11-20 12:00 UTC 起可用）：海外 4 周净卖出 −0.575 万亿日元 → 先验 flag=0（会拦新多；当前默认书全为空单，不受影响）；13 周 +0.516（回退 flag=1）；个人 13 周净买入 +0.293（icum_chg_n13 flag=1，会拦新空）。仅供记录，不进纸面。
- 结论：**否决**（不改默认、不入纸面、不加代码）。先验 fcum_chg_n4_long_off 只赢深未见（3/9），调参段与 post 全输、月 1/3，且 +365d 平移 9/9、多个平移 6/9 胜过真实；回退 0/9。两个 9/9 都是非先验：icum_chg_n13_short_off post 边 +4.7 pp 但月份 3/4、6/1、3/3（OKX 不满足 ≥6/9），+7d 平移 8/9、+365d 7/9 接近或更强，邻域断续，new8 两所 pre/post 都输；fcum_trend_n13_contra_both post 边 +2.7 pp、月 1/4 / 4/1，−7d 平移 9/9 且更强，邻域 n=20 崩。无格达到强观察或值得入纸面的弱观察。
- 勿重测：不要通过改 n（2~52 周）、z 窗口 / k、方向 / 侧、滞后（周四 / 周五 / 下周一）来重测本族；也不要换投资者类别（海外 / 个人 / 投信 / 信托银行 / 事业法人 / 证券公司自营）、换市场（Prime / Standard / Growth / 二市场）、换金额 / 股数、换现金 / 信用、换净额 / 买卖比 / 总成交占比、换 JPX 月度或按地区（非居民地区）统计、换 ETF / REIT 投资者类别、或换成 TWSE 三大法人 / TAIFEX 外资期货未平仓 / KRX 外国人 / 港股通北向南向等其他交易所的外资净买入序列；也不要改成 1h「JPX 周四投资者类别发布」事件来绕过本条。
- CSV：`output/research_jpx_foreign_investor_flow_gate_4h.csv`（主网格 + 先验安慰剂 + icum 邻域 + STRESS，381 行）、`_supp.csv`（先验邻域 + icum_chg_n13_short_off 安慰剂）、`_supp2.csv`（fcum_trend_n13_contra_both 安慰剂 + 邻域，事后补充）、`_new8.csv`（new8 未调参）、`output/jpx_investor_type_official_weekly.csv`（官方周度，不入库）；脚本 `scratch/twsefi4h/parse_jpx.py`、`run.py`、`supp.py`、`supp2.py`、`new8.py`、`score.py`。
- 下一轮（短线）：日经 225 官方日线开盘跳空冲击（09:00 JST = 00:00 UTC 现货开盘 vs 前日收盘，Nikkei Inc. 官方指数历史）→ 8 币永续 1h 事件；已查 nikkei / 日经 / tokyo / equity_open / index_gap：0 命中（与已测 crypto 自身 Asia/EU/US 时段动量、CME 周末缺口、股票永续盘后缺口不同）。
