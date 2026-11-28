# 长线新族：国家外汇管理局官方月度「银行结售汇」（银行代客结售汇差额 / 资本与金融项目差额 / 远期签约差额）→ 4h 默认书 #1 入场闸门（2026-11-27 ~20:28 PST，研究，不改默认；否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 已超过 GitHub 连接器写入上限，只在本地追加）。

- 查重：`docs/STRATEGY_FORMULAS.md`（全部轮换记录）、`docs/*.md`、`output/research_*.csv`、`scratch/ROTATION_LOCK.txt` 检索 结售汇 / FX settlement / 涉外收付 / capital flight / 资本外流：0 命中。不同于 `safe_gold_reserves_gate_4h`（央行黄金持仓；其勿重测禁的是外汇储备 / 储备模板科目，不含居民银行结售汇）、`pboc_cny_fixing_shock_event_1h`（中间价价格）、`pboc_tsf_credit`、`pboc_omo_liquidity`、`shibor_liquidity`、`fx_jpy_cny_trend`（汇率价格）、`mof_resident_foreign_bond_flow`（日本）、`jpx_foreign_investor_flow`。本轮另排除：Gate 永续保险基金（官方接口只有 31 天）、ChinaClear 新增投资者（官网只剩年报）、Indeed 职位（与 JOLTS 同机制且有修订）、NAAIM / AAII（无免费官方历史）。
- 机制：中国居民 / 企业通过银行的结汇（卖美元）减售汇（买美元）= 民间外汇转换压力。差额下降或为负 = 居民买美元（资本外流、人民币贬值压力、亚洲美元流动性收紧）→ 风险偏好下降 → 经济先验「不新开多」。`cap_short_off` 侧检验相反的「资本外逃利好加密」说法。
- 数据（只用官方，不编造、不插值、不回补）：safe.gov.cn「银行结售汇数据时间序列.xlsx」（页面 /safe/2023/0215/22329.html，文件 20261116 上传，sha256 5feb9dcdff1a…），「以美元计价（月度）」表，亿美元；2010-01 → 2026-10 共 **202 个月，0 个日历缺口**。取三条：`cli` = 银行代客差额，`cap` = 代客资本与金融项目差额，`fwd` = 远期结售汇签约额差额。最新 2026-10：cli +651.9、cap −52.2、fwd +158.4。
  可用时点：M 月值自 **M+2 月 1 日 00:00 UTC** 起使用（SAFE 通常在 M+1 月中旬公布，取保守滞后）。SAFE 不发布历史版本，只能用最新版（小幅修订无法排除，已注明）。官方表 `output/safe_fx_settlement_official_monthly.csv`。
- 公式（看 PnL 前锁定 `scratch/safefx4h/PRE_REGISTER.json`，sha256 `16f852fc…`，90 格）：x = 3 个月均值；flag = 1 表示外流压力上升。
  `trend_n{12,24}`：x < 该序列近 N 月均值；`neg`：x < 0；`chg_n{3,6}`：x − x(N 月前) < 0；`z_k1`：x 的 36 个月 z < −1。三条序列 × 6 形式 × 5 侧（long_off / short_off / both / contra_both / cap_short_off），只拦新开仓，已有同向仓位不动。
  先验 `cli_trend_n12_long_off`，回退 `cap_neg_long_off`；安慰剂 = 先验 + 回退各 8 个时移（±30 / ±90 / +180 / −120 / +365 / −119 天）。
- 回测：同脚本默认 #1（双均线 50/150，8 币 perp_both，官方资金费），官方 OKX / Gate 4h 永续深缓存；真实费 maker 2 / taker 5.1 bps，压力费 perp 15.1 / spot 20 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根 4h）。

## 结果（`output/research_safe_fx_settlement_gate_4h.csv` 399 行；`_new8.csv` 20 行）

收益 % / Sharpe；9 段 = 3 套 × (深未见 / 调参 / post) Sharpe 胜基线次数。

