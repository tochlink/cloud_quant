# 长线新族：联合国 FAO 食品价格指数（FFPI / 谷物 / 植物油）→ 默认 #1 4h 入场闸门（2026-11-27 ~11:00 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、记忆中对 FAO / 食品价格 / 化肥 / 小麦 / 谷物 / 糖 / USDA / 农作物 / 咖啡 均 0 条；不同于已测的汽油柴油、天然气、钻机数、铜金比、盈亏平衡通胀、Cleveland 通胀 nowcast、美国货运。
- 机制：全球食品价格上行 → 名义通胀 / 新兴市场压力 / 实际收入受挤 → 风险偏好下降 → 拦新开多（先验 long_off / both）。只拦新开仓，已持仓、止损、退出、再平衡不变。
- 数据（仅官方）：FAO 官方月度 CSV `food_price_indices_data.csv`（fao.org，2014-16=100），1990-01 → 2026-10 共 442 个月，日历缺口 0，无缺失；列 ffpi / cereals / oils。M 月值保守按 M+1 月 10 日 00:00 UTC 才可用。局限：为当前版本（FAO 每月会修订近几个月），无历史 vintage；因此偏乐观，结论为否决时影响不大。存 `output/fao_ffpi_official_monthly.csv`（不入库）。
- 格子（PnL 前锁定，PRE_REGISTER.json sha256 81b39eb3…77f7，120 格）：序列 ffpi / cer / oil × 形式 trend（月值 > 6 / 12 月均值）、chg（3 / 12 月变化 > 0）、z60gt（60 月 z > 0.5 / 1 / 1.5 / 2）× 侧 long_off / short_off / both / contra_both / cap_short_off。先验侧 long_off / both，回退 ffpi_chg_n12_long_off。
- Harness：与 geomag4h 同一脚本（run_backtest 默认双均线 50/150 4h，8 币永续）。OKX d8（2023-02 起）/ Gate d8（2022-07 起）/ OKX d7_noBNB（2022-04 起）；deep_unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；官方资金费；永续吃单 5.1 bps，压力 15.1；安慰剂平移 ±30 / ±90 / +180 / −120 / +365 / −119 天；邻域；未调参 new8。
- 基线 post：OKX +59.90% / Sharpe 2.23，Gate +60.32% / 2.25。
- 结果（CSV `output/research_fao_food_price_gate_4h.csv`、`_new8.csv`）：
  - 先验侧最佳 cer_chg_n3_both：9 片 Sharpe 8/9，但 post 收益 OKX +48.83% / Gate +48.98%（低 ≈ 11 pp），月份 3/3、3/3、2/4（d7）；平移 +30 天安慰剂 post +60.03% / Sharpe 2.37，比真信号还好 → 无信息。
  - 先验 long_off 最佳 cer_chg_n3_long_off 6/9，post −15 pp，月份 1/3；ffpi 系列先验侧 ≤ 4/9。回退 ffpi_chg_n12_long_off 未达标。
  - 非先验最佳 cer_chg_n3_short_off（食品下行才拦空）7/9：post OKX +64.12% / 2.37、Gate +64.92% / 2.40（+4.2 / +4.6 pp），月份 4/2 与 6/0，但 d7 月份 2/4，Gate deep_unseen −6.45%（基线 −3.63%）、Sharpe −0.01 < 0.09；压力费 post +60.47% / +61.33% 仅比基线 +4.5 pp；邻域 n6 / n9 / n18 / n24 的 deep 与 post 大幅回落（n6 deep −4.6% / −26.2%，n18 post +26.75%），不稳；侧与经济先验相反。
  - new8（未调参）：cer_chg_n3_both pre Sharpe 0.85 vs 0.69，post +5.2% vs +3.3%（OKX）、+18.7% vs +16.4%（Gate），月份 4/2；cer_chg_n3_short_off 与基线几乎相同。压力费下仍略好，但只是 new8 的小样本，d8 / deep 不支持。
  - 未达 ≥ 6/9 月份、两所 post 不差、邻域稳定、安慰剂更差 的任何一条联合标准。
- 结论：**否决**，不实现、不进观察名单、不改默认、不加纸面实例、无代码改动，仅文档。勿以同一机制换 n / k / 方向、换 FFPI 子指数（肉 / 乳 / 糖）、实际 / 名义、同比环比，换 IMF / World Bank / USDA / 其他食品或农产品价格指数，或换发布滞后重测。
- 脚本 `scratch/faofpi4h/{build,run,new8}.py`、`PRE_REGISTER.json`（研究脚本未推送）。
