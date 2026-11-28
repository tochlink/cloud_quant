# 短线新族：USGS 官方全球强震（M≥6.5 / PAGER 橙红预警）1h 事件 → 8 币永续篮子（2026-11-27 ~20:00 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、`output/research_*.csv`（1,380 个）、`scratch/ROTATION_LOCK.txt` 对 earthquake / 地震 / USGS 无策略条目（仅 geomagnetic Kp 4h 闸门的查重行提到「地震」无相关条目）。机制与已否决的 geomagnetic / ERCOT 电价 / 天气 / 交易所事故均不同：自然灾害巨灾冲击 → 风险偏好。（未调用记忆检索工具，查重靠本地文件。）
- 数据（官方，未插值）：USGS FDSN event service `earthquake.usgs.gov/fdsnws/event/1/query`（geojson，M≥6.0，2019-01-01→2026-11，type=earthquake）共 1,074 次；M≥6.5 317 次、M≥7.0 107 次、PAGER 黄/橙/红 136 次、橙/红 53 次。每年 M6.5+ 28–53 次。官方表 `output/usgs_quakes_official.csv`。价格：OKX d8 1h 永续 2022-01-29 07:00→2026-11-27 19:00 UTC（42,325 根）、OKX 未调参 new8、Gate d8 1h 2025-09-24→（10,308 根），官方资金费。
- 公式：事件时间=震源时间，可用=+60min（保守；PAGER 级别可能事后更新，属轻微前视，已标注），下一整点 open 入场、H 根后 open 出场；8 币等权篮子；重叠事件跳过；taker 5.1 bps/边（压力 15.1）+官方资金费。
- 预注册 48 格（sha256 fa32eeee1ed383cc…b3307，PnL 前锁定）：集合 mag65/mag70/pager_yellow/pager_orange × 深度 any/shallow(<70km) × 做空/做多 × H 4/24/48。先验 pager_orange_any_short_H24；回退 mag70_shallow_short_H24。切分 train(深未见)<2024-10-21、test→2026-03-05、post 之后。
- 结果（`output/research_usgs_earthquake_event_1h.csv`，3,168 行）：
  - 先验 pager_orange_any_short_H24：OKX train −60.8 bps(n14) / test +185.2(n10) / post +29.0(n8, t0.5)；Gate post +29.1；压力费 post +9.0；随机时点 placebo 分位 train 36 / test 96 / post 66；−168h 时移 post +85 > 真实，月不足。→ 失败。
  - 回退 mag70_shallow_short_H24：train −165.2(n22) test +52.1 post +11.1 → 失败。
  - 唯二 8/8 可用格均为非先验：pager_orange_any/shallow_short_H48（同一批事件）：OKX train +8.2(n14,t0.1,placebo 58) / test +243.6(n10,t1.3,placebo 95.5) / post +77.1(n8,t0.9,placebo 72.5)；Gate post +76.8；new8 train +36.9/test +268.6/post +84.2；压力费 post +57；post 有交易月 4 个 3 正（06 +5.7%、07 −1.7%、08 +1.6%、10 +0.5%）；+24h/−24h 时移 post +128/+72 ≥ 真实 +77，邻域 H24 post +29/H4 +30 但 train H24 −61。post t<1，n=8，收益由个别事件主导（2025-11-02 +14.4%），非稳健。
  - 全部 48 格：mag65/mag70 集合（样本较大）post 均值 −22…+82 bps、t 最大 1.3（mag65_shallow_short_H48 train −113/test −114/post +82，方向不一致）；做多方向 post 多为负。基线（M6.5+ 全部事件）无稳定方向。
- 结论：**否决**。无观察、无纸面、无代码改动。
- 勿重测：不得通过改阈值（M / PAGER / 深度）、持有时长、方向、震中区域（日本/智利/印尼等）、海啸标志、余震过滤，或换成 USGS 其它灾害（火山/滑坡）、GFZ/EMSC 目录再测同一机制。
