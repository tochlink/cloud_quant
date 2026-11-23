# 美国油气钻机数（EIA 官方月度 rotary rigs，来源 Baker Hughes）→ 4h 默认书入场闸门（否决）

> 本文件是 docs/STRATEGY_FORMULAS.md 本地追加章节的同内容 sidecar（不覆盖远端 STRATEGY_FORMULAS.md）。

## 长线新族：美国油气钻机数（能源资本开支周期）→ 4h 默认书 #1（MA 50/150）入场闸门（2026-11-22 ~19:20 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md 中 Baker Hughes / rig count / rigcount 只作为「下一轮（未测）」指针出现（ercot / epu / erc4337 / seaport / pboc 各节），无已完成条目；docs/*.md 无钻机 sidecar；约 1220 个 `output/research_*.csv` 无 rig / baker 文件；/workspace/scratch 无对应目录。最近的已否决族：`us_rates_oil_trend`（WTI **价格**均线闸门）、`eia_wpsr_crude`（周度原油**库存** 1h 事件）、ERCOT 电价 1h、美国实体经济情绪（UMich / 零售 / 工业产出）、纽约联储 WEI。钻机数是能源资本开支的**实物数量**（滞后油价约 3–6 个月），不是价格、库存或调查。
- 数据（仅官方）：EIA Petroleum Navigator 月度「U.S. Crude Oil and Natural Gas Rotary Rigs in Operation」`E_ERTRR0_XR0_NUS_C`（油 + 气总数）与原油钻机 `E_ERTRRO_XR0_NUS_C`，数据来源 Baker Hughes（rigcount.bakerhughes.com 周度页面对本机 Akamai 403，未绕过，改用 EIA 官方转载的月度值）。Release 2026-10-30（最新 2026-09），下次 2026-11-30。1987-08 → 2026-09 共 470 个月，日历缺口 0，无补值 / 插值；存 `output/eia_rigcount_official_monthly.csv`（不入库）。**滞后**：EIA 约在 M+1 月最后一个工作日发布 M 月，这里保守地从 **M+2 月 8 日 00:00 UTC** 起才使用，ffill 到 4h。当前 vintage。
- 公式：total = ln(油 + 气钻机数)，oil = ln(原油钻机数)。flag = 1 表示收缩：`trend_nN`：s < 近 N 个月均值（N 3 / 6 / 12 / 24）；`mom3_lt0` / `yoy_lt0`：s − s[−3 / −12] < 0；`dz_n36_lt1/2`：1 个月变化相对 36 个月滚动的 z < −1 / −2；`yoyz_n60_lt1`：12 个月变化相对 60 个月滚动的 z < −1（2022–2026 占用率 0，退化格，按预注册保留）。侧：long_off（收缩时不开新多）/ short_off（扩张时不开新空）/ both / contra_both；只拦新开仓，已持仓、止损、离场不变。
- 预注册：2 序列 × 9 形式 × 4 侧 = **72 格** + 同脚本基线（默认书 #1）；`PRE_REGISTER.json` 于 2026-11-22 19:07:25 PST、任何 PnL 之前锁定（sha256 1471220e…69ac）。唯一先验 `total_trend_n6_long_off`（钻机总数跌破 6 个月均值 → 拦新多）；回退 `total_yoy_lt0_long_off`。harness 复制 finramargin4h：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续 + 官方资金费；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（永续 maker 2 / taker 5.1 bps，现货 10），压力 15.1 / 20；安慰剂 ±7 / ±14 / ±60 / +180 / −120 / +365 / −119 天；邻域；未调参 new8（LINK / LTC / DOT / TRX / BCH / ATOM / NEAR / UNI，最近 4500 根）。
- 结果（`output/research_us_rigcount_gate_4h.csv` 321 行；`_new8.csv`）：

