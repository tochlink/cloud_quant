# 短线新族：8 币横截面收益离散度 / 同涨同跌（herding）1h 冲击 → 8 币永续篮子（2026-11-21 ~15:40–15:50 PST，研究，不改默认；否决）

- 选题与查重：上一轮指针 Cboe VIX 月度结算（VRO）与已否决的「到期日历事件」（CME 加密期货到期、IBIT / Deribit / Gate 期权到期、月末交割窗口闸门）同族，不做。本轮做 docs 中 2026-11-21 ECB 节曾列为「下一轮」但从未执行的「跨币种 1h 收益横截面离散度骤升 / 骤降」。查重：离散度此前只作为 4h 默认书**静态水平入场闸门**测过（2026-11-10 `research_market_breadth_dispersion_gate.csv`）；广度冲刺、篮子投降 / 集体暴涨、篮子成交额冲击都看方向或幅度，不看「币与币之间分得多开」。`output/research_*.csv`、docs、记忆中无离散度 / herding 的 1h 事件测试。
- 公式（看 PnL 前锁定 `scratch/disp1h/PRE_REGISTER.csv`，2026-11-21 23:44:11 UTC = 15:44 PST，sha256 `03364658…28ae8`，96 格）：
  - `r_i,L = ln C_i(t) − ln C_i(t−L)`（同一交易所 / 同一币池、只用已收盘 1h，≥6 币有值）；`disp = 横截面 std(r_i,L)`；`herd = |横截面均值| / disp`（所有币同向同幅 → 大）。
  - `x = ln(序列)`，`z = (x_t − mean_{t−720..t−1}) / std`（W = 720h，最少 360）；触发：high `z ≥ k` / low `z ≤ −k`；方向 follow = 篮子 `mean r_L` 的符号，contra = 反向；下一根 1h 开盘吃单入场，持有 H 小时后开盘离场，不重叠，8 币等权。
  - 网格：序列 {disp, herd} × L {1, 4} × k {2, 3} × side {high, low} × dir {follow, contra} × H {12, 24, 48}。
  - 唯一先验 `herd_L4_k2_high_contra_H24`（4h 同涨同跌骤升 = 宏观 / 爆仓驱动的共同运动过冲 → 反向 24h）；回退 `disp_L4_k2_high_follow_H24`。
  - **修正 A1**（2026-11-21 23:45:26 UTC = 15:45 PST，只看过触发占比、未看任何 PnL 时锁定，`scratch/disp1h/AMENDMENT_A1.txt`）：herd 下有界接近 0，`ln(herd)` 左偏，`z ≥ 2` 在所有币池只占 0.000–0.001 → 所有 herd-high 格（含先验）退化为 0 笔。只对 herd-high 改用原值 z（占比 z≥2 约 4.5%、z≥3 约 1.3%），其余不变；原退化行保留在 CSV（`amendment=orig`）。
- 数据（仅官方）：OKX USDT 永续 1h（2022-01-29 → 2026-11-20 23:00 UTC）、Gate USDT 永续 1h（2025-09-24 →）、未调参 OKX new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，离散度用 new8 自身计算）；官方资金费（OKX 深历史官方 csv、Gate 官方 csv）。无现货替代、无合成、无补值。
- 验证：OKX d8 train（→2024-10-21，深未见）/ test（→2026-03-05）/ post（→末），Gate d8 post + gate_window（2025-09-28→），new8 三段；真实吃单 5.1 bps/边，压力 15.1；官方资金费；±720h 平移安慰剂（全格）；先验 / 回退 / 最佳格追加 ±168/±336/±2160h 平移与邻域（k±0.5、W 336/1440、L 2/8、H 18/36）；同脚本逐小时基线（同方向规则、同 H）与 post 月度。
- 结果（`output/research_cs_dispersion_herding_shock_event_1h.csv` 4,800 行；`_nbhd_placebo.csv`；`_months.csv`），每笔净收益 bps（真实费）：

| 格 | OKX 深未见 | OKX test | OKX post | Gate post | new8 train/test/post | 8 槽为正 | post 月份胜（OKX / Gate） |
|---|---|---|---|---|---|---|---|
| 先验 herd L4 k2 high contra H24 | −0.4 (n399) | −18.0 | −14.0 (n108, t −0.6) | −15.4 | +25.0 / +12.5 / +27.9 | 3/8 | 3/9 / 4/9 |
| 回退 disp L4 k2 high follow H24 | −39.0 (n190) | +17.0 | +14.1 (n53, t 0.3, 中位 −9) | +10.4 | −6.0 / +12.7 / +8.7 | 5/8 | 5/9 / 5/9 |
| 最佳非先验 disp L4 k3 high follow H48 | −39.3 (n36) | +33.6 | +176.6 (n10, t 1.3) | +178.2 | +25.9 / +8.0 / +52.3 | 7/8 | 4/9 / 4/9 |

  - 96 格 8 槽为正分布：0:6、1:13、2:19、3:24、4:15、5:13、6:5、7:1；**可用 8/8 为 0**。
  - 先验 post 同脚本基线 OKX −6.3 / Gate −7.2 bps，事件更差；压力费 post −34.0 / −35.4；邻域 k1.5/k2.5、W336/1440、L2、H18/36 的 OKX d8 post 全部为负（只有 L8 +6.7）；+2160h 平移安慰剂（+20.1 / +26.6）反而优于真实。
  - 回退 post 被平移安慰剂追平或超过（+336h：+67.4 / +62.6；−336h +36.3 / +30.2），邻域 k1.5 / k2.5 post −48 / −53，深未见 −39。
  - 最佳 7/8 只有 10 笔 post、深未见 −39，+336h 平移安慰剂 post +215.8（高于真实），k3.5 post −143 → 孤立尖峰。
- 结论：**否决**，不实现、不进观察名单、不加模拟盘、不改默认，无代码改动。8 币横截面离散度 / 同涨同跌冲击对未来 12–48h 篮子方向没有稳定信息：先验在 OKX d8 三段与 Gate post 全负，回退与最佳格在深未见段亏损并被平移安慰剂追平。勿以同一机制换 L / k / W / H / 方向 / 高低侧再测，也勿换离散度定义（MAD、四分位距、秩离散、相对 BTC 的残差离散）、换平均成对相关 / 吸收比率 / PCA 第一因子占比作为 1h 事件、换币池（new8 / 16 币）或换 15m / 4h 周期再测。
- 文件：`scratch/disp1h/{prereg,run,analyze,extra,plog}.py`，`PRE_REGISTER.csv(.json)`，`AMENDMENT_A1.txt`，`analyze_wide.csv`（研究脚本未推送）。
- 下一轮（长线）：美联储官方高级信贷员调查（SLOOS，FRED DRTSCILM 大中企业 C&I 贷款标准净收紧比例，季度，1990 起）作为 4h 默认书入场闸门（信贷收紧 → 拦新多）。docs / output / 记忆中无 SLOOS / 贷款标准；不是已否决的 NFCI / 金融压力 / 信用利差 / FINRA 保证金 / M2 / 净流动性。须按官方发布日（季度会议后约 1 周）+ 滞后使用，样本只有约 140 个季度点，先验与网格要小。
