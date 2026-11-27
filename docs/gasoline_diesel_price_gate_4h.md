# 长线新族：EIA 官方周度零售汽油 / 柴油价格 → 4h 默认书入场闸门（2026-11-27 07:43 PST，研究，不改默认；否决）

## 机制与公式
- 假设：消费者燃料成本上升（零售汽油相对 156 周分布偏高）→ 购买力 / 通胀压力 → risk-off → 拦新开多。这不是已否决的 WTI（DCOILWTICO，原油价）、Henry Hub 天然气、EIA 库存 / 钻机数、CPI / 盈亏平衡通胀闸门；是终端零售价（含炼厂裂解与税）。
- 数据（仅官方）：EIA 周度美国零售普通汽油 GASREGW（1990-08-20→2026-11-23）与柴油 GASDESW（1994-03-21→2026-11-23），经 FRED fredgraph.csv 转载（EIA 原值不修订）；重叠 1,706 周，0 缺值，0 断点（>7 天）。output/eia_gasoline_diesel_weekly_official.csv sha256 6403f5bc3413117850356486f8188e6af4cebc178926e0a101d60feaa5dd5386。不补缺、无合成。
- 滞后：周一日期的价格自「观测日 + 2 天 08:00 UTC」起才可用，前向填充到 4h 棒。
- 序列：lgas = ln GASREGW；ldsl = ln GASDESW；dslgas = 柴油 / 汽油比。形式：z（156 周窗口，k = 0.5/1/1.5/2，标签 z252）、趋势 s > SMA{13,26} 周、变化 s − s.shift{4,13} > 0。侧：long_off / short_off（flag=0 拦新空）/ both / contra_both。闸门只拦新开仓，同向持仓、出场、止损不动。
- 96 格预注册（scratch/gasoline4h/PRE_REGISTER.csv，sha256 813921a93f3a1318bfd076fa7467025f8ce8a1b899316bdf1670a5f158ac9005，看 PnL 前锁定）；唯一先验 lgas_z252gt1_long_off；回退 lgas_trend_n26_long_off。
- 验证：同脚本 qtw.backtest 默认 4h 书基线（双均线 50/150），OKX d8（2023-02→）、Gate d8（2022-07→）、OKX d7 去 BNB（2022-04→）；deep 未见 →2024-10-21，tune →2026-03-05，post →2026-11-14；永续 taker 5.1 / maker 2 bps，压力 spot20 / perp15.1；官方资金费；±7/14/180/−120/365/−119 天安慰剂；邻域；untuned new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI）。

## 结果（vs 同脚本基线）
| 单元 | 9 段 Sharpe 胜 | OKX d8 post（基线 +59.90% / 2.23） | Gate d8 post（基线 +60.32% / 2.25） | 月份更优/更差 OKX · Gate · d7 | 备注 |
|---|---|---|---|---|---|
| 先验 lgas_z252gt1_long_off | 1/9 | +39.53% / 1.86 | +39.78% / 1.87 | 1/3 · 1/3 · 1/3 | post 汽油 97% 时间 flag=1 → 长期封多，损失 −20 pp；deep / tune 从不触发（与基线相同） |
| 回退 lgas_trend_n26_long_off | 3/9 | +39.53% / 1.86 | +39.78% / 1.87 | 1/3 · 1/3 · 1/3 | post flag=1 94%，同样拦多 |
| 最佳非先验 ldsl_chg_n13_short_off | 8/9 | +67.65% / 2.51 | +68.85% / 2.55 | 3/3 · 4/2 · 2/4 | 月份未达 ≥6/9（OKX 3 好 3 差；d7 2 好 4 差）；tune 收益 79.8% 低于基线 85.1% |
| lgas_chg_n13_short_off | 6/9 | +67.65% / 2.51 | +68.85% / 2.55 | 3/3 · 4/2 · 2/4 | 同上 |

- 邻域（ldsl_chg_short_off）：n=2 −74.6 pp、n=3 −14.4 pp、n=6 −79.2 pp、n=8 +5.4 pp（6/9）、n=10 +17.9 pp（5/9）、n=26 +3.2 pp（3/9）→ 只有 n=13 附近有边，不稳定。先验邻域 z=0.25–1.25 全部 post −53.6 pp，z=1.75 −30.3 pp。
- 安慰剂：先验 ±7/±14 天平移结果与原先验完全相同（周序列 + post 常数 flag），+180 天 3/9，+365/−119/−120 天 post 无变化；没有一个安慰剂能「证伪」先验，是因为先验本身就在 post 失败。回退 ±7/14 天 3/9 且 −53.6 pp。
- new8（untuned，OKX / Gate 近 4,500 棒）：先验 post +5.05% vs 基线 +3.26%（OKX），+18.82% vs +16.36%（Gate），月份 3/1；但同一先验在 d8 上 −53.6 pp，方向相反 → 无稳定边。最佳非先验在 new8 pre 段明显更差（OKX 13.6% vs 32.5%）。
- 压力费（spot20 / perp15.1）下排序不变。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例。
- 勿重测：勿以改 n / z 阈值 / 窗口、改方向、换汽油 ↔ 柴油 ↔ 柴汽比、改 EIA 其他零售价（取暖油、丙烷、E85、航空煤油）、改同比 / 实际价（CPI 平减）、换成 AAA 价格来重测「美国燃料零售价 → 4h 默认书入场闸门」。
- 输出：output/research_gasoline_diesel_price_gate_4h.csv、output/research_gasoline_diesel_price_gate_4h_new8.csv、output/eia_gasoline_diesel_weekly_official.csv（本机，不推送）。
