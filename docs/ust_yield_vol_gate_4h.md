# 美债官方日度收益率已实现波动率（债市波动 / MOVE 代理）4h 入场闸门（否决）

## 长线新族：美债 10Y / 2Y 收益率已实现波动率 → 4h 默认书入场闸门（2026-11-21 ~14:15 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、`output/research_*.csv`、/workspace/scratch/* 检索 MOVE / bond vol / 利率波动 / 收益率波动 / yield vol 无测试条目。已否决的利率族全部是**水平 / 趋势 / 变动**：DGS10 / 2s10s / WTI 均线趋势（`research_us_rates_oil_trend_gate_4h.csv`）、Kim–Wright 期限溢价、TIPS 实际利率、JGB 10Y 水平 / 变动、SOFR−IORB；波动率族只测过加密自身 vol-of-vol、VIX / VIX 期限结构 / SKEW / VRP / DVOL（股、币隐含波动）。本族是**美债收益率日变动的已实现波动**（债市去杠杆压力），统计量与序列都不同。原定 NAAIM Exposure Index：官网自 2026-08-01 起改为订阅制，免费历史不全，不绕过，换族。
- 机制（看 PnL 前锁定的唯一先验）：债市波动飙升 → 跨资产去杠杆 / risk-off → **拦新开多**：`rv10_20_z252gt1_long_off`（10Y 收益率 20 日已实现波动的 252 日 z > 1 时不开新多）；回退 `rv10_60_trend_n120_long_off`。只拦新开仓，持仓、止损、退出不变。
- 数据（仅官方）：财政部 Daily Treasury Par Yield Curve CSV（home.treasury.gov `daily-treasury-rates.csv/{年}/all?type=daily_treasury_yield_curve`），1990-01-02 → 2026-11-20 共 9,229 个交易日，2Y / 10Y 各缺 1 个值（丢弃，不补），最大间隔 4 天；票面收益率不修订（无 vintage 前视）。存 `output/ust_par_yield_vol_official_daily.csv`（sha256 6677ffff…0380，不入库）。公式：`rv10_20 = std(Δy10_bp, 20 个交易日) × √252`，`rv10_60` 同理 60 日，`rv2_20` 为 2Y。**滞后**：D 日收盘值（官方约 18:00 ET 发布）从 D+1 08:00 UTC 才使用，ffill 到 4h。
- 格子：序列 rv10_20 / rv10_60 / rv2_20 × 形式 z252>0.5/1/1.5/2、`s>SMA60/120`、`s−s[−5/−20]>0` × 侧 long_off / short_off / both / contra_both = **96 格** + 同脚本基线；`PRE_REGISTER.csv` 13:48 PST 在任何 PnL 前锁定（sha256 be6e3f06…a4f3）。harness 同 epu4h / gpr4h：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（永续 maker 2 / taker 5.1 bps），压力 spot 20 / perp 15.1；官方资金费；安慰剂平移；邻域；未调参 new8。
- 占用率：post 段债市波动偏高（rv10_20 z>1 占 29.5%，deep 4.6%、tune 6.5%），但与默认书新多信号几乎不重合。
- 结果（`output/research_ust_yield_vol_gate_4h.csv` 399 行；`_new8.csv`；`_best_placebo.csv`）：
  - 基线 post：OKX d8 +59.90% / Sharpe 2.23，Gate d8 +60.32% / 2.25，OKX d7 +50.76% / 2.10；deep OKX +35.14%、Gate −3.63%；tune OKX +85.08%、Gate +84.25%。
  - 先验 `rv10_20_z252gt1_long_off`：**4/9**，post 与基线完全相同（月份 0/0，没拦到新多）；deep OKX +28.57（输）/ Gate +11.12（赢）/ d7 +49.08（输）；tune +87.73 / +86.81 / +96.21（小赢）。new8 post OKX +12.22% vs +3.26%、Gate +27.07% vs +16.36%（月份 4/0、4/0，pre 不变），但 d8 post 无作用，未达 ≥6/9。安慰剂 +180d 6/9（高于真实 4/9），邻域 z0.75 2/9、z0.25 3/9、z1.75 1/9，z365 1/9。
  - 回退 `rv10_60_trend_n120_long_off`：**3/9**，只赢 deep，tune 变差（OKX +85.08→+71.35），post 相同。
  - 96 格最好的是非先验 `rv10_60_chg_n5_both` **7/9**：post OKX +61.44%/2.29、Gate +62.16%/2.31、d7 +52.06%/2.16，月份 4/4、6/2、2/6（未达 ≥6/9）；OKX d8 deep +20.75 vs +35.14（输）；压力费 post 仍略好（OKX +57.69 vs +55.94）。平移安慰剂（±7/±14/±30/+90/+180/−120/+365 天）最高 5/9，post 全部变差——只有真实格 post 为正。但 new8 全面变差（OKX pre +56.71→+23.30、post +3.26→+2.51，月份 3/5；Gate pre +53.65→+26.43），邻域 chg n3 4/9、n10 3/9、n15 3/9（tune 掉到 +7%）、n30 3/9、n40 6/9、n60 6/9 → n5 是孤立尖峰。另一 7/9 `rv10_20_chg_n5_short_off` Gate deep 输、月份 4/4、4/3、4/3，new8 pre 变差。
- 结论：**否决**，不实现、不进观察名单、不加模拟盘、不改默认，无代码改动。债市已实现波动对默认书新开仓没有稳定增量：先验在 d8 post 空转，未见段输赢参半且被平移安慰剂追平；唯一 7/9 非先验在 new8 与邻域崩塌、月份不足。勿以同一机制换窗口 / z 阈值 / SMA / chg 长度 / 侧，或换期限（1M–30Y、2s10s 波动）、换隐含波动（ICE MOVE / SRVIX / TYVIX）、换 GARCH / 已实现区间波动、换他国国债收益率波动再测。
- 文件：`scratch/ustvol4h/{build,prereg,run,new8,plc_best}.py`，`run.log`，`new8.log`，`plc_best.log`，`PRE_REGISTER.csv`（研究脚本未推送）。
- 下一轮（短线）：Cboe 官方 VIX 月度期货 / 期权最终结算日（VRO，周三开盘结算）→ 8 币永续篮子 1h 事件（上轮指针，仍未测；CME 加密期货到期、IBIT 期权到期、VIX 日冲击已否决）。
