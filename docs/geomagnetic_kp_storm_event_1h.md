# 短线新族：地磁风暴（GFZ 行星 Kp 指数）→ 8 币永续篮子（2026-11-27 ~21:45 PST；已否决）

- 族名：`geomagnetic_kp_storm_event_1h`。预注册 `scratch/geomagkp1h/PRE_REGISTER.json`（任何 PnL 之前锁定，24 格，sha256 `5517b0880f496b62c7a5e815293d9ae75456e64e93341df043f457305007579e`）。
- 查重：`docs/*.md`、`output/research_*.csv`（1393 个）、记忆；`lunar_phase_event_1h`、`usgs_earthquake_event_1h` 只是天文 / 地震日历，无太阳 / 地磁；Kp / geomagnetic / 太阳风 0 命中，判新。
- 机制：文献（Krivelyova–Robotti 2003）称强地磁风暴与情绪 / 风险偏好变差、股市回报偏低；先验 = 风暴后做空篮子 1–3 天。低先验，诚实测试。
- 数据：GFZ Potsdam 官方 3 小时 Kp（kp.gfz.de JSON API，2005-01-01→2026-11-28，64,009 条，公开，未编造）。事件 = Kp≥k 的首个 3h 区间（此前 24h 内无 Kp≥k）；区间结束后 +60 分钟可用，入场该整点 1h 开盘，H 根后开盘出场；8 币等权（OKX d8 2022-01-29→、OKX 未调 new8、Gate d8 2025-09-24→），官方资金费；taker 5.1 bps/边（压力 15.1）；重叠事件跳过。
- 格：k∈{5.0,5.67,6.33,7.0}（G1–G3+）× short/long × H∈{24,48,72}。先验 `kp5.0_short_H24`，回退 `kp6.33_short_H48`。事件数（OKX 期）：k5 145、k5.67 57、k6.33 44、k7 23；post（2026-03-05→）k5 仅 21、k6.33 仅 4。
- 结果：**无任何格 8/8 可用**（最高 7/8 `kp5.67_long_H72`，post n=9，t 0.45，且同 k 的做空也相近，等同总是做多基线）。
  - 先验（real，bps/笔）：OKX d8 train n76 −4.4、test n48 +20.2（随机百分位 74）、post n21 −14.8（t −0.2，百分位 40）；压力费 test +0.2、post −34.8；Gate post −14.8。new8 train −2.2 / test +37.2 / post −9.4。
  - 回退：OKX train +3.1 / test −9.9 / post +146（n=4，t 1.3，百分位 77）；new8 test −95.5。样本只有 4 件。
  - 全事件基线（总是做空 k5 H24/48/72）与先验同值，说明先验 = 基线，没有信息。
  - 平移 ±24h/±168h 安慰剂与真实同量级。
- 结论：**已否决**，不改默认，不加影子账本，不改纸面，无代码改动。
- 勿重测：换 Kp 阈值 / 窗口 / 方向 / H；换用 Ap、Dst、F10.7、太阳耀斑 / 太阳黑子 / 太阳风速度 / X 射线、NOAA G 级预警、日冕物质抛射公告等任何空间天气序列；换天文 / 地震 / 月相类自然现象事件；做成 4h 闸门。
- CSV（不入库）：`output/research_geomagnetic_kp_storm_event_1h.csv`；事件 `scratch/geomagkp1h/kp_events.csv`。下一轮（长线 4h）：另选未测官方数据做 4h 默认书入场闸门；下一个短线备选：OPEC / OPEC+ 部长级会议新闻稿发布事件（先核对 eia_wpsr_crude / henryhub 勿重测范围）。
