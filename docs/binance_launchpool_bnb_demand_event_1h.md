# 短线新族：币安官方 Launchpool / Megadrop / Launchpad 公告 → BNB 永续（BNB 锁仓需求，1h，2026-11-27 ~18:50 PST，研究，不改默认；否决）

- 查重：在 `docs/STRATEGY_FORMULAS.md`（含轮换日志）、`docs/*.md`、`output/research_*.csv`（约 1,370 个）和 scratch 目录名里搜 `Launchpool / Launchpad / Megadrop / HODLer / launchpool`：**0 条**。相邻但不同的已否决族：`binance_announcement_listing_delisting_event_1h`（交易的是被上 / 下架的币本身）、`exchange_token_shock_event_1h`（OKB/GT 相对 BTC 的价格冲击 → 8 币篮子）、`token_unlock_event_1h`（解锁抛压）、`newlist_perp_own_drift`（新永续自身漂移）。本族交易的是 **BNB 本身**，机制是：要参加挖矿 / 认购，就必须锁仓或持有 BNB。
- 本轮先否掉的候选：THORChain 跨链兑换流（Midgard 官方节点在本机连不上）；财政部季度再融资 QRA（`us_treasury_auction_demand_gate_4h` 的勿重测已禁止）；BoJ 议息（`ecb_boe` 条款禁止）；SEC / CFTC 新闻稿（DOJ 条款禁止）；FVG 回补限价单（与已否决的斐波回撤限价同属回撤挂单）。
- 数据（只用官方数据，不编造、不回补）：
  - 事件：币安官方 CMS 公告列表 API（`www.binance.com/bapi/composite/v1/public/cms/article/list/query`，catalog 48 / 49 / 93 / 128），共 10,156 篇，releaseDate 精确到毫秒。标题规则写在 `events.py` 里，在看任何 PnL 之前就定好了：
    - `lpool`：以 Introducing 开头，且含 Launchpool 或 Megadrop。共 72 条，2020-09-06 → 2026-03-02。
    - `lpad`：Launchpad 代币销售介绍，或 “Using the Launchpad Subscription Format”。共 32 条，2019-03 → 2023-07。
    - `fwd` = lpool + lpad，共 104 条。
    - 机制安慰剂 `hodl`：HODLer Airdrops 介绍，按**回溯快照**发放，没有前向锁仓需求。共 65 条，2024-07 → 2026-06。
    - 非 BNB 需求安慰剂 `list`：标题以 “Binance Will List” 开头，共 248 条。
  - 交易腿：
    - OKX 官方 BNB-USDT-SWAP 1h（2022-12-23 OKX 上线起）和 OKX d8 篮子。
    - Gate 官方 BNB_USDT 永续 1h：download.gatedata.org 月度批量包（2020-01 起）+ api.gateio.ws。BNB 在 2020 年低量时段批量包缺 2,403 根小时，没有补；入场或出场那根缺失的事件直接跳过。
    - 资金费：两所官方资金费都计入。
- 公式：入场 = 公告 releaseDate + 60 秒之后第一根完整 1h 的开盘价；持有 H 根后按开盘平仓；同一格内事件不重叠。
  - raw = 只做 BNB 永续。
  - hedged = BNB 对等名义做空其余 7 币（BTC ETH SOL XRP ADA DOGE AVAX）等权篮子。两条腿都付手续费和资金费，往返共 4×5.1 bps。
  - 费用：taker 5.1 bps / 边 / 腿，压力测试 15.1 bps。
- 预注册：在任何 PnL 之前锁定 `PRE_REGISTER.json`，64 格，sha256 302749f3。
  - 网格：集合 {fwd, lpool, hodl, list} × {hedged, raw} × H {6, 12, 24, 48} × {long, short}。
  - 先验 `fwd_hedged_H24_long`，回退 `fwd_raw_H24_long`。
  - 切分：Gate pre_okx 2020-01 → 2022-12-23（完全未见）；deep → 2024-10-21；test → 2026-03-05；post → 今。
  - 安慰剂：时间平移 ±72h / ±168h；同数量随机小时（先验 / 回退各 1,000 次，其余格 200 次）；hodl / list 两个集合；同脚本基线（每天 09:00 UTC 无条件做多）；邻域为入场延迟 1h / 2h。

## 结果（`output/research_binance_launchpool_bnb_demand_event_1h.csv`，3,164 行；实费下每笔净 bps，括号内为事件数，rnd = 随机小时安慰剂分位）

