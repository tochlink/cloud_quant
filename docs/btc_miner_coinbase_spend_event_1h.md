<!-- Sidecar for docs/STRATEGY_FORMULAS.md (main file exceeds the GitHub connector 1MB push cap). -->

## 短线新族：官方比特币矿工 coinbase 产出花费 1h 突发 → 8 币永续篮子顺势 / 逆势（1h，2026-11-22 ~07:15 PST，研究，不改默认；否决）

- 查重：文档、`output/research_*.csv`、记忆检索 miner outflow / coinbase spend / 矿工抛售 无完成条目。不是已否决的 Puell / 矿工收入、BTC 手续费占比 4h、链上手续费冲击 1h、hash ribbon、难度调整 1h、出块间隔 / 空块、矿池集中度、CBECI 矿工利润、CDD 休眠、政府 BTC 流出 1h。网格在看任何收益之前锁在 `scratch/btcminer1h/PRE_REGISTER.json`（2026-11-22 03:30 PST，216 格，sha 543b6b71f595df97）。
- 数据（只用官方比特币主网链数据，经公开 Esplora REST：blockstream.info、mempool.space 及同源 Esplora/mempool 实例；mempool.guide 因服务错误链被剔除并清掉其数据；不用 Glassnode / CryptoQuant / 矿池标签，不编造、不回补）：高度 688,800 → 977,046 每块 coinbase 交易、各输出金额与官方 outspends（花费块高与块时间），288,247 块，缺块 0。
  - 序列（按花费块 UTC 小时）：fresh_btc = 币龄 A=S−C < 4,320 块（约 30 天）的 coinbase 输出被花费的 BTC；aged_btc = 4,320 ≤ A < 25,920（约 30–180 天）；n_spent = A < 25,920 的被花费输出个数。起点为高度 714,720（=688,800+25,920）之后第一根完整小时，无左截断：43,186 根完整小时，2021-12-19 01:00 → 2026-11-22 10:00 UTC，缺口 0，零花费小时 15,315（真实零）。合计 fresh 1,207,065.9 BTC、aged 34,031.2 BTC、314,457 个输出。
- 公式（预注册 216 格）：指标 `log1p(fresh_btc)` / `log1p(aged_btc)` / `log1p(n_spent)`，序列整体后移 1 小时（块时间容差），z 窗 168h（最少 84h），L=1 为 (x−μ)/σ，L>1 为 (sum_L x − Lμ)/(σ√L)，μ/σ 截至 t−1；L 1/4/8，k 3/4/5，burst / twosided，mom / contra，H 24/48；下一根 1h 永续开盘入场。OKX d8、未调参 new8、Gate d8 官方 1h 永续 + 官方资金费；真实 5.1 bps、压力 15.1 bps 每边 taker。分段 train 2022-02-15→2024-10-21（深层未见）、test →2026-03-05、post 之后、Gate 窗 2025-09-28 起；安慰剂 ±720h。经济先验（锁定）：老 coinbase 币（30–180 天）突发移动 = 矿工抛售 → 做空篮子，`log_aged_btc_L1_k3_burst_contra_H48`。
- 结果（CSV 6,912 行）：
  - 先验格只有 3/8：OKX d8 train −46.58 bps / t=−1.27 / n=196，test −48.43 / −0.98 / 104，post +34.46 / 0.56 / 58；new8 train −25.66、test −70.87、post −9.61。矿工抛售做空在深层未见与 test 都亏，不成立。
  - 可用 8/8 有 9 格，全是非先验，且没有一格 post t ≥ 1.5（预注册门槛）。最好的 `log_fresh_btc` L4 k3 burst contra H24：OKX d8 train +75.32 / t=2.11 / n=13，test +222.78 / 2.20 / 16，post +141.83 / 1.32 / 10；new8 post 中位数 −50.58；但 −720h 安慰剂 post +177.8 / t=1.80，比真格还好，样本仅 10 笔。`log_aged_btc` L8 burst mom H48 一组（与先验方向相反）post t 只有 0.67–0.87，安慰剂与压力费下 Gate test 为负。
- 结论：**否决**，不实现、不进观察名单、不加纸面盘、不改默认。勿以换 L、k、H、方向、mode，或对调 fresh / aged / n_spent、改币龄分界、加矿池标签、改用美元计价或日频再测本机制。
- CSV（不入库）：`output/research_btc_miner_coinbase_spend_event_1h.csv`；官方 1h 序列 `scratch/btcminer1h/btc_coinbase_spend_official_1h.csv`；脚本 `scratch/btcminer1h/{fetch3,build,run,analyze}.py`（研究脚本未推送）。
