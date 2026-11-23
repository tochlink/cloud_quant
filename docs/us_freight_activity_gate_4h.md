<!-- Sidecar for docs/STRATEGY_FORMULAS.md (main file exceeds the GitHub connector 1MB push cap). -->
# 美国货运活动（Cass Freight Index 出货量 / 运费支出、BTS 货运 TSI，ALFRED 实时 vintage）→ 4h 默认书入场闸门（否决）

## 长线新族：美国货运量 / 运费体制 → 4h 默认书 #1 入场闸门（2026-11-23 ~02:12–02:35 PST，研究，不改默认；否决）

- 查重：rg `freight / Cass / TSIFRGHT / trucking / shipments / BTS / 货运` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`：0 条。最接近的已否决族：美国实体经济 / 消费者情绪（UMCSENT / RSAFS / INDPRO，`research_us_real_activity_sentiment_gate_4h.csv`）、纽约联储 WEI（条款只禁「其它联储周度活动指数」）、Census 企业申请、OECD CLI、ifo / ZEW、韩国海关出口、TSA、ISM、GDPNow。货运运输量 / 运费指数不是这些序列中的任何一个；按 Census BA / WEI 在 realact 条款之后仍被单独测试的先例，视为新机制。**本次否决后，该解释收紧**：见文末勿重测。
- 机制（看结果前锁定）：货运出货量 / 运费支出 = 实物商品需求与库存周期；高于趋势 / 同比上升 = 周期性 risk-on → 允许新多；走弱 → 拦新多（先验侧 long_off / both）。cap_short_off = 货运强时拦新空（探索侧）。只拦新开仓，已有同向仓、止损、离场不变。
- 数据（只用官方，不编造、不插值）：ALFRED（圣路易斯联储官方 vintage 存档）`FRGSHPUSM649NCIS`（Cass 出货量指数）、`FRGEXPUSM649NCIS`（Cass 运费支出指数）、`TSIFRGHT`（BTS Freight Transportation Services Index，季调）。每周一取一个完整 vintage，2021-06-07 → 2026-11-23，各 286 个；每个 vintage 只用自身历史（无修订前视）。**滞后**：vintage 日 D 的序列在 D+1 00:00 UTC 才使用，前向填充到 4h 开盘；实测 vintage 日减最后观测月：Cass 39–95 天，TSI 71–132 天。最新：Cass 2026-10 出货量 1.056、运费 4.01；TSI 2026-08 134.4。官方 vintage 表 `output/us_freight_activity_alfred_vintages.csv`。
- 公式（月度）：trend_n `x > 最近 n 个月均值`（n 3 / 6 / 9 / 12）；chg_n `x > n 个月前`（n 3 / 12，12 = 同比）；z24_k `(x − 均值24)/标准差24 > k`（k −0.5 / 0 / 0.5）。侧：long_off（flag=0 拦新多）、cap_short_off（flag=1 拦新空）、both。3 × 9 × 3 = **81 格** + 同脚本基线，PnL 前锁定于 `scratch/freight4h/PRE_REGISTER.json`（sha256 `a284eadf…7a61c`）。**先验** `cass_shp_chg_n12_long_off`（出货量同比下滑 = 货运衰退 → 拦新多）；**回退** `tsi_trend_n6_long_off`（BTS 多式联运货运 TSI 低于半年均值 → 拦新多）。
- Harness：与 cnmargin4h / nyfed_wei4h 同一脚本（`qtw.backtest.run_backtest` 默认双均线 50/150 4h，8 币永续，真实费：永续吃单 0.051%、挂单 0.02%；压力费 20 / 15.1 bps）。官方 OKX / Gate 4h 现货 + 永续到 2026-11-23 04:00 UTC，官方资金费。OKX d8（2023-02-01 起）/ Gate d8（2022-07-01 起）/ OKX d7_noBNB（2022-04-01 起）；deep 未见 → 2024-10-21 / tune → 2026-03-05 / post → 2026-11-23。同脚本基线（收益 % / Sharpe）：OKX d8 deep +35.1 / 0.71、tune +85.1 / 1.47、post +73.0 / 2.49；Gate d8 −4.3 / 0.08、+84.3 / 1.46、+73.4 / 2.51；d7 +54.9 / 0.75、+92.9 / 1.56、+61.0 / 2.34。
- 结果：

| 格 | 9 格 Sharpe 胜 | OKX d8 deep / tune / post | Gate d8 deep / tune / post | post 月份 好/差（OKX, Gate） | new8 post OKX / Gate（基线 +11.6 / +25.7） |
|---|---|---|---|---|---|
| 先验 cass_shp_chg_n12_long_off | 0/9 | +16.3 (0.47) / +24.1 (0.68) / +53.5 (2.13) | −12.9 (−0.10) / +22.8 (0.65) / +53.5 (2.14) | 1/3, 2/2 | +16.2 / +31.5（更好） |
| 回退 tsi_trend_n6_long_off | 1/9 | +48.7 (0.91) / +48.9 (1.06) / +56.6 (2.35) | +4.3 (0.20) / +47.5 (1.04) / +56.8 (2.37) | 1/3, 1/3 | +13.6 / +28.3（更好） |
| 最好（先验侧）cass_exp_trend_n3_long_off | 6/9 | +50.1 (1.00) / +87.6 (1.53) / +64.4 (2.40) | +12.9 (0.32) / +85.6 (1.51) / +65.0 (2.42) | 1/3, 1/3 | +16.4 / +31.8（更好） |

  - 81 个真实格 9 格胜数分布：0:17、1:12、2:9、3:28、4:5、5:5、6:5；没有 7/9 以上；**没有任何格在 d8 两所 post 收益 ≥ 基线**（watch 条件未达，压力费段按规则跳过）。所有 long_off / both 格 post 都少赚（post 段货运走弱，拦掉的新多恰好是 post 段不多的盈利多单），cap_short_off 格 post 只剩 +3 ~ +36%（拦掉主要盈利的新空）。
  - 6/9 的 `cass_exp_trend_n3_long_off`：胜在 deep / tune，post 三套都输（−8.6 / −8.4 / −5.6 pp），post 月份 1 好 3 差；邻域崩：n2 OKX deep −1.0、n4 +6.4、n5 +11.8（对 n3 +50.1），Gate n2–n10 deep 全为负；n15 / n18 tune 只剩 +50 / +46。
  - 安慰剂（时间平移）：−365 天 5/9（OKX deep +62.8，**好于真实**）、+365 天 4/9、±30 / ±60 / +180 / −120 天 0–3/9；真实最好格与安慰剂无实质区分。
  - new8（未调参，近 4500 根）：三个格 post 都比基线好（+2 ~ +6 pp，月 3–4 好 0–1 差，压力费同向），但这与 d8 主书 post 一致变差相反——new8 post 段新多单亏损，拦多自然占便宜，不是货运信息。
- 结论：**否决**。不实现、不进观察名单、不改默认、不动纸面实例，只写文档。美国货运量 / 运费体制对 4h 默认书没有超出安慰剂的增量；先验 0/9、回退 1/9，唯一 6/9 格 post 输且邻域断裂。
- **勿重测**：不要换 n / z 窗口 / 阈值 / 侧 / 方向，不要在 Cass 出货量 ↔ 运费支出 ↔ Cass 线运费率（Truckload Linehaul）↔ BTS TSI 货运 / 客运 / 合计之间互换，不要改用 ATA 卡车吨位、AAR 铁路车皮（已测铁路）、DAT / FreightWaves SONAR、港口集装箱吞吐（洛杉矶 / 长滩）、空运货量、Baltic Dry / 集装箱运价指数，不要改用同比 ↔ 环比 / 水平或缩短发布滞后来重测「美国 / 全球实物运输活动」同一机制。连同已否决的 UMCSENT / RSAFS / INDPRO、WEI、Census BA、ISM、OECD CLI、ifo / ZEW、韩国出口、TSA、GDPNow：**月度 / 周度实体经济活动指数类 4h 闸门视为全部覆盖，之后长线轮换不再选此类序列**。
- 文件（不入库）：`output/research_us_freight_activity_gate_4h.csv`（294 行，含安慰剂 / 邻域）、`output/research_us_freight_activity_gate_4h_new8.csv`、官方 vintage 表 `output/us_freight_activity_alfred_vintages.csv`；脚本 `scratch/freight4h/{fetch,build,run,new8}.py`、`PRE_REGISTER.json`（研究脚本未推送）。
- 下一轮（短线）：比特币 Ordinals 铭文（witness `OP_FALSE OP_IF "ord"` 信封）每小时数量爆发 → 8 币永续篮子 1h 事件（已列指针，先查重 mempool / btc_fee_share / btc_miner）。
