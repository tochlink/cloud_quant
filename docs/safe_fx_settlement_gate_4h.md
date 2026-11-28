# 长线新族：国家外汇管理局官方银行结售汇（代客差额 / 资本项目差额 / 远期签约差额）→ 4h 默认书 #1 入场闸门（2026-11-27 ~20:40 PST，否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 超过连接器写入上限，只在本地追加）。

- 查重：在 docs/*.md、docs/STRATEGY_FORMULAS.md、output/research_*.csv、scratch/ROTATION_LOCK.txt 中检索 结售汇 / FX settlement / 涉外收付 / capital flight / 资本外流，0 命中。与 safe_gold_reserves（官方黄金储备）、pboc_cny_fixing（中间价）、pboc_tsf、pboc_omo、shibor、日本 MOF 居民外债流、fx_jpy_cny_trend（价格）均非同一机制。
- 机制：境内私人部门换汇压力。银行代客结汇 − 售汇（亿美元）走弱 / 为负 = 居民买美元（资本外流、人民币贬值压力、亚洲美元流动性收紧）→ 视为 risk-off。flag = 1 表示外流压力。
- 数据（只用官方，不编造、不回补）：safe.gov.cn「银行结售汇数据时间序列.xlsx」以美元计价（月度）表，2010-01 → 2026-10，202 个月，无缺口。月 M 的数据从 M+2 月 1 日 00:00 UTC 起才可用（保守；外汇局约在 M+1 月中旬发布）；只有最新版本（外汇局不发布历史版本）。官方月表 output/safe_fx_settlement_official_monthly.csv。
- 公式（看 PnL 前锁定 scratch/safefx4h/PRE_REGISTER.json，sha256 16f852fc…，90 格）：序列 cli（代客差额）、cap（代客资本与金融项目差额）、fwd（远期结售汇签约差额）；x = 3 个月滚动均值。形式 trend_nN（x < 序列 N 月均值，N=12/24）、neg（x < 0）、chg_nN（x − x.shift(N) < 0，N=3/6）、z_k1（36 月 z < −1）。侧 long_off / short_off / both / contra_both / cap_short_off。先验 cli_trend_n12_long_off，回退 cap_neg_long_off；安慰剂为先验与回退时移 ±30 / ±90 / +180 / −120 / +365 / −119 天。
- 回测：同脚本默认 #1（双均线 50/150，8 币，官方资金费），OKX d8、Gate d8、OKX d7（不含 BNB）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；真实费 taker 5.1 / maker 2 bps，压力费 perp 15.1 / spot 20 bps；另测未调参 new8。

## 结果（output/research_safe_fx_settlement_gate_4h.csv 399 行；_new8.csv）

| 格子 | 9 段 Sharpe 胜 | post 收益 / Sharpe（OKX、Gate） | post 月份 好/差 |
|---|---|---|---|
| 基线 默认 #1 | — | +59.90% / 2.23、+60.32% / 2.25 | — |
| 先验 cli_trend_n12_long_off | 3/9 | +55.89% / 2.21、+56.48% / 2.23 | 1/2、1/2 |
| 回退 cap_neg_long_off | 0/9 | +55.89% / 2.21、+56.48% / 2.23 | 1/2、1/2 |
| 事后最好 cli_chg_n3_cap_short_off（非先验） | 7/9 | +70.72% / 2.57、+71.21% / 2.58 | 4/2、4/2 |

- 先验：深未见 Sharpe 有改善（OKX 0.90 vs 0.71），但调参窗大幅变差（OKX +54.1% vs +85.1%），post 也低于基线；回退三处都不赢。时移安慰剂 post 多数等于或低于基线。
- 最好格 cli_chg_n3_cap_short_off 不是先验；post 多约 11 pp，但能比较的月份只有 6 个（4/2），不到 ≥6/9 的要求。邻域断裂：n1 post +28.7%、n2 只有 +6.7% / +3.7%、n4 +70.7%、n9 / n12 等于基线，n2 与 n4 相反说明是几个月的偶然时点。未调参 new8 上调参前段 Sharpe 变差（OKX 0.51 vs 0.72、Gate 0.49 vs 0.69），月份 3/3。
- 结论：**否决**。不改默认、无代码改动、无纸面变更。

## 勿重测（never retest by…）

不要通过改 N / 均值窗 / z 窗 / 侧 / 可用滞后重测；不要在代客差额、经常项目、资本与金融项目、证券投资、远期签约、结汇率 / 售汇率等子项之间换序列，也不要改用人民币计价表、涉外收付款表、外汇储备或其他国家的同类资本流数据，重测同一「官方结售汇换汇压力 → 默认 #1 入场闸门」机制，也不要改成 1h 发布日事件。

## 文件
- output/research_safe_fx_settlement_gate_4h.csv、_new8.csv、output/safe_fx_settlement_official_monthly.csv（不入库）。
- 脚本 scratch/safefx4h/{build,run,new8}.py、PRE_REGISTER.json(.sha256)、官方 ts.xlsx（不推送）。
