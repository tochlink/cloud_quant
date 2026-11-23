# 长线新族：美国国债附息拍卖需求体制（bid-to-cover / 间接投标占比 / 一级交易商承接占比）→ 4h 默认书 #1 入场闸门（2026-11-23 ~03:07–03:25 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`/workspace/scratch` 检索 auction / 拍卖 / bid-to-cover / indirect / TreasuryDirect：只有短线 1h 事件 `docs/us_treasury_auction_event_1h.md`（10Y/30Y 单次拍卖 z 冲击 → 篮子持有 4–48h，已否决；其勿重测条款只覆盖 1h 事件的 N / k / H / 方向 / 指标 / 期限 / 入场小时，未提 4h 闸门）和 `us_debt_issuance_gate_4h`（发行量 / 债务上限，不是需求）。从未把「滚动拍卖需求体制」做成 4h 入场闸门。不是 TGA / 逆回购 / 净流动性（联储净流动性族已否决）、不是 CFTC COT、不是收益率 / 期限溢价 / 利率波动。
- 机制：近期国债附息拍卖需求弱（覆盖倍数低、间接投标占比低、一级交易商被迫承接多）= 久期供给压力 / 期限溢价上行 / 美元流动性收紧 → risk-off，拦新多；需求强 → 拦新空。只拦新开仓，已有持仓、止损、离场不变。默认 4h 书 #1（MA 50/150，8 个永续）。
- 数据（只用官方，不编造、不回补）：美国财政部 Fiscal Data `v1/accounting/od/auctions_query`（928 次完整拍卖，2014-11-13 → 2026-10-08）+ TreasuryDirect `TA_WS/securities/auctioned`（Fiscal Data 尚未填完的最近 10 次，2026-10-21 → 2026-11-18）；两源重叠 466 次，bid-to-cover、竞争性中标额、间接、交易商四个字段逐笔完全一致。名义固定息 Note / Bond，原始期限 2 / 3 / 5 / 7 / 10 / 20 / 30 年，含续发；剔除 TIPS / FRN。共 938 次。官方表 `output/us_treasury_auction_demand_official.csv`（不入库）。
- 滞后：结果在拍卖日约 13:00 ET 公布；一律按次日 00:00 UTC 才可用，日度 flag 前向填充到 4h K 线。
- 公式：
  - 逐次拍卖：x ∈ {bid_to_cover, indirect / comp_accepted, primary_dealer / comp_accepted}；z = (x − 同期限前 12 次均值) / 前 12 次标准差（ddof=1，至少 8 次）。s_btc = z_btc，s_ind = z_ind，s_dlr = −z_dlr，s_comp = 三者均值。
  - 体制：D_n(t) = t 时已公布、拍卖日在 (t − n 天, t] 内的拍卖 s 的均值；flag = 1（需求强）当 D_n > k（预注册 k = 0）。
  - 侧：long_off（flag=0 时不开新多）、cap_short_off（flag=1 时不开新空）、both、contra_both（反向假设）。
- 预注册（`scratch/ustauctdemand4h/PRE_REGISTER.json`，2026-11-23 03:07 PST 在任何 PnL 前锁定，sha256 `1466609fdd1282be8409139c7283ac0d33cf88d1b7a7fe10c0973ecd9c09d9cb`）：series {comp, btc, ind, dlr} × n {30, 60, 91} 天 × 4 侧 = **48 格**；先验 `comp_w60_long_off`，回退 `btc_w91_long_off`。
- 回测：同脚本 `qtw.backtest.run_backtest` 默认 4h 书；官方 OKX / Gate 4h 现货 + 永续与官方资金费；真实费（永续 taker 0.051% / maker 0.02%），压力费现货 20 / 永续 15.1 bps。三套：OKX d8（deep 2023-02-01→）、Gate d8（2022-07-01→）、OKX d7 去 BNB（2022-04-01→）；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-23。9 段夏普对同脚本基线计分（x/9）。未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，官方 4h 近 4,500 根，2024-11-28 起，无 deep 段）。安慰剂：时间平移 ±30 / ±60 / +180 / −120 / ±365 天 + 5 个随机种子打乱逐次拍卖分数。

## 结果（`output/research_us_treasury_auction_demand_gate_4h.csv`，258 行；`_new8.csv`）

