# 短线新族：政府 / 破产托管 BTC 地址链上大额转出 → 8 币永续篮子（1h）

> 侧记（docs/STRATEGY_FORMULAS.md 超出连接器写入上限）。研究，不改默认；**否决**。

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、记忆中无 Mt.Gox / 美国政府(USG/USMS/DOJ) / 德国 BKA 托管地址转出研究。不同于已否决的交易所流入流出、全网 CDD / 沉睡币、鲸鱼 / mempool 研究（那些是全网口径，本轮只看少数已知托管实体）。
- 数据（只用比特币链上区块数据，不编造、不补数）：公开 esplora（mempool.space，blockstream.info 备用）`/api/address/<a>/txs/chain` 全量分页。地址集一次锁定（`output/gov_btc_addresses.csv`，100 个）：公开文献 / 官方声明 / 媒体报道的种子地址 + Mt.Gox 2024-05-28 归集交易的输入地址 + 同实体往返规则（从集合收 ≥100 BTC 且回转 ≥100 BTC，迭代）；mtgox 84、us_gov 6、de_bka 10。579 笔花费交易（`output/gov_btc_spend_txs_official.csv`）。每笔外流 = 输出到集合外地址的金额（含找零到新地址，交易所入金标记无法在链上核实，故未用）。小时序列 `output/gov_btc_outflow_official_1h.csv`：2021-02-01 19:00 → 2026-11-22 03:00 UTC，50,865 小时，0 缺口，无交易小时 = 真实 0。
- 公式：区块时间所在 UTC 小时 h 的外流 ext_out；事件 out_ge100 / out_ge500 / out_ge1000（ext_out ≥ 100/500/1000 BTC），dormant_ge100（某实体此前 720h 无 ≥100 BTC 外流小时后首次 ≥100）。h 收盘后再延 1 根，h+2h 的 1h 永续开盘入场，持有 H 根，同格不重叠。成本 taker 5.1 bps/边（压力 15.1）+ 官方资金费。
- 预注册（PRE_REGISTER.json，任何 PnL 前锁定 32 格，sha 7fabae84…）：4 事件 × {short 跟随抛压, long 反向} × H {4,12,24,48}。先验 `out_ge1000_short_H24`，回退 `dormant_ge100_short_H24`。切分 train 2022-02-15→2024-10-21（深度未见）、test →2026-03-05、post →今；Gate 自 2025-09-28；new8 未调参；安慰剂 ±720h 平移 + 500 次同数量随机小时分位。
- 结果（真实费，每笔净 bps；`output/research_gov_btc_outflow_event_1h.csv`，1,920 行；事件小时 out_ge100 198 / ≥500 75 / ≥1000 44 / dormant 24）：
  - **先验** out_ge1000 short H24：OKX d8 train +65.3（n=17，t 0.82，随机分位 0.84 < 0.90）/ test **−85.0**（n=6，不足 8 次，不计分）/ post +481（n=1）；new8 +57.1 / **−212.6** / +186.7，全样本 −4.9；Gate 只有 post 1 次。±720h 安慰剂 train −105 / −86（真实较好），但 train 显著性不够、test 反向。
  - **回退** dormant_ge100 short H24：OKX d8 train **−173.3**（n=12，t −1.87），new8 train −197.3（t −2.87）→ 深度未见段反向，否决。
  - 探索：32 格 × 3 宇宙内，没有一格在 train/test/post 都为正（n≥8 且好于基线）。post 只有 1–2 个事件（2026-06-02 Mt.Gox 约 10,306 BTC），无法验证。
- 局限：us_gov 地址覆盖只有 6 个（只抓到 6 笔），2024 年后的美国政府转出大多未覆盖；事件数太少。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动，仅文档。勿以同一机制换阈值 / H / 方向、换实体子集、扩地址集（Arkham 标签、其他政府如英国 / 不丹 / 萨尔瓦多）、改用入金交易所标记或改滞后再测。
- 文件：output/research_gov_btc_outflow_event_1h.csv、output/gov_btc_outflow_official_1h.csv、output/gov_btc_spend_txs_official.csv、output/gov_btc_addresses.csv；脚本 scratch/govbtc1h/{discover,fetch,build,run}.py、PRE_REGISTER.json（研究脚本未推送）。
