# 地缘政治风险指数（Caldara–Iacoviello GPR 日度）4h 入场闸门（否决）

## 长线新族：Caldara–Iacoviello 地缘政治风险指数（GPR 日度 GPRD / GPRD_ACT / GPRD_THREAT）→ 4h 默认书入场闸门（2026-11-20 ~23:50 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、output/research_*.csv、记忆中无 GPR / geopolitical / 地缘 条目（EPU 也未测，本轮按要求不加）。不同于已测宏观（利率 / 期限溢价 / SOFR−IORB / VIX / 美元 / NFCI）、地磁、链上族。
- 机制（看 PnL 前锁定的唯一先验）：Caldara–Iacoviello（2022 AER）——地缘风险高 → 风险偏好下降 / risk-off → **拦新开多**：`gprd7_z365gt1_long_off`（GPRD 7 日均的 365 日 z > 1 时不开新多）；回退 `gprd7_trend_n180_long_off`。只拦新开仓，已持仓、止损、退出不变。
- 数据（仅官方）：https://www.matteoiacoviello.com/gpr.htm 链接的 `gpr_files/data_gpr_daily_recent.dta`（sha256 daeab440…d022，与同页 .xls 同源；.xls 因环境无 calamine 未解析），当前 vintage。1985-01-01 → 2026-11-16 共 15,295 天，日历缺口 0，缺失 0，丢弃 0（2 天 GPRD=0，是官方真实计数，保留）；7 日均与官方 GPRD_MA7 末值一致（145.08）。存 `output/gpr_official_daily.csv`（不入库）。**滞后**：D 日值从 D+8 天 00:00 UTC 才使用（官方约周更且有修订），ffill 到 4h。**注意**：GPR 是报纸文本计数，会被修订，只有当前 vintage，历史回测存在 vintage 前视偏差（只会让结果偏乐观）。
- 格子：序列 gprd1（日 GPRD）/ gprd7 / act7 / threat7（7 日均）× 形式 z365>0.5/1/1.5/2、`s>SMA90/180`、`s−s[−7/−30]>0` × 侧 long_off / short_off / both / contra_both = **128 格** + 同脚本基线；`PRE_REGISTER.csv` 在任何 PnL 前锁定（sha256 2e174ecb…44b4）。harness 复制 geomag4h / kwtp4h：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（现货 10 / 永续 taker 5.1 bps，maker 2 bps），压力 20 / 15.1；官方资金费；安慰剂 ±7 / ±14 / +180 / −120 / +365 / −119 天（先验与回退都跑）；邻域；未调参 new8。修正了旧模板 is_econ 把 contra_both 误当 both 的后缀 bug。
- 结果（`output/research_gpr_geopolitical_risk_gate_4h.csv` 492 行；`_new8.csv`）：基线 post OKX +59.90% / Sharpe 2.23，Gate +60.32% / 2.25；deep OKX 0.71、Gate 0.09、d7 0.75。
  - **先验** `gprd7_z365gt1_long_off`：仅 3/9（只赢 3 个 tune 段，1.51 / 1.50 / 1.57 vs 1.47 / 1.46 / 1.56）；post 与基线**完全相同**（OKX +59.90 / 2.23，Gate +60.32 / 2.25，月份 0 好 / 0 差——post 的 14 笔新多都不在高 GPR 窗口）；**deep unseen 输**：OKX 0.05 vs 0.71，Gate −0.39 vs 0.09，d7 0.33 vs 0.75；压力费同样输（OKX deep −0.10 vs 0.56）。
  - 回退 `gprd7_trend_n180_long_off`：0/9（deep 0.41 / −0.03 vs 0.71 / 0.09，tune 1.35 vs 1.47），post 同基线。
  - 安慰剂：先验平移 −120 / −119 天达 6/9（deep OKX 0.77 / 0.80，远高于真实 0.05），回退平移 −120 / −119 也 6/9；±7 / ±14 天 0–3/9。平移序列不弱于甚至强于真实 → 无特异信息。
  - 全格无 7/9 以上；最好非先验 `gprd7_trend_n180_short_off`（低 GPR 时不开新空）6/9：post OKX +61.88 / 2.37、Gate +62.87 / 2.40，月份仅 5/2、5/2（< 6/9），deep 被打穿（OKX −0.19 vs 0.71，Gate −0.59 vs 0.09，d7 0.10 vs 0.75）；邻域 n120 post +67.28 / 2.53 但 deep 仍输，n150 post 不如基线，n60 / 270 / 365 post 大幅变差，不稳定；非先验，不可晋升。
  - 未调参 new8（官方 OKX / Gate 4h，2024-11-26 起）：先验 pre Sharpe 1.08 / 1.05 vs 1.04 / 1.02，post 与基线完全相同；非先验 short_off post 1.14 / 1.71 vs 0.28 / 1.00（月份 4/3），但 d8 deep 不复现。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动，仅文档。勿以同一机制换 k / n / 窗口 / 方向、换 GPRD / ACT / THREAT / 月度 GPR / 国别 GPR、换 7 / 30 日均或 z252，或换 EPU / WUI 等新闻文本不确定性指数（若要测 EPU 须单独立项）再测。
- 脚本 `scratch/gpr4h/{build,prereg,run,new8}.py`、`PRE_REGISTER.csv(.sha256)`（研究脚本未推送）。默认策略与纸面实例均未改动。
