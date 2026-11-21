# FINRA 官方月度保证金统计（美股融资余额）→ 4h 默认书入场闸门（否决）

> 本文件是 docs/STRATEGY_FORMULAS.md 本地追加章节的同内容 sidecar（不覆盖远端 STRATEGY_FORMULAS.md）。

## 长线新族：FINRA 官方月度保证金统计（美股客户融资余额 debit balances / 融资÷贷方余额杠杆比）→ 4h 默认书入场闸门（2026-11-21 ~02:00 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md（FINRA / margin statistics / 保证金统计 / debit balance / 融资余额）只在 Kim-Wright 一节作为「下一轮」候选出现，无已完成条目；`output/research_*.csv`（约 1040 个）无 finra / 美股融资文件（`research_bitfinex_margin_*` 是 Bitfinex 加密保证金多空仓位，不同市场、不同机制）；记忆 0 条。与已否决的 MMF/H.8 现金囤积、联储净流动性、NFCI / 信用利差、M2、CFTC TFF、美国宏观风险体制不同：这里看的是**美股散户 / 杠杆资金的加杠杆—去杠杆周期**。
- 数据（仅官方）：FINRA Rule 4521(d) 月度保证金统计，官方 xlsx `https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx`（finra.org 保证金统计页链接；Last-Modified 2026-11-13 20:59 GMT，sha256 ce727def…681f）。1997-01 → 2026-10 共 358 个月，日历缺口 0，无补值 / 插值；存 `output/finra_margin_official_monthly.csv`（不入库）。**滞后**：FINRA 一般在 M+1 月第三周发布 M 月数据，这里保守地从 **M+2 月 1 日 00:00 UTC** 起才使用，ffill 到 4h。当前 vintage（FINRA 说明 2021-04 FAQ 后部分会员口径有调整）；2010-02 前为 NYSE 口径、贷方余额为现金 + 保证金合并列。
- 公式：debit = ln(借方余额)；lev = ln(借方余额 / (现金账户贷方 + 保证金账户贷方))。flag = 1 表示去杠杆：`trend_nN`：s < 近 N 个月均值（N 3 / 6 / 12 / 24）；`mom3_lt0` / `yoy_lt0`：s − s[−3 / −12] < 0；`dz_n36_lt1/2`：1 个月变化相对 36 个月滚动的 z < −1 / −2；`yoyz_n60_lt1`：12 个月变化相对 60 个月滚动的 z < −1。侧：long_off（去杠杆时不开新多）/ short_off（加杠杆时不开新空）/ both / contra_both；只拦新开仓，已持仓、止损、离场不变。
- 预注册：2 序列 × 9 形式 × 4 侧 = **72 格** + 同脚本基线（默认书 #1）；`PRE_REGISTER.json` 在任何 PnL 前锁定（sha256 062bd243…18b5）。唯一先验 `debit_trend_n6_long_off`（融资余额跌破 6 个月均值 → 拦新多）；回退 `debit_yoy_lt0_long_off`。harness 复制 mmfh8_4h / gpr4h：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续 + 官方资金费；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（永续 maker 2 / taker 5.1 bps，现货 10），压力 15.1 / 20；安慰剂 ±7 / ±14 / ±60 / +180 / −120 / +365 / −119 天；邻域；未调参 new8。
- 结果（`output/research_finra_margin_debt_gate_4h.csv` 324 行；`_new8.csv`）：基线 post OKX +59.90% / Sharpe 2.23，Gate +60.32% / 2.25；deep 0.71 / 0.09 / 0.75，tune 1.47 / 1.46 / 1.56。
  - **先验** `debit_trend_n6_long_off`：3/9。deep 三段都赢（0.89 / 0.42 / 0.82），但 tune 三段都输（1.24 / 1.24 / 1.34），**post 与基线完全相同**（融资余额 2025–26 一路上升，post 里没拦到任何新多，月份 0 好 / 0 坏）。
  - 回退 `debit_yoy_lt0_long_off`：3/9，只在 deep 赢（0.99 / 0.48 / 0.88），tune 与 post 都未触发 = 基线。
  - 最好 `debit_trend_n12_long_off` / `lev_trend_n24_long_off` 6/9：同样只是 2022 熊市段的 deep 增益，tune 仅 +0.01，post 完全等于基线（0 / 0 月）。邻域 n7–n11 同为 6/9、n4 / n5 / n13+ 降到 3/9，全部 post = 基线。
  - 安慰剂：先验平移 +7 天 6/9、−119 / −120 天 6/9（tune 1.56–1.57 反而比真实好），+180 天 deep OKX 1.28 远高于真实 0.89 → 增益只是「2022 年美股与加密同步熊市」这一个体制，不是融资数据本身的时点信息；默认书已有 BTC SMA1200 体制闸门覆盖同一段。
  - 改变 post 的格子（short_off / both / contra_both 等 57 格）：post 月份达到 6/9 的只有 7 格，其中仅 `debit_trend_n3_both` 收益高于基线（+69.15% / 2.77、+69.68% / 2.78），但 deep 被打穿（OKX −0.34、Gate −0.65）、tune 1.01 / 1.02，非先验、不可用。
  - 压力费：先验 deep OKX 0.76 vs 0.56、Gate 0.28 vs −0.07，tune 1.13 vs 1.35，post 同基线；结论不变。
  - 未调参 new8：先验 pre Sharpe 1.22 / 1.21 vs 1.21 / 1.19（只拦 5 笔），post 与基线完全相同；回退完全不触发。
- 结论：**否决**。不实现、不进观察名单、不改默认，无代码改动，仅文档。未见历史（2022 熊市）有增益，但 post 0 / 9 个月改善，达不到「post ≥ 6/9 月两所都更好」的门槛，且平移安慰剂同样能拿到增益。勿以同一机制换 N / 阈值 / 方向、换借方 / 贷方 / 杠杆比 / 净借方、换 NYSE 历史口径、换月度变化 z / 同比，或换美联储 Z.1 融资 / 券商保证金贷款等同类「美股融资杠杆周期」序列再测。
- 脚本 `scratch/finramargin4h/{parse,build,prereg,run,new8}.py`、`PRE_REGISTER.json(.sha256)`（研究脚本未推送）。默认策略与纸面实例均未改动。
- 下一轮（长线）：Ethena 官方链上 USDe 总供给 / sUSDe 质押汇率隐含年化（2024-02 起）作为 4h 默认书入场闸门——须先确认与已否决的「稳定币供应增长」闸门有清晰区别（拟用 sUSDe 汇率隐含收益 = 基差 / 资金费套利需求，而非供应量），且历史较短、deep unseen 只有约 8 个月，需在预注册里写明。
