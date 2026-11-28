# 短线新族：USDJPY 日度冲击（日元急升套息平仓 / 日元急贬）→ 8 币永续篮子（2026-11-27 ~20:15–20:45 PST；已否决）

- 族名：`usdjpy_daily_shock_event_1h`。预注册 `scratch/yenshock1h/PRE_REGISTER.json`（任何 PnL 之前锁定，48 格，sha256 `2287fff6ff8d5bc2b26e6c4f7bc610f5e57eafaa847ef7fdb746e8875b95108b`）。脚本 `scratch/yenshock1h/{build,prereg,run,analyze}.py`（研究脚本不推送）。
- 查重：已查 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`。本轮首选「BTC Taproot / OP_RETURN / 铭文 / Runes 见证占比」= 已测的 `btc_witness_bytes_burst_event_1h`（影子 #18），**判重放弃**。USDJPY 仅有 4h 趋势闸门（`fx_jpy_cny_trend_gate_4h`，SMA 拦新开仓），无日度冲击 → 1h 事件篮子，也不同于 N225 开盘缺口、PBoC 人民币中间价、CNY 篮子冲击。
- 机制：日元单日急升（USDJPY 大跌）= 套息平仓（2024-08 式），风险资产 1–2 天内被动去杠杆；对立假设为超跌反弹。
- 数据：Yahoo Finance chart API `JPY=X` 日线收盘（2000-01-03→2026-11-18，6,979 日，公开外汇报价，非 OKX/Gate；未编造未回补）。z = 当日对数收益 / 前 60 日收益标准差（shift 1，至少 40）。事件日 D 收盘 ~23:00 UTC → 可用 D+1 00:00 UTC + 60 分钟，次个整点 1h 开盘入场，H 根后开盘出场；8 币等权（OKX d8 2022-01-29→，OKX 未调 new8，Gate d8 2025-09-24→），官方资金费，重叠事件跳过。手续费 taker 5.1 bps/边（压力 15.1）。
- 格：集合 yenstrong（z≤−k）/ yenweak（z≥+k）× k∈{1.5,2.0,2.5,3.0} × short/long × H∈{4,24,48}。先验 `yenstrong_k2.0_short_H24`；回退 `yenstrong_k2.5_short_H48`。可用：OKX d8 train n≥8 / test n≥8 / post n≥3 且 OKX d8、new8 三段 + Gate post / gate_window 共 8 槽均值 > 0。安慰剂：入场平移 ±24h / ±168h；随机小时（先验 / 回退 1000 次，其余 200 次）。
- 事件数（OKX 可交易期 2022-01-29→）：yenstrong 事件日数 k=1.5 78、k=2.0 41、k=2.5 22、k=3.0 15；post（2026-03-05→）仅个位数。
- 结果：**无任何格 8/8 可用（最高 7/8：yenweak_k2.0_short_H48，但 post 仅 1 件）。**
  - 先验 `yenstrong_k2.0_short_H24`（real）：OKX d8 train n28 −52 bps（t −0.6）、test n7 −218 bps（t −1.1，随机百分位 6）、post n6 +83 bps（t 1.4，随机百分位 80）；Gate post n6 +82 bps；压力费用 post +63。train/test 做空日元急升即亏，只有 post 为正 → 方向不稳。
  - 回退 `yenstrong_k2.5_short_H48`：train −64 / test −352 / post +43 bps（n 13/3/5）。
  - 反向（日元急升后做多反弹）k1.5 H24/H48 在 test/post 为正（+107/+80、+97/+198 bps），但 train 为负或约 0（−3 / −48），平移安慰剂同量级，t 约 1，等同「所有事件总是做多」基线（H24 post +75 bps t 0.9）→ 没有独立信息。
  - 全事件基线（|z|≥1.5，总是做多 / 做空 H4/H24/H48）均不显著（t 绝对值 ≤ 1.5）。
- 结论：**已否决**（无可用格；先验 train/test 为负；信号落在随机 / 平移安慰剂范围；样本量小）。不改默认、不新增影子账本、不改纸面。
- 勿重测：USDJPY 日度收益冲击 z 的 k / 窗口 / 方向 / H 变化、日元强弱互换、换用 EURUSD / CHF / CNH 等其他外汇对的日度冲击、以 1h 外汇替代日线。数据末端 Yahoo 日线停在 2026-11-18（与第二方源不可交叉验证），仅作为信号输入。
- CSV（不入库）：`output/research_usdjpy_daily_shock_event_1h.csv`；事件 `scratch/yenshock1h/usdjpy_daily_events.csv`。下一轮（长线 4h）：另选未测官方数据做 4h 默认书入场闸门。
