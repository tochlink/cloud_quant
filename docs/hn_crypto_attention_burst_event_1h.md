# 短线新族：Hacker News 官方加密新闻投稿爆发 → 8 币永续篮子 1h 事件（2026-11-27 ~08:15 PST，研究，不改默认；否决）

## 机制与公式
- 假设：加密相关帖子在 Hacker News（主流科技受众）集中出现 = 散户注意力峰值，常出现在大幅波动之后 → 过度反应，随后 1 天回吐（先验 fade）。这不同于已否决的 Wikipedia 页面浏览量 4h 闸门、GDELT 新闻覆盖/情绪 1h 冲击（新闻媒体），以及 Google Trends 类搜索热度；这里是 HN 社区投稿时间。
- 数据（仅官方）：Hacker News 官方搜索 API（hn.algolia.com/api/v1/search_by_date，news.ycombinator.com 页脚链接的搜索），tags=story、仅标题、typoTolerance=false、26 个加密关键词并集按 objectID 去重，再本地按词边界正则过滤标题。时间 = 帖子 created_at_i（提交时间，实时可知；不用点数/评论 → 无前瞻）。19,113 条帖子，2021-12-01→2026-11-27 05:59 UTC；小时序列 output/hn_crypto_stories_official_1h.csv（43,744 小时）。不补缺、无合成。
- 序列：core = 标题匹配 \b(bitcoin|btc|ethereum|stablecoins?|coinbase|binance|ftx|tether|cryptocurrenc(y|ies)|solana|dogecoin|memecoins?|microstrategy|altcoins?|satoshi|usdc)\b；all = core 或 \b(crypto|blockchain|defi|web3|nfts?)\b（排除 cryptograph）。x_h = UTC 小时 h 内匹配帖子数。
- 信号：S_t = Σ x（t−L+1..t）；μ、sd = L 窗口之前 720 小时的小时均值/标准差（≥360 有效，sd 下限 1/√720）；z = (S_t − Lμ)/(sd√L)；z 首次上穿 k 时触发。入场 t+1 开盘。follow/fade：方向 = ± 同期 L 小时等权篮子收益符号（OKX d8 篮子用于 okx_d8/new8，Gate 用 gate_d8）；long/short = 无条件方向。H 小时后开盘出场，不重叠。
- 网格：series {core, all} × L {6, 24} × k {3, 5} × {follow, fade, long, short} × H {12, 24, 48} = 96 格，看 PnL 前锁定（scratch/hncrypto1h/PRE_REGISTER.json，sha256 9a323436eca68998727f8fa442fdd6aca07bb39370be9a9cd40dcdf9016e309f）。先验 core_L24_k3_fade_H24；回退 all_L24_k3_fade_H48。
- 验证：OKX d8（BTC ETH BNB SOL XRP ADA DOGE AVAX）、untuned OKX new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）、Gate d8；train（deep 未见，2022-01-29→2024-10-21）、test（→2026-03-05）、post（→）、gate_window（≥2025-09-24）。真实 taker 5.1 bps/边 + 官方资金费，压力 15.1 bps；安慰剂：信号 ±168h / ±720h 平移、随机同小时日（先验/回退 1000 次，其余 200 次）。usable = 8 个槽位均值全 >0 且 n(OKX train/test/post) ≥ 10/6/4。

## 结果（真实费率，单位 bps/笔）
| 单元 | 槽位为正 | OKX train / test / post | new8 train / test / post | Gate post / gate_window | 随机日安慰剂分位 test / post |
|---|---|---|---|---|---|
| 先验 core_L24_k3_fade_H24 | 7/8（不可用） | +50.7 (55) / −7.3 (23) / +13.9 (12) | +74.0 / +6.5 / +66.3 | +14.2 / +7.3 | 51 / 64 |
| 回退 all_L24_k3_fade_H48 | 3/8 左右（不可用） | −15.9 (44) / −84.8 (21) / +104.1 (12) | −49.8 / −75.5 / +67.8 | +104.0 / +32.2 | — |
| 唯一 usable 8/8 非先验 all_L24_k3_fade_H12 | 8/8 | +46.0 (57) / +47.7 (31) / +2.3 (16) | +30.9 / +56.5 / +4.3 | +34.0 / +7.5 | 86 / 64.5（Gate 83.5） |

- 96 格中只有 1 格 usable（随机水平）。先验 test 为负、随机日安慰剂分位仅 51/64；post 月份 OKX、Gate 各 4 正（2026-11 −386 bps）；压力费下 test/post 均为负。
- 回退 deep 未见 train 与 test 均为负，post 正值只来自 12 笔。
- 唯一 usable 非先验格 post 仅 +2.3 bps（16 笔），安慰剂 post 分位 64.5 < 80，达不到弱观察标准。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例。
- 勿重测：勿以改 L / k / H / 方向、换 core ↔ all 关键词集、加入点数/评论/首页排名、换 Reddit / Lobsters / 其他社区投稿计数，或改成 4h 入场闸门来重测「社区加密投稿注意力爆发」这一族。
- 输出：output/research_hn_crypto_attention_burst_event_1h.csv、output/hn_crypto_stories_official_1h.csv（本机，不推送）；脚本 scratch/hncrypto1h/{fetch,build,prereg,run,analyze}.py。
