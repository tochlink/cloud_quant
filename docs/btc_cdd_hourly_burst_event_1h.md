# 比特币链上逐小时币天销毁（CDD）/ 休眠度爆发 1h 事件 → 8 币永续篮子（短线，2026-11-27 ~12:20–12:55 PST，已否决）

- 结论：**REJECTED（否决）**。先验 / 回退都失败；仅 2 个非先验 8/8，post t < 1.5，深度未见段接近 0，邻域在 k=4 断裂，−720h 时移安慰剂产生 6 个 8/8（多于真实的 2 个）。默认书、代码、纸面账本都不变，不加 shadow 子账本。
- 查重：docs / `output/research_*.csv`（1,322 个）/ 轮换锁中只有 **日度 CDD / 休眠度 4h 默认书闸门**（长线，`btc_cdd_dormancy_gate_4h`，已否决）；短线 1h 只有按**转账额**的巨鲸爆发（`btc_whale_transfer_burst_event_1h`，不看币龄）与矿工 coinbase 产出花费（`btc_miner_coinbase_spend_event_1h`，只看矿工输出）。逐小时全网币天销毁（老币苏醒）1h 事件 0 条。按此前 DVOL / Coinbase 溢价 / ETF 资金流「4h 闸门 + 1h 事件」分开测的先例，本族为新短线族。
- 机制（看 PnL 前锁定）：老币在一小时内集中移动 = 长期持有者派发 / 供给苏醒 → 之后 12–48h 加密篮子走弱（先验做空）。事件稀少（L720 k3 约每月 7 次），每笔持有 12–48h，目标是比 1h 主动成交费大得多的单笔边际。
- 数据（只用链上区块数据，不编造、不补数）：Blockchair 公开区块 dump（gz.blockchair.com/bitcoin/blocks）逐块 `cdd_total`、`input_total`，高度 663,913–976,966，按区块头时间汇总到 UTC 小时：2021-07-01 00:00 → 2026-11-21 23:00，47,280 小时；127 个无块小时、dump 缺的 2 个高度（854599、854614，2024-07-30）所在小时记 NaN（不算事件）。逐日加总与已入档的 `output/btc_cdd_dormancy_official_daily.csv` 1,969 天逐位一致（最大相对差 6e−16）。小时序列 `output/btc_cdd_official_1h.csv`。
- 公式：cdd = ln(小时 CDD，BTC·天)；dorm = ln(小时 CDD ÷ 小时花费输入 BTC) = 被花费币的平均币龄（天）。z_h = (x_h − 过去 L 小时均值) / 标准差（需 ≥0.8L 有效小时）；z_h ≥ k 为事件。方向：short 恒做空；mom = sign(BTC 永续 close(h+1)/close(h−1) − 1)；contra 取反。小时 h 的数据在 h+1 收盘才用（+1h 滞后），下一根 1h 永续开盘进场，等权 8 币，持有 H 根；同 cell 不重叠。网格 series{cdd,dorm} × L{168,720} × k{3,4} × side{short,contra,mom} × H{12,24,48} = 72 格；`PRE_REGISTER.json` 在任何 PnL 前锁定（sha256 510b5a8e…）。先验 `cdd_L720_k3_short_H24`，回退 `dorm_L720_k3_short_H24`。
- 验证：官方 OKX 1h 永续 d8（train = 深度未见 2022-02-15→2024-10-21，test →2026-03-05，post 2026-03-05→）、OKX 未调参 new8、Gate 1h 永续 d8（post + gate_window 2025-09-28→）；官方资金费；taker 5.1 bps/边（压力 15.1）；±720h / ±168h 时移安慰剂；同脚本无条件基线。打分 = 8 个槽位均值 > 0；usable = OKX d8 n ≥ 10/8/8。
- 结果（OKX d8 real，bps/笔，净费与资金费）：
  - 先验 `cdd_L720_k3_short_H24`：train −38.9（n180，t −1.55）/ test −77.2（t −2.46）/ post −30.3（n34，月 4/9）；new8 post −24.4；**失败**（老币苏醒后反而偏涨，但做多不在预注册里，不追认）。
  - 回退 `dorm_L720_k3_short_H24`：train −1.1 / test −42.6 / post −60.7（月 2/7）；**失败**。
  - usable 8/8 仅 2 个，均为非先验 mom H48：`cdd_L168_k3_mom_H48` train +7.2（t 0.19，压力费 −12.8）/ test +87.4 / post +95.1（n29，t 1.07，月 6/9），Gate post +95.1，new8 post +54.7（月 4/9）；`dorm_L168_k3_mom_H48` train +21.1 / test +84.6 / post +61.5（t 0.71，月 5/9），new8 post +25.0。
  - 邻域：同 mom H48 换 k=4 → cdd L168 post −18.6、cdd L720 −45.1；L720 k3 post 仅 +19；深度未见段 24 个 mom 格里 19 个为负（cdd_L720_k3_mom_H24 train −48.8）。
  - 安慰剂：−720h 时移 6 个 8/8（≥7 有 12 个）、−168h 3 个，均多于真实的 2 个 → mom H48 的正值是一般动量 / 时段效应，不是 CDD 特异。
  - 基线（无条件，同脚本）：OKX d8 post 做多 H24 −20.7 / H48 −31.2，做空 H24 +0.3 / H48 +10.8；Gate d8 做多 H48 post −29.7。
- 否决理由：先验 / 回退在三段与两家交易所均为负；唯一 8/8 为非先验、post t<1.5、深度未见接近 0、压力费 train 为负、k 邻域断裂、时移安慰剂产生更多 8/8。
- 永不重测：不要通过改 L、k、H、方向（short / mom / contra / 镜像做多），或换 cdd / dorm / 最大单块 CDD / 币龄分桶（≥1y、≥5y 等）/ 美元计价 / 天数加权的币龄指标、改滞后、换数据商（Glassnode / CoinMetrics 等）或换其他 UTXO 链（LTC / BCH / DOGE）的同类「币龄销毁爆发」来重测本族。
- 纸面：无变更；8788 / 8789 / 8792（及 8793–8799）照常纸面运行，实盘关。
- CSV（不入库）：`output/research_btc_cdd_hourly_burst_event_1h.csv`（5,256 行，含压力费 / 时移安慰剂 / 基线）、`output/btc_cdd_official_1h.csv`；脚本 `scratch/btccdd1h/{build,run,analyze}.py`。
- 下一轮（长线）：选一个未测过、官方历史足够覆盖 2024-10-21 / 2026-03-05 切分的 4h 默认书闸门族，先查重。
