# EIA-930 美国本土 48 州电力需求 4h 入场闸门（长线，REJECTED）

## 数据（官方，无填补）
- EIA Open Data API v2 `electricity/rto/region-data`，respondent = US48（United States Lower 48），type = D（Demand），hourly（UTC）。69,318 小时，2019-01-01 00:00 → 2026-11-28 05:00 UTC，0 小时缺口、0 重复。只用完整 UTC 日（24 小时）：2,888 天，0 日历缺口。官方日序列 `output/eia930_us48_demand_official_daily.csv`。
- 当前版本（EIA-930 数值事后可能被修订 / 插补，属已知限制）。
- 滞后：日 D（D+1 00:00 UTC 结束）从 D+1 12:00 UTC 起使用（EIA-930 约 1–3 小时发布，留 12 小时余量给迟报的 BA）。

## 公式
- dem7 = 日需求 7 日均值；yoy = dem7 / dem7(364 天前) − 1；wk = 7 日均值( 日需求 / 前 1–4 周同星期均值 − 1 )。
- 趋势旗：s > s 的 n 日均线（n = 30 / 60 / 120 / 240）；变化旗：s − s(n 日前) > 0（n = 14 / 30 / 60 / 120）。
- 侧：long_off（旗=1 拦新多）、short_off（旗=0 拦新空）、both、contra_both（旗=0 拦新多、旗=1 拦新空）、cap_short_off（旗=1 拦新空）。只拦新开仓，持仓、止损、出场不变。
- 120 格 = 3 序列 × 8 形式 × 5 侧，PnL 前锁定（scratch PRE_REGISTER.json）。先验：需求偏强 = 经济活动强 = risk-on → cap_short_off / contra_both；先验格 yoy_trend_n60_cap_short_off；回退 wk_chg_n30_contra_both。
- 验证：默认 #1 双均线 50/150 4h；OKX d8（2023-02→）、Gate d8（2022-07→）、OKX d7_noBNB（2022-04→）；deep < 2024-10-21、tune-pre、post 2026-03-05→2026-11-14；官方资金费；真实费用，压力费 现货 20 / 永续 15.1 bps。

## 结果（post / Sharpe，基线 OKX +59.90/2.23，Gate +60.32/2.25）
| 格 | 胜 | OKX post | 月份 | Gate post | 月份 | Gate deep |
|---|---|---|---|---|---|---|
| yoy_trend_n30_both（非先验） | 9/9 | +64.79 / 2.35 | 4/4 | +65.67 / 2.44 | 5/3 | +34.03（基线 −3.63） |
| yoy_trend_n60_cap_short_off（先验） | 6/9 | +64.09 / 2.40 | 3/5 | +65.02 / 2.43 | 3/5 | −29.11 |
| wk_chg_n30_contra_both（回退） | <6/9 | +8.59 / 0.70 | 2/7 | +7.30 / 0.61 | 3/6 | −20.56 |

- 压力费下 yoy_trend_n60_cap_short_off post：OKX +61.19 / 2.32、Gate +62.17 / 2.35（仍高于基线，但 deep 崩）。
- 邻域：先验 n=90 只有 4/9、n=180 6/9；打乱安慰剂 PLC_yoy_trend_n60_contra_both_shiftshuf3 达 7/9，高于先验。

## 结论：否决（REJECTED）
- 先验 6/9：post 好于基线，但 deep 两所为负（Gate −29.11 vs 基线 −3.63），post 月份 3/5。
- 唯一 9/9 的 yoy_trend_n30_both 是非先验（反向侧：强需求时拦新多），OKX post 月份 4/4，未达 ≥6/9；打乱安慰剂 7/9，邻域不稳。
- 默认、候选、纸面实例全部不变，无代码改动。new8 未跑（未达观察线）。

## 勿重测
不要以下列方式重测「EIA-930 US48 小时电力需求 → 4h 入场闸门」：改 n（趋势窗 / 变化窗）、改侧、换 dem7 / yoy / wk 序列或其他去季节化（同日历日、HDD/CDD 调整）、改滞后小时、改用 US48 之外的区域 / BA / 子区域（含 ERCOT、CISO、PJM）、改用净发电 / 互联 / 预测需求 / 分燃料发电量。