| 格子 | 所 | deep unseen 收益 / Sharpe | tune 收益 / Sharpe | post 收益 / Sharpe | post 月 好/坏 | 9 段 |
|---|---|---|---|---|---|---|
| 基线 | OKX | +35.14% / 0.71 | +85.08% / 1.47 | +59.90% / 2.23 | — | — |
| 基线 | Gate | −3.63% / 0.09 | +84.25% / 1.46 | +60.32% / 2.25 | — | — |
| 先验 total_trend_n6_long_off | OKX | +7.98% / 0.29 | +34.57% / 0.85 | +59.90% / 2.23 | 0/0 | 0/9 |
| 先验 | Gate | −18.79% / −0.19 | +33.09% / 0.82 | +60.32% / 2.25 | 0/0 | |
| 回退 total_yoy_lt0_long_off | OKX | +9.31% / 0.32 | +24.07% / 0.68 | +59.90% / 2.23 | 0/0 | 0/9 |
| 回退 | Gate | −18.08% / −0.18 | +22.79% / 0.65 | +60.32% / 2.25 | 0/0 | |
| 最好 oil_trend_n24_contra_both（非先验） | OKX | +42.89% / 0.96 | +59.51% / 1.53 | +34.38% / 2.16 | 5/4 | 5/9 |
| 最好 | Gate | +18.30% / 0.41 | +60.24% / 1.54 | +34.64% / 2.17 | 5/4 | |

  - 先验 / 回退 0/9：2022–2025 钻机数长期下行（tune 段占用率 0.69 / 1.00），拦掉了大量正确的新多，deep 与 tune 都大幅变差；post 段未拦到任何新多，与基线完全相同（0 / 0 月）。最好的 econ 侧格 `total_dz_n36_lt1_long_off` 只有 3/9（post = 基线）。
  - 72 格中最高只有 5/9（`oil_trend_n24_contra_both`、`total_trend_n24_contra_both`），post 收益掉 25–38 个百分点；**没有任何格在两所 post 月份达到 ≥ 6/9**。
  - 安慰剂：先验 / 回退平移 +365 天 3/9（高于真实 0/9），+180 天 1/9，其余 0/9——真实信号不优于平移。
  - 邻域：先验 n4 / n5 / n7 / n8 / n9 全部 0/9；最好格 oil trend n22 / n23 / n25 / n26 同为 5/9、n36 降到 2/9（全部 post 掉 25 pp 以上）。
  - 压力费（taker 15.1 bps）：基线 post OKX +55.94% / 2.12、Gate +56.78% / 2.15；先验 / 回退 = 基线；最好格 +33.37% / +33.71%。结论不变。
  - 未调参 new8：先验 pre Sharpe OKX 0.98 vs 1.02、Gate 0.96 vs 0.99（拦掉 51 笔，更差），post = 基线；最好格 pre 0.34 / 0.36 vs 1.02 / 0.99（大幅更差），post 6/3 月但只 +6.6% / +6.0%（Gate 基线 +16.4%）。
- 结论：**否决**。不实现、不进观察名单、不改默认，无代码改动，仅文档；纸面实例不变。
- 勿重测（never retest via）：换 N / 阈值 / 侧 / 方向；换原油 / 天然气 / 总数 / 油气比；换 Baker Hughes 周度、北美 / 加拿大 / 国际钻机数或水平钻机子类；换 EIA 钻井生产率报告（DPR）、完井数 / DUC 库存、压裂车队数（Primary Vision）等同类「能源上游资本开支」实物序列；换同比 z / 月度变化 z；也不要改成 1h「Baker Hughes 周五发布」事件来绕过本条。
- 脚本 `scratch/rigcount4h/{build,prereg,run,new8}.py`、`PRE_REGISTER.json(.sha256)`（研究脚本未推送）。
- 下一轮（短线）：主链出块停顿 / 链停摆冲击（Solana 官方 RPC 的 slot→blockTime 间隔、以太坊 / BTC 官方区块时间间隔异常长）→ 8 币永续篮子 1h 事件；docs / output 中「chain halt / 停摆」0 条，须先查重 btcinterval1h（BTC 出块间隔已测）后只保留未测的链。
