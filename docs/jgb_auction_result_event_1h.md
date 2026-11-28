# 短线新族：日本财务省官方 JGB 拍卖结果（投标倍数 / 尾差）→ 8 币永续篮子（1h，2026-11-27 ~17:20 PST，研究，不改默认；否决）

- 查重 / 换题：本轮原候选「Gate bulk 大额主动成交聚簇 taker-flow 1h」与已否决的 `okx_taker_flow_imbalance_event`、`taker_flow_imbalance_gate`、`avg_trade_size_whale_event_15m`、`deribit_block_trade_shock_event_1h` 同机制（上一轮 `gate_longtail_breadth_event_1h` 也已判重），**不跑**。改跑上一轮留下的短线指针：JGB 拍卖结果 1h 事件。`us_treasury_auction_event_1h` 的勿重测只禁美债期限 / 指标互换，`jgb10y_yield_gate_4h` 只禁收益率水平 / 期限 / 利差闸门；docs、1,364 个 `output/research_*.csv` 无 JGB 拍卖条目。
- 数据（仅官方，不编造、不回补）：财务省 `Auction_Results_for_JGBs.xls`（mof.go.jp/english/policy/jgbs/auction/past_auction_results/）10Y / 20Y / 30Y / 40Y 与 5Y（未调参未见期限），加 2026-11 官方 eresul 结果页（11/05 10Y、11/10 30Y、11/12 5Y、11/18 20Y、11/25 40Y）。事件表 `output/jgb_auction_results_official.csv`：10Y 452 / 20Y 347 / 30Y 229 / 40Y 97 / 5Y 322 场；落在 OKX 1h 永续窗口（2022-01-29 起）的主集 203 场，5Y 58 场。抽查：2026-08-04 10Y 投标倍数 2.558、尾差 6.0 bp，2026-11-05 10Y 3.21 / 3.2 bp，与官方结果页一致。交易腿：OKX d8 1h 永续 2022-01-29→2026-11-27 19:00 UTC、OKX 未调参 new8、Gate d8 1h 2025-09-24→；官方资金费。
- 公式：btc = 竞争性投标额 / 中标额；tail_bp = (最低中标价收益率 − 平均价收益率)×100（10/20/30Y；40Y 是收益率荷兰式，无尾差）。各期限分别 z = (x − 前 N 场均值) / 前 N 场标准差（严格只用之前的拍卖）。弱需求：btc_z ≤ −k 或 tail_z ≥ +k；强需求反之。结果 12:35 JST（03:35 UTC）公布，入场 = 04:00 UTC 那根 1h 开盘，持有 H 根后开盘平；重叠事件跳过。
- 预注册（PRE_REGISTER.json 在任何 PnL 前锁定，96 格，sha c744c58e）：metric {btc, tail} × N {6, 12} × k {1.0, 1.5} × 侧 {weak_short 只做空, hyp_both 弱空强多, contra_both 镜像, weak_long 弱需求做多} × H {4, 24, 48}。先验 `tail_z_N12_k1.0_weak_short_H24`（尾差放大 = 全球久期 / 日元套息压力 → 加密次日 risk-off），回退 `btc_z_N12_k1.0_weak_short_H24`。成本：taker 5.1 bps/边（压力 15.1）+ 资金费。切分：deep 未见 2022-01-29→2024-10-21、test →2026-03-05、post →今；Gate 窗口 2025-09-24→。可用 = 8 槽全正且 OKX n train≥10 / test≥6 / post≥4。安慰剂：入场 ±24h / ±168h 平移；随机工作日 04:00 UTC 同数量同方向（先验 / 回退 1000 次，其余 200 次），要求分位 ≥80。基线：同脚本全部拍卖无条件多 / 空。

## 结果（`output/research_jgb_auction_result_event_1h.csv`，8,448 行；真实费每笔净 bps，括号为事件数）