| 格子 | 9 段 | OKX d8 深未见 / 调参 / post | Gate d8 深未见 / 调参 / post | post 月 好/差（OKX、Gate） |
|---|---|---|---|---|
| 基线 默认 #1 | — | +35.14/0.71、+85.08/1.47、+59.90/2.23 | −3.63/0.09、+84.25/1.46、+60.32/2.25 | — |
| 先验 cli_trend_n12_long_off | 3/9 | +42.03/0.90、+54.09/1.11、+55.89/2.21 | +24.76/0.49、+52.87/1.09、+56.48/2.23 | 1/2、1/2 |
| 回退 cap_neg_long_off | 0/9 | +21.20/0.56、+24.07/0.68、+55.89/2.21 | −7.10/−0.00、+22.79/0.65、+56.48/2.23 | — |
| 最好非先验 cli_chg_n3_cap_short_off | 7/9 | +39.08/0.88、+81.45/1.47、+70.72/2.57 | +8.03/0.26、+80.26/1.45、+71.21/2.58 | 4/2、4/2 |

- OKX d7（无 BNB）：基线 +54.92/0.75、+92.93/1.56、+50.76/2.10；先验 +57.92/0.86、+58.57/1.18、+46.31/2.03；最好非先验 +63.29/0.92、+86.11/1.53、+60.18/2.43（post 月 2/3）。
- 压力费：最好非先验 post OKX +67.69/2.49 vs 基线 +55.94/2.12，Gate +68.21/2.50 vs +56.78/2.15；先验 post OKX +52.40 vs +55.94。
- 安慰剂：16 个时移最高只有 3/9（与先验一样），先验没有好过安慰剂。
- 邻域（cli_chg_n?_cap_short_off）：n1 4/9（OKX post +28.71）、**n2 post 崩塌（OKX +6.67、Gate +3.67）**、n4 9/9（post 与 n3 完全相同）、n6 4/9（OKX post +31.80）、n9 / n12 post = 基线。只有 n3 / n4 两格成立，邻域断裂。
- 未调参 new8（pre / post Sharpe，基线 OKX 0.72 / 0.28、Gate 0.69 / 1.00）：最好非先验 pre 0.51 / 0.49（两所都更差），post 0.52 / 1.18；先验 pre 0.70 / 0.68、post 0.55 / 1.24（post 月 3/0）；回退 pre 0.94 / 0.91、post 0.55 / 1.24。

## 结论

**否决**，不实现、不进观察名单、不改默认、不加纸面盘，无代码改动。先验 3/9：只在深未见段（2023–2024 资本外流期）少开多有帮助，调参窗 Sharpe 从 1.47 掉到 1.11、post 略差、post 月 1/2，安慰剂同样 3/9；回退 0/9。唯一 7/9 的 `cli_chg_n3_cap_short_off` 是非先验（外流压力上升时不开空），post 月只有 4/2（< 6/9），邻域 n2 / n6 post 崩塌，未调参 new8 两所 pre 段都更差 → 连弱观察也不够。

## 勿重测（never retest by…）

不要通过改 n / 均值窗口（3 个月均值 ↔ 单月 / 6 个月）/ z 窗口 / k / 侧 / 方向 / 滞后（M+1 月 15 日 / 20 日 / 25 日 / M+2 月）重测本族；不要在代客差额、资本与金融项目、经常项目、货物贸易、服务贸易、直接投资、证券投资、银行自身、结汇或售汇单边、结汇率 / 售汇率、远期签约 / 平仓 / 展期 / 未到期额、期权 Delta 净敞口之间换序列，不要换人民币计价、分地区数据，也不要改用 SAFE「银行代客涉外收付款」、国际收支 BoP、外债、跨境资金流动或其他国家 / 地区的同类居民购汇数据重测「中国民间外汇转换压力」同一机制；也不要做成 1h「结售汇数据公布」事件来绕过本条。

## 文件
- `output/research_safe_fx_settlement_gate_4h.csv`、`output/research_safe_fx_settlement_gate_4h_new8.csv`、`output/safe_fx_settlement_official_monthly.csv`（均不入库）。
- 脚本 `scratch/safefx4h/{build,run,new8}.py`、`PRE_REGISTER.json(.sha256)`、`ts.xlsx`（官方工作簿原件，不推送）。纸面 8788 / 8789 / 8792 等未改动。
- 下一轮（短线）：选一个未测过、官方历史足够的 1h 事件族，先查重。
