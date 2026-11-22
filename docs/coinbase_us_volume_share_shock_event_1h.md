# 短线新族：Coinbase 美国现货成交占比（Coinbase USD 现货 ÷ OKX USDT 永续成交额）1h 冲击 → 8 币永续篮子（2026-11-21 ~22:50 PST，研究，否决）

- 查重：Coinbase 此前只做过**价格**溢价（4h 闸门 + 1h 冲击事件，2026-11-14 均否决），从未用过 Coinbase **成交额 / 场所占比**；Upbit 韩国成交占比只做过 4h 长线闸门（否决）。与已否决的 8 币篮子 1h 成交额冲击（本所总量）、主动买卖失衡、现货 / 永续成交量占比 4h 闸门、平均单笔成交额、Gate × OKX 价差、ETF 资金流不同。任务给的种子 (a) Deribit IV 偏斜 / 期权成交流 1h 与 (b) MEV-Boost 块交付价值 1h 在日志中都已测过并否决，所以本轮未用。
- 机制：美国合规现货场所（Coinbase Exchange USD 盘）相对离岸永续场所（OKX USDT 永续）的成交占比，在某小时远高于同一 UTC 时段的常态 = 美国 / 机构现货资金到场；用 Coinbase BTC-USD 该小时涨跌定方向 = 美国主导买入或卖出。先验：美国主导的现货买入突发会延续约一天。
- 数据（全部官方，不插值、不回补）：
  - 信号：Coinbase Exchange 官方公共 K 线 `api.exchange.coinbase.com/products/{BTC-USD,ETH-USD}/candles?granularity=3600`，2021-12-01 → 2026-11-22 04:00 UTC，各 43,600 根已收盘小时；3 个 Coinbase 停机小时（2023-03-04、2025-10-25、2026-05-08）缺失记为 NaN。与本机 2026-11-14 已存 `output/coinbase_spot_1h.csv` 重叠 85,362 行收盘价、成交量逐行一致。USD 成交额 = base 成交量 × 收盘价。
  - 分母：OKX 官方 1h USDT 永续 BTC / ETH（张数 × 面值 0.01 BTC / 0.1 ETH × 收盘）。
  - 有效信号小时 41,659 / 42,161（2022-02-18 → 2026-11-20 23:00 UTC；缺的是前 28 天季节预热 + 停机小时）。Coinbase / OKX 美元成交额中位比 2022 0.122、2023 0.075、2024 0.075、2025 0.058、2026 0.059。
- 公式：
  - `logshare_t = ln(CB_btc_usd + CB_eth_usd) − ln(OKX_btc_usd + OKX_eth_usd)`
  - `share_t = logshare_t − 前 28 天同一 UTC 小时 logshare 均值`（≥20 个有效，去日内季节）
  - `us_led_t = share_t × sign(Coinbase BTC-USD 该小时 close/open − 1)`
  - 突发 z：168h 滚动均值 / 标准差截至 t−1；L=1 用 `(v−μ)/σ`，L>1 用 `(Σ_L v − Lμ)/(σ√L)`。
  - 信号小时 h 在 h+1h 收盘后可知，下一根 1h 永续开盘入场，持有 H 根后开盘平；8 币等权、不重叠；费用 2×taker + 官方资金费。
- 预注册（`scratch/cbshare1h/PRE_REGISTER.json`，任何 PnL 前锁定，sha256 `e7dafde7…ffecc`）：metric {share, us_led} × L {1,4,8} × k {2.0,2.5,3.0} × side {high, low} × dir {long, short} × H {6,12,24,48} = **288 格**。先验 `us_led L4 k2.5 high long H24`（美国主导买入突发 → 跟多 1 天）；回退 `us_led L4 k2.5 low short H24`（镜像：美国主导卖出 → 跟空）。安慰剂 ±720h 时移。分段 train 2022-02-15 → 2024-10-21（深度未见）/ test → 2026-03-05 / post → 2026-11-20；Gate 官方 1h 永续 2025-09-24 起；未调参 new8（OKX）。
- 结果（`output/research_coinbase_us_volume_share_shock_event_1h.csv`，11,520 行；每事件净 bps，真实费 taker 5.1 bps）：

