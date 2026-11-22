# Cboe 官方美股期权认沽 / 认购成交比 → 4h 默认书入场闸门（先验否决；非先验弱观察）

## 长线新族：Cboe put/call ratio（equity / total / index，5 日均）作为 4h 默认书入场闸门（2026-11-22 ~02:05 PST，研究，不改默认）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,157 个）中 Cboe put-call ratio 只作为「下一轮」指针出现（us_megacap_earnings_8k_event_1h、steth_eth_discount_shock_event_1h），从未跑过；已测 Cboe 族只有 VIX 期限结构、SKEW、跨资产隐含波动（GVZ/OVX/VXN/RVX）；Deribit 加密期权偏斜 / 认沽认购量闸门（2026-11-14）是不同市场、不同数据源。不是宏观利率 / 流动性 / 信用、链上、情绪调查（AAII / NAAIM 官方免费历史不可得）。
- 机制：美股期权认沽需求 = 美国投资者的对冲 / 恐慌程度。闸门只拦新开仓，已有持仓、止损、离场不变。
- 数据（只用官方，不编造、不回补）：Cboe 官方每日市场统计 JSON `https://cdn.cboe.com/data/us/options/market_statistics/daily/YYYY-MM-DD_daily_options`，2019-10-07 → 2026-11-20 共 1,793 个交易日；非交易日返回 403（不建行、不填），最长日历间隔 4 天；自算 put/call 与官方公布的 EQUITY / TOTAL P/C 两位小数逐日一致（差 0.00）。2025-01-09（卡特国葬休市）股票期权成交为 0 → equity 记 NaN。D 日 D+1 12:00 UTC 起用，前向填充到 4h K 线。存 `output/cboe_putcall_official_daily.csv`（不入库）。
- 公式：`eq5 / tot5 / idx5` = equity / 全部产品 / 指数期权 put_vol ÷ call_vol 的 5 个交易日均值；形式 `z = (s − SMA252) / STD252 > k`（k 0.5/1/1.5/2）、`s > SMA(n)`（n 60/120）、`s − s.shift(n) > 0`（n 5/20）；侧 long_off / short_off / both / contra_both / cap_short_off（flag=1 时拦新空）。3 × 8 × 5 = 120 格，看 PnL 前锁定（PRE_REGISTER.json）。先验：高认沽 = risk-off → long_off / both；回退 eq5_z252gt1_long_off。
- 验证：OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）官方永续 + 现货 4h，真实资金费；真实费率（永续 maker 0.02% / taker 0.051%）与压力费率（永续 taker 15.1 bps）；深未见 →2024-10-21、调参段 →2026-03-05、post →2026-11-14；同脚本基线；安慰剂日历平移 ±7/±14/+180/−120/+365/−119 天；邻域；new8 未调参币。
- 结果（`output/research_cboe_putcall_ratio_gate_4h.csv`、`_supp.csv`、`_new8.csv`）：
  - 基线（真实费率）：OKX 深 +35.14%/0.71、调参 +85.08%/1.47、post +59.90%/2.23；Gate −3.63%/0.09、+84.25%/1.46、+60.32%/2.25。
  - 先验（long_off / both）失败：long_off 在 post 段对账本完全没有影响（post 收益逐位相同、月份 0/0）；最好的先验格 idx5_z252gt1_long_off 6/9 只是深 / 调参 Sharpe +0.02~0.03 的微差，平移安慰剂同样量级。both 侧中位 0/9，eq5_chg_n5_both post 三套都差 2/7 月。
  - 非先验最好：tot5_z252gt1_cap_short_off（全部产品认沽比 5 日均 z>1 时不开新空，「恐慌时不追空」）8/9：OKX 深 +35.69/0.72、调参 +118.25/1.80、post +62.77/2.38（月 5 好 / 2 差）；Gate 深 +2.30/0.18、调参 +116.56/1.79、post +63.58/2.41（4/2）；压力费率仍胜（OKX post 59.80 vs 55.94，Gate 60.62 vs 56.78）。
  - 安慰剂：调参段增益是特定的（真实 +118 / +117 vs 平移最多 +96 / +95），但 post 增益不特定（+7d / +14d / +180d 平移 post 也有 +63~64%）；深未见只有 OKX +0.5 pp。
  - 邻域：z 0.25 / 0.5 / 0.75 / 1.0 都正（post +63.5~65.5%），1.25 post 转差（54.1 / 54.7），≥1.75 无触发；tot5 trend n60/n120 cap_short_off 调参与 post 好但深未见明显变差（Gate −21.8 / −18.1 vs −3.6）。
  - new8 未调参：pre +62.3 vs +47.5（OKX）、+60.4 vs +44.7（Gate），post 2.41 vs 3.26（OKX 差）、16.29 vs 16.36（Gate 平）。
- 结论：**先验否决；非先验 tot5_z252gt1_cap_short_off 弱观察（只监控，不实现、不进纸面）**。post 好月只有 5/9、4/9（< 6/9 默认门槛），post 增益不比时间平移安慰剂大，深未见几乎无增量，new8 post 不支持。不改默认、不改纸面。
- 勿重测：不要通过改 k / n / 平滑窗口 / z 窗口 / 方向，或在 equity / total / index / ETP / SPX / VIX 认沽比、认沽认购成交额 / 未平仓量之间互换，或改用 Cboe 旧 CSV 拼更早历史的方式重测本族。弱观察格只在有 ≥3 个月新的 post 数据后原样复核一次（tot5 z252>1 拦新空）。
