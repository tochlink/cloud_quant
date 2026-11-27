# 短线新族：Gate 官方全市场长尾 USDT 永续 24h 暴涨 / 暴跌广度冲击 1h 事件 → 8 币永续篮子（2026-11-27 ~15:05–15:35 PST，研究，不改默认；否决）

状态：先验 `pump_X0.15_k2_any_short_H24` **否决**（0/8）；回退 `dump_X0.15_k2_any_long_H24` 8/8、post 月份 6/9（两所），但 t 全部 < 1.5，+168h 平移安慰剂保留大部分 train / test 收益，剔除「8 主流币自身暴跌」小时后 train / post 转负 → 信息来自主流币自身急跌（已由 #14 投降 ∪ DVOL 强观察 / 纸面覆盖），长尾广度没有独立增量。**否决**，不实现、不加影子子账本 / 纸面实例、不改默认、无代码改动；live 关，8787 / 8790 / 8791 未触碰。

## 选题与查重（原定题目被判重复）

- 原定：Gate 官方批量逐笔成交（download.gatedata.org `futures_usdt/trades`）的大单主动成交 / 大额吃单聚簇（bulk take-flow / large-aggressor cluster）1h → 8 币篮子。
- 查重结论：**重复，放弃**。`docs/STRATEGY_FORMULAS.md` 2026-11-14 ~21:35「平均单笔成交额（大单参与度）/ 买卖单笔均额倾斜（大单方向）」（`output/research_avg_trade_size_whale_event_15m.csv`，否决，「大单方向族不再重测」）、主动买卖失衡（`research_okx_taker_flow_imbalance_event.csv`、`research_taker_flow_imbalance_gate.csv`、`research_microstructure_1h_events_grid.csv`）、Deribit 大宗成交冲击（`research_deribit_block_trade_shock_event_1h.csv`）、BTC 链上鲸鱼转账爆发（`research_btc_whale_transfer_burst_event_1h.csv`）已覆盖「大额主动成交聚簇」同一机制；换交易所 / 换成 1h 只是换数据源。
- 另外排除：Morpho / Compound 清算（与已否决 Aave V3 / GMX 清算同机制）、DAX 开盘跳空（官方 STOXX 历史需登录，且与日经开盘跳空同机制）、Gate 保险基金（官方只有日度）、交易所公告（币安公告节已禁止换交易所）、ATH / 前高突破（日历前高突破、52 周高锚定已否决）、ETH/BTC 比值（alt_btc_ratio、配对价差已测）。
- 选定：**Gate 全市场长尾永续（剔除 d8 与 new8 共 16 个交易币）24h 涨跌幅超过 ±X 的合约占比**冲击。`rg -i 'breadth|广度'`：已测的是 8 币篮子站上均线比例（breadth thrust，8 币）、Gate 全市场资金费过热广度（4h 闸门，资金费而非价格）、8 币横截面离散度；从未用过**全市场长尾合约价格**广度（含已下架合约，无幸存者偏差）。机制先验：长尾暴涨面扩散 = 散户投机过热顶部 → 主流币随后回落（做空）；长尾暴跌面扩散 = 全市场强制去杠杆 → 主流币反弹（做多，回退）。事件少、单笔持有 24h，结构上可覆盖费用。

## 数据（只用官方，不编造、不插值、不回补）

- 信号：Gate 官方批量 `download.gatedata.org`（S3 `gateio-public-data`）`futures_usdt/candlesticks_1h/YYYYMM/<C>-YYYYMM.csv.gz`，2021-10 → 2026-10 共 27,701 个月文件，**含已下架合约**（列序 ts, volume, close, high, low, open）；2026-11 用官方 v4 REST `/futures/usdt/candlesticks`（在架合约，丢弃未收盘 K 线）。合计 1,678 个合约，广度宇宙 1,662 个（剔除 16 个交易币），45,214 个小时 2021-10-01 → 2026-11-27 21:00 UTC。每小时合格合约中位数 2022 年 153 → 2026 年 693。官方月文件存在个别全市场缺 bar 的小时（合格数临时下降），不填补，比例自动只用当时有数据的合约。
- 官方 1h 序列：`scratch/gatebulk1h/gate_longtail_breadth_official_1h.csv`（n_elig、n_p15/p30、n_d15/d30、Gate d8 24h 均值对数收益）。
- 行情：OKX 官方 1h 永续 d8（2022-01-29 →）、未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI）、Gate 官方 1h 永续 d8（2025-09-24 →），另用同一批 Gate 官方批量 1h 重建 Gate d8 深历史（gate_deep_d8，2022-01 →）；官方资金费（OKX 深历史 + Gate `funding_applies` 长历史）。不用现货代替永续。

## 公式与预注册（`scratch/gatebulk1h/PRE_REGISTER.json`，2026-11-27 15:14 PST 锁定，sha256 `3f14344a7394bd46…`，先于任何 PnL，96 格）

