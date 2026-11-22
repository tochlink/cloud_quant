# Gate 全 USDT 永续资金费过热广度 → 4h 默认书入场闸门（否决）

## 长线新族：Gate 全市场（含已下架）资金费过热合约占比 → 4h 默认书入场闸门（2026-11-21 ~23:55 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv` 检索「funding breadth / 触顶 / funding_rate_limit / heat share / 资金费占比」：只有上一轮写下的「下一轮」计划，无已测条目。最接近的已否决族是 `basket_funding_regime_gate_4h`（2026-11-14）：那是**8 个交易币**资金费**带符号均值** F_n 的水平 / 趋势；本族是 **Gate 全部 USDT 永续**（每天 73 → 1,167 个合约，含日后下架的）的**横截面广度计数**（极端费率合约所占比例），统计量和样本范围都不同。也不是已否决的 Gate 资金费结算间隔缩短 1h 事件（单合约事件）、资金费 carry / 跨所价差 / 成本倾斜。
- 区分度（只用信号，不看 PnL；`scratch/gatefundcap4h/distinct.py`）：Spearman(pos375, 篮子 7 日均费率) = 0.21，(pos10, 篮子7) = 0.41，(neg10, 篮子7) = −0.62（Pearson −0.43）。旧弱观察规则「F30 < 0」与本族 `neg10 z>1` 同时成立的天数只有 7%（两者各自 21.5% / 18.8%）。
- 机制：很多山寨永续同时出现极端正费率 = 全市场杠杆多头过热 → 拦新开多；很多合约同时极端负费率 = 空头拥挤 → 拦新开空。只拦新开仓，已持仓、止损、离场不变。
- 数据（只用官方，不编造、不回补）：Gate 官方 bulk `futures_usdt/funding_applies`（download.gatedata.org，全部 USDT 永续含已下架，2021-01 → 2026-10，由 `scratch/gatefundint1h` 下载）+ 官方 API `/futures/usdt/funding_rate`（2026-11 在架合约）。日序列 `output/gate_funding_heat_breadth_official_daily.csv`：2,151 个完整 UTC 日，2021-01-01 → 2026-11-21，日历缺口 0。D 日数据 D+1 04:00 UTC 才使用，ffill 到 4h。
- 关于上限：已下架合约没有公开的历史 `funding_rate_limit`，现有合约的上限从 0.02% 到 3% 都有，所以用固定阈值（8h 等效）：0.375%（= Gate 标准山寨上限 0.75% 的一半）和 0.1%。
- 公式：合约 c 在 D 日的 8h 等效费率 `e_cD = (D 日所有已结算费率之和) / 3`；`pos_share_τ = #(e ≥ +τ) / #当日有结算的合约`，`neg_share_τ = #(e ≤ −τ) / #有结算`；序列取 7 日均：pos10、neg10、pos375、neg375。形式：`z365 > k`（k 0.5 / 1 / 1.5 / 2）、`s > SMA(n)`（n 90 / 180）、`s − s[−n] > 0`（n 7 / 27）。侧：long_off / short_off / both / contra_both / cap_short_off。4 × 8 × 5 = **160 格** + 同脚本基线，任何 PnL 之前锁定在 `scratch/gatefundcap4h/PRE_REGISTER.json`（sha256 `bf0e7ca4…2f87`）。**先验** `pos375_z365gt1_long_off`，**回退** `neg10_z365gt1_cap_short_off`；经济侧 = pos 系列配 long_off / both，neg 系列配 cap_short_off。
- Harness：与 geomag4h / kwtp4h 同一脚本。OKX d8（2023-02 起）/ Gate d8（2022-07 起）/ OKX d7_noBNB（2022-04 起）；deep_unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；默认双均线 50/150 4h perp_both 10×，官方资金费；真实费现货 10 / 永续吃单 5.1 bps，压力 20 / 15.1；安慰剂平移 ±7 / ±14 / +180 / −120 / +365 / −119 天；邻域；未调参 new8 两所。
- 结果（收益 % / Sharpe；基线 OKX d8 deep +35.14 / 0.71、tune +85.08 / 1.47、post +59.90 / 2.23；Gate d8 −3.63 / 0.09、+84.25 / 1.46、+60.32 / 2.25；d7 +54.92 / 0.75、+92.93 / 1.56、+50.76 / 2.10）：

