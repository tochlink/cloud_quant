# TSA 官方每日安检旅客数（美国航空出行 YoY）→ 4h 默认书入场闸门（否决）

## 长线新族：TSA checkpoint travel numbers YoY 作为 4h 默认书入场闸门（2026-11-22 ~02:40 PST，研究，不改默认）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`scratch/`、`output/research_*.csv` 中 TSA / checkpoint / 航空旅客 / passenger 0 命中；记忆中无出行族。与 GDPNow、Empire/Philly、初请失业金、实体活动情绪不同：那些是调查 / 模型宏观数据，这里是每日实测的美国消费者出行人数。
- 机制：美国机场安检人数 = 实时消费者可选消费 / 出行需求。出行同比强 = 消费 risk-on；弱或减速 = risk-off。闸门只拦新开仓，已有持仓、止损、离场不变。
- 数据（只用官方，不编造、不回补）：tsa.gov `travel/passenger-volumes`（及 /2019…/2025 年页）官方表格，2019-01-01 → 2026-11-19 共 2,880 天，0 日历缺口，无填充，跨年页无冲突。D 日 **D+5 00:00 UTC** 起用（TSA 下一工作日发布，周末 / 假期批量周一或周二发布；D+5 覆盖周一假期周的周五数据），前向填充到 4h K 线。存 `output/tsa_checkpoint_official_daily.csv`（不入库）。最新 yoy7 +3.7%、yoy28 +0.1%、yoy91 −1.6%。
- 公式：`yoyW = log(sumW(D) / sumW(D−364))`（按星期对齐），W = 7 / 28 / 91；形式 `yoy > 0`、`yoy > SMA(n)`（n 28/91）、`yoy − yoy.shift(n) > 0`（n 28/91）、`z365 = (yoy − SMA365)/STD365 > k`（k 0/0.5/1）；flag=1 = 出行强 / 上升。侧：long_off（flag=0 拦新多）、short_off（flag=1 拦新空）、both、contra_both（flag=1 拦新多、flag=0 拦新空）、cap_long_off（flag=1 拦新多）。3 × 8 × 5 = 120 格，看 PnL 前锁定（PRE_REGISTER.json sha256 b2ecd0f1…）。先验：long_off / both（精确匹配；修正了旧框架把 contra_both 当成 both 的问题）；回退 yoy28_trend_n91_long_off。注意：2021–22 的 YoY 受疫情基数扭曲，z365 形式在深未见段几乎不触发；按预注册未做任何过滤。
- 验证：OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）官方永续 + 现货 4h，真实资金费；真实费率（永续 maker 0.02% / taker 0.051%）与压力费率（永续 taker 15.1 bps）；深未见 →2024-10-21、调参段 →2026-03-05、post →2026-11-14；同脚本基线；安慰剂日历平移 ±7/±14/+180/−120/+365/−119 天；邻域；new8 未调参币（OKX + Gate，最近 4,500 根 4h）。

### 结果（`output/research_tsa_checkpoint_travel_gate_4h.csv`，补充 `_supp.csv`、`_new8.csv`）

收益 % / 日 Sharpe；月份 = post 月度优于 / 劣于基线。

| 格子 | 场所 | 深未见 | 调参段 | post | post 月份 | 9 格胜 |
|---|---|---|---|---|---|---|
| 基线 | OKX d8 | +35.1 / 0.71 | +85.1 / 1.47 | +59.9 / 2.23 | – | – |
| 基线 | Gate d8 | −3.6 / 0.09 | +84.3 / 1.46 | +60.3 / 2.25 | – | – |
| 先验最佳 yoy7_chg_n28_both | OKX d8 | +51.2 / 0.98 | +50.7 / 1.15 | +60.4 / 2.32 | 5/4 | 6/9 |
| 同上 | Gate d8 | +15.5 / 0.35 | +51.8 / 1.17 | +61.2 / 2.35 | 5/4 | |
| 回退 yoy28_trend_n91_long_off | OKX d8 | +30.7 / 0.71 | +34.1 / 0.81 | +32.9 / 1.55 | 0/4 | 1/9 |
| 同上 | Gate d8 | +9.2 / 0.27 | +31.3 / 0.76 | +33.1 / 1.56 | 0/4 | |
| 非先验最高 yoy91_chg_n91_short_off | OKX d8 | +34.8 / 0.73 | +99.1 / 1.64 | +64.7 / 2.43 | 4/4 | 7/9 |
| 同上 | Gate d8 | −8.0 / 0.01 | +106.1 / 1.69 | +65.2 / 2.44 | 4/4 | |

- 先验 yoy7_chg_n28_both：6/9 只靠深未见 + post Sharpe，调参段三本书都大幅落后（OKX 85→51）；post 月份 5/4（<6/9）。邻域崩：n14 post +18.1%、n21 −11.6%、n42 +28.8%、n56 +13.9%、n70 +10.6%（基线 +59.9%）。安慰剂：−14 天平移 6/9、+365 天 5/9，与真信号同级。new8：post +20.8% vs 基线 +3.3%（OKX）、+20.9% vs +16.4%（Gate），月份 6/3，但 pre 段 OKX +0.7% vs +47.5%、Gate −7.4% vs +44.7%，全段不稳。压力费率 post OKX +57.0 vs 55.9、Gate +57.9 vs 56.8（边际薄）。
- 回退 yoy28_trend_n91_long_off：全面变差（post 约 −27 pp）。
- 非先验 yoy91_chg_n91_short_off（出行加速时拦新空）：7/9，但 Gate 深未见输（0.01 vs 0.09），post 月份 4/4 两边；安慰剂 −7 天平移 post +68.3% / 2.54 反而比真信号高，−14 天平移调参段更好；new8 OKX post +6.9 vs +3.3、Gate +20.6 vs +16.4 但月份 3/2、2/3。效应等同于 post 期减少逆势空单，不是出行信息。
- 结论：**否决**。先验与回退都没过；非先验最高格被安慰剂追平，不到弱观察。不改默认、不加纸面子账本。
- 以后不要再测：换 W / n / k / 侧、换 7/28/91 日窗口、用水平值或去季节化水平代替 YoY、换发布滞后、改用航空公司 / 机场 / 酒店等其他出行代理数据重测同一「美国消费者出行」机制。
- CSV（不入库）：`output/research_tsa_checkpoint_travel_gate_4h.csv`、`_supp.csv`、`_new8.csv`；官方日度 `output/tsa_checkpoint_official_daily.csv`；脚本 `scratch/tsa4h/{fetch,run,supp,new8}.py`（研究脚本未推送）。
