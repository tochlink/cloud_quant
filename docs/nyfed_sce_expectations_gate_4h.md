# 长线新族：纽约联储官方 SCE 家庭预期动量 → 4h 默认书 #1 入场闸门（2026-11-23 ~04:35 PST，研究，否决）

## 查重
- 建议题 BoJ 当座預金 / 货币基础：`docs/snb_sight_deposits_gate_4h.md` 勿重测已明确覆盖「BoJ 当座預金等其他非美央行准备金序列」，ECB 资产负债表文档也排除 BoJ 资产负债表 → 换题。
- `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`/workspace/scratch`、ROTATION_LOCK 检索 Survey of Consumer Expectations / SCE / consumer expectations：0 命中。不同于已否决的 `us_real_activity_sentiment`（密歇根 UMCSENT 水平 / 零售 / 工业产出）、`cleveland_inflation_nowcast`（模型 nowcast）、`breakeven_inflation`（TIPS）、初请 / JOLTS / 劳动周期（实际劳动数据）、美股指数趋势（价格）。本族是家庭**预期调查**。

## 数据（全部官方，不编造、不插值、不回补）
- 纽约联储 SCE 官方图表数据 `https://www.newyorkfed.org/medialibrary/interactives/sce/sce/downloads/data/frbny-sce-data.xlsx`（sha256 `7dddb0eb…bfa5`），161 个调查月 2013-06 → 2026-10。
- 4 条序列：`stock_up` 美股 1 年后更高的平均概率（符号 +1）；`infl1y_med` 1 年通胀预期中位数（−1）；`unemp_up` 1 年后失业率更高的平均概率（−1）；`fin_net_ahead` 一年后财务状况（较好 + 好很多）−（较差 + 差很多）百分点（+1）。最新 2026-10：40.00% / 3.91% / 45.31% / −11.42。
- 发布滞后：官方 CMD 发布日历 `https://www.newyorkfed.org/medialibrary/research/interactives/data/cmdCalendar/cmdCalendar.csv`（71 个 SCE 发布日 2021-01 → 2026-11，11:00 ET），调查月 M 从发布日 +1 天 00:00 UTC 起可用；2021 年前无官方日历的月份保守取 M+1 月 16 日 +1 天（官方日期最晚是 15 日）。测试窗口（2022 起）用到的值全部有官方发布日。SCE 文件为当前 vintage；官方 Notes 只记录 2016 不确定性指标和商品价格预期修订，本研究 4 条序列不受影响。
- 文件：`output/nyfed_sce_official_monthly.csv`；`scratch/nyfedsce4h/`（不入库）。

## 公式（`scratch/nyfedsce4h/PRE_REGISTER.json`，sha256 `33a329b3…de96`，2026-11-23 04:26 PST 看任何 PnL 前锁定）
- X = 月度值；M_n = 最近 n 个月均值（含当月）；flag = 1（家庭风险偏好向上，有利）当 sign·(X − M_n) > k，k = 0；按可用时间日度前向填充到 4h。
- 网格：序列 4 × n {3, 6, 12} 月 × 侧 {long_off（不利时拦新多）, cap_short_off（有利时拦新空）, both, contra_both（反向）} = 48 格。
- 先验 `stock_up_m6_long_off`，回退 `unemp_up_m12_long_off`。
- 只拦新开仓（默认 #1 双均线 50/150 4h、8 币永续），出场 / 止损 / 已有同向仓不动。真实费率永续 maker 2 / taker 5.1 bps；压力 spot 20 / perp 15.1 bps。
- 9 项 = {OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01} × {深度未见 < 2024-10-21、tune 2024-10-21 → 2026-03-05、post ≥ 2026-03-05} Sharpe 胜同脚本基线。

## 结果（真实费率，收益 % / Sharpe）
| 格 | 9 项 | OKX d8 深度未见 | Gate d8 深度未见 | OKX d8 post（月胜/负） | Gate d8 post（月胜/负） |
|---|---|---|---|---|---|
| 基线 | – | +35.14 / 0.71 | −4.32 / 0.08 | +72.98 / 2.49 | +73.41 / 2.51 |
| 先验 stock_up_m6_long_off | 3/9 | +91.44 / 1.39 | +49.20 / 0.73 | +72.98 / 2.49（0/0，post 从未拦截） | +73.41 / 2.51（0/0） |
| 回退 unemp_up_m12_long_off | 3/9 | +57.55 / 1.02 | +27.87 / 0.51 | +50.79 / 2.17（1/3） | +51.08 / 2.18（1/3） |
| 最好非先验 infl1y_med_m3_cap_short_off | 7/9 | +29.48 / 0.70 | −4.07 / 0.05 | +72.00 / 2.50（1/4） | +72.85 / 2.52（1/4） |
| post 最好 fin_net_ahead_m3_both | 6/9 | +34.27 / 0.77 | +0.33 / 0.12 | +75.45 / 2.72（4/2） | +76.10 / 2.74（4/2） |

- 先验 / 回退 tune 段都大幅受损（先验 OKX +41.24 / 0.97 vs 基线 +85.08 / 1.47）；深度未见的大幅改善在 tune 段完全反转。
- infl1y_med_m3_cap_short_off：7/9 但 OKX / Gate d8 post 收益都低于基线，月份 1/4；锚定安慰剂 +30 天、+365 天平移都 6/9。
- fin_net_ahead_m3_both：tune 三项全输（OKX +54.95 / 1.26）；post 月份 4/2 未达 ≥6/9；邻域 m2/m4/m9 只有 3/9，m18/m24 0/9（k ±0.1 仍 6/9，因为月度值几乎不在阈值附近）；安慰剂 30 天块洗牌 shuf4 8/9 超过真格，+365 天 / +180 天平移 post Sharpe 2.81 / 2.75 高于真格 2.66。
- 压力费：fin_net_ahead_m3_both OKX d8 post +72.11 / 2.63（基线 +68.62 / 2.38），深度未见 +27.76 / 0.66（基线 +24.67 / 0.56）。
- new8 未调参（OKX / Gate 各 4500 根 4h）：fin_net_ahead_m3_both post OKX 1.39 vs 0.78、Gate 1.93 vs 1.39（月 5/1），但 pre 段 0.60 vs 0.97、0.63 vs 0.97 都差；先验 pre 段 0.36 vs 0.97。
- CSV（不入库）：`output/research_nyfed_sce_expectations_gate_4h.csv`（255 行，含邻域 / 安慰剂 / 压力）、`_new8.csv`、`_placebo2.csv`。脚本 `scratch/nyfedsce4h/{build,run,new8,plc2}.py`。

## 结论
**否决**。先验 3/9、回退 3/9；唯一 7/9 是非先验且 post 收益输基线；post 最好的 6/9 格 tune 全输、月份 4/2、邻域塌、块洗牌安慰剂更好。不实现、不进观察、不改默认、不改纸面。

## never retest by
改 n / k / 侧，在 stock_up / infl1y_med / unemp_up / fin_net_ahead 之间互换或组合，换成 SCE 其他序列（3 年 / 5 年通胀预期、通胀不确定性、房价 / 收入 / 支出 / 收入预期、失业 / 找工作 / 离职概率、信贷可得性、拖欠概率、政府债务、储蓄利率、人口分组 Demo 表），改用水平阈值 / 同比 / 意外值，改发布滞后，换成密歇根 / Conference Board 等其他消费者调查，换 token / 换交易所，或做 1h / 15m / 1d「SCE 发布日」事件版本来重试这个「家庭预期调查动量闸门」机制。
