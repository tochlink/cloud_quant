## 短线新族：Cboe VIX 月度结算（VRO，周三 09:30 ET 特别开盘报价）→ 8 币永续篮子 1h 事件（2026-11-27 ~09:15 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`（含轮换日志）、`docs/*.md`、`output/research_*.csv`（约 1,300 个）、`/workspace/scratch` 目录名与记忆中检索 VRO / VIX settlement / VIX 结算 / 到期：VRO 只以「下一轮（短线）」指针出现 5 次，从未执行。已否决的相邻族：CME 加密月度期货到期 + IBIT 月度期权到期（周五，`research_cme_ibit_expiry_event_1h.csv`）、Deribit / Gate 期权到期、月末到期日历闸门、VIX 期限结构 4h 闸门、VIX 日冲击。本族锚点不同：美股**波动率**衍生品（VIX 期货 / 期权）在周三开盘 SOQ 结算，机制假设 = 交易商 vega / vanna 对冲在结算后解除，结算日 → 周五 OPEX 的「弱势窗口」(window of weakness) 波及唯一 24/7 的风险资产。
- 数据（只用官方，不编造、不回补）：Cboe 官方 `VRO_History.csv`（cdn.cboe.com，sha256 a681d9df…，含 2021 年起每周结算）与 `VIX_History.csv`（sha256 195053f3…）。月度标准结算日按 Cboe 规则（次月第三个周五往前 30 天的周三；遇节假日顺延到前一交易日）计算，并与 VRO 官方日期逐一核对：2021-01→2026-11 共 66 个月度全部匹配（2022-03-15、2024-06-18、2025-03-18、2026-05-19 为周二，与 Cboe 节假日规则一致）；其余 221 个为周度结算。交易：OKX 官方 1h 永续 d8（2022-01-29 → 2026-11-23 06:00 UTC，42,216 根，0 缺口）、未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）、Gate 官方 1h 永续 d8（2025-09-24 →，10,199 根，0 缺口）、官方资金费；真实 taker 5.1 bps×2 + 资金费，压力 15.1 bps×2。事件表 `output/vix_vro_settlement_official.csv`（不入库）。
- 公式（全部因果；结算日日期提前公布）：
  - `win`：结算日 10:00 ET（SOQ 后第一根完整 1h）开盘入场，固定方向，持有 H 根后开盘平。
  - `pre`：结算日前两个美股交易日 10:00 ET 入场，固定方向。
  - `gap`：g = ln(VRO / 前一交易日 VIX 收盘)，z = (g − 前 24 个同类事件均值) / 标准差（不含本次）；k=0 只看符号，k=1 要求 |z| ≥ 1；follow：g>0（结算时波动率被抢买）→ 做空，g<0 → 做多；fade 反向；11:00 ET 入场（VRO 开盘后才发布）。
  - 篮子等权，不重叠，持有期内计资金费。
- 预注册（`scratch/vixvro1h/PRE_REGISTER.json`，任何 PnL 前锁定，sha256 be1a77ab…e402）：{monthly, weekly} × [win {short,long} × H{6,24,48} + pre {long,short} × H{24,48} + gap {follow,fade} × k{0,1} × H{6,24,48}] = **44 格**。先验 `monthly_win_short_H48`（结算 → OPEX 弱势窗口做空），回退 `monthly_gap_follow_k1_H24`。usable = 8 槽（OKX d8 train/test/post、new8 train/test/post、Gate post/gate_window）全正且 OKX n ≥ 10/6/4；切分 train 2022-01-29→2024-10-21（深度未见）、test →2026-03-05、post →2026-11-23。安慰剂：±168h / ±336h 平移、同星期同 ET 钟点随机非事件小时；事后补充（标注）：因 2021 年起每个周三都是 VIX 周度结算，月度格再用「随机抽同数量的**非月度**周度结算日、同入场钟点」2,000 次做对照。
- 结果（真实费，每笔净 bps，OKX d8 train / test / post；`output/research_vix_vro_settlement_event_1h.csv` 2,578 行）：