| 格 | 正槽 | OKX d8 train / test / post | new8 train / test / post | Gate post | post t | 压力费 post（OKX） | +720h / −720h 安慰剂 post |
|---|---|---|---|---|---|---|---|
| 先验 us_led L4 k2.5 high long H24 | 3/8 | +21.5 (n103) / −0.0 (n61) / **−41.8** (n38) | +41.4 / +4.8 / −33.3 | −41.5 | −1.1 | −61.8 | −15.7 / +4.3 |
| 回退 us_led L4 k2.5 low short H24 | 7/8 | +6.8 (n104) / +95.1 (n65) / +8.6 (n31) | +25.5 / +88.9 / **−18.6** | +8.3 | 0.19 | **−11.4** | **+83.3** / −6.5 |
| 非先验 us_led L4 k2.0 low short H24（唯一 usable 8/8，不可采用） | 8/8 | +1.5 (n215) / +21.2 / +29.7 (n59) | +15.9 / +0.2 / +15.9 | +29.0 | 0.9 | — | — |

  - 同脚本无条件基线（每小时入场、同方向 H24）：做多 OKX train −4.7 / test −5.6 / post −19.6 bps；做空 post −0.8（Gate −1.4）。回退 post 相对基线只多约 +9 bps / 笔，t 0.19，post 月份胜基线 6/9（OKX、Gate 相同）。
  - 先验邻域（L×k、H）post 全部为负（−13.5 至 −132.8 bps）；回退邻域 L1 / L8 和 k3.0 post 多为负（L4 k3.0 −20.1，L8 k2.5 −49.7），只有 L4 k2.0 / k2.5 两格为正。
  - 网格分布：288 格中 8/8 仅 1 格、7/8 3 格；`share` 单边高 → 做空（L1 k3.0 H24 post +111 bps，t 2.0）是 test 段为负的非先验格。
- 结论：**否决**，不实现、不进观察名单、不加纸面、不改默认，无代码改动。先验（美国主导买入跟多）只有 3/8，post 两所约 −42 bps / 笔；回退 7/8 但 post 边际薄（+8.6 bps，t 0.19）、未调参 new8 post 为负、压力费为负、+720h 时移安慰剂 post +83 bps 远超本格，邻域不稳定。Coinbase 美国现货成交占比对 1h 篮子没有超出安慰剂与费用的增量。
- **勿重测**：不要以换 L / k / H / 方向 / high↔low、换 share↔us_led、换去季节方法（同星期小时 / 不同回看天数）、换分母（OKX 现货、Gate、Binance）、换币对（加 SOL / XRP 等 USD 盘或 USDC / USDT 盘）、换成笔数或 Coinbase 单独成交额，或改成 4h 长线闸门的方式重测本族。
- 文件：`output/research_coinbase_us_volume_share_shock_event_1h.csv`（不入库）；脚本与数据 `scratch/cbshare1h/{fetch,run,analyze}.py`、`coinbase_btc_eth_official_1h.csv`、`cb_share_official_1h.csv`、`prior_events.csv`、`baseline.log`、`PRE_REGISTER.json`（研究脚本未推送）。
- 下一轮（长线）：比特币矿工收入中的**手续费占比**（官方区块 coinbase：手续费 ÷（手续费 + 区块补贴），日度）趋势 / z → 4h 默认书入场闸门（D+1 滞后）。docs 检索「手续费占比 / fee share / subsidy」0 条；与已否决的 BTC 手续费 1h 冲击、Puell 倍数（总收入 / 365 日均）、CBECI 矿工利润带、算力带不同。需先确认可从 mempool.space 官方区块数据免费全历史重建。
