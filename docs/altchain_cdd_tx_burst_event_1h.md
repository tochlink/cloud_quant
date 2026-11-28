# 短线新族：自有链（DOGE / LTC / BCH）官方逐小时币天销毁（CDD）/ 交易笔数突发 → 同币永续 1h 事件（2026-11-27 ~23:58 PST，研究，不改默认；否决）

- 换题：上一轮建议的「以太坊合约创建交易数 1h 突发」与已否决的 univ2_paircreated 1h 突发、eth_onchain_demand（gas / 笔数）、eth_gas_fullness、deposit-contract 突发同属“ETH 链上活跃度”族；且合约创建数需逐笔回执（每小时约 数百到上千笔 × 5 年），RPC 回补本轮完不成，故放弃。比特币 CDD 已测（btc_cdd_dormancy）但 DOGE / LTC / BCH 自有链休眠度 / 活跃度 + 同币永续从未测过（docs / output / 记忆无 Blockchair、dogecoin 链上、litecoin 链上）。
- 数据（只用官方，不编造、不回补）：Blockchair 官方数据库日包 `gz.blockchair.com/{dogecoin,litecoin,bitcoin-cash}/blocks/…_YYYYMMDD.tsv.gz`，2021-12-01 → 2026-11-27 共 1,823 个 UTC 日 × 3 链 = 5,469 个文件，全部取到。字段 `time`、`transaction_count`、`cdd_total`；按区块时间归到整点小时求和（DOGE 2,473,826 块、LTC 1,053,321、BCH 262,853）。43,752 小时：DOGE 缺 1 小时、LTC 2、BCH 395（无出块，原样 NaN，不补）。价格 = OKX 官方 1h 永续（DOGE 默认 8 币的一员，LTC / BCH 来自 new8，2022-01-29 起）与 Gate DOGE；官方资金费率。
- 公式：x = ln(1+CDD_小时) 或 ln(笔数_小时)；z = (Σ_L x − L·μ168)/(σ168·√L)，μ / σ 用上一根起的 168h 滚动；触发 high z≥k / low z≤−k；信号小时收盘后下一根开盘入场、同币永续、持有 H 小时、逐币不重叠；真实费 5.1 bps/边（压力 15.1），计资金费。
- 预注册：`scratch/altchain_cdd1h/PRE_REGISTER.json`（sha256 f9d87eae9ecf9e07…，看 PnL 前锁定 96 格 = 2 指标 × L{1,4} × k{3,4} × 方向{high,low} × 开仓{多,空} × H{6,24,48}；宇宙 okx_own3（三币合并）/ okx_doge / gate_doge）。先验 = log1p_cdd_hour L1 k4 high 做空 H24（休眠币苏醒 = 派发）；回退 = log_tx_hour L4 k3 high 做多 H24。切片：train 2021-12→2024-10-21、test →2026-03-05、post 2026-03-05→。
- 结果（OKX own3 实费 bps / 事件数，t）：
  - 同脚本无条件基线（H24）：多 train −2.8 / test −3.3 / post −22.3（t −2.0）；空 −17.6 / −17.1 / +1.9。自有链币逐小时随机入场本身就亏费。
  - 先验：train **−59.6**（n=277）、test +7.8（125）、post +18.9（69，t 0.4）；Gate DOGE post +33.1（22）；OKX 三段 2/3 → **先验失败**（train 即为负）。
  - 回退：train +25.3、test −12.4、post −15.4（127，t −0.5）；Gate −8.6；post 月 3/9 → 失败。
  - 96 格里 OKX 三段 + Gate test / post 全正（n 达标）的可用格只有 1 个：cdd L4 k4 high 做多 H48：train +41.4（111）、test +161.7（56，t 1.6）、post +20.0（30，t 0.2，中位 −32.5）、Gate post +68.7（15）；压力费 post 0.0；−720h 安慰剂 test −170、post +16（与真实 post 同号同量级）。邻域 cdd L4 k3 / k4 high 做多 H24 三段也为正，但 post t 0.5 / 0.2、中位数全为负、压力费归零。
  - 安慰剂：三段全正且 n≥5 的格数，真实 7/90，+720h 5/90，−720h 7/90，无区分。
  - 先验 post 月度 6/9（偏集中于 2026-05 / 06 的少数大月），回退 3/9。
- 结论：**否决**，不实现、不进观察名单、不改默认、不加 shadow、纸面实例与代码均不变。唯一可用格 post t 0.2、中位为负、压力费归零、安慰剂可复制。
- 勿重测（never retest by）：换 L / k / H / 方向 / 指标（CDD ↔ 笔数 ↔ 输出额 ↔ 手续费）；换币（DASH、ZEC、BTC 以外的 Blockchair 链）；改用日度聚合；把 DOGE / LTC / BCH 链上量用作 4h 闸门或篮子事件；Blockchair 以太坊块表（与 ETH 链上族重复）。
- CSV（不入库）：`output/research_altchain_cdd_tx_burst_event_1h.csv`（4,680 行）；数据 `scratch/altchain_cdd1h/{raw/,*_official_1h.csv}`，脚本 `fetch.py / build.py / run.py / an.py`，逐笔 `prior_events.csv`。
- 下一轮（长线 4h）：建议找一个尚未碰过的官方低频宏观 / 市场结构序列做 4h 默认书闸门（先在 docs / output / 记忆查重）；例如美国 BLS JOLTS 职位空缺 / 辞职率，或 Census 官方月度零售库存 / 销售比（docs 中 jolts / inventory 先 grep）。