| 格 | 9 格 Sharpe 胜 | OKX d8 deep / tune / post | Gate d8 deep / tune / post | post 月份 好/差（OKX, Gate） | new8 post OKX / Gate（基线 +3.26 / +16.36） |
|---|---|---|---|---|---|
| 先验 pos375_z365gt1_long_off | 6/9 | +40.24 (0.78) / +90.14 (1.52) / +59.90 (2.23) | −2.04 (0.11) / +89.13 (1.51) / +60.32 (2.25) | 0/0, 0/0（post 21.7% 天 flag=1，但这些时段没有新开多可拦） | +3.26 / +16.36（相同） |
| 回退 neg10_z365gt1_cap_short_off | 5/9 | +37.92 (0.75) / +134.90 (1.97) / +59.90 | −2.20 (0.12) / +142.37 (2.01) / +60.32 | 0/0, 0/0（post flag=1 天数 0%） | 相同 |
| 最佳经济格 pos375_z365gt0.5_both | 8/9 | +27.90 (0.74) / +142.43 (2.28) / +63.01 (2.34) | +5.49 (0.22) / +137.54 (2.23) / +64.01 (2.37) | 3/5, 2/6 | +23.05 (6/3) / +21.82 (4/5) |
| 非先验 neg10_chg_n27_contra_both | 8/9 | +34.91 (0.76) / +82.04 (1.59) / +59.86 (2.41) | +4.07 (0.19) / +85.35 (1.63) / +60.08 (2.42) | 3/3, 3/3 | +14.74 (6/2) / +30.18 (6/2)，但 new8 pre +33.5 vs +48.1 |

  - 先验 / 回退：post 段与基线逐值相同——回退的 neg10 z>1 在 post 一天都没触发；先验 pos375 z>1 在 post 有 21.7% 的天 flag=1，但这些时段默认书没有要新开的多单。deep / tune 只有小幅变化，不能满足改默认门槛。
  - `pos375_z365gt0.5_both`：tune 段大幅更好（主要来自 flag=0 时拦新空），但 d7 deep +27.07 vs +54.92 变差，post 月份 OKX 3/5、Gate 2/6（多数月份更差），**邻域崩**：k=1.0 post +36.57 / +36.94，k=1.25 +26.45，k≥1.5 只有 +9 ~ +18（基线 ~+60）；k=0.75 post +69.68 但 deep 0.54 / 0.02 低于基线。**安慰剂** +14 天 post +67.92 / +68.62 高于真实，deep Sharpe 1.01 / 0.35 也高于真实。压力费：OKX post +59.84 vs +55.94，Gate +61.00 vs +56.78，d7 deep 0.47 vs 0.62。
  - `neg10_chg_n27_contra_both`：post 收益与基线相同（+59.86 vs +59.90），只是 Sharpe 略高，月份 3/3；邻域 n7 post +38.22（崩），neg375 版 post +46.02；非先验。
  - 160 个真实格的 9 格胜数分布：0:25、1:20、2:11、3:70、4:8、5:6、6:16、7:3、8:2、9:0。
- 结论：**否决**。不实现、不进观察名单、不改默认、不动纸面实例，只写文档。全市场资金费过热广度对 4h 趋势书没有稳定的增量：先验和回退在 post 段与基线逐值相同（没有可拦的新开仓）；唯一 8/9 的经济格邻域崩、post 月份多数更差、被 +14 天安慰剂超过。**勿重测**：不要换 τ / 平滑窗 / k / n / 侧，不要换成 OKX 全市场广度、按当前上限折算的「触顶」比例、加权（按 OI / 成交额）广度、中位费率，或改成 1h 事件来重测本机制。
- 文件：`output/research_gate_funding_heat_breadth_gate_4h.csv`（561 行，含安慰剂 / 邻域 / 压力费）、`output/research_gate_funding_heat_breadth_gate_4h_new8.csv`、官方日序列 `output/gate_funding_heat_breadth_official_daily.csv`（均不入库）；脚本 `scratch/gatefundcap4h/{build,distinct,run,new8}.py`、`PRE_REGISTER.json`（研究脚本未推送）。
- 下一轮（短线）：OKX 官方 `rubik/stat/contracts/long-short-account-ratio` 等只有短历史的序列不做回测、只开记录器；可回测的短线候选：OKX 官方 1h 永续「标记价 − 指数价」溢价（premium index history）横截面同向骤变 → 8 币篮子 1h 事件（先查重 basis_extreme_1h、cross_venue_dislocation、coin_funding_price_divergence）。
