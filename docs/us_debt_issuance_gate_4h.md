# 美国财政部官方 Debt to the Penny（国债发行节奏 / 债务上限冻结）→ 4h 默认书入场闸门（否决）

## 长线新族：Debt to the Penny 日度国债余额增速与债务上限冻结 → 4h 默认书入场闸门（2026-11-22 ~01:10 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、记忆检索「Debt to the Penny / public debt / debt ceiling / 债务上限 / 国债余额」：无条目。候选 (a) TGA 余额变化已测（FRED 净流动性 WALCL−TGA−RRP 4h 闸门否决；DTS TGA 1h 冲击否决且注明勿以水平 / 趋势重测），(b) VIX/VIX3M 期限结构 4h 闸门已否决，(c) Deribit 期权 25d 偏斜 / 看跌看涨比 4h 闸门已否决，故改选本族。与 MTS 月度收支 / 赤字闸门（月度、滞后约 20 天）不同：这里是**每日国债存量**的发行节奏和债务上限停滞期。区分度（只用信号）：2015 年起 Spearman(pubg63, TGA 63 营业日对数变化) = 0.59，(totg21, TGA 21 日) = 0.38。
- 机制：公众持有国债增速高于常态 = 财政部发债抽走私人流动性 → risk-off → 拦新开多（long_off / both）；债务上限冻结（总债务 21 营业日几乎不变，财政部被动消耗 TGA 放水）→ risk-on → 拦新开空（cap_short_off）。只拦新开仓，已有持仓、止损、离场不变。
- 数据（只用官方，不编造、不回补）：fiscaldata.treasury.gov API v2 `accounting/od/debt_to_penny`（`tot_pub_debt_out_amt`、`debt_held_public_amt`、`intragov_hold_amt`），8,438 个财政部营业日 1993-04-01 → 2026-11-19（公众持有从 1997-09-30 起），最大间隔 5 个日历日（节假日），无填充。记录日 D 在下一财政部营业日发布，本研究**再加 1 天 00:00 UTC**（≈ 发布日美东 19:00）才使用，ffill 到 4h。日序列 `output/us_debt_to_penny_official_daily.csv`。
- 公式（按营业日行计）：`totg21 = 100·ln(TOT_t / TOT_{t−21})`，`pubg63 = 100·ln(PUB_t / PUB_{t−63})`，`pubg252 = 100·ln(PUB_t / PUB_{t−252})`。形式：`s > SMA_n`（n 90 / 180）、`s − s[−n] > 0`（n 7 / 27）、`z252 = (s − 均值252)/标准差252 > k`（k 0.5 / 1 / 1.5 / 2）；冻结 `frz: |totg21| < 0.10%`。侧：long_off / short_off / both / contra_both / cap_short_off。3 × 8 × 5 + 冻结 5 = **125 格** + 同脚本基线，任何 PnL 之前锁定在 `scratch/debtpenny4h/PRE_REGISTER.json`（sha256 `efe834f3…01ad`）。**先验** `pubg63_z252gt1_long_off`，**回退** `totg21_frz0.1_cap_short_off`。
- Harness：与 gatefundcap4h / geomag4h 同一脚本（`qtw.backtest.run_backtest` 默认双均线 50/150 4h，8 币永续）。OKX d8（2023-02 起）/ Gate d8（2022-07 起）/ OKX d7_noBNB（2022-04 起）；deep_unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；官方 4h K 线与官方资金费；真实费 现货吃单 10 / 永续吃单 5.1 / 挂单 2 bps，压力 20 / 15.1；安慰剂平移 ±7 / ±14 / +180 / −120 / +365 / −119 天；邻域；未调参 new8 两所。
- 结果（收益 % / Sharpe；基线 OKX d8 deep +35.14 / 0.71、tune +85.08 / 1.47、post +59.90 / 2.23；Gate d8 −3.63 / 0.09、+84.25 / 1.46、+60.32 / 2.25；d7 +54.92 / 0.75、+92.93 / 1.56、+50.76 / 2.10）：