| 格子 | OKX deep（2022-12→2024-10） | OKX test | Gate pre_okx（2020→2022-12，未见） | Gate deep | Gate test | post（2026-03-05→） |
|---|---|---|---|---|---|---|
| 先验 fwd_hedged_H24_long | **+111.0（31，t2.47，rnd 99.9）** | −15.8（14，rnd 54） | **−58.8（42，rnd 27）** | +12.2（73） | −17.0（14） | 无事件 |
| 回退 fwd_raw_H24_long | +66.0（31，t1.32） | +0.2（14，rnd 54） | +174.4（46，t1.59，rnd 95） | +129.1（77，t1.89，rnd 98） | −1.7（14） | 无事件 |
| 非先验 fwd_raw_H12_long（5/5） | +3.8（32） | +51.9（14，t0.99，rnd 86） | +115.2（45，t2.81，rnd 99.5） | +66.2（77，t2.34） | +49.6（14） | 无事件 |
| 机制安慰剂 hodl_raw_H24_long | 1 条 | −16.4（55） | — | — | −16.5（55） | +89.6（6，t0.74） |
| 安慰剂 list_raw_H24_long | −54.0（37） | +7.8（26） | +12.7（107） | −4.4（144） | +8.2（26） | −113.2（14） |
| 基线 每天 09:00 无条件做多 BNB H24 | +7.5 | −4.7 | +31.1 | +21.5 | −4.8 | −14.7 |

- **先验（BNB 相对 7 币对冲）**：只有 OKX 那段 2023–2024 成立（+111 bps，随机安慰剂分位 99.9）。到了完全未见的 2020–2022 Gate 段变成 −58.8，test 段 −15.8 / −17.0。−168h / −72h 平移安慰剂在 deep 段为负，说明那段效应是真实存在的，但不跨时期。→ 不成立。
- **回退（只做 BNB）**：2020–2024 两所 deep 段都为正（+174 / +129 bps，随机分位 95 / 98，压力费下仍有 +154 / +109），且远高于同期无条件做多基线（+31 / +21）。但 test 段（2024-10 → 2026-03，14 笔）≈ 0、随机分位 54，而 +168h 平移在 test 段得到 +134，比真实值更好。→ 2024 年底之后边际消失。
- **post 段没有任何前向事件**：币安 2025 年起基本用 HODLer Airdrops（回溯快照）取代了 Launchpool。2026 年只有 1 次 Launchpool（OPN，2026-03-02，在切分点之前）。机制本身在消失，即使历史成立，也几乎没有可交易的事件。
- 机制安慰剂符合预期：hodl（回溯快照）test −16 bps；list 普遍为负或接近 0。说明 2020–2024 的效应确实和前向锁 BNB 有关，只是已经失效。
- 非先验 fwd_raw_H12_long 是 64 格里唯一有 5 个可用槽全正的格，但它是看过结果后挑出来的：OKX deep 只有 +3.8，test t<1，+168h 平移在 test 段得 +95 > 真实值，post 无事件 → 不晋升。

## 结论
**否决**。不实现、不进观察名单、不改默认、不动纸面实例、无代码改动。该效应是 2020–2024 币安 Launchpool 时代的结构性 BNB 锁仓需求；2024-10 之后不复现，2026 年几乎没有事件。

## 勿重测（never retest by…）
不要通过以下方式重测本族：
- 改 H、入场延迟、方向，或在 raw / BTC 对冲 / 篮子对冲之间换口径；
- 在 Launchpool / Megadrop / Launchpad / HODLer Airdrops / Launchpool 结束 / 认购开始 / 分发完成这些公告之间互换，或改用挖矿开始 / 结束时刻；
- 换成其他平台币的同类活动（OKX Jumpstart → OKB、Gate Startup → GT、Bybit Launchpool → MNT、Bitget Launchpad → BGB）；
- 改用 BNB 现货，或改用 BNB / BTC 比值。

只有当币安重新恢复前向锁仓式 Launchpool、并在 2026-03 之后积累 ≥10 个新事件时，才可以按原预注册（sha 302749f3）做一次前向复核。

## 文件
- `output/research_binance_launchpool_bnb_demand_event_1h.csv`（不入库）
- `scratch/bnblpool1h/`：fetch_ann.py、fetch_gate.py、events.py、events_official.csv、binance_announcements_official.csv、prereg.py、PRE_REGISTER.json(.sha256)、run.py、run.log、analyze.py、analyze.log、analyze_wide.csv、events_real.csv、px/

## 下一轮（长线 4h）
国家外汇管理局（SAFE）官方月度「官方储备资产」中的黄金储备（万盎司）：用中国央行增持 / 暂停增持黄金的 n 月变化或连续增持月数，作为 4h 默认书入场闸门。每月 7 日公布，次日 00:00 UTC 才使用，不补数据。需要先核对 `fed_custody_gate_4h`、`snb_sight_deposits_gate_4h`、`gld_gold_etf_holdings_gate_4h` 的勿重测范围。
