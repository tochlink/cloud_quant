# 长线新族：CFTC 官方 TFF 周报跨资产投机持仓（VIX 期货杠杆基金净空 / E-mini S&P 500、Nasdaq-100 杠杆基金与资产管理人净多）→ 4h 默认书 #1 入场闸门（2026-11-27 ~14:20–14:45 PST，研究，不改默认；否决）

- 换题说明：原定「FOMC SEP 点阵图中位数变化」**不跑**——`docs/fomc_minutes_event_1h.md` / STRATEGY_FORMULAS 第 9373 行的勿重测已写明不得改用「SEP 点阵图」重测；且 SEP 每年只有 4 次（2021 起约 20 次），撑不起 9 段检验。
- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、1,342 个 `output/research_*.csv`、ROTATION_LOCK 检索 FOMC / SEP / dot plot / fed funds / CFTC / COT / TFF / VIX futures / E-mini：只有 2026-11-14 CFTC TFF **CME 比特币 / 以太坊期货**持仓闸门（BTCAM_n13_contra_both 弱观察，其余否决）与 VIX 期限结构闸门（勿重测含「VX 期货期限结构」，不含持仓）。本族用的是**传统资产**（美股股指期货 + VIX 期货）投机 / 机构持仓作为跨资产风险偏好，合约、投资者与机制都不同。
- 数据（只用官方，不编造、不回补）：CFTC Public Reporting Environment，Traders in Financial Futures 仅期货数据集 `gpe5-46if`，合约代码 1170E1（VIX，CFE，1,026 周）、13874A（E-mini S&P 500，1,067 周）、209742（E-mini Nasdaq-100，1,067 周），2006-06-13 → 2026-11-17。周表 `output/cftc_tff_crossasset_official_weekly.csv`（不入库）。**滞后**：周二持仓、周五 15:30 ET 公布 → 报告日 +4 天 00:00 UTC 起用；2025-10 美国政府停摆期间积压的报告（报告日 2025-09-30 → 2026-01-13）保守地一律到 2026-01-31 00:00 UTC 才用（只会更旧，不会提前）。
- 公式（看 PnL 前锁定 `scratch/cotxa4h/PRE_REGISTER.json`，sha256 `8edb6633…be456e7`，180 格）：x 越高 = 投机风险偏好越高：VIXLEV = −(VIX 杠杆基金多 − 空) / OI；ESLEV、NQLEV = 杠杆基金净多 / OI；ESAM、NQAM = 资产管理人净多 / OI；XA3 = VIXLEV / ESLEV / NQLEV 各自 156 周 z 的均值。形式：trend（x > n 周均线，n 4 / 13 / 26）、chg（x − x₋ₙ > 0，n 4 / 13）、z52 > 1。flag = 1 为 risk-on。侧：long_off / short_off / both / contra_both / cap_short_off；只拦新开仓，同向持仓保留。先验 `XA3_trend_n13_contra_both`（risk-on 放行多、拦空），回退 `VIXLEV_trend_n13_cap_short_off`。
- 回测：同脚本默认 #1（perp_both 10×、官方资金费），真实费 maker 2 / taker 5.1 bps，压力费 20 / 15.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21、调参窗 → 2026-03-05、post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根）。

## 结果（`output/research_cftc_tff_crossasset_spec_gate_4h.csv` 717 行；`_supp.csv` 最优非先验格安慰剂；`_new8.csv`）

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | OKX post 收益 / Sharpe | Gate d8 深未见 / 调参 | Gate post | post 月胜 / 负（OKX、Gate） |
|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | +59.90% / 2.23 | 0.09 / 1.46 | +60.32% / 2.25 | — |
| 先验 XA3_trend_n13_contra_both | 3/9 | 0.26 / 1.71 | +41.88% / 1.83 | −0.05 / 1.62 | +42.78% / 1.87 | 3/3、4/2 |
| 回退 VIXLEV_trend_n13_cap_short_off | 3/9 | 0.39 / 1.60 | +29.72% / 1.56 | −0.18 / 1.66 | +30.20% / 1.59 | 4/5、5/4 |
| 最好经济侧 ESLEV_chg_n4_cap_short_off | 8/9 | 0.67 / 1.60 | +62.54% / 2.39 | 0.10 / 1.57 | +63.70% / 2.42 | 3/6、4/5 |
| 最好非先验 NQAM_trend_n26_short_off | 9/9 | 0.80 / 1.63 | +70.66% / 2.63 | 0.19 / 1.60 | +71.87% / 2.67 | 3/4、4/3 |
| 同上，压力费 | — | 0.65 / 1.52（基线 0.56 / 1.35） | +67.93% / 2.56（基线 +55.94%） | 0.04 / 1.50（基线 −0.07 / 1.34） | +68.99%（基线 +56.78%） | — |

- 先验 / 回退：深未见三组全输、post 少 18 ~ 30 点，否决。
- 最好非先验 `NQAM_trend_n26_short_off`（只在纳指期货资产管理人净多高于 26 周均线时才允许新开空，与经济先验方向相反）：9/9，邻域 n13 / 17 / 20 / 39 / 52 为 7–9/9，但
  - post 月度只 3 胜 4 负（OKX）/ 4 胜 3 负（Gate），远低于 ≥ 6/9；post 增益集中在少数月份；
  - 安慰剂：+30 天平移 post 反而更好（OKX +72.15% / 月 7 胜 2 负，Gate +73.06%），−119 / −120 天平移 post +63 ~ +66% 也接近；
  - 未调参 new8：pre 段明显更差（OKX Sharpe 0.33 vs 0.77、Gate 0.33 vs 0.75），只有 post 小幅更好；
  - 换序列（VIXLEV / ESLEV / ESAM / NQLEV / XA3 同形式）都没有同样效果。
- 结论：**否决**。不实现、不进观察名单、不加 shadow、不改默认、无代码改动；纸面 8788 / 8789 / 8792 与 8793–8799 未动。
- 勿重测（never retest via）：不要改 n / z 窗口 / 阈值 / 侧 / 滞后（含停摆积压处理）来重测本族；不要在 VIX / E-mini S&P / Nasdaq-100 / Russell / Dow / 美债期货 / 外汇 / 商品期货之间换合约，不要在杠杆基金 / 资产管理人 / 交易商 / 其他报告类别之间互换，不要改用 Legacy COT、Disaggregated COT、期货 + 期权合并报告、净持仓变化的 1h「COT 公布时刻」事件，或把多个合约另组合成新综合指数重测同一「传统资产投机持仓 → 加密风险偏好」机制。
- 文件：`output/research_cftc_tff_crossasset_spec_gate_4h.csv`、`_supp.csv`、`_new8.csv`、`output/cftc_tff_crossasset_official_weekly.csv`（均不入库）；脚本 `scratch/cotxa4h/{build,run,supp,new8}.py`、`PRE_REGISTER.json(.sha256)`（不推送）。
- 顺带发现：`scratch/cot/run.py`（2026-11-14 BTC / ETH COT 闸门）`flag()` 里 `.astype(float); f[ma.isna()] = np.nan` 被写进了注释，均线未就绪的前 n 周被当成「非 cap」而不是缺失；只影响各段最开始约 n 周，未重跑。
- 下一轮（短线）：日本央行官方国债购入操作（Rinban）结果公布 → 8 币永续篮子 1h 事件（先查重 jgb10y_yield_gate_4h、n225_open_gap_session_event_1h 等日本族的勿重测范围）。
