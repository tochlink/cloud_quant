# 官方 Gate + OKX 新 USDT 永续上新节奏（全所上新速度）4h 入场闸门（否决）

## 长线新族：交易所新永续上线节奏（Gate / OKX 官方新 USDT 永续上线数）→ 4h 默认书入场闸门（2026-11-21 ~02:35 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、output/research_*.csv、记忆中只有逐币「上市后漂移」做空（`research_post_listing_drift_perp`，交易新币本身，已否决）和币安公告事件（交易被点名的币，弱观察）；从未把「全所上新速度」做成默认书的体制闸门。本条是不同机制（市场层面山寨过热 regime）。
- 数据（全部官方，`output/perp_listing_official.csv`，2,205 行）：
  - Gate：官方公共数据桶 download.gatedata.org（`gateio-public-data` S3 列表 `futures_usdt/candlesticks_1h/YYYYMM/`，**含已下架合约**）2019-11 → 2026-10 共 1,652 个合约，上线时刻 = 首个归档月文件的第一根 1h K 线；与现存合约官方 API `create_time` 对比，97.4% 在 ±24h 内（中位 +1h）。2026-11 新上线尚未进月文件的 22 个用官方 API `create_time`。
  - 剔除非加密：现存合约 `contract_type`（stocks 456 / indices / metals / forex / commodities）、已下架合约按 Gate 官方现货币种 `category`（stocks / xstocks / ondo-stocks / metals）+ 8 个按官方币种名称人工标注（ORCLX、RDDTON、VIX、BVIX、EVIX、XBR、XTI、ZJINNOLIGHT）；剔除盘前合约；首月 2019-11 已存在的合约视为左删失不计。最终 Gate 加密新永续 1,143 个（其中 605 个已下架，靠归档补回），2020: 69 / 2021: 104 / 2022: 111 / 2023: 125 / 2024: 291 / 2025: 307 / 2026: 136。
  - OKX：官方 `public/instruments` SWAP `listTime`（USDT、instCategory=1）只有现存合约 289 个；**已下架合约拿不到（官方公告接口对本机只返回美国站现货公告）→ 早年严重低估（2022 年仅 8 个）**，okx30 只作次要 / 有偏序列。
  - 已知偏差：已下架合约默认按加密计；改名 / 重新上线只算首次出现；2019-12 归档月为空。不补数据、不编造。
- 时滞：上线 +24h 才算已知；D 日计数在 D+1 00:00 UTC 才使用，前推到 4h K 线。
- 公式（看 PnL 前锁定，`scratch/perplisting4h/PRE_REGISTER.csv`，84 格）：序列 gate30 / gate90（Gate 近 30 / 90 天新加密永续数）、okx30（有偏）；形式 ratio365gt{1.25,1.5,2}（s / 过去 365 天 s 的均值 > k）、z365gt{1,1.5}、trend s > SMA{90,180}；侧 long_off（过热时拦新多）/ short_off（不过热时拦新空，即 cap_short_off 类）/ both / contra_both。只拦新开仓，持仓、止损、出场不变。唯一先验 `gate30_ratio365gt1.5_long_off`，回退 `gate90_z365gt1_long_off`。同脚本基线 = 默认书（沿用 gpr4h / finramargin4h 闸门框架）。
- 验证：OKX d8（2023-02 起）/ Gate d8（2022-07 起）/ OKX d7 无 BNB；深未见 → 2024-10-21、调参窗 → 2026-03-05、post → 2026-11-14；真实费（永续 taker 5.1 bps）+ 压力费 20 / 15.1 bps；官方资金费；9 格 Sharpe 计分；平移安慰剂 ±7 / ±120 / ±180 / +365 / −119 天；邻域；未调参 new8。
- 结果（`output/research_perp_listing_pace_gate_4h.csv`、`_new8.csv`）：
  - 基线 post：OKX +59.90% / Sharpe 2.23，Gate +60.32% / 2.25；深未见 Sharpe OKX 0.71 / Gate 0.09 / d7 0.75。
  - **先验 3/9**：post OKX +55.89% / 2.21、Gate +56.48% / 2.23（都更差），逐月 1/2（post 只 16% 时间触发）；深未见 Sharpe 赢（0.91 / 0.23 / 0.92），调参窗三处都输（1.45 vs 1.47 等）。压力费同向。安慰剂 +7d、−120d 达 6/9、+365d 5/9，**都不比真实信号差** → 无特异性。new8：pre Sharpe 0.85 vs 1.21（OKX）/ 0.82 vs 1.19（Gate），post 略好（0.43 vs 0.28 / 1.13 vs 1.00，逐月 1/0）。
  - 回退 6/9 但 post 完全不触发（与基线逐笔相同，0 个月不同），只靠深未见 + 调参窗；±7d 安慰剂同样 6/9。
  - 全网格最高 6/9，无 7/9 以上。最好的非先验格 `gate30_trend_n90_short_off`（与假设方向无关）post OKX +76.08% / 2.81、Gate +77.29% / 2.85，但逐月 4/5、6/3，**深未见三处全输**（OKX 0.09 vs 0.71、Gate −0.28 vs 0.09、d7 0.41 vs 0.75），邻域 n60 5/9、n120 3/9、n150 0/9 断崖；new8 post 好但逐月 5/4、4/5。属于看结果后挖掘，不采用。
- 结论：**否决**，不实现、不进观察名单、不改默认、不加可选策略，仅文档。上新节奏高位不能改善默认 4h 书，先验调参窗和 post 都输、安慰剂同样好。**勿以改窗口（30/60/90 天）、阈值、z / ratio / trend 形式、方向（side），或换交易所（币安 / Bybit 上新数）、换现货上币数、换含已下架 OKX 数据的方式重测本族。**
- 文件：`output/perp_listing_official.csv`、`output/research_perp_listing_pace_gate_4h.csv`、`output/research_perp_listing_pace_gate_4h_new8.csv`；脚本 `scratch/perplisting4h/{list_bucket,first_candle,build_table,make_run,run,prereg,new8}.py`、`PRE_REGISTER.csv`（研究脚本与数据未推送）。默认策略与纸面实例均未改动，无需拉取或重启。
