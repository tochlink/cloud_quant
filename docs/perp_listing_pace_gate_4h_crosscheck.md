# 交易所新永续上线节奏 → 4h 默认书入场闸门：独立复核（否决）

> 本文件是 docs/STRATEGY_FORMULAS.md 本地追加小节的同内容 sidecar（主节见 docs/perp_listing_pace_gate_4h.md，commit 52aa5944；不覆盖远端 STRATEGY_FORMULAS.md）。

### 独立复核（同族第二套预注册，2026-11-21 ~02:30 PST；结论不变：否决）

- 背景：另一个执行进程同时在跑同一族（上节）。本复核用**另一套独立锁定的格子与另一种已下架合约分类方式**，只作稳健性交叉检查，不是新族；文件均带 `_k` 后缀，不覆盖上节文件。
- 数据（全部官方，`output/perp_listing_official_daily.csv`，2020-01-01 → 2026-11-20 UTC 共 2,516 天，0 缺日，不补值）：Gate 加密 USDT 永续上线事件 1,154 个（2020 年前 3 个不计入日序列 → 1,151），上线时刻 = 官方批量下载 1h 存档首根 K 线；其中 **613 个已下架 / 下架中**靠存档补回。已下架合约的类型直接用 Gate **官方单合约接口** `/futures/usdt/contracts/{name}`（对已下架合约仍返回 status / contract_type / is_pre_market），共剔除 517 个股票 / 指数 / 金属等非加密合约与盘前合约；4 个接口返回 400（TONCOIN、TRUMPOLD、U、ZKOLD）按加密计。2026-11 尚未进存档的 3 个用 API `create_time`。OKX 只有现存 289 个（2020 年起 280 个）`listTime`，**已下架 OKX 永续缺失，早年严重低估**。逐合约表 `scratch/perplisting4h_k/listing_events.csv`。时滞：D 日计数 D+1 00:00 UTC 起使用。
- 公式（`scratch/perplisting4h_k/PRE_REGISTER.md + .csv` 合并 sha256 41d8def8…，看 PnL 前锁定 180 格）：cw = 滚动 W 天新上线数（W = 30 / 60 / 90）；序列 gate / okx / comb(=gate+okx)；形式 sma365（cw > 365 天均值）、z1 / z2（365 天滚动 z > 1 / 2）、q80（cw > 过去 730 天 80 分位）；侧 long_off / short_off / both / contra_both / cap_short_off。先验 `gate_w60_z1_long_off`，回退 `comb_w90_q80_long_off`。harness 同上节（finramargin4h 框架，同脚本基线、9 格 Sharpe、真实费 + 压力费、官方资金费、post 2026-03-05 切分）。
- 结果（`output/research_perp_listing_pace_gate_4h_k.csv` 645 行、`_k_new8.csv`）：基线 post OKX +59.90% / 2.23、Gate +60.32% / 2.25；deep Sharpe 0.71 / 0.09 / 0.75，tune 1.47 / 1.46 / 1.56。
  - **先验 9/9 但边际很薄**：post OKX +62.02% / 2.36、Gate +62.63% / 2.38（+2.1 / +2.3 pp），但 post 只有 3 个月与基线不同，**逐月 1 好 / 2 坏**（远低于 ≥6/9）；deep 0.87 / 0.20 / 0.82，tune 1.55 / 1.53 / 1.63；压力费同号（post 58.46% / 2.26 vs 55.94% / 2.12）。
  - 安慰剂：+7d 6/9（deep / tune 几乎同真实，post = 基线）、−7d 6/9（post 更差 55.89%）、−180d 6/9；±120d / +180d / +365d 3/9 → deep / tune 增益大半是慢变的山寨周期本身，真实信号只在 post 多拦了一两笔。
  - 邻域断崖：W45 / z0.5 post 都变差（55.89% / 2.21），W75 / z1.5 / L730 post = 基线（6/9），W120 4/9、z2.5 3/9。
  - 回退 6/9，post 完全不触发（= 基线）。全网格另有 `gate_w60_z1_both` 9/9 但 post 收益只剩 +40.9%（Sharpe 高、收益腰斩，逐月 6/3），非先验侧、不可用。
  - 未调参 new8：先验 **pre Sharpe 大幅变差**（OKX 0.92 vs 1.21、Gate 0.90 vs 1.19），post 略好（0.45 vs 0.28、1.15 vs 1.00，逐月 3/0）；+7d 安慰剂 post 同样略好且 pre 更好 → 无特异性。
- 结论：**否决（复核一致）**。两套独立预注册都达不到「post ≥ 6/9 月两所都更好 + 未见历史成立 + 邻域 / 安慰剂支持」的门槛。不实现、不改默认、无代码改动。上节的禁止重测清单同样适用（含改用 60 天窗口、comb 合并序列、q 分位、官方单合约接口分类等任何变体）。
- 下一轮（短线，1h，持有数小时–2 天）：**Upbit 官方「거래 유의 종목 지정」（投资警告 / 交易注意指定）公告 → 被点名币在 Gate / OKX 的 USDT 永续做空**。Upbit 官方公告接口 `api-manager.upbit.com/api/v1/announcements?category=trade`（约 818 篇，`first_listed_at` 精确到秒）可取全部历史；韩国散户在警告指定后集中抛售、之后常被终止交易支持，单笔结构性边际大（预期数百 bps）。查重：docs / output / 记忆中 Upbit 只做过韩国溢价短线与韩国成交占比闸门（都否决，与公告无关）；币安下架公告为弱观察（不同交易所、不同事件：Upbit 指定发生在下架决定之前）。须预注册：事件类型（指定 / 指定延长 / 解除 / 终止支持）× 方向 × H 4/12/24/48 × BTC 对冲；Gate 存档含已下架合约，OKX 只用现存 + 逐笔归档复核；入场延迟 +1h 邻域；点差 / 滑点与容量单列。
