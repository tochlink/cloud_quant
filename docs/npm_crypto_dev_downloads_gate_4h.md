# npm 官方加密开发 SDK 日下载量 → 4h 默认书入场闸门（2026-11-21，研究，否决）

- 换题原因：原定 CME 比特币期货年化基差（近月结算 / CME CF BRR − 1）。CME 官方结算价无免费批量历史（cmegroup.com 结算接口反爬封禁、Data Terms 禁止自动抓取、深历史为付费 DataMine），本地官方 BRR 只从 2025-11-16 起，且机制与已否决的 OKX 季度年化基差闸门 / 永续基差闸门重复，按规则换族；未用第三方聚合源。
- 数据：npm 官方 `api.npmjs.org/downloads/range`，ethers / web3 / viem / bitcoinjs-lib / @solana/web3.js，2015-01-10 → 2026-11-19，4,332 天，日历无缺；五包同日全 0 的 57 天视为 npm 统计中断记 NaN，不插值不回补。D 日值 D+2 00:00 UTC 才用。
- 公式：all7 / all28 = 五包合计 7 / 28 日均（≥5 / ≥24 有效日），evm28 = ethers + web3 + viem 28 日均；flag：trend（> SMA n，n 30/90/180）、chg（n 日变化 > 0，n 30/90）、z365（ln 值 365 日 z > k，k 1/1.5/2）。方向 long_off / short_off / both / contra_both / cap_short_off，只拦新开仓。120 格预注册（sha256 e4909c8614fe1f79742a63621eea5ef0a18aec40f025d970976958b92d91c21a），先验 all28_trend_n90_cap_short_off，回退 all28_trend_n180_cap_short_off。
- 验证：官方 OKX d8 / Gate d8 / OKX d7 去 BNB 4h，真实费率（taker 5.1 / maker 2 bps + 官方资金费，压力 15.1 bps），同脚本基线，deep 未见（< 2024-10-21）/ tune / post（≥ 2026-03-05）9 槽 Sharpe；new8 未调参；邻域；平移与 30 日块打乱安慰剂。
- 结果：先验 / 回退 3/9，post OKX +35.66% vs +59.90%、Gate +36.09% vs +60.32%，月份 5/4；post 段下载量结构性上涨使 flag 恒为 1，等于不开新空。全网格最高 6/9 但 post 两所输约 20 点；非先验 all28_z365gt2_short_off post +5 点、月份 6/2，但 deep 未见与 tune 双输。平移安慰剂最高 4/9 高于真实。
- 结论：否决，不改默认、不改纸面、无代码改动。勿以同一机制换参数 / 包组合 / 改用 PyPI、crates.io、GitHub 指标重测。
- CSV（不入库）：`output/npm_crypto_dev_downloads_official_daily.csv`、`output/research_npm_crypto_dev_downloads_gate_4h.csv`、`_shuffle.csv`、`_new8.csv`。
- 下一轮（短线）：Upbit 官方「신규 거래지원」新上币公告 → 被点名币 OKX / Gate 永续 1h 事件（先查重、核对官方历史深度）。
