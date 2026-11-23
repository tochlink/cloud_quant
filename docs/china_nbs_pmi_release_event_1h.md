# 短线新族：中国国家统计局（NBS）官方 PMI 发布事件 → 8 币永续篮子（1h）

2026-11-22 ~22:00 PST，研究，不改默认、不动纸面；**否决**。

## 查重
`docs/STRATEGY_FORMULAS.md` 对「PMI」只有 ISM（美国，作为「下一轮」指针）与 OECD CLI 的顺带提及；`docs/*.md`、`output/research_*.csv`（约 1,235 个）、`/workspace/scratch` 目录名与记忆中无 NBS / 国家统计局 / 中国 PMI / 财新 事件测试。BoJ 决议事件只是已否决 ECB/BoE 决议事件（`research_ecb_boe_policy_decision_event_1h.csv`）的央行替换，跳过。

## 数据（全部官方）
- 事件：国家统计局官网「最新发布」`https://www.stats.gov.cn/sj/zxfb/` 中全部「YYYY年M月中国采购经理指数运行情况」页面（59 期，参考月 2021-12 → 2026-10），从正文抽取制造业 PMI、非制造业商务活动指数、综合 PMI 产出指数及正文给出的「比上月」变动（百分点）。
- 发布时刻：NBS 官方英文「Regular Press Release Calendar」2021–2026 各年表（PMI 行，09:30 北京时间）给日期；2024-04 起页面 `PubDate` meta 也给出发布时间，25/25 与日历一致（含 2025-01-27、2026-03-04 春节调整）。官网页面 URL 里的日期是建页日期（如 2022 年各期都是 20230203），**不用**。
- 时点：09:30 北京 = 01:30 UTC；t0 = 01:00 UTC 那根 1h K 线；入场 = 02:00 UTC 开盘（发布后第一根完整 K 线），出场 = 入场后 H 根开盘。因果。
- 行情：OKX 官方 1h 永续（2022-01-29 → 2026-11-22，默认 8 币 + 未调参 new8：LINK LTC DOT TRX BCH ATOM NEAR UNI）、Gate 官方 1h 永续（2025-09-24 起），含官方资金费；费率 taker 5.1 bps/边（压力 15.1）。不重叠持仓。
- 官方事件表：`output/china_nbs_pmi_official.csv`；实时官方记录器 `scratch/nbspmi1h/record.py`（每 6 小时抓 NBS 最新发布，下一期 2026-11-30 09:30 北京）。

## 公式与参数（PRE_REGISTER.csv，102 格，sha256 9e6058ae…，21:53 PST 在任何 PnL 前锁定）
- surp：chg = 官方「比上月」变动（制造业 PMI 或综合 PMI 产出指数）。thr=0：chg>0 做多、chg<0 做空；thr∈{0.3,0.5}：chg≥thr 做多、chg≤−thr 做空，其余不交易。hyp = 上述方向，contra = 反向。H∈{4,12,24,48}。48 格。
- lvl50：PMI≥50 多、<50 空，hyp/contra × mfg/comp × H。16 格。
- follow/fade：r0 = t0 K 线 BTC 或 8 币等权 close/open−1，|r0|>k·σ720（k∈{0,1}）时顺/逆。32 格。
- predrift：t0−H 入场、t0 开盘出场，多/空，H∈{4,12,24}。6 格。
- 先验 surp_mfg_thr0.0_hyp_H24（官方制造业 PMI 改善 → 风险偏好 → 做多篮子），回退 surp_comp_thr0.3_hyp_H24。
- 可用 = 8/8 槽为正（OKX d8 train/test/post、new8 train/test/post、Gate post/gate_window）且 OKX d8 train≥10、test≥6、post≥4。切分 train<2024-10-21≤test<2026-03-05≤post。
- 安慰剂：随机任意日 02:00 UTC 同数量同方向（先验与 H24 1000 次，其余 300 次）；事件整体平移 ±24h、±168h。基线：每期都做多/做空同入场。

## 结果（real 费，bps/笔）
| 格 | OKX train | OKX test | OKX post | new8 train / test / post | Gate post | 随机安慰剂分位 test / post |
|---|---|---|---|---|---|---|
| 先验 surp_mfg_thr0.0_hyp_H24 | +37.8 (n32) | **−45.2** (n17) | +28.5 (n8) | +92.0 / −31.7 / +72.0 | +28.3 | 36 / 67 |
| 回退 surp_comp_thr0.3_hyp_H24 | +76.3 (n28) | +32.6 (n14) | **−32.5** (n6) | +90.6 / +28.2 / +33.0 | −31.8 | 66 / 42 |
| 非先验 surp_mfg_thr0.5_hyp_H24（最好） | +65.4 (n18) | +105.7 (n7) | +60.3 (n4) | +124.3 / +97.4 / +104.4 | +60.2 | 81 / 70 |
| 非先验 surp_comp_thr0.5_hyp_H12 | +17.8 | +112.6 | +38.1 (n4) | +18.5 / +125.1 / +107.4 | +38.1 | 97 / 73 |
| 基线 always_short_H24 | +37 | +108 | +28 | +17 / +149 / +38 | +28 | — |
| 基线 always_long_H24 | −58 | −129 | −49 | −37 / −169 / −58 | −48 | — |

- 先验 post 月度（OKX，2026-03→10）：−540 / −22 / +163 / −108 / +108 / +185 / −46 / +19，正 4/8；Gate 同样 4/8。压力费 post OKX +8.6、Gate +8.3，test −65。
- 全网格可用 8/8 = 5/102，全部是 surp hyp 大阈值（mfg thr0.5 H4/H24、mfg thr0.3 H24、comp thr0.5 H12/H24）；thr0 与 lvl50、follow 全不过；fade 只有 fade_basket_k1.0_H24 8/8 但 post n=2。
- 最好的 surp_mfg_thr0.5_hyp_H24：post 只有 4 笔（03-31 多 −70、07-31 空 +108、08-31 多 +185、10-31 空 +19）；test 均值被 2026-01-31 一笔空单 +785 bps 撑起（其余 6 笔均值 −7.5）；随机安慰剂 post 分位 70 < 80；平移 −168h / +168h 的 post 均值 +122 / +158 **高于**真实 +60；相对每期都做空基线 post 只多 +32 bps，且方向 2 多 2 空。H48 邻格 post −33，H12 train −27，邻域不稳。

## 结论
**否决**。不实现、不进观察名单、不改默认、不动纸面实例，仅文档 + 官方记录器。先验（制造业 PMI 环比方向）test −45 bps、回退 post −32 bps；唯一 8/8 的大惊喜（|ΔPMI|≥0.5pp）顺向格 post 仅 4 笔、随机安慰剂分位 70、±168h 平移安慰剂更好，未达预注册弱观察标准（安慰剂分位 test 与 post ≥80）。

勿重测：不要通过换 thr / H / 方向、换制造业 vs 非制造业 vs 综合 PMI、换水平 50 vs 环比、换 BTC vs 篮子反应、改用财新（非官方）PMI、或把 NBS CPI/PPI/工业增加值/社零等其它 NBS 月度发布换进来重测同一「中国官方宏观发布 1h 事件」机制。

结果 CSV：`output/research_china_nbs_pmi_release_event_1h.csv`；脚本 `scratch/nbspmi1h/{crawl.py,fetch_pages.py,parse_cal.py,events.py,prereg.py,run.py,analyze.py,record.py}`。