| 格子 | OKX deep 未见 | OKX test | OKX post | new8 deep / test / post | Gate post / 窗口 | 5Y 未见期限 deep / test / post | 8 槽 | post 月份 OKX / Gate |
|---|---|---|---|---|---|---|---|---|
| 先验 tail_N12_k1.0_weak_short_H24 | −118.5 (22) | +142.5 (7) | −49.0 (8) | −109.4 / +133.1 / −39.4 | −49.5 / −72.0 | −180.2 / +277.3 / +246.8 | 2/8 | 3/9、3/9 |
| 回退 btc_N12_k1.0_weak_short_H24 | +57.2 (22) t0.65 | +39.6 (9) t0.21 | +28.1 (4) t0.38 | +66.7 / +20.7 / +56.9 | +28.3 / +28.3 | −71.9 / +66.5 / 无 | 8/8 | 2/9、2/9 |
| 非先验最好 btc_N6_k1.0_contra_both_H48 | +135.6 (44) | +104.8 (22) | +73.4 (13) t1.1 | +121.7 / +100.5 / +29.7 | +72.0 / +93.3 | +22.2 / −259.9 / −664.4 | 8/8 | 5/9、5/9 |
| 基线 全部拍卖 always_long H24 | −18.9 (114) | −26.0 (58) | −22.5 (31) | — | — | — | — | — |

- 先验：deep 未见 −118.5 bps、post −49.0，随机安慰剂分位 deep 11.8 / post 26.9，+24h / +168h 平移与真实同样为负 → 不成立。
- 回退：8 槽符号全正但 t 只有 0.2–0.65；压力费 post 只剩 +8.1；随机安慰剂分位 deep 83.7 / test 67.3 / post 56.7（未达 80）；−24h 平移 post +124、−168h +184，比真实更好；post 只有 4 笔，月份 2/9；5Y 未见期限 deep −71.9 → 否决，不进观察。
- 非先验（看过结果后，与先验方向相反）：弱需求后做多 / contra_both 的 H48 有 7 格可用，但只在 H48 成立：同参数 H24 btc_N6 contra 5/8、btc_N12 contra 0/8、btc_N12 weak_long 0/8；post t ≤1.4、月份 ≤5/9；5Y 未见期限 test / post 大幅为负（−260 / −664）；随机安慰剂 post 分位 72 / 65；+24h 平移 test +200 / post +50，接近真实 → 是 2022–2025 的事后边际，不晋升。
- 96 格可用 8/8 共 7 格，全部是非先验 H48 的弱需求做多 / 镜像侧，或 t<0.7 的回退。

## 结论
**否决**。不实现、不进观察名单、不改默认、不动纸面实例，不起记录器（官方 Excel 从 1987 年起有完整历史，按月更新）。

## 勿重测（never retest by…）
不要通过改 N / k / H / 方向（顺势↔逆势↔单边）、在投标倍数 / 尾差（价格或收益率口径）/ 最低价分配比例 / 非竞争性投标 / 第Ⅰ·Ⅱ非价格竞争额之间互换、换期限（2Y / 5Y / 10Y / 20Y / 30Y / 40Y / 物价连动 / GX 气候转型债 / 流动性供给入札 / 短期国库券 TB），或改入场小时来重测本族；也不要换成其他主权拍卖（德国 Bund、英国 Gilt、意大利 BTP）重测同一机制。

## 文件
- `output/research_jgb_auction_result_event_1h.csv`、`output/jgb_auction_results_official.csv`（不入库）
- `scratch/jgbauction1h/`：build.py、prereg.py、PRE_REGISTER.json(.sha256)、run.py、analyze.py、analyze.log、analyze_wide.csv、events_real.csv、jgb.xls、nov/*.htm

## 下一轮（长线 4h）
国家外汇管理局（SAFE）官方月度「官方储备资产」中的**黄金储备（万盎司）**——中国央行增持 / 暂停增持黄金的 n 月变化或连续增持月数 → 4h 默认书入场闸门（官方去美元化 / 货币贬值对冲体制；每月 7 日公布，次日 00:00 UTC 才用，不补数据）。原想的 JPX 信用取引残高不跑：`cn_margin_financing_gate_4h` 勿重测已禁止「日本信用交易余额」。须先核对 `fed_custody_gate_4h`（禁外汇储备）、`snb_sight_deposits_gate_4h`（禁 SNB 黄金）、`gld_gold_etf_holdings_gate_4h`（禁其他黄金 ETF / WGC ETF 持仓）的勿重测范围；黄金储备是中国央行的官方持仓，不在上述条款内，若判同机制就换题。
