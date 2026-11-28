# 长线新族：区域联储制造业调查扩散指数（纽约 Empire / 费城 / 达拉斯 + 三者均值）→ 4h 默认书 #1 入场闸门（2026-11-28 ~03:10 PST，研究，否决）

## 查重
- 本轮候选按序检查：(a) Deribit 25-delta skew / 期权持仓：`research_deribit_options_skew_flow_regime_gate_4h_{BTC,ETH}.csv` 已测（跳过）；(b) 趋势年龄 / 信号年龄仓位：`research_trend_age_entry_gate_long_history.csv`、`research_signal_age_gate.csv`、`research_signal_age_position_profile_long_history.csv`、金字塔 / 持仓年龄再平衡均已测（跳过）；(c) TGA：联储净流动性（WALCL−RRP−TGA）闸门 + `tga_dts_shock_event_1h` 已测；TIC：`fed_custody_gate_4h.md` 与 `mof_resident_foreign_bond_flow_gate_4h.md` 明确禁止换 TIC 重测（跳过）。
- 选定 (d)：区域联储制造业调查。Empire / Philly 只作为**公布日 1h 事件**测过（`research_empire_philly_survey_event_1h.csv`，否决）；月度扩散指数**水平 / 趋势作为 4h 入场闸门**、以及达拉斯联储 TMOS，文档 / output / scratch 检索均无条目。机制不同于 ISM / PMI 事件、工业产出、费城 / Empire 1h 事件（该族 do-not-retest 针对 1h 公布日窗口；本轮是月度状态闸门，且新增达拉斯与均值）。

## 数据（官方，不编造、不回补）
- FRED 官方镜像：`GACDISA066MSFRBNY`（纽约联储 Empire，2001-07→）、`GACDFSA066MSFRBPHI`（费城联储，1968-05→）、`BACTSAMFRBDAL`（达拉斯联储 TMOS 一般商业活动，2004-06→），季调扩散指数，均 0 缺月；avg3 = 同月三者均值，2004-06 → 2026-10，269 个月。
- 可用时间：Empire = 官方公布日（`output/empire_philly_survey_official.csv`）+1 天 00:00 UTC；费城 = 公布日表（2022+）/ 第三个周四规则（此前；2022+ 58 个中 57 个吻合）；达拉斯 = 次月 1 日 00:00 UTC（达拉斯月内最后一个周一公布，保守）；avg3 取三者最晚。
- 诚实披露：ALFRED vintage 清单今日不可达，故用 FRED 当前 vintage（季调因子年度修订，扩散指数修订很小）；这是已披露的口径限制。
- 文件：`output/regional_fed_mfg_official_monthly.csv`（不入库）；脚本 `scratch/regfed4h/{build,run,new8}.py`。

## 公式（`scratch/regfed4h/PRE_REGISTER.json`，sha256 `07a53566077664fafead46679ea1783fd7cc019b717cfed2b53cbd394b1111a3`，任何 PnL 前锁定 140 格）
- flag = 1（制造业偏弱）：trend_n（指数 < 最近 n 次均值，n=3/6）、chg_n（较 n 次前下降，n=1/3）、lvl（指数 < 0）、z36（36 次 z < −k，k=0.5/1）；4 序列 × 7 形式 × 5 侧 = 140。侧：long_off / short_off / both / contra_both / cap_short_off（弱时拦新空）。
- 先验 `avg3_trend_n6_long_off`（制造业转弱 → risk-off → 不开新多）；回退 `avg3_chg_n3_long_off`。
- 只拦新开仓；真实费率 perp maker 2 / taker 5.1 bps，压力 spot 20 / perp 15.1 bps；9 项 = {OKX d8、Gate d8、OKX d7_noBNB} × {深度未见 < 2024-10-21、tune、post ≥ 2026-03-05} Sharpe 胜同脚本基线。

## 结果（收益 % / Sharpe）
| 格 | 9 项 | OKX 深度 | Gate 深度 | OKX tune | OKX post（月好/差） | Gate post（月好/差） |
|---|---|---|---|---|---|---|
| 基线 | – | +35.14 / 0.71 | −3.63 / 0.09 | +85.08 / 1.47 | +59.90 / 2.23 | +60.32 / 2.25 |
| 先验 avg3_trend_n6_long_off | 1/9 | +14.97 / 0.42 | +1.96 / 0.17 | +31.99 / 0.81 | 同基线 | 同基线（post 几乎不触发） |
| 回退 avg3_chg_n3_long_off | 1/9 | +15.52 / 0.42 | −0.79 / 0.13 | +39.52 / 0.94 | 同基线 | 同基线 |
| 最好 phi_lvllt0_cap_short_off（非先验） | 9/9 | +31.93 / 0.74 | +4.96 / 0.20 | +102.35 / 1.71 | +60.26 / 2.27（5/3） | +61.07 / 2.30（5/3） |
- 次好 dal_chg_n1_short_off 8/9（post +62.01 / +63.25，月 3/5，Gate 深度 +1.28 vs 基线 −3.63，tune 输）；avg3_lvllt0_cap_short_off 7/9（post 月 0/1）。
- 最好格问题：post 边际仅 +0.36 / +0.75 pp（Sharpe +0.04 / +0.05）；月数 5/3 < 6/9 门槛（OKX 与 Gate 都不达标）；OKX d8 深度 Sharpe 0.74 vs 0.71 几乎无增益；压力费率 Gate 月 4/4；邻域不稳：lvl 阈值 −5/−10/−15 退化为基线（deep 全输或持平）、+5/+10 deep 输（Gate deep −5.96 / −18.55）、+15 月 3–4/5–4；new8 未调币：OKX post +6.91 vs +3.26（月 2/3）、Gate post +9.95 vs +16.36（更差）。
- 先验日期平移安慰剂（±30/90/180/−120/365/−119 天）最高 2/9，与先验 1/9 同量级，信号无可辨别的时点信息；+30 天平移 post 掉到 +49.2 / +46.9（偶然触发）。
- 结论：**否决**。先验 / 回退不过线；唯一 9/9 是非先验方向（Philly < 0 时拦新空，经济先验相反）且 post 月数、邻域、new8 都不过。默认、纸面、代码不变，不进观察名单。
- CSV：`output/research_regional_fed_mfg_survey_gate_4h.csv`（含基线 / 安慰剂 / 邻域 / 压力费）、`output/research_regional_fed_mfg_survey_gate_4h_new8.csv`（不入库）。
- 勿重测：换 n / 阈值 / k / 侧、换 Empire / Philly / Dallas / avg3 / 加 Richmond / KC、用未来分量或新订单 / 就业子项重测本族。
