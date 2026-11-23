# 长线新族：克利夫兰联储官方日度通胀 nowcast 动量 → 4h 默认书 #1 入场闸门（2026-11-23 ~03:55 PST，研究，否决）

## 查重
`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`/workspace/scratch`、ROTATION_LOCK 与记忆中检索 Cleveland / 克利夫兰 / nowcast / inflation nowcasting：只有三处「下一轮（长线）」指针，从未执行。不同于已否决的 `breakeven_inflation_gate_4h`（TIPS 市场隐含通胀，其勿重测只覆盖 T10YIE / T5YIE / T5YIFR / TIPS 派生）、`cpi_inflation_regime_gate_4h`（已公布的实际 CPI）、CPI 1h 发布事件、`us_gdpnow_gate_4h`（亚特兰大联储实际 GDP nowcast，增长不是通胀）。

## 数据（全部官方，不编造、不插值、不回补）
- 克利夫兰联储 Inflation Nowcasting 官方图表数据 `https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_year.json`（同比 %，161 个目标月 2013-07 → 2026-11；每个目标月带每个营业日发布当时的 nowcast 值，即点时 vintage）。
- 4 条序列：CPI、核心 CPI、PCE、核心 PCE 同比 nowcast。22,508 个观测，3,326 个 as-of 营业日 2013-08-20 → 2026-11-20，最大间隔 5 天，2020 年后无缺失。
- 每个 as-of 日 D 取当天有值的**最新目标月**；日历日按最后一个发布日前向填充。
- 发布滞后：nowcast 约 10:30 ET 更新，D 的值从 D+1 00:00 UTC 起才用（无前视）。2013–2014 早期值可能是模型上线前回算，但测试窗口（2022 起）全为实时发布值。
- 文件：`output/cleveland_inflation_nowcast_official_daily.csv`、`scratch/clevnowcast4h/nowcast_year_long_official.csv`（不入库）。

## 公式（`scratch/clevnowcast4h/PRE_REGISTER.json`，sha256 `803e3820…ea45`，2026-11-23 03:40 PST 看任何 PnL 前锁定）
- X = 日度 nowcast；M_n = 过去 n 个日历日（含当天）X 均值；flag = 1（去通胀动量，有利）当 M_n − X > k，k = 0。
- 网格：序列 {cpi_yoy, core_yoy, pce_yoy, corepce_yoy} × n {30, 60, 91} × 侧 {long_off（通胀上行拦新多）, cap_short_off（去通胀拦新空）, both, contra_both（反向）} = 48 格。
- 先验 `core_yoy_w60_long_off`（核心通胀动量上行 → 鹰派重定价 → 拦新多），回退 `cpi_yoy_w91_long_off`。
- 只拦新开仓（默认 #1 双均线 50/150 4h、8 币永续），出场 / 止损 / 已有同向仓不动。真实费率永续 maker 2 / taker 5.1 bps；压力 spot 20 / perp 15.1 bps。
- 9 项 = {OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01} × {深度未见 < 2024-10-21、tune 2024-10-21 → 2026-03-05、post ≥ 2026-03-05} Sharpe 胜同脚本基线。

## 结果（真实费率，收益 % / Sharpe）
| 格 | 9 项 | OKX d8 深度未见 | Gate d8 深度未见 | OKX d8 post（月胜/负） | Gate d8 post（月胜/负） |
|---|---|---|---|---|---|
| 基线 | – | +35.14 / 0.71 | −4.32 / 0.08 | +72.98 / 2.49 | +73.40 / 2.51 |
| 先验 core_yoy_w60_long_off | 1/9 | +26.23 / 0.59 | +4.59 / 0.21 | +72.98 / 2.49（0/0，post 从未拦截） | +73.40 / 2.51（0/0） |
| 回退 cpi_yoy_w91_long_off | 3/9 | +42.98 / 0.82 | +3.08 / 0.19 | +68.46 / 2.47（1/2） | +69.12 / 2.49（1/2） |
| 最好非先验 cpi_yoy_w30_cap_short_off | 7/9 | +16.98 / 0.48 | −11.33 / −0.10 | +76.87 / 2.63（4/3） | +77.79 / 2.66（6/1） |

- 先验 tune 段 OKX +12.39 / 0.42（基线 +85.08 / 1.47），大幅损伤；回退 tune +28.56 / 0.75 也差。
- 最好格两个 d8 深度未见都输；post 月份 OKX 只有 4/3，未达 ≥6/9 双交易所；OKX d7 post 月份 1/5。压力费：OKX d8 post +73.0 / 2.54（基线 +68.62 / 2.38），深度未见 +8.62 / 0.31（基线 +24.67 / 0.56）。
- 安慰剂（锚 cpi_yoy_w30_cap_short_off，±30/60/180/−120/±365 天平移 + 5 个 30 天块洗牌）：+30 天平移 6/9 且 post 边际更大（post Sharpe 边际合计 +0.92 vs 真格 +0.38；OKX d8 post +83.26 / 2.79），其余 ≤4/9。
- 邻域（n 14/21/45/75/120/150/182、k ±0.05）：多为 6/9、5/9，深度未见普遍输；k=+0.05 7/9 但 post 边际几乎为 0（OKX 月 1/5）。
- new8 未调参（OKX / Gate 各近 4500 根 4h）：最好格 post OKX 0.86 vs 0.78、Gate 1.46 vs 1.39，但月份 2/4、2/3；先验 pre 段 Sharpe 0.62 vs 0.99（OKX）。
- CSV：`output/research_cleveland_inflation_nowcast_gate_4h.csv`（267 行，含邻域 / 安慰剂 / 压力）、`_new8.csv`（均不入库）。脚本 `scratch/clevnowcast4h/{build,run,new8}.py`。

## 结论
**否决**。先验 1/9、回退 3/9；唯一 7/9 是非先验、深度未见双输、post 月份不达标、+30 天平移安慰剂更好。不实现、不进观察、不改默认、不改纸面。

## never retest by
改 n / k / 均值窗口 / 侧、在 CPI / 核心 CPI / PCE / 核心 PCE 之间互换或做差、改用环比（nowcast_month）或季度年化（nowcast_quarter）、改成「最早未公布目标月」、nowcast − 实际值意外、nowcast 水平阈值、改发布滞后、换 token / 换交易所、或做 1h / 15m / 1d 版本来重试这个「克利夫兰联储通胀 nowcast 动量闸门」机制。
