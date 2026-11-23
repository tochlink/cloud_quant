# 短线新族：Hyperliquid 官方永续 DEX 小时溢价（funding premium）冲击 → 8 币永续篮子（1h）

> 侧记；研究，不改默认，不加纸面。2026-11-23 ~02:00 PST。**先验 / 回退均否决；唯一像样的非先验格仅“弱观察（不实现）”**。

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、scratch/* 中 Hyperliquid 只出现在 Bridge2 USDC 存提流（已否决）。从未测过 Hyperliquid 永续 DEX 的小时资金费 / 溢价。不同于 OKX / Gate 资金费窗口、okx_premium_cojump（OKX 标记-指数溢价）、Gate 资金费间隔、跨所价差 / 成交量份额、Bitfinex 保证金。
- 数据（官方，`output/hyperliquid_premium_official_1h.csv`）：Hyperliquid 官方公共 API `api.hyperliquid.xyz/info` type=fundingHistory，16 币（d8 + new8）每小时 `premium`（该小时永续相对预言机的溢价采样）与 `fundingRate`。30,993 个整点 2023-05-12 00:00Z → 2026-11-23 08:00Z，0 日历缺口；2023-05~06 HL 官方仅 8 小时一条（570 小时无值，NaN，不插值，z 的 168h 窗口至 2023-07 才起算）；之后每小时一条。时间戳 T 的 premium 覆盖 [T−1h, T)，信号 K 线开盘 = T−1h，下一根开盘入场，无前视。
- 公式：med_prem = d8 八币 premium 中位数；btc_prem = BTC premium；prem_disp = d8 八币 premium 横截面标准差。z = 滚动 168h 均值 / 标准差（shift 1，最少 84）；L>1 时用 L 小时和。z ≥ k（high）或 ≤ −k（low）触发，持有 H 小时，非重叠。
- 预注册（PRE_REGISTER.json，sha256 `3c088bffc886…`，看任何 PnL 前锁定 432 格）：metric {med_prem, btc_prem, prem_disp} × L {1,4,8} × k {3,4,5} × {high, low} × {long, short} × H {6,12,24,48}。先验 med_prem L4 k3 high short H24（多头杠杆过热 → 逆势做空）；回退 btc_prem L4 k3 high short H24。宇宙 OKX d8 / OKX 未调参 new8 / Gate d8；费 0.051% 单边（压力 0.151%），OKX 用官方深历史资金费，Gate 用官方资金费；切分 2024-10-21（深度未见）/ 2026-03-05（post）；安慰剂 ±720h 日期平移。
- 结果（`output/research_hyperliquid_funding_premium_shock_event_1h.csv`，17,280 行，416 格有事件；真实费每笔 bps）：
  - **先验** 1/8：OKX d8 train −41.1（n=122）/ test −44.3（n=121）/ post −31.9（n=57，t −0.76）；new8 −22.7 / −31.3 / −48.2；Gate post −33.0；压力 post −51.9。post 月份正 4/9、优于基线 4/9（OKX），Gate 3/9。相邻 L×k 与 H 多数为负。否决。
  - **回退** 0/8：OKX d8 −38.4 / −25.1 / −26.7（n=59）；Gate post −27.7；post 月份正 4/9。否决（+720h 安慰剂 post +38，说明负值并非稳定逆势边际）。
  - 全网格 usable 8/8 = 15（416 格中），全部非先验、全部是事后挑选。最好的一类：`prem_disp_L1_k3_high_long`（八币溢价离散度骤增 → 做多）H24：OKX d8 train +63.9 / test +54.3 / post **+155.1**（n=21，t 2.0）；new8 +15.8 / +64.8 / +164.1；Gate post +156.1（t 2.0）；压力费 post +135；post 月份正 6/9（OKX、Gate 相同，优于基线 7/9）；但事件每月仅 1–4 次，8 月 3 次贡献 +675，去掉最大 3 次 post 均值只剩 +42；−720h 安慰剂 post 仍有 +40、+720h 为 +88、−1440h −120，即真实与日期平移无法区分。H48：post +216（n=17，t 1.6），月份 5/8，去 top3 +16。邻格 L1 k4 H24 post +101（n=7）、L8 k5 H12/H48、L4 k5 H12 同向为正但 n 小、t < 1。
  - 其余 usable 格 post n 多在 1–10 或 t < 1.3；med_prem low long H48（post +81，n=10）同样月份少、安慰剂重叠。
- 结论：**先验 / 回退否决**；非先验 prem_disp L1 k3 high long 满足「深度未见为正、两所 post 月份 ≥6/9」，但在 416 格中事后挑选、t ≈ 2.0（多重检验后不显著）、依赖少数事件、日期平移安慰剂不可区分，**只算弱观察，不实现、不加纸面、不改默认、无代码改动**。若要继续，只能向前记录（官方 API 可复现）并要求新事件样本 ≥ 30 且去 top3 仍为正。
- 勿重测：不要靠改 L / k / H / 方向、换 med / BTC / 离散度、换币篮子、用 fundingRate 代替 premium、换 8 小时 / 日聚合，或加 Hyperliquid 持仓 / 清算 / 其他 DEX 的同类溢价来重测本族。
- 文件：`output/research_hyperliquid_funding_premium_shock_event_1h.csv`、`output/hyperliquid_premium_official_1h.csv`；脚本 scratch/hlprem1h/{fetch,build,run,analyze,baseline,cand}.py、PRE_REGISTER.json（不推送）。
- 下一轮（长线）：美国财政部官方 TIC 月度外国持有美债净买入 → 4h 默认书入场闸门（先查重；本轮检索 Treasury International Capital 0 条）。
