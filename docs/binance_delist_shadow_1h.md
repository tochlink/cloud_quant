# 影子子账本 #15：币安官方现货下架公告做空（短线 1h，纸面前向检验）

> 2026-11-21 PST。研究结论是「弱观察」（docs/STRATEGY_FORMULAS.md「短线新族：币安官方下架 / 上币公告」，
> output/research_binance_announcement_listing_delisting_event_1h.csv）。按 kean 要求「自己做的策略也要做交易」，
> 现在把事先登记的 prior 格 `spot_delist_short_H24_none` 做成真实纸面影子子账本，用实时官方数据前向验证。
> **只记录，不下任何真实 / 交易所模拟单，不计入主账本，不改默认参数。**

## 代码与开关

* 代码：`qtw/delist_shadow.py`（sid `binance_delist_short_1h`，编号 #15）；`qtw/app.py` 启动时调用 `delist_shadow.start()`，
  状态接口 `GET /api/shadow/delist`。
* 默认关闭（可选策略）：只有进程环境变量 `QTW_SHADOW_DELIST=1` 才启动轮询线程。本机只在 8788 paper-default 的 run.sh 里打开；
  测试 / 安全模式（`QTW_FORBID_LIVE=1`）永远不启动、不联网。
* 账本：SQLite 表 `shadow_books`（与 #13 / #14 同一结构，存在 data/，不入库），起始 1000U。

## 公式

1. **信号源**：币安官方 CMS 公告列表 `https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=20`
   （catalog 161 = Delisting），每 300 秒轮询一次；时间戳用公告 `releaseDate`（毫秒）。
2. **标题解析**（与研究脚本 parse.py 的 spot_delist 完全一致）：标题匹配 `^Binance Will Delist `，且不含 `Margin` / `Futures`；
   去掉 ` on YYYY-MM-DD…` 尾巴后按 `,` / ` and ` / `&` 切分；只留 2–12 位字母数字代码；去掉 `1000000 / 1000 / 1M` 前缀；
   去掉 USDT、USDC、BUSD、BTC、ETH、BNB、FDUSD、TRY、EUR、USD、USDS 等计价 / 停用词。
3. **可交易判定**：先看 OKX（纸面账本主场所）`<币>-USDT-SWAP` 是否 `state=live` 且 `listTime ≤ releaseDate − 24h`；
   否则看 Gate `<币>_USDT` USDT 永续是否 `trading`、不在下架流程中、`create_time ≤ releaseDate − 24h`。都没有 → 记日志跳过。
4. **入场**：`releaseDate + 60s` 之后的第一次轮询，按该场所官方实时标记价开**空**；记录实际入场延迟（秒，相对 releaseDate）。
   发现时已晚于发布 2 小时（重启 / 首次启动看到的旧公告）不补开（研究里一半收益在前 1–2 小时，晚 1h 入场均值从 +577 降到 +237 bps）。
5. **仓位**：每条公告名义 = 0.2 × 当前权益，在该公告可交易的币之间等权；全部持仓名义 ≤ 1.0 × 权益（超出按剩余空间缩小）；
   同一币已有持仓不重复开。
6. **离场**：开仓满 24 小时后的第一次检查（每 60 秒检查一次），按同一场所官方实时标记价平仓；取价失败下次再试。
7. **费用**：taker 5.1 bps / 边（开、平各一次）；资金费不计（与 #13 / #14 影子一致；研究里近 180 天事件币资金费对空单影响很小，见原研究节）。

## 日志格式

开仓按 kean 的格式：第一行「时间 影子子账本 binance_delist_short_1h（#15，不计入主账本） 开仓」，下面每个币一行：币种 / 方向 / 金额(U) / 开仓价；
再附一行场所与入场延迟。平仓表：币种 / 方向 / 开仓价 / 平仓价 / 盈亏(U)。

## 回测预期（对照用）

Gate prior `spot_delist_short_H24_none`：train +523 bps/事件（n=10）、test +683（n=11）、2026-03-05 后 +509（n=9，t 0.98）、全样本 +577（n=30，t 2.03）。
公告频率约每月 0.5–1 条（2026 年 4 / 5 / 6 / 6 / 8 / 8 / 9 / 10 月各一条），所以前向证据积累很慢；
每条公告按 0.2× 权益计，回测均值（+577 bps，已扣真实费）相当于每条约 +1.15% 账本收益。

## 验收

* 测试：`tests/test_delist_shadow.py`（标题解析、等 60 秒、等权、不重复开、过时不补开、24h 平仓盈亏与费用、取价失败重试、默认关闭、日志表格），全部离线。
* 前向检验看「每条公告平均 bps」与回测 +500 bps 量级是否同号；累计 ≥ 6 条后复查。
* 独立记录器 `scratch/bnbannounce1h/record.py`（本机，不入库）继续记录 161 / 48 两个目录的新公告，作为原始证据。
