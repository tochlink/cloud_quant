# 短线新族：OPEC / OPEC+ 部长级会议（ONOMM / JMMC / 8→7 国自愿减产组）结果新闻稿 → 8 币永续篮子 1h（2026-11-27 ~22:10 PST；已否决）

- 族名：`opec_ministerial_meeting_event_1h`。预注册 `scratch/opecmtg1h/PRE_REGISTER.md` + `PRE_REGISTER_cells.csv`（任何 PnL 之前锁定，24 格，sha256 `aaf9e07b987a70cd327046d27f80e62c5c552d31efa2d74ee039be7ba8507f1f`）。
- 查重：`docs/*.md`、`docs/STRATEGY_FORMULAS.md`、`output/research_*.csv`（1396 个）中 OPEC 0 个研究命中（仅在“下一轮”提示里出现）。已测油 / 能源族（`eia_wpsr_crude_event_1h`、`eia_petroleum_stocks_gate_4h`、`us_rates_oil_trend_gate_4h`、`henryhub_natgas_gate_4h`、`eia_natgas_storage_report_event_1h`、`gasoline_diesel_price_gate_4h`、`bcpi_commodity_gate_4h`）禁的是库存 / 价格序列，不是产量政策会议事件，判新。
- 数据：opec.org 官方新闻稿年度页 `press-releases-2022/2023/2024/2025.html`、当年页 `press-releases.html` 及若干 `pr-detail` 页（每个事件的来源 URL 记在 `scratch/opecmtg1h/opec_events.csv`），共 51 个发布日 2022-01-04→2026-11-01（同日多稿合并）；OKX 期内 50 个（2022-01-04 早于 OKX 起点）。分类只看官方标题 / 正文：decision 34 个（ONOMM，或正文写 adjust / extend / cut / return 产量的会）；review 17 个（只开 JMMC，或只写“reaffirm commitment”不调整）。减产 / 增产方向不作为边，因为拿到的官方文本无法对每个事件一致判定。
- 时点：opec.org 不给发布钟点 → 保守入场 = 维也纳发布日次日 00:00 UTC 那根 1h 的开盘，H 根后开盘出场；8 币等权（OKX d8 2022-01-29→、OKX 未调 new8、Gate d8 2025-09-24→），官方资金费；taker 5.1 bps/边（压力 15.1）；重叠事件跳过。
- 格：set∈{all, decision, review} × long/short × H∈{6,12,24,48}。先验 `decision_long_H24`（2024 年后的 decision 多为恢复供给 → 油价降 → 通胀降 / 偏风险偏好），回退 `all_long_H48`。切分：train <2024-10-21，test 2024-10-21→2026-03-05，post 2026-03-05→，gate_window 2025-09-24→。
- 结果（real，bps/笔）：
  - 先验 `decision_long_H24` 1/8：OKX d8 train n14 −172.8（t −2.2）、test n14 +4.1（随机百分位 57.7）、post n5 −21.8（百分位 48.7）；压力费 test −15.9、post −41.8；new8 train −127.6 / test −40.1 / post −3.9；Gate post −20.3、gate_window n9 −117.5。
  - 回退 `all_long_H48` 2/8：OKX train −14.9 / test −84.6 / post −5.3；Gate post −3.3、gate_window −36.4。
  - 8/8 只有两个非先验格：`all_short_H12`（OKX train n22 +2.6、test n20 +63.3、post n8 +25.8，t 0.6；随机百分位 test 93.0、post 75.5；压力 post +5.8；Gate post +25.1、gate_window +51.0；post 正月数 OKX 4/9、Gate 4/9）和 `all_short_H24`（train +109.6、test +16.6、post +35.0，t 1.1；随机百分位 test 66.0、post 66.5；压力 test −3.4；Gate test −25.2、post +33.7；正月数 5/9、4/9）。二者本质是对全部会议无过滤地总是做空（H24 与 baseline_all_always_short_H24 同值），OKX test 中位数为负（−37.3 / −200.3）；邻域断裂（all_short_H6 5/8、H48 3/8）；H24 的 −168h 平移安慰剂 OKX post +36.1、gate_window +49.6，不弱于真实 +35.0 / +6.7。
  - review 组样本太小（train 8 / test 6 / post 3）；`review_short_H24` 7/8、H48 6/8 不算可用。
- 结论：**已否决**。达不到强观察（随机百分位 post <80、post 正月数 <6/9、邻域不稳、先验失败），不改默认，不加影子账本，不改纸面，无代码改动。
- 勿重测：换 H / 方向 / 分组（decision / review / ONOMM-only / 8 国组 / JMMC-only）；按减产 / 增产 / 维持方向重切；换入场时点（发布当日估计钟点、会议公告日、会前 T-1）；换 OPEC 月报（MOMR）、世界石油展望（WOO）、年鉴（ASB）、补偿计划公告、OPEC Conference、IEA 油市月报、沙特 OSP 官价等任何“油产政策 / 油机构发布日历”事件；做成 4h 闸门。
- CSV（不入库）：`output/research_opec_ministerial_meeting_event_1h.csv`；事件 `scratch/opecmtg1h/opec_events.csv`，逐笔 `scratch/opecmtg1h/events_real.csv`，汇总 `scratch/opecmtg1h/summary.csv`。
- 下一轮（长线 4h）：EIA-930 官方美国本土 48 州小时电力需求（EIA Open Data API，日汇总 + 已知滞后）做 4h 默认书入场闸门（docs / output 中 electricity 0 命中，开跑前再查 eia / grid / power 勿重测范围）。
