# 短线新族：斐波那契回撤（Fibonacci retracement）挂限价单顺势入场 → 逐币 1h 永续事件（2026-11-27 ~11:35–11:50 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、约 1,316 个 `output/research_*.csv`、`/workspace/scratch` 中检索 fibonacci / 斐波 / retracement / 回撤比例：**0 条**。已测过的相近族只有 4h 默认书的回调入场闸门（等回踩快均线 / k×ATR 回调补仓）、15m 盘中回调入场、1h VWAP 回补、4h 突破失败反向、15m 影线反转——都不是「摆动幅度按固定比例回撤 + 挂限价单 + 止损在摆动起点、止盈在摆动极值」这一结构。不是重复。
- 机制（技术派广泛使用的先验）：一段足够大的摆动（swing）之后，价格回撤到 38.2% / 50% / 61.8% / 78.6% 会获得支撑 / 阻力并沿原方向继续。结构上每笔盈亏比大（61.8% 时奖励 : 风险 = 0.618 : 0.382 ≈ 1.6），入场与止盈都用 maker 限价，交易不频繁，满足「单笔边际 > 费用 + maker 执行」。
- 公式（逐币，只用 t−1 及之前已收盘 K 线；t 根开盘挂单）：窗口 `[t−N, t−1]` 内 `Hi = max high`、`Lo = min low`、`amp = Hi − Lo`，`ATR = mean(TR, 168)`（截至 t−1）。
  - 上行摆动：`argmin(low) < argmax(high)` 且 `amp ≥ A·ATR`，且 `close_{t−1} > P = Hi − f·amp` → t 根挂限价买 P；下行摆动对称挂限价卖 `P = Lo + f·amp`。
  - 成交：`low_t < P`（严格穿价），成交价 `min(open_t, P)`（空单 `max`）。止损 = 摆动起点（多 Lo / 空 Hi，吃单，**从成交根本身开始检查，止损优先**）；止盈 = 摆动极值（多 Hi / 空 Lo，maker 限价，成交根之后才算）；同根同时触发记止损；否则持有 H 根后开盘吃单平仓。逐币一仓，扣资金费。
- 预注册（`scratch/fibretr1h/PRE_REGISTER.json`，sha256 `9426ba1c8843f571f4379a80100ed480e96efef9fad14cdee7f2c21e1f86f7f7`，2026-11-27 11:35 PST 在任何 PnL 之前写入）：N ∈ {24, 48, 96} × A ∈ {6, 10} × f ∈ {0.382, 0.5, 0.618, 0.786（斐波）; 0.45, 0.55, 0.70（**非斐波安慰剂比例**）} × H ∈ {24, 48} = **84 格**。先验 `fib_N48_A6_f0.618_H48`，回退 `fib_N24_A6_f0.618_H24`。同脚本基线 `BASE_market_N*_A*_H*`：同一摆动条件首次成立即下一根开盘吃单入场（不等回撤），止损 / 止盈 / H 相同。
- 数据（只用官方、不编造）：OKX 官方 1h 永续 K 线 + 官方资金费，默认 8 币 2022-01-29 → 2026-11-23 06:00 UTC；Gate 官方 1h 永续 2025-09-24 → 2026-11-23（无 train 段）；未调参 new8（LINK / LTC / DOT / TRX / BCH / ATOM / NEAR / UNI）OKX 官方 1h。分段：train（深未见）2022-02-15 → 2024-10-21、test → 2026-03-05、post → 末尾。费用：real = 入场 maker 0.02% + 止盈 maker 0.02% / 止损与到期吃单 0.051%；all_taker = 每边 0.051%；stress = 每边 0.151%。
- 结果（`output/research_fib_retracement_swing_limit_event_1h.csv` 2,592 行；月度 `..._months.csv`）。每笔净 bps（real 费），括号为笔数：
  - **先验 N48 A6 f0.618 H48：2/8**。OKX d8 train +25.5（1,677，t 2.4）/ test −8.1（887）/ **post −7.3（489，t −0.6）**；Gate test −2.8 / post −1.6；new8 −3.3 / −2.1 / +8.7。post 月份 OKX 3/9。
  - **回退 N24 A6 f0.618 H24：2/8**。OKX d8 −3.4 / +12.7 / post −3.4；Gate +21.2 / −3.5；new8 三段全负（−13.5 / −23.9 / −15.6）。
  - **斐波 vs 非斐波比例（安慰剂）无差别**：斐波 48 格 8 槽平均正数 3.0，非斐波 36 格 3.2；OKX d8 post 平均斐波 −5.7、非斐波 +4.8；Gate post −3.5 vs +5.4。61.8% 没有任何特殊性。
  - 唯一 8/8：`N48 A6 f0.786 H24`（非先验）每段只有 +2 ~ +19 bps：OKX post +2.4（365，t 0.2）、Gate post +4.1、new8 post +1.7；all_taker 下 OKX post −1.0；压力费 OKX post −21.0；post 月份 OKX 3/9、Gate 3/9 → 不可用。
  - 7/8 两格都在 N48 A10：`f0.70 H24`（**非斐波安慰剂比例**）OKX d8 +81.6（292，t 3.1）/ +31.7 / post +74.8（64，t 2.2），Gate post +71.8（66），但 **Gate test −126.3（52，t −2.4）**；`f0.786 H24` OKX post 仅 +3.3（31）。同簇 f0.618 H24：OKX train +80.7（t 3.3）/ test −13.4 / post +42.2，Gate test −140.8（t −2.9）、new8 post −23.4。邻域：N24 A10、N96 A10 大多为负 → 只在 N=48 成立、2025-09 → 2026-03 下跌段大亏，属孤岛。
  - 同脚本基线（不等回撤直接吃单）：8 槽平均 2.6 正，OKX post −15.0、Gate post −15.2（等回撤挂限价只比追价略好，仍不超过成本）。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例、无代码改动。斐波那契回撤比例在 1h 加密永续上没有超过非斐波比例的信息量；先验 / 回退 2/8；唯一 8/8 边际薄到压力费即负；N48 A10 深回撤簇对 N 不稳且 Gate test 显著为负，而且最好的格是安慰剂比例。
- 勿重测（never retest by…）：不要通过改 f（任何斐波 / 非斐波比例、扩展位 1.272 / 1.618 止盈）、N / A / ATR 窗口、H、止损位置（78.6% / 100% / k×ATR）、止盈位置（摆动极值 / 扩展位 / 固定 R 倍数）、穿价规则或成交价假设、只做多 / 只做空、加趋势 / 资金费 / BTC 状态过滤、改用 ZigZag / 分形摆动点定义、改 15m / 4h 周期、改篮子级 / BTC 单币、或「斐波回撤 + 时间窗（斐波时间周期）」重测同一「固定比例回撤支撑 / 阻力顺势」机制。
- 文件（不入库）：CSV `output/research_fib_retracement_swing_limit_event_1h.csv`、`output/research_fib_retracement_swing_limit_event_1h_months.csv`；脚本 `scratch/fibretr1h/{prereg,run,an}.py`、`PRE_REGISTER.json`、`PRE_REGISTER.sha256`、`wide.csv`、`trades.pkl`。
- 下一轮（长线）：美国财政部官方季度再融资（Quarterly Refunding）借款估计 / 附息券发行规模变化 → 4h 默认书入场闸门（docs / output 中 refunding 0 条；须先与已否决的 Debt to the Penny 国债余额增速 / 债务上限、国债拍卖需求族查重）。