- 合格：t 与 t−24h 都有官方收盘、上线 ≥168h、24h 成交量 > 0；`r24 = ln(C_t / C_{t−24})`。
- `pump_X = 合格中 r24 ≥ ln(1+X) 的占比`，`dump_X = r24 ≤ ln(1−X) 的占比`，X ∈ {0.15, 0.30}，合格数 ≥ 50。
- `z = (B_t − mean_720h) / sd_720h`（窗口截至 t−1，min 360）；事件 `z ≥ k`，k ∈ {2, 3}；cond ∈ {any, quiet：Gate d8 24h 均值收益绝对值 < 3%}。
- 下一根 1h 开盘吃单等权 8 币永续做多 / 做空，持 H ∈ {12, 24, 48}h，不重叠；官方资金费计入。taker 5.1 bps / 边（压力 15.1 bps；maker 2 bps 仅参考）。
- 先验 `pump_X0.15_k2_any_short_H24`；回退 `dump_X0.15_k2_any_long_H24`。
- 切分：train（深未见 2022-01-01 → 2024-10-21）/ test（→ 2026-03-05）/ post（→ 2026-11-27）/ gate_window（2025-09-28 →）；8 槽 = OKX d8 三段 + new8 三段 + Gate d8 post / window，另加 gate_deep_d8 三段；同脚本无条件基线；±720h、+168h 平移安慰剂；事后 200 次随机时点安慰剂、主流币自身暴跌对照。

## 结果（每笔净 bps，真实费；`output/research_gate_longtail_breadth_event_1h.csv` 6,720 行；事后诊断 `_supp.csv`）

| 格 | 8 槽 | OKX d8 train / test / post（n，post t） | new8 train / test / post | Gate 深 train / test / post | post 月份胜基线 OKX / Gate |
|---|---|---|---|---|---|
| 先验 pump X0.15 k2 any 做空 H24 | 0/8 | −10.6 (153) / −24.8 (58) / −48.7 (40, −0.9) | −17.8 / −25.1 / −48.5 | −6.6 / −26.0 / −49.4 | 4/9 / 4/9 |
| 回退 dump X0.15 k2 any 做多 H24 | 8/8 | +29.2 (121) / +98.3 (52) / +23.4 (41, 0.57) | +11.0 / +69.9 / +63.2 | +26.9 / +98.2 / +23.7 | 6/9 / 6/9 |
| 基线 无条件做多 H24 | — | +0.5 / −8.1 / −22.0 | −3.0 / −9.5 / −10.8 | −5.0 / −5.6 / −20.8 | — |

- 网格 8 槽为正分布：0:15、1:7、2:14、3:15、4:21、5:9、6:7、7:1、8:7；usable 7 格，全是做多（dump 6 格 + pump X0.15 k2 any H48），无一做空格。
- 回退格稳健性：
  - 压力费 OKX post +3.4、Gate post +3.7、Gate d8 test −6.8 → 只剩很薄的边际。
  - 平移安慰剂：+720h post −101 / train −15.5；−720h post −64 / train +0.5；**+168h train +39.1 / test +91.1（与真实 +29.2 / +98.3 同量级）**，post −47 → 深历史收益主要是「暴跌周之后做多」的体制效应，不是事件时点本身。
  - 随机时点（同笔数，200 次）分位：OKX train 0.78 / test 0.98 / post 0.85；Gate 深 0.90 / 0.96 / 0.88，train 与 post 不到 0.95。
  - 全网格安慰剂：OKX+Gate 深 6 槽全正格数 真实 10、+720h 7、−720h 7、+168h 12 → 与安慰剂无区分。
  - **与主流币自身暴跌重叠**：只用 8 币自身 24h 跌幅 z ≥ 2 做同样交易（对照），train / test +70.6 / +49.7；把这些小时剔除后回退格 train −27.5 / test +91.2 / post −20.1（Gate 深 −24.9 / +91.1 / −19.5）。cond=quiet（主流币没大动、只有长尾暴跌）H24 只有 2/8，post −16.2。长尾广度没有超出主流币自身急跌的增量，后者已由 #14（投降 ∪ DVOL）覆盖。
  - 邻域：dump any 做多在 X0.15 k2 / k3、X0.30 k2 的 H24 / H48 大致为正，但 H12 与 X0.30 k3 全部转负，post t 全部 < 1。
- 结论：**否决**。先验 0/8；回退虽然 8/8、月份 6/9，但统计上弱（t < 1.5）、被 +168h 平移复制、去掉主流币自身暴跌后转负，属于 #14 投降族的重复暴露。不进强观察，不加纸面。

## 勿重测（never retest by…）

- 改 X / k / H / z 窗口 / cond / 方向，或在 pump / dump / 二者之差 / 净广度之间互换；
- 改用 OKX / Binance / Bybit 全市场长尾广度、按成交额或 OI 加权的广度、新高 / 新低个数、站上均线比例、中位数 / 分位数收益；
- 改成 15m / 4h / 日线周期或 4h 默认书入场闸门；
- 把它与 #14 投降 / 主流币自身跌幅组合后当新族重测（同一机制）；
- 也不要再用 Gate / OKX 逐笔大单 / 主动成交聚簇（已判与大单 / 主动失衡族重复）。

## 文件

- CSV（不入库）：`output/research_gate_longtail_breadth_event_1h.csv`、`output/research_gate_longtail_breadth_event_1h_supp.csv`（事后诊断）；官方 1h 序列 `scratch/gatebulk1h/gate_longtail_breadth_official_1h.csv`。
- 脚本（不推送）：`scratch/gatebulk1h/{fetch,build,prereg,run,an,supp}.py`、`PRE_REGISTER.json`、`analyze_wide.csv`。
- 下一轮（长线）：中国人民银行官方社会融资规模存量同比 / 信贷脉冲（社融增量 12 个月和占 GDP 变化）→ 4h 默认书入场闸门（`rg TSF / 社融 / credit impulse / 信贷脉冲` 0 命中；不同于已否决的美国 M2、SLOOS、金融压力信用闸门）。须先确认 PBoC 官方月度历史可免费下载、发布时滞按官方日程；拿不到则改测美联储官方 G.19 消费信贷（FRED TOTALSL / REVOLSL，0 命中）。
