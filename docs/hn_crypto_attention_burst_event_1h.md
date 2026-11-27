# 短线新族：Hacker News 官方加密标题投稿 1h 突发 → 8 币永续篮子（2026-11-27 ~08:15–08:50 PST，研究，不改默认；否决）

## 选题与查重
- 原定 Solana pump.fun `Create`（新币创建）1h 突发：**不跑**。(1) 已被禁：`STRATEGY_FORMULAS.md` 中 Uniswap V2 PairCreated 1h 族（2026-11-21，否决）的勿重测条款明确写有「换 … Base / Solana pump.fun 等其他工厂或链的新池计数」；(2) 官方历史也拿不到：公共 Solana RPC `getSignaturesForAddress(6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P, limit=1000)` 一页 1,000 条只覆盖约 1 秒，全历史需上亿次翻页；pump.fun 自家 `frontend-api-v3/coins?sort=created_timestamp` 的 offset 超过约 1,000 就返回空。
- 改测：docs/*.md、`docs/STRATEGY_FORMULAS.md`、`output/research_*.csv`、scratch 目录名检索 hacker news / hackernews / algolia / HN：0 条测试（只有不相关的字样）。不同于已否决的维基百科浏览量（日度，D+2 才可用）、GDELT 新闻占比 / 情绪、Google Trends / Fear&Greed、马斯克 / 特朗普帖子、npm / GitHub 开发者指标：本族是**技术圈主流受众（HN）对加密话题的投稿突发**，按投稿时刻逐小时可得。

## 数据（只用官方，不编造、不回补）
- 事件源：Hacker News 官方搜索 API（`https://hn.algolia.com/api/v1/search_by_date`，即 news.ycombinator.com 页脚「Search」），`tags=story`、只搜标题、`typoTolerance=false`、`queryType=prefixNone`，26 个关键词（bitcoin / btc / crypto / cryptocurrency / ethereum / stablecoin / tether / coinbase / binance / ftx / solana / blockchain / defi / web3 / dogecoin / memecoin / nft / satoshi / usdc / microstrategy / altcoin 等）分 90 天窗口抓取（单窗 >1,000 自动二分），按 objectID 去重，共 19,113 条，2021-12-01 → 2026-11-27 16:06 UTC；再在本地用单词边界正则过滤标题。
- 时间 = 投稿时刻 `created_at_i`（实时可知）。**不用分数 / 评论数**（事后累积，会前视）。
- 序列（`output/hn_crypto_stories_official_1h.csv`，43,744 个 UTC 小时，0 缺口）：core = 标题命中 bitcoin|btc|ethereum|stablecoin|coinbase|binance|ftx|tether|cryptocurrency|solana|dogecoin|memecoin|microstrategy|altcoin|satoshi|usdc（9,205 条）；all = core ∪ crypto|blockchain|defi|web3|nft（剔除含 cryptograph 的标题，18,910 条）。年度 core：2022 3,807 / 2023 1,705 / 2024 1,374 / 2025 1,205 / 2026 886（到 11-27），2022 年后明显变稀。
- 价格：OKX 官方 1h 永续 d8（BTC ETH BNB SOL XRP ADA DOGE AVAX，2022-01-29 07:00 → 2026-11-23 06:00 UTC，42,216 根，0 缺口）+ 官方深历史资金费；未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，42,205 根，0 缺口）；Gate 官方 1h 永续 d8 + 资金费（2025-09-24 08:00 → 2026-11-23 06:00 UTC，10,199 根，0 缺口）。

## 公式（`scratch/hncrypto1h/PRE_REGISTER.json`，sha256 `9a323436eca68998727f8fa442fdd6aca07bb39370be9a9cd40dcdf9016e309f`，看任何 PnL 前锁定 96 格）
- x_h = 第 h 个 UTC 小时投稿的命中条数；S_t = 最近 L 小时之和；μ、σ = L 窗口之前 720 小时的小时均值 / 标准差（σ 下限 1/√720）；`z = (S_t − Lμ) / (σ√L)`；z 首次上穿 k 时触发，t+1 根 1h 开盘入场。
- 方向：follow / fade = 同 / 反 L 小时篮子收益（OKX d8 篮子给 OKX d8 与 new8，Gate 篮子给 Gate）；long / short = 无条件。出场 = 入场 + H 根开盘。不重叠，等权 8 币。
- 网格：2 序列 × L{6, 24} × k{3, 5} × 4 方向 × H{12, 24, 48} = 96 格。真实吃单 5.1 bps/边 + 官方资金费（压力 15.1 bps/边）。
- 分段：train（深度未见，2022-01-29 →）< 2024-10-21 ≤ test < 2026-03-05 ≤ post；Gate 窗口 ≥ 2025-09-24。可用 = 8 槽（OKX d8 train/test/post、new8 train/test/post、Gate post/窗口）全正且 n ≥ 10 / 6 / 4。
- 先验 `core_L24_k3_fade_H24`（加密投稿在 HN 一天内爆发 = 大行情后散户关注见顶 → 次日反转）；回退 `all_L24_k3_fade_H48`。安慰剂：信号平移 ±168h / ±720h；随机日同小时（先验 / 回退 1000 次，其余 200 次）。

## 结果（`output/research_hn_crypto_attention_burst_event_1h.csv`，6,072 行；每笔净 bps，括号为事件数）

| 格子 | 8 槽正 | OKX train（深度未见） | OKX test | OKX post | new8 train / test / post | Gate post | Gate 窗口 | 随机日分位 test / post | post 月份 正/负（OKX，Gate） |
|---|---|---|---|---|---|---|---|---|---|
| 先验 core_L24_k3_fade_H24 | 7/8 | +50.7 (55) | −7.3 (23) | +13.9 (12) t0.20 | +74.0 / +6.5 / +66.3 | +14.2 (12) | +7.3 (19) | 51 / 64 | 4/3，4/3 |
| 回退 all_L24_k3_fade_H48 | 4/8 | −15.9 (44) | −84.8 (21) | +104.1 (12) t1.06 | −49.8 / −75.5 / +67.8 | +104.0 (12) | +32.2 (19) | 25 / 85 | 4/2，4/2 |
| 唯一可用（非先验）all_L24_k3_fade_H12 | 8/8 | +46.0 (57) | +47.7 (31) | +2.3 (16) t0.06 | +30.9 / +56.5 / +4.3 | +34.0 (16) | +7.5 (29) | 86 / 65 | 3/3，3/3 |
| 基准 15:00 UTC 无条件做多 H24 | — | −4.3 | −6.3 | −20.1 | −6.9 / −9.6 / −10.6 | −19.4 | −32.7 | — | — |
| 基准 15:00 UTC 无条件做空 H24 | — | −16.1 | −14.1 | −0.3 | −13.5 / −10.8 / −9.8 | −1.0 | +12.3 | — | — |

- 96 格中 8/8 可用只有 1 格（fade 1 格，follow / long / short 0 格）。
- 先验：test 段为负，post +13.9 bps 只有 12 笔、t 0.20；压力费下 OKX test −27.3、post −6.1、Gate 窗口 −12.7；随机同小时安慰剂分位 test 51 / post 64（远低于 80）；+168h 平移 post +72.0 > 真实。post 月份 OKX 4 正 3 负（2 个月无交易），Gate 同样 4/3 → 未达 ≥6/9。
- 回退：train −15.9、test −84.8（安慰剂分位 25），只有 post 为正，与 −168h 平移 post +65.2 同量级。
- 唯一可用 all_L24_k3_fade_H12：post 每笔只剩 +2.3 bps（OKX）/ +34.0（Gate），压力费下 OKX post −17.7、Gate 窗口 −12.5；随机日分位 post 64.5；+168h 平移 post +42.4 > 真实；post 月份 3/3（两所）→ 不满足观察条件。
- 邻域：L24 k3 fade H12 / H24 为 8/8、7/8，H48 跌到 4/8；core 同参数 H48 3/8；k5 每段 post 只有 1–3 笔，不可评；L6 fade post 多数为负（core_L6_k3 fade 三个 H 全负，post −48 ~ −89 bps）→ 只在 L24 k3 短持有附近有薄弱正值，且 post 边际接近 0。
- 无条件 long / short 格只跟随市场漂移（post 段做空、train 段做多），没有 HN 特有效应。
- 深度未见 + new8：先验 train 与 new8 train 为正（+50.7 / +74.0），但 test 段即失效；不是稳健的跨段信号。

## 结论
**否决**。先验 7/8 但 test 为负、安慰剂分位 51 / 64、post 月份 4/9；回退 4/8；唯一 8/8 非先验格 post 边际 ≈ 0、压力费为负、+168h 平移更好、月份 3/3。不进观察，不加纸面盘，不加影子子账户，不起记录器，默认与代码不变。

## 勿重测（never retest by…）
不要通过改 L / k / H / z 窗口 / 方向（follow ↔ fade ↔ long ↔ short），换关键词表或 core / all 口径，改用分数 / 评论数 / 上首页时刻（会前视）、HN 评论数 / Ask HN / Show HN 子集，或换其他技术社区 / 社交源（Reddit、Lobsters、Product Hunt、Stack Overflow、Mastodon、Bluesky、Telegram）的加密投稿计数、或改成 4h 入场闸门来重测本族；也不要再用 pump.fun / 其他链新币创建计数（已被 PairCreated 族勿重测条款覆盖）。

## 文件
- `scratch/hncrypto1h/`：fetch.py、build.py、prereg.py、PRE_REGISTER.json(.sha256)、run.py、analyze.py、analyze.log、analyze_wide.csv、events_real.csv、hn_stories_raw.csv
- `output/research_hn_crypto_attention_burst_event_1h.csv`、`output/research_hn_crypto_attention_burst_event_1h_months.csv`、`output/hn_crypto_stories_official_1h.csv`（均不入库）
- 下一轮（长线）：选一个未测过、官方日度 / 周度历史覆盖 2022 → 2026 的 4h 默认书入场闸门族（先查重 docs / 侧文档 / output / 记忆）。
