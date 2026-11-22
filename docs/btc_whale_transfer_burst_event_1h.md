# 比特币链上巨鲸转账额爆发（官方逐块转账额）1h 事件 → 8 永续篮子（短线，2026-11-22，已否决）

- 结论：**REJECTED（否决）**。默认书与纸面不变，不新增 shadow 子账本。
- 查重：docs / `output/research_*.csv` / 记忆中无"链上大额转账 / 巨鲸转账 / 逐块转账额"1h 事件。不是已否决的 CDD/休眠度 4h（按币龄）、blockchain.com 日度链上转账额/NVT/活跃地址 4h 闸门、手续费冲击、mempool 拥堵、出块间隔、coinbase 花费、难度调整、政府 BTC 外流、WBTC、ETF 资金流、交易所逐笔平均成交额巨鲸。
- 数据（只用官方链上区块数据，不编造、不补数）：Blockchair 公开区块 dump（gz.blockchair.com/bitcoin/blocks）高度 663,913–976,966；dump 缺的 2 个高度（854599、854614）取 mempool.space `/api/v1/blocks/<h>` 官方值。逐块转账额 = output_total − coinbase reward（与 mempool.space `extras.totalOutputAmt` 随机 9/9 块逐聪一致）。按区块头时间 UTC 小时聚合：2021-07-01 00:00 → 2026-11-21 23:00 UTC，47,280 小时，127 个无块小时（记 NaN，不填）。官方数据存 `output/btc_onchain_transfer_official_1h.csv`。
- 为何不是逐笔 ≥100/1000 BTC 计数：Blockchair 交易 dump 限速约 100 KB/s（约 30 MB/天 × 约 1,800 天，不可行），API 返回 430 IP 黑名单。逐块转账额由巨鲸大额交易主导，作为巨鲸流量代理。
- 公式：序列 vol = ln(小时转账 BTC)，vpb = ln(转账 BTC / 块数)，avgtx = ln(转账 BTC / 非 coinbase 交易数)；z_h = (x_h − 过去 L 小时均值) / 标准差（需 ≥0.8L 有效小时）；z_h ≥ k 即事件。方向 mom = OKX BTCUSDT 永续 close(h+1)/close(h−1) 符号，contra 取反，short 恒做空。信号滞后 +1h，下一根 1h 开盘进场，持有 H 根，同 cell 不重叠。L∈{168,720}，k∈{2,3}，H∈{12,24,48}，共 108 个 cell，PnL 前锁定 PRE_REGISTER.json（sha256 72fbdc1a…）。
- 先验（锁定）：vpb_L720_k3_short_H24（巨鲸搬币 = 派发 → 做空）；备选 vpb_L720_k2_contra_H24。
- 验证：官方 OKX / Gate 永续 1h K 线 + 官方资金费；taker 5.1 bps/边（压力 15.1）；okx_d8 / okx_new8（未调参）/ gate_d8；train（深度未见）2022-02-15→2024-10-21，test →2026-03-05，post 2026-03-05→；±720h / ±168h 时移安慰剂；同脚本无条件基线。
- 结果：
  - 先验 vpb_L720_k3_short_H24：OKX d8 train +24.0 bps（n52），test −181.4 bps（t −2.31），post +0.0 bps（n23，月 3/9）；new8 post −46.1；失败。
  - 备选 vpb_L720_k2_contra_H24：5/8，OKX post −5.7 bps、Gate post −6.0 bps；失败。
  - 唯一 usable 8/8 是非先验 avgtx_L720_k2_contra_H24：OKX d8 train/test/post +35.6/+38.0/+27.9 bps（n 248/134/72），post t 0.87、中位 +51 bps、月 5/9（<60%）；Gate post +27.5 bps（t 0.86）；new8 post +57.9（t 1.59）；压力费 post 仅 +7.9 bps；邻域断裂（k3 post −99.9，L168 post −5.3，vpb/vol 同参 post −5.7/−46.1）。
  - 安慰剂：+720h 时移产生 3 个 8/8、+168h 2 个、−168h 1 个，均不少于真实的 1 个 → 8/8 不显著。
  - 基线：OKX d8 无条件做空 H24 post +1.4 bps，做多 −21.8 bps。
- 否决理由：先验/备选均失败；唯一 8/8 为非先验、post t<1.5、月份 <60%、邻域不稳、安慰剂同等频率出 8/8。
- 永不重测：不要通过改 L、k、H、方向，或换 vol/vpb/avgtx/USD 计价/输入额/逐笔阈值，或改用其他链上数据商的同类"链上转账额爆发"来重测本家族。
- CSV（不入库）：`output/research_btc_whale_transfer_burst_event_1h.csv`；脚本 `scratch/btcwhale1h/{build,run,analyze}.py`。
- 下一轮（长线）：美联储官方商业票据利率（AA 金融 / 非金融 30 天 CP − 4 周国库券利差）趋势 / z 作为 4h 默认书入场闸门（短期融资压力 → 拦新开多），按发布滞后入场。
