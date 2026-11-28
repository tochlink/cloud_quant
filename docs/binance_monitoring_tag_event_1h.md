# 短线新族：币安官方「监控标签（Monitoring Tag）」新增公告 → 做空被点名币 USDT 永续（1h 事件，2026-11-28 ~01:00 PST；弱观察 → 纸面影子 #19，不改默认）

## 选题 / 查重
- 上一轮指定的 TRON 主网 USDT（TRC-20 `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`）每小时转账笔数 / 大额转账冲击 **不跑**：(1) 与已否决的 `btc_whale_transfer_burst_event_1h`（勿重测写明「其他链上数据商的同类链上转账额爆发」）、`altchain_cdd_tx_burst_event_1h`、`weth9_deposit_withdrawal_shock_event_1h`、`exchange_stablecoin_flow_event_1h`、`stablecoin_supply_shock_event_1h` 同属「链上转账 / 稳定币流量爆发」机制；(2) TronGrid / TRONSCAN 只有逐笔接口，没有 ≥2 年的官方小时汇总，USDT-TRC20 全量转账是数十亿行，本轮不可能完整拉取。
- 改测：docs/STRATEGY_FORMULAS.md、docs/*.md、`output/research_*.csv`、scratch 目录名与记忆中检索 monitoring tag / seed tag / 监控标签 / 种子标签：0 条测试。相近但不同：币安下架 / 上币公告（#15 影子，勿重测只禁「换别家交易所公告重测下架 / 上币」）、Upbit 投资警告（勿重测只禁 Bithumb / Coinone 等韩国交易所）、Upbit 充提暂停。监控标签是币安自己对高风险小币的季度 / 月度风险标记（下架前的公开观察名单），事件与下架公告不同（下架是另一条公告）。

## 数据（全部官方，不编造、不回补）
- 信号：币安官方 CMS 公告列表接口 `bapi/composite/v1/public/cms/article/list/query`，catalog 49（Latest Binance News，4,530 篇）+ 161（Delisting，447 篇）；标题含 Monitoring / Seed Tag 的 29 篇（2023-07-26 介绍文 + 28 篇事件，2023-10-04 → 2026-11-20）。时间戳 = `releaseDate`（毫秒）。标题正则解析 `scratch/bnbmontag1h/parse.py`：mt_add 147 币次（27 篇）、mt_remove 8、seed_remove 29。
- 价格：Gate 官方 USDT 永续 1h（批量下载 `download.gatedata.org/futures_usdt/candlesticks_1h`，含已下架合约；2026-11 用官方 API）；OKX 官方 `history-candles` 1h（只有现存合约，被打标签的小币多已下架 → OKX 样本小）。资金费只在近 180 天官方窗口计入。

## 公式
- 入场 = `releaseDate + 60s` 之后第一根 1h 开盘（taker）；该币须在公告前 ≥24h 已有永续 K 线、公告后 2h 内有成交。持有 H 根后开盘平（合约中途停则用最后收盘）。同一公告多币等权合成 1 个事件；同币持仓未平不重复开。hedge=btc：同所反向等名义 BTC 永续（两腿都收费）。
- 费用：taker 5.1 bps / 边（真实），压力 15.1 bps / 边。

## 预注册（PRE_REGISTER.json，任何价格 / PnL 前锁定，2026-11-28 00:47 PST，sha256 `9b9424b0dfb5739b283c6ea22f86cda46c7e0ccfea5f533bab3115f6c8f9c4ba`）
- 48 格：event_type {mt_add, mt_remove, seed_remove} × {long, short} × H {4, 12, 24, 48} × hedge {none, btc}。
- 先验 `mt_add_short_H24_none`（监控标签 = 币安公开的下架前观察名单，持有人去风险）；回退 `mt_add_short_H48_btc`。
- 切分：deep 未见 2023-10 → 2024-10-21、test → 2026-03-05、post → 2026-11-28。安慰剂：同币时移 ±168h / ±720h；邻域 H、入场再晚 1h。new8 不适用（单币事件）。
- 强观察：Gate 三段 > 0、压力 post > 0、post t ≥ 1.5、post 月份 ≥5/9、OKX test 与 post（n≥3）> 0、post 胜过 4 个时移、晚 1h post > 0。弱观察：Gate 三段 > 0 且 OKX post > 0，但未满足其余条件。

## 结果（真实费，每事件净 bps；`output/research_binance_monitoring_tag_event_1h.csv` 2,688 行）
- **先验 `mt_add_short_H24_none`**：
  - Gate：deep **+410**（n=4 事件 / 15 币次，t 2.4）/ test **+649**（n=9，t 2.1）/ post **+255**（n=12 / 49 币次，t 2.38，中位 +363，胜率 67%）；全样本 +421（n=25，t 3.3）。压力费 post +235。post 月份 5/9。
  - OKX（只剩现存合约）：deep +611（n=1）/ test **−398（n=3）** / post **+503**（n=7，t 2.88，月份 6/9）。
  - 安慰剂（Gate post）：+168h −378、−168h +78、+720h +42、−720h −14 → 真实 +255 胜过全部 4 个时移。
  - 入场再晚 1h：Gate post 只剩 **+11**（OKX post +294）→ 大部分边际在公告后第 1 小时内（与 #15 下架公告同样的延迟敏感）。
  - 邻域：H4 Gate +196 / +258 / +115（OKX +130 / +236 / +60，5/5 正）；H12 +267 / +424 / +185（OKX test −300）；H48 post 翻负（−178）。BTC 对冲版 H24 post 降到 +73（t 0.9）→ 部分边际是 2026 年小币整体下跌的 beta。
  - 逐事件（Gate，bps）：2026-03 起 +546 / +397 / +531 / +361 / +598 / −3 / −387 / +365 / +19 / −111 / −130 / +869；2026-06 → 10 月明显转弱。
- **回退 `mt_add_short_H48_btc`**：Gate deep +766 / test +978 / post **−268**（t −0.8）→ 失败。
- 全网格：Gate 三段全正 6 格（全是 mt_add short），但时移 +720h 安慰剂网格也有 12 格三段全正 → 网格层面「被打标签小币本来就阴跌」解释了一部分，只有先验格在 post 胜过它自己的四个时移。mt_remove / seed_remove 样本 ≤10，方向不稳。

## 结论
- **弱观察（未达强观察）**：先验 Gate 三段全正、post t 2.38、压力费仍正、胜过全部时移，但 (1) OKX test 为负（n=3，存续偏差），(2) post 月份刚好 5/9、2026-06 起转弱，(3) 晚 1h 入场 Gate post 只剩 +11 bps，(4) 被点名小币点差 / 滑点可能远大于 5.1 bps，容量小。每笔边际结构上大（数百 bps）、交易很稀（约每月 1 条公告），符合短线「少交易、大边际」的要求，值得前向检验。
- 不改默认参数。已加纸面影子子账本 **#19 `binance_montag_short_1h`**（`qtw/montag_shadow.py`，默认关；只在 8788 paper-default 以 `QTW_SHADOW_MONTAG=1` 打开；状态 `GET /api/shadow/montag`）：每 300 秒轮询 catalog 49 + 161，新增监控标签公告在 releaseDate+60s 后的首次轮询按 OKX（优先）/ Gate 官方实时价开空，每条公告 0.2×权益在可交易币间等权，持 24h 平仓，taker 5.1 bps / 边，晚于发布 2h 不补开（2026-11-20 那条已正确记为过时）。测试 `tests/test_montag_shadow.py`（含与研究 parse.py 在全部 28 篇官方标题上逐条一致的检查），全套 554 passed。
- 前向复核：累计 ≥6 条新公告后看每条平均 bps 是否与回测 +255 bps（post）同号同量级；若 OKX / Gate 实时成交价因点差明显差于 1h 开盘，则否决。

## 勿重测（never retest by）
不要通过改 H / 侧 / 对冲、改入场延迟（含 15m / 5m 入场）、换 mt_remove / seed_remove / 介绍文、把监控标签与下架公告合并、换币篮子或改成 4h 闸门在现有历史上重测本族；不要用其他交易所的风险标签（OKX / Bybit / Bitget「风险提示」类）换源重测同一机制。只能用 #19 的前向官方数据复核先验格。

## 文件
- `output/research_binance_monitoring_tag_event_1h.csv`（不入库）；脚本与数据 `scratch/bnbmontag1h/{fetch_ann,parse,fetch_px,fetch_fund,run}.py`、`binance_announcements_official.csv`、`events_parsed.csv`、`PRE_REGISTER.json(.sha256)`、`INPUTS.sha256`（研究脚本未推送）。
- 代码：`qtw/montag_shadow.py`、`qtw/app.py`（启动 / 停止 / 状态接口）、`tests/test_montag_shadow.py`。

## 下一轮（长线）
ICI 官方周度长期共同基金 / ETF 资金流估计（Estimated Long-Term Mutual Fund Flows 中的美股权益类净流入）趋势 / z → 4h 默认书入场闸门（散户权益资金追涨 → 拦新多）。先查重：`mmf_h8_cash_gate_4h` 勿重测只禁货币基金（ICI 20 周快照 / OFR MMF），`finra_margin_debt`、`us_spot_etf_flow` 已测；需确认 ici.org 官方周度历史可完整下载，否则换题。