| 格 | 槽 | OKX d8 train / test / post（n） | new8 train / test / post | Gate post / gate_window | 压力费 OKX | 周度结算对照分位 train / test / post |
|---|---|---|---|---|---|---|
| **先验** monthly_win_short_H48 | 1/8 | +14.6 (33) / **−109.9** (16) / **−229.3** (9) | −10.3 / −59.9 / −289.2 | −230.1 / −60.8 | −5.4 / −129.9 / −249.3 | 89 / 15 / 0 |
| **回退** monthly_gap_follow_k1_H24 | 3/8 | −9.6 (9) / −28.6 (8) / +31.1 (2) | −14.7 / −1.0 / +47.0 | +32.0 / −17.9 | −29.6 / −48.6 / +11.1 | —（同钟点随机：test 36） |
| 最佳非先验 monthly_win_long_H24（先验的反向） | 7/8 | +32.0 (33, t 0.61) / +87.1 (16, t 1.09) / +65.3 (9, t 0.42) | +45.8 / +56.7 / +45.0 | +65.6 / **−9.1** | +12.0 / +67.1 / +45.3 | 80 / 97 / 99.95 |
| 唯一 8/8 monthly_gap_follow_k1_H6 | 8/8 | +87.4 (9) / +74.2 (8) / +6.8 (**2**) | +111.1 / +81.1 / +36.1 | +6.9 / +34.3 | +67.4 / +54.2 / **−13.2** | — |
| 基线 每个周三 10:00 ET 做空 H24 | — | −18.6 / +3.5 / +75.0 | | +74.3 / +96.1 | | |

  - 44 格槽数分布 {0:4, 1:2, 2:7, 3:10, 4:7, 5:7, 6:4, 7:2, 8:1}，**usable 0 格**。
  - 先验（结算 → OPEX 做空）在 test / post 两所一致亏损，post 比周度结算对照还差（分位 0）；+168h 平移（下一个周三做空）post +259，说明 2026 年的「周三做空」是普通工作日季节性，与月度结算无关。
  - 反向的 monthly_win_long_H24 相对「其他周三」好（因为 2026 年周三做多普遍 −95 bps），但绝对收益 t 都 < 1.1，Gate 窗口 −9，post 月份 4/9 正；邻域不稳：H6 test −34、H48 train −35；train 段 −168h 平移（+54.6）好于真实（+32.0）。属于事后反向挑格，不立观察。
  - 唯一 8/8 的 gap_follow_k1_H6 post 只有 2 笔，达不到 n 门槛，压力费 post 为负。
- 结论：**否决**，不实现、不进观察名单、不加纸面、不改默认，无代码改动。VIX 月度结算对 8 币永续篮子没有稳定、超出费用与「普通周三」安慰剂的方向性效应。
- 勿重测：不要换 H / 方向 / 入场钟点（10:00 ↔ 11:00 ET、结算前 n 天）、换 gap 阈值 k / z 窗口、在月度 ↔ 周度 ↔ 季度结算之间互换，不要改用 VIX 期货结算价、SPX AM 结算（SET）/ 第三周五 OPEX / 季度「四巫日」、VIX 期权未平仓量或其他 Cboe 波动率指数（VXN、VVIX、RVX）结算来重测「美股衍生品结算日历 → 加密篮子」机制；也不要把它改成 4h 闸门或逐币反应。
- 文件（不入库）：`output/research_vix_vro_settlement_event_1h.csv`、`output/research_vix_vro_settlement_event_1h_supp.csv`（基线 / t 值 / 周度结算对照）、`output/vix_vro_settlement_official.csv`；脚本 `scratch/vixvro1h/{build,prereg,run,analyze,supp,plog}.py`、`PRE_REGISTER.json`（研究脚本不推送）。
- 纸面：8788 / 8789 / 8792 及 8793–8798 均在运行，未改动；2026-11-27 08:00 PST 起只有 8788 一笔 XRP 调仓买入（08:00:05 PST，目标偏离 >10% 的正常调仓），与预期一致。
- 下一轮（长线）：iShares IBIT 官方日度市价对 NAV 折溢价（发行人官网历史）n 日趋势 / 分位 → 4h 默认书入场闸门；须先与已否决的美国现货 ETF 资金流趋势闸门（`research_us_spot_etf_flow_trend_gate_4h.csv`）和 GLD 持仓闸门的勿重测条款核对，历史仅 2024-01 起，深度未见段约 9 个月。