| 格 | 9 格 Sharpe 胜 | OKX d8 deep / tune / post | Gate d8 deep / tune / post | post 月份 好/差（OKX, Gate） | new8 post OKX / Gate（基线 +3.26 / +16.36） |
|---|---|---|---|---|---|
| 先验 pubg63_z252gt1_long_off | 6/9 | +38.66 (0.76) / +87.98 (1.54) / +59.90 (2.23) | −1.42 (0.12) / +86.72 (1.52) / +60.32 (2.25) | 0/0, 0/0（post flag=1 天数 0%） | +3.26 / +16.36（相同） |
| 回退 totg21_frz0.1_cap_short_off | 6/9 | +41.58 (0.81) / +103.69 (1.74) / +57.82 (2.17) | +0.91 (0.15) / +102.59 (1.72) / +58.33 (2.18) | 2/4, 2/4 | +2.31 / +15.36（更差） |
| 非先验 totg21_z252gt1_cap_short_off | 9/9 | +37.81 (0.76) / +89.19 (1.49) / +60.52 (2.25) | −2.00 (0.11) / +95.62 (1.55) / +61.10 (2.27) | 2/3, 3/2 | +3.90 / +17.14 |
| 非先验 totg21_z252gt0.5_contra_both | 8/9 | +54.07 (1.12) / +89.76 (1.54) / +60.44 (2.35) | +35.21 (0.63) / +96.73 (1.60) / +61.01 (2.37) | 4/2, 4/2 | +9.03 / +23.07 |

  - 先验：post 段 z>1 一天都没触发，post 与基线逐值相同，月份 0/0；deep / tune 的小幅改善被安慰剂超过：+14 天平移 OKX deep +74.65 (1.18)、Gate +21.06 (0.41)、d7 +97.79 (1.08)，+7 天平移 tune +102.70 / +100.54，都好于真实。邻域 k=0.25 post 崩到 +28.31 / +28.65，k≥0.75 post 与基线相同。
  - 回退（债务上限冻结 → 拦新空）：tune 好（2025 年上限期），但 post 两所都更差（月份 2/4），new8 也更差。
  - 唯一 9/9 `totg21_z252gt1_cap_short_off` 非经济侧、post 边际很薄（+0.6 pp / Sharpe +0.02），月份 2/3、3/2；邻域 z1.5 只 3/9、z0.5 7/9（post 月份 4/2、5/1 但 Gate deep 更差）。压力费下 OKX post +56.84 vs 基线 +55.94，Gate +57.54 vs +56.78。
  - 125 个真实格的 9 格胜数分布：0:30、1:6、2:13、3:46、4:13、5:1、6:11、7:3、8:1、9:1。没有任何格同时满足 ≥6/9 Sharpe 与两所 post 月份 ≥6/9 更好。
- 结论：**否决**。不实现、不进观察名单、不改默认、不动纸面实例，只写文档。国债发行节奏 / 债务上限冻结对 4h 趋势书没有稳定的增量：先验在 post 段无触发、被 ±7 / +14 天安慰剂超过；回退 post 更差；唯一 9/9 是非经济侧、边际薄、月份不过半、邻域崩。**勿重测**：不要换 n / k / 窗口 / 冻结阈值 / 侧，不要换成总债务 / 公众持有 / 政府内部持有的其他组合、债务占 GDP、发债净额（DTS public debt cash issues − redemptions）或改成 1h 事件来重测本机制。
- 文件：`output/research_us_debt_issuance_gate_4h.csv`（456 行，含安慰剂 / 邻域 / 压力费）、`output/research_us_debt_issuance_gate_4h_new8.csv`、官方日序列 `output/us_debt_to_penny_official_daily.csv`（均不入库）；脚本 `scratch/debtpenny4h/{build,run,new8}.py`、`PRE_REGISTER.json`（研究脚本未推送）。
- 下一轮（短线）：以太坊主网官方 Beacon 链罚没（slashing）/ 大额退出事件 → 8 币永续篮子 1h 事件（先查重 eth_beacon_staking_gate_4h、steth_eth_discount、eigenlayer）。