基线：OKX d8 deep 夏普 0.71、post +72.98% / 2.49；Gate d8 deep 0.08、post +73.40% / 2.51；OKX d7 deep 0.75、post +60.96% / 2.34。

| 格子 | x/9 | OKX d8 post | Gate d8 post | deep 夏普 OKX / Gate / d7 | post 月 胜/负（OKX / Gate） | new8 post OKX / Gate（基线 +11.6 / +25.7） |
|---|---|---|---|---|---|---|
| 先验 comp_w60_long_off | 1/9 | +72.98% / 2.49（= 基线，post 无拦截） | +73.40% / 2.51 | −0.03 / −0.43 / 0.23 | 0/0、0/0 | +11.6 / +25.7（无变化） |
| 回退 btc_w91_long_off | 2/9 | +72.98% / 2.49（= 基线） | +73.40% / 2.51 | 0.71 / 0.15 / 0.76 | 0/0、0/0 | +11.6 / +25.7 |
| 最好非先验 ind_w30_cap_short_off | 6/9 | +86.93% / 2.93 | +87.47% / 2.94 | 0.44 / −0.22 / 0.53（三套全输） | 5/4、5/4 | +34.5 / +34.1（月 5/3、4/3） |

- 最好非先验 6/9 全部来自 tune + post；deep unseen 三套都输给基线（OKX 0.44 vs 0.71、Gate −0.22 vs 0.08、d7 0.53 vs 0.75）。post 月份只有 5/4，达不到 ≥ 6/9。压力费 post OKX +84.65 vs +68.62、Gate +85.35 vs +69.54，但 deep 仍输。
- 邻域（只改窗口 / 阈值）：w14 post +47.6 / w21 +49.5 / w45 +46.8 / w75 +15.2 / w150 +44.3 / w182 +38.4 / k −0.25 +49.1（基线 +73.0）——除 w30 本身、k+0.25（+84.1，Gate deep −0.02 仍输）和 w120（+73.6，边际 0.6 pp）外，post 全部大幅落后基线，是悬崖不是平台。
- 安慰剂：13 个平移 / 打乱最高 5/9（shuf3），post 均不超过真实格；说明 w30 的 post 优势不是纯随机标签，但它在 deep unseen 与相邻窗口都不成立。
- 48 格里 ≥ 7/9 的真实格为 0；long_off（经济先验方向）在 post 几乎不触发（2026-03 后需求 flag 多数为 1），长期只是在 deep 段少开多，deep 夏普变差。

## 结论

**否决**。先验 1/9、回退 2/9；唯一 6/9 的非先验格 deep unseen 全输、post 月 5/4、邻域崩。不实现、不进观察名单、不改默认、无代码改动、不开新纸面实例，仅文档。

## 勿重测（never retest by）

不要换窗口 n / 阈值 k / 标准化窗口（前 N 次）/ 侧 / 方向，不要在 bid-to-cover / 间接 / 直接 / 交易商 / 综合分数之间互换或重新加权，不要只用某个期限（2Y…30Y）或只用续发 / 新发，不要改用尾部（高收益率 − 发行前收益率）/ 中标 vs 中位收益率、外国官方（FIMA）或 SOMA 认购占比、短券（Bills）/ TIPS / FRN 拍卖、拍卖规模或发行计划（季度再融资）、其他国家国债拍卖（Bund / JGB / Gilt），也不要把同一「国债拍卖需求」机制改成 1h 事件、15m 或 1d 周期重测。

## 文件

- `output/research_us_treasury_auction_demand_gate_4h.csv`、`output/research_us_treasury_auction_demand_gate_4h_new8.csv`、`output/us_treasury_auction_demand_official.csv`（均不入库）。
- 脚本 `scratch/ustauctdemand4h/{fetch.py, fetch_td.py, build.py, run.py, new8.py}`、`PRE_REGISTER.json(.sha256)`、`run.log`、`new8.log`（研究脚本未推送）。
- 下一轮（短线）：SEC EDGAR 官方 8-K Item 1.05（重大网络安全事件披露，2023-12-18 起强制）全市场披露计数 / 大市值公司披露 → 8 币永续篮子 1h 事件（按 EDGAR 受理时间戳滞后入场；docs / output 中无 Item 1.05 / 网络安全披露条目，先再查重 edgar_crypto_etf_s1、mstr_8k、us_megacap_earnings_8k、defillama_hack）。
