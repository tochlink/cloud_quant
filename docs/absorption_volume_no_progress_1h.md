# 短线新族：1h「放量不涨跌」吸收事件（高投入、低结果，Wyckoff effort-vs-result）→ 8 永续逐币（2026-11-27 ~07:07–07:25 PST，研究，否决）

- 查重：文档 / `output/research_*.csv` / 记忆里已测的相邻族有 basket_volume_shock（全篮子成交额冲击）、CMF/MFI（收盘位置×量）、absorption_ratio（PCA 吸收比，与本族无关）、15m 影线回撤、微观结构 1h 事件、收益自相关（方差比）。没有「逐币单根 1h：成交量 z 高但 |收益|/σ 很小（量价背离的『无进展』）→ 按此前 L 小时趋势方向顺 / 逆」的条目。
- 公式（`scratch/absorb1h/PRE_REGISTER.json`，sha256 `dbcbc4e54e96bea52de8efe186b390e2df0de40090bb91a41e3b833bffe75498`，在任何 PnL 前锁定；48 格）：
  - 第 i 根 1h 收盘后触发：`vz_i = (ln(1+v_i) − μ720)/σ720 ≥ k`（720h 滚动，shift 1）且 `|r_i| / σ168 ≤ e`（σ168 = 此前 168 根 1h 对数收益标准差，shift 1）；趋势 `T = ln C[i−1] − ln C[i−L−1]`；方向 `follow = sign(T)`、`contra = −sign(T)`；下一根开盘吃单入场，持有 H 小时，同币不重叠。
  - 网格 L{24,72} × k{2,3} × e{0.5,1.0} × 方向{contra,follow} × H{12,24,48}；先验 `abs_L24_k2.0_e0.5_contra_H24`（趋势末端放量不动 = 衰竭），后备 `abs_L24_k2.0_e0.5_follow_H24`；邻域 = 网格内相邻格；安慰剂 = 事件序列 ±720h 平移；同脚本基线 = 同 L / 方向 / H 的每小时全入场；真实费 taker 5.1 bps × 2 + 官方资金费，压力费 15.1 bps × 2。
- 数据：官方 OKX 1h 永续（8 币 2022-01-29 起）、Gate 1h 永续（2025-09-24 起，所以 Gate 无 train 段）、未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI，OKX 官方 1h，2022-01-29 起）+ 官方资金费；本地 1h 数据截止 2026-11-23 06:00 UTC。分段 train → 2024-10-21（deep unseen）、test → 2026-03-05、post → 末尾。
- 结果（每笔均值 bps，扣费后；括号为事件数）：

| 格 | OKX train | OKX test | OKX post | Gate test | Gate post | new8 train / test / post |
|---|---|---|---|---|---|---|
| 先验 contra | −37.5 (572) | +53.0 (337) | −0.2 (114) | −52.0 (72) | +0.6 (103) | +18.2 / +25.1 / −37.5 |
| 后备 follow | +17.1 (572) | −73.4 (337) | −20.2 (114) | +31.6 (72) | −21.0 (103) | −38.6 / −45.5 / +17.1 |
| 同脚本基线 L24 contra H24 | −7.2（new8 train）| −21.6 | −8.0 | −16.8 | −8.2 | — |

  - 先验 4/8 个可比段为正、后备 3/8；post 的 t 值 −0.0 / −0.5；post 月份好于基线 4/9（OKX）、4/9（Gate）。
  - 48 格里 0 格同时满足「≥7/8 段为正且 post 事件数 ≥30」；事件数 ≥30 的格最多 5/8 段为正；OKX 与 Gate post 同时为正的格 10/48，post 月 ≥6/9 且两所都满足的只有 2 格（post 收益 +0.7 / −19 bps 与 −14 / +21 bps，没有经济意义）。
  - 最佳「7/8」格 `abs_L24_k3.0_e1.0_contra_H24` 只有 post 16 笔（OKX，t 1.0；Gate post 10 笔 −24.3 bps），+720h 安慰剂 post −128 bps 而 −720h 为 +56 bps，说明是少数大波动事件，不是机制；压力费后仍 +132 bps 但无复现价值。
  - 同脚本基线（每小时全入场）所有 L/方向/H 在 post 都是 −5…−16 bps（基本等于 2 × 费用 + 资金费），事件过滤没有把均值抬离 0。
- 结论：**否决**。不改默认、不新增纸面子账本、无代码改动。勿以同一机制换 L / k / e / H / 方向、换成 15m 或 4h 根、换成成交额（quote volume）或 Parkinson 范围、或按币 / 按侧分池再测。
- 文件（不入库）：`output/research_absorption_volume_no_progress_1h.csv`（含 prereg sha）、`_months.csv`；脚本 `scratch/absorb1h/{prereg,run,an}.py`。
