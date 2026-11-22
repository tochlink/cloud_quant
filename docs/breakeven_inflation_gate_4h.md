# FRED 官方市场隐含通胀预期（T10YIE / T5YIE / T5YIFR）4h 默认书入场闸门（长线，已否决）

日期：2026-11-21（PST）。结论：**否决，不实现、不改默认、不加纸面实例。**

## 机制
美国国债市场隐含通胀预期（10 年 breakeven、5 年 breakeven、5y5y 远期）下行 = 通缩/避险（risk-off）。经济先验：flag=1（通胀预期下行）时不开新多仓（只拦新开仓，已有同向持仓不动）。与已测的 CPI 公布 regime、VIX 期限结构、Kim-Wright 期限溢价、美债收益率波动、SOFR/IORB、宏观美元/实际利率/VIX 闸门不同。

## 数据
- FRED（St. Louis Fed）官方 `fred.stlouisfed.org/graph/fredgraph.csv?id={T10YIE,T5YIE,T5YIFR}` 日度，2003-01-02 → 2026-11-20，各 5,976 个有效观测（256 个官方缺失“.”/节假日直接丢弃，无填充/回补；最大间隔 4 天）。2026-11-20：T10YIE 2.15、T5YIE 2.18、T5YIFR 2.12。
- 日线 CSV：output/breakeven_official_daily.csv。D 日数值 **D+2 00:00 UTC** 才可用（保守发布滞后），ffill 到 4h。只有当前 vintage（无 ALFRED 历史版本；市场序列基本不修订，但仍注明）。
- 交易数据：官方 OKX / Gate 永续 4h K 线 + 官方资金费；真实费用 perp taker 5.1 bps，压力 spot 20 / perp 15.1 bps。

## 公式与格子（看 PnL 前锁定，PRE_REGISTER.csv / .md，sha256 已存）
flag=1（通胀预期下行）：
- trend n∈{30,60,90,180}：x < 自身 n 期 SMA
- chg n=20：x < 20 期前的 x
- z k∈{0.5,1,1.5}：20 期变化在过去 252 期上的 z 分数 < −k

侧：long_off（flag=1 拦新多）、short_off（flag=0 拦新空）、both、contra_both（flag=0 拦新多 + flag=1 拦新空）、cap_short_off（flag=1 拦新空）。
3 序列 × 8 形式 × 5 侧 = **120 格** + 同脚本基线（默认 #1 MA50/150 4h）。**先验 t10yie_trend_n90_long_off**，**回退 t10yie_z1_long_off**。
评分：9 个 Sharpe 切片（OKX d8 2023-02 / Gate d8 2022-07 / OKX d7_noBNB 2022-04 × deep unseen <2024-10-21 / tune 2024-10-21→2026-03-05 / post ≥2026-03-05）；post 月度 ≥6/9 且两所 d8 更好；邻域；时间平移（±7/±14/+180/−120/+365/−119 天）与洗牌安慰剂；untuned new8。

## 结果
基线：OKX d8 deep +35.14% / Sharpe 0.71，tune +85.08% / 1.47，post +61.54% / 2.27；Gate d8 deep −3.63% / 0.09，tune +84.25% / 1.46，post +61.96% / 2.29；OKX d7 post +52.12% / 2.14。
- **先验 t10yie_trend_n90_long_off：1/9**。post OKX +34.71% / 1.54、Gate +35.26% / 1.56（基线 +61.54/+61.96），post 月度 1 好 /3 差、2/2；deep OKX +31.82%（0.70，低于基线），只有 Gate deep 赢。其安慰剂 −7d / −14d 反而达 6/9。压力费用下同样大幅落后。
- **回退 t10yie_z1_long_off：6/9 但 post 与基线完全相同**（post 期间没有拦下任何新多，月度 0/0）；6 胜全部来自 deep/tune，且 ±14d 平移安慰剂同样 6/9 → 无信息量。
- 120 格分布：没有 9/9；8/9 两格、7/9 两格，全部是非先验、与经济先验方向相反的 cap_short_off（通胀预期下行时拦新空）：
  - t5yifr_trend_n90_cap_short_off 8/9：post OKX +65.55% / 2.45、Gate +65.98% / 2.47、d7 +57.54% / 2.37；但 **post 月度仅 1 好 /1 差（两所）**，远低于 ≥6/9；OKX d7 tune 输。
  - t10yie_trend_n180_cap_short_off 8/9：post 收益反而低 0.6 / 0.2 点（OKX +60.95%、Gate +61.72%，Sharpe 仅高 0.06–0.07），月度 3 好 /4 差（两所）。
  - t10yie_trend_n90_cap_short_off 7/9：post +68.24% / +69.44%，月度 3/3、4/2，Gate deep −8.54%（输）。
- 补充（事后、已标注，output/research_breakeven_inflation_gate_4h_supp.csv）围绕 t5yifr_trend_n90_cap_short_off：n105/120/150 仍 8/9，但 n75/n60 6/9、n180 4/9、n240 5/9、n45 1/9；**+7d 平移安慰剂 7/9 且 post Sharpe 边际（+0.87）大于真实格（+0.58）**，−7d 6/9 → 无法与噪声区分。
- **untuned new8**（output/research_breakeven_inflation_gate_4h_new8.csv）：基线 post OKX +12.77% / 0.85、Gate +26.93% / 1.46；先验 +9.50% / 0.64、+23.90% / 1.29；回退 +13.35% / 0.88、+27.58% / 1.49（月度 1/0）；t5yifr_trend_n90_cap_short_off +6.35% / 0.57、+20.27% / 1.32（pre 也从 +48% 掉到 +23%）；t10yie_trend_n90_cap_short_off +7.50% / 0.61、+20.51% / 1.29。
- 压力费用（15.1 bps）行写入 CSV（variant 后缀 __stress），不改变结论。

## 结论
**否决**。先验在 post 大幅输（OKX −26.8 点、Sharpe −0.73），回退在 post 无任何作用；仅有的 8/9 格是反经济先验的 cap_short_off，post 月度 1/1、邻域塌陷、+7d 安慰剂更强、untuned new8 变差。默认不变，不进纸面。

## never retest by
改 n / k / z 窗口 / 变化窗口 / 侧、在 T10YIE / T5YIE / T5YIFR 之间互换或做差（如 10y−5y 斜率）、换成 TIPS 实际利率 / 名义利率派生的 breakeven、改发布滞后、或换 token / 换交易所来重试这个“市场隐含通胀预期 breakeven 闸门”机制。

CSV：output/research_breakeven_inflation_gate_4h.csv、_supp.csv、_new8.csv、output/breakeven_official_daily.csv（均不入库）。脚本：scratch/breakeven4h/{build,prereg,run,supp,new8}.py。
