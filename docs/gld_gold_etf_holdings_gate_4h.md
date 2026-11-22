# 长线新族：SPDR Gold Trust（GLD）官方每日黄金持仓（吨）/ 20 日净申赎 / 成交量 → 4h 默认书入场闸门（2026-11-22 ~09:15–09:35 PST，研究，不改默认；否决）

状态：**否决**。不改默认、不加可选代码、不加纸面实例；纸面 8788/8789/8792/8793/8794/8795/8796 照常运行，8790/8791/8787 未触碰。

## 选题与查重

- 本轮先查的候选均为重复：GitHub 核心客户端提交活跃度（`github_core_dev_gate_4h.md` 已否决）、FINRA 融资余额（已否决）、Beacon 存款合约质押净流入（已测 4h + 1h）、DTS 预扣税（TGA DTS 1h 已测，且是 WEI 成分）。
- 选定：黄金 ETF 实物持仓。rg `GLD / SPDR Gold / gold trust / gold ETF holdings / 黄金 ETF` 于 `docs/STRATEGY_FORMULAS.md`（含轮换记录）、`docs/*.md`、`output/research_*.csv` 文件名、`scratch/ROTATION_LOCK.txt`：0 条已测（仅 EGLD 币名命中）。不同于 `copper_gold_ratio_gate_4h`（价格比）、`xaut_gold_shock_event_1h`（金价 1h 冲击）、加密 ETF 资金流。
- 机制：GLD 实物持仓 = 贬值对冲 / 硬资产需求；持仓上升（净申购）= "数字黄金" 顺风 → 允许新多；走弱 → 拦新多。只拦新开仓，持仓 / 止损 / 出场不动。

## 数据（只用官方，不补缺、不插值）

- 发行方官方 xlsx：`https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en`（spdrgoldshares.com/usa/historical-data 页面链接），sha256 `20f7b5b2…35be`。
- 5,535 个 NYSE 营业日 2004-11-18 → 2026-11-19；"US Holiday" 行剔除；>4 天缺口仅 2007-01-02（福特国葬休市）与 2012-10-29/30（飓风桑迪休市）。最新持仓 1,038.14 吨（2026-11-19）。存 `output/gld_holdings_official_daily.csv`（不入库）。
- 可用时刻：D 日（NYT）持仓 **D+1 14:00 UTC** 起使用（发行方在 D 日 16:15 NYT 估值后公布），按 4h 前向填充。

## 预注册（`scratch/gldhold4h/PRE_REGISTER.json`，文件 mtime 2026-11-22 09:20 PST 锁定（JSON 内 locked_at 字段误写为 09:31，未改动以保 sha），sha256 `342015d7…0652`，先于任何 PnL）

- 序列：`ton` = log(吨)；`flow` = log(吨) 20 营业日变化（净申赎）；`vol` = log1p(20 日均 GLD 成交股数)。
- 形式 8 种：trend（s > SMA_n，n = 20/60/120）、chg（n = 20/60）、z252 > k（k = −0.5/0/0.5）。侧 5 种：long_off / short_off / both / contra_both / cap_long_off。3 × 8 × 5 = **120 格** + 同脚本基线。
- 先验侧 long_off / both；回退 `ton_trend_n60_long_off`。harness 与 `scratch/us_ipo_issuance4h/run.py` 完全相同（只换信号块）：OKX d8（2023-02-01 起）/ Gate d8（2022-07-01 起）/ OKX d7_noBNB；deep_unseen → 2024-10-21，tune_pre → 2026-03-05，post → 2026-11-14；真实费用 + 官方资金费，压力费 perp 15.1 / spot 20 bps。

## 结果（`output/research_gld_gold_etf_holdings_gate_4h.csv` 450 行；`_supp.csv`、`_new8.csv`）

- 同脚本基线 post：OKX +59.90% / Sharpe 2.23，Gate +60.32% / 2.25（deep Sharpe OKX 0.71 / Gate 0.09）。
- 9 格 Sharpe 胜数分布：9/9 ×1、8/9 ×1、7/9 ×1、6/9 ×13，其余 ≤5/9。
- **先验最佳** `ton_trend_n20_both` 6/9：post OKX +70.04% / 2.55、Gate +70.73% / 2.57，但 post 月份仅 3/3，OKX d8 deep Sharpe 0.55 < 0.71（失败）。post 与 short_off 完全相同 = post 期内收益全部来自"拦新空"，拦新多部分无贡献。
- **回退** `ton_trend_n60_long_off` 0/9：post 与基线完全相同，deep / tune 全输（OKX deep 0.03、Gate −0.09）。
- 先验锚点安慰剂（±7/±14/+180/−120/+365/−119 天）：最好 +180d 5/9；−14d 3/9 但 post 边际 +29.6 pp 与真实 +29.9 pp 几乎一样。
- **最佳非先验** `ton_trend_n20_short_off` 9/9（持仓高于 20 日均线时拦新空）：post OKX +70.04% / 2.55、Gate +70.73% / 2.57、d7 +60.10% / 2.44；deep OKX +43.93% / 0.87 vs +35.14% / 0.71，Gate +5.33% / 0.21 vs −3.63% / 0.09；压力费仍胜（post OKX +66.94% / 2.47 vs +55.94% / 2.12）。但：post 月份只有 **3/3**（两所），远低于 ≥6/9；补充安慰剂（事后，非预注册）−7d 6/9、−14d 6/9（post +69.99% / 2.53 ≈ 真实），**+180d post +73.33% / 2.77、月份 6/3 反而好于真实** → post 边际不是时点特异；邻域 n10/15 6/9、n30/40 7/9、n60 3/9（n≥60 塌陷）。
- **新 8 币未调参**（OKX/Gate 最近 4500 根 4h）：`ton_trend_n20_short_off` pre OKX +30.53% / 0.85 vs 基线 +44.30% / 0.99，Gate +31.70% / 0.87 vs +41.55% / 0.96（**未见历史两所都输**）；post 好（OKX +18.75% vs +3.26%，Gate +33.39% vs +16.36%，月份 4/2）。
- 判定：先验 / 回退失败；非先验 9/9 被安慰剂（+180d 更好、−14d 相同）追平、post 月份 3/3、新 8 币 pre 两所都输 → 不到 WATCH。**否决**，默认与纸面不变。

## 勿重测

不要通过改 n / k / 侧、换序列（吨数、净申赎、成交量、NAV、溢价折价、每股盎司）、换其他黄金 ETF（IAU、PHYS、GLDM 等）或 World Gold Council 全球黄金 ETF 持仓、改滞后来重测本族。

脚本 `scratch/gldhold4h/{parse,build,run,supp,new8}.py`、`PRE_REGISTER.json(.sha256)`（研究脚本未推送）。
