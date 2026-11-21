# 长线：Cboe 官方 VIX 期限结构（VIX/VIX3M、VIX9D/VIX）作为 4h 默认书入场闸门（2026-11-21 ~12:55 PST，弱观察，不改默认）

- 查重：docs/*.md、docs/STRATEGY_FORMULAS.md、output/research_*.csv 中 `VIX3M` / `VIX9D` / `backwardation` / `期限结构` 无 VIX 期限结构条目。命中的只有：季度交割合约基差期限结构、已实现波动率 RV 短 / 长窗期限结构、Pendle 隐含利率期限结构；VIX 只测过收盘水平（FRED VIXCLS 宏观闸门）、VIX 日冲击（短线）和价格合成的 Williams VIX Fix，SKEW 已否决。VIX/VIX3M 比值（期限结构斜率 / 倒挂）是另一种机制。
- 数据：Cboe 官方 cdn.cboe.com `VIX_History.csv`（1990→）、`VIX3M_History.csv`（2009-09-18→）、`VIX9D_History.csv`（2011-01-04→），都到 2026-11-20，CLOSE 无缺失或非正值，不补数据。合并后的日度文件 `output/cboe_vix_term_official_daily.csv` 有 4,354 行；VIX/VIX3M 有 4,321 个观测，VIX9D/VIX 有 3,995 个。发布滞后：美股交易日 D 的收盘（16:15 ET，约 21:15 UTC）从 **D+1 04:00 UTC** 起才用。最新一天 2026-11-20：VIX 35.89，VIX3M 30.94，VIX/VIX3M = 1.160（倒挂）；VIX9D/VIX = 1.135。
- 倒挂天数占比（VIX/VIX3M>1）：全样本 7.6%，深未见段 2.0%，调参段 9.9%，2026-03 后 6.2%。
- 公式：比值 r = VIX/VIX3M 或 VIX9D/VIX。flag=1 表示压力或倒挂，有三种定义：lvl `r>thr`，thr∈{0.9, 0.95, 1.0}；trend `r>最近 n 个观测的均值`，n∈{20, 60, 120}；chg `r>r_{n个观测前}`，n∈{5, 20}。方向 5 种：long_off（flag=1 拦新多）、short_off（flag=0 拦新空）、both、contra_both、cap_short_off（flag=1 拦新空）。只拦新开仓，同向续持不拦。共 2×8×5 = **80 格**，看 PnL 前锁定在 scratch/vixterm4h/PRE_REGISTER.csv / .md。先验格 `vixvix3m_lvl1_long_off`（倒挂 → risk-off → 不开新多），备选格 `vixvix3m_trend_n60_long_off`。
- 回测：同一脚本跑默认 #1 MA 50/150 书作为基线，用官方 OKX / Gate 4h 现货加永续 K 线和官方资金费。真实费率（永续 maker 0.02% / taker 0.051%），压力费率（现货 20 / 永续 15.1 bps）。深未见段：OKX d8 从 2023-02、Gate d8 从 2022-07、OKX d7_noBNB 从 2022-04，到 2024-10-21；调参段到 2026-03-05；post 段 2026-03-05→2026-11-14。按 9 个 Sharpe 切片比较（3 段 × 3 套）。

## 结果（output/research_vix_term_structure_gate_4h.csv）

| 格 | 9 切片 | OKX d8 post | Gate d8 post | post 逐月好/差（OKX·Gate） | 深未见收益（OKX·Gate） |
|---|---|---|---|---|---|
| 基线 | — | +59.90%（Sh 2.23） | +60.32%（2.25） | — | +35.14%·−3.63% |
| 先验 lvl1_long_off | 0/9 | +59.90% | +60.32% | 0/0·0/0 | +35.14%·−3.63%（不变）；调参段 +64.27% 对 +85.08% |
| 备选 trend_n60_long_off | 0 胜深未见 | +59.90% | +60.32% | 0/0·0/0 | −1.06%·−24.96% |
| 网格最好 lvl0.9_cap_short_off（非先验） | 8/9 | +59.94% | +60.85% | 2/5·3/4 | +31.43%·−1.12% |
| 事后邻域 **lvl0.85_cap_short_off** | 9/9 | **+64.44%（2.46）** | **+65.19%（2.48）** | **6/3·6/3** | +54.50%·+31.30% |

- 先验格不成立。倒挂太少，而且和新多信号几乎不重合：深未见段和 post 段与基线完全相同，只在调参段少赚 21 个百分点。备选格在深未见段大亏。long_off 类格在 post 段全部等于基线，因为这段时间默认书基本没有新多。
- 80 格中有效的只有 cap_short_off（VIX 曲线变平或倒挂时不开新空）。
- 事后邻域（output/research_vix_term_structure_gate_4h_supp.csv、_supp2.csv，**不是预注册格**）：
  - VIX/VIX3M 阈值 0.85 / 0.8625 / 0.875 / 0.9 / 0.925 都在 8–9/9。但只有 0.85 的 post 逐月 ≥6/9（两所都是 6/3）。0.8625 是 3/5·4/4，0.875 是 3/5·4/4，0.9 是 2/5·3/4。
  - 阈值往下是悬崖：0.825 的 OKX post 只有 +31.15%，0.8 只有 +10.70%，0.75 只有 +13.43%。原因是 flag 的占比太高（0.85 时 post 段 68%、深未见段 84%），几乎不再开空。
  - VIX9D/VIX 0.85 / 0.875 只有 3/9。
  - 压力费率下 lvl0.85 仍是 9/9：OKX post +61.49% 对 +55.94%，Gate +62.32% 对 +56.78%，逐月 6/3·6/3。
  - 未调参的 new8（output/research_vix_term_structure_gate_4h_new8.csv）：OKX post +7.92% 对 +3.26%（逐月 6/3），Gate +21.80% 对 +16.36%（5/4）。
  - 安慰剂共 14 个（时移 ±7/±14/±30/+180/−120/+365/−119 天，加 4 次打乱）。+14 天是 8/9（OKX post +66.11%），+7 天是 7/9，其余 ≤5/9；打乱 shuf1 的 post 也有 +64.08%，但深未见段输。
- 判定：**弱观察，不改默认，不加可选闸门，不开新纸面实例。** 理由：
  - 先验和备选都失败，lvl0.85 是看过 PnL 后在邻域里找到的；
  - 阈值 0.825 / 0.85 之间是悬崖；
  - +14 / +7 天的时移安慰剂几乎一样好，说明增益主要来自“少开空”的整体暴露，而不是期限结构的时点信息。
- 前向复核：每月用新的 post 月份检验 `vixvix3m_lvl0.85_cap_short_off` 和 0.875。只有两所逐月都 ≥6/9、并且高于 +14 天安慰剂时，才做一次 paper 候选。
- 以后不再重测：不换 thr / n / 方向、不换 VIX9D/VIX6M/VIX1D/VVIX 比值、不改用分位数 / z 分数 / 斜率差（VIX3M−VIX）、不提前起点、不换成 VX 期货期限结构重测同一机制。弱观察只按上面的前向复核走。
- 脚本：scratch/vixterm4h/{build,prereg,run,supp,supp2,new8}.py（研究脚本未推送）。
