# 短线新族：SEC EDGAR 官方「单币加密 ETF / 信托首次 S-1 注册」受理时刻 → 点名币永续 / 8 币永续篮子（1h）

> 侧记（2026-11-22 ~03:30 PST）。研究，不改默认；**否决**。

- 原计划（矿池 coinbase / 出块奖励地址转出 1h 突发）放弃：mempool.space 地址分页约 2.5 s/次且间歇限流；Foundry 主地址 3.2 万笔（约 1,300 页）、F2Pool 9.3 万笔（约 3,700 页），AntPool / ViaBTC / MARA 的 coinbase 地址轮换或接口取不到，45 分钟内拿不到干净的多年小时序列；而且矿池钱包转出主要是固定时间的 PPS 例行派发，机制上接近已否决的「政府 / 托管实体地址转出」（gov_btc_outflow 已写明勿扩地址集重测）。未跑任何 PnL。
- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv（1,165 个）、记忆中无 S-1 / 19b-4 / ETF 申请 / 注册 事件测试。不同于：已否决的现货 ETF 资金流 1h（us_spot_etf_flow_shock）、IBIT 期权到期、MSTR 8-K、美股巨头 8-K 财报、EDGAR 加密提及数 4h 闸门（全文提及量的体制闸门，不是单个注册事件）、币安 / Upbit 公告（交易所公告，非监管申报）、新合约上市后漂移。
- 机制：某个币首次出现在发行商的现货 / 质押 ETF 注册书（S-1）里 = 机构需求预期；检验点名币在公开后 4–168h 是继续涨（跟随）还是利好兑现（回吐）。
- 数据（只用官方，不编造、不补数）：
  - SEC EDGAR 全文检索 efts（forms=S-1，币名 + digital asset / crypto / staking / blockchain / Trust ETF，2013→2026-11-22），实体名含 Trust / ETF / Fund；每个 CIK 从 data.sec.gov submissions（含分页文件）取**首次**表格类型为「S-1」的申报及其 `acceptanceDateTime`。币种按锁定的正则从 EDGAR 当前实体名识别；指数 / 多币 / 期货 / 收益增强 / 杠杆 / 商品等按名剔除。118 个 CIK → 88 个单币事件（2019-01 → 2026-11-17），交易窗口内（2022-02-15 起）83 个，33 个币；train 15 / test 61 / post 7。表 `output/edgar_crypto_trust_s1_events_official.csv`。
  - 公开时刻：受理时间在周一至周五 06:00–17:30 ET 内即用；否则按 EDGAR 发布规则顺延到下一个工作日 06:00 ET（12 个事件顺延；美国联邦假日未处理，已注明）。
  - 价格：OKX 官方 1h USDT 永续（d8 与 new8 用本地官方序列；其他币用 OKX `history-candles` 现拉，2022 起；AXL、MOG 无 OKX 永续 → 只进篮子格）；Gate 官方 1h 永续（d8 自 2025-09-24，其他币约自 2025-12-16，接口只给约 1 万根）。
  - 资金费：d8 + new8 用 OKX 官方深度资金费；其他币 OKX / Gate 只给 3–6 个月历史 → 记 0（已标注，偏乐观）。
- 公式：事件小时 h = floor(公开时刻)；h+2 根 1h 开盘吃单入场，持有 H 根后开盘平；同币同格不重叠（篮子格全局不重叠）。named = 点名币永续；basket = d8 等权；hedged = 点名币 − 篮子（四边费用）。成本 taker 5.1 bps/边（压力 15.1）+ 资金费。
- 预注册（`PRE_REGISTER.json`，sha256 `a01805fe…1c139`，任何 PnL 前锁定 60 格）：事件集 {all, firstcoin（该币全市场首个 S-1）} × 标的 {named, basket, hedged} × {long, short} × H {4,12,24,72,168}。先验 `all_named_long_H24`，回退 `firstcoin_named_long_H24`。切分 train 2022-02-15→2024-10-21（深度未见）、test →2026-03-05、post →今；8 项检查：train/test/post 均值 >0、post 压力费 >0、Gate >0、post 好于 ±720h 安慰剂、全期随机小时分位 ≥0.90、post 正月份多于同币逐时基线。
- 结果（真实费，每笔净 bps；`output/research_edgar_crypto_etf_s1_event_1h.csv` 2,188 行，汇总 `_summary.csv`）：

| 格 | train | test | post | Gate 全期 | ±720h 安慰剂 post | 随机分位(全期) | 得分 |
|---|---|---|---|---|---|---|---|
| **先验** all_named_long_H24 | −141.1（n15，t −1.67） | −4.1（n57） | −1.0（n7） | +119.8（n19） | +29.1 / +103.9（安慰剂更好） | 0.30 | 2/8 |
| **回退** firstcoin_named_long_H24 | −439.5（n3） | −16.1（n21） | +90.7（n4，t 0.50） | +322.9（n7） | −8.5 / +130.2 | 0.31 | 3/8 |
| 邻域 all_named_long_H12 / H72 | −66.0 / −52.1 | +6.4 / +48.8 | −59.0 / −250.1 | | | | 3 / 3 |
| all_hedged_long_H24 | −90.3 | −41.7 | +87.3 | +72.3 | | 0.30 | 4/8 |
| all_basket_long_H24 | −71.1 | +4.1 | −108.7 | | | | — |

  - d8 子集（先验）：train −166.3（n14，t −1.91）、test +13.9（n30）、post 无事件；非 d8 子集 test −24.1、post −1.0。
  - 全 60 格：没有 7/8 或 8/8；最高 6/8 的 5 格（如 all_basket_short_H24：train +50.7 / test −24.5 / post +88.3 t 1.23；all_named_short_H4：test −61.6）都在 test 段反向，非先验，不可晋升。
  - Gate 窗口为正主要来自 2025-09 以后少数小币（n=12，t 1.45），OKX 同期不一致；post 只有 7 个事件且全是 d8 以外的币。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例、无代码改动，仅文档。现货 ETF 注册书公开后点名币没有稳定的跟随或回吐：深度未见段做多显著为负（利好多已在 Bloomberg 报道 / 特拉华信托登记时被提前交易），test 接近 0，post 样本太小，安慰剂更好。勿以同一机制换 H / 方向 / 对冲、换成 S-1/A 修订稿、19b-4、N-1A、8-A、生效通知（EFFECT）或 ETF 上市首日、换入场延迟、换币集合或改用特拉华信托登记日再测。
- 局限：EDGAR 全文检索可能漏掉少数实体（例如 Franklin EZBC 名字不含币名被规则剔除）；非 d8 币资金费记 0；post 样本小。
- 文件：`output/research_edgar_crypto_etf_s1_event_1h.csv`、`output/research_edgar_crypto_etf_s1_event_1h_summary.csv`、`output/edgar_crypto_trust_s1_events_official.csv`；脚本 scratch/cryptoetfs1/{fetch_efts,fetch_efts2,cand,events,fetch_px,fetch_gate,run,analyze}.py、PRE_REGISTER.json（研究脚本未推送）。
- 下一轮（长线）：日本财务省（MoF）官方每周「对外及对内证券买卖」（International Transactions in Securities，周四 08:50 JST 发布，2005 起）—— 日本居民净买外债 / 外股、非居民净买日股的 4 周趋势或极值 → 4h 默认书入场闸门（日元套息资金流）。docs / output 中 0 条（JGB 收益率闸门已否决，是利率不是资金流）；按发布时刻 + 1 根 4h 滞后，不补数据。
