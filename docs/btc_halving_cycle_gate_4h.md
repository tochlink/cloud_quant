# 长线新族：BTC 减半周期相位（4 年供给周期）作为 4h 默认书入场闸门（否决）

> 侧记（docs/STRATEGY_FORMULAS.md 超出连接器写入上限）。研究，不改默认；**否决**。

- 查重：docs/*.md、output/research_*.csv（1,133 个）、scratch、记忆中 halving / 减半 / block subsidy / 区块奖励 / 4 年周期 0 条。不同于已否决的幂律 / Mayer / 200 周估值带（价格口径）、Puell / 矿工收入、算力带、日历季节性。
- 数据：比特币官方区块时间（blockstream.info esplora；mempool.space 交叉核对高度 630000 = 1589225023）：高度 210000 / 420000 / 630000 / 840000 的出块时间。D 日只用 D 00:00 UTC 前已出块的减半（无前视），days_since_halving 为确定值。`output/btc_halving_phase_official_daily.csv`（2019-01-01 → 2026-11-22）。
- 公式：flag=1 当 a ≤ days_since_halving < b（经典"减半后熊市窗"），(a,b) ∈ {(365,900),(450,900),(540,900),(365,1100),(450,1100),(540,1100)}；侧 long_off / short_off / both / contra_both / cap_short_off，只拦新开仓。默认 #1 4h，真实费 + 压力费，官方资金费。
- 预注册（scratch/halving4h/PRE_REGISTER.csv/.md，sha256 2a7e35d2…/66d1b2d1…，任何 PnL 前锁定 30 格）。先验 `halv_w540_900_long_off`（减半后 18 个月～2.5 年 = 历史周期熊市 → 不开新多），回退 `halv_w540_900_both`。事前写明：永续数据只覆盖约 1.5 个周期，结论最多弱观察。
- 结果（`output/research_btc_halving_cycle_gate_4h.csv`，183 行；占用率 w540_900：deep 0.23 / tune 0.29 / post 0.83）：
  - **先验** 4/9：post OKX +38.81% / Sharpe 1.82 vs 基线 +61.54% / 2.27；Gate +39.06% / 1.84 vs +61.96% / 2.29；post 月份好 1 / 差 3（两所）。OKX deep 与基线相同（窗口未覆盖），Gate deep +10.77% / 0.29 vs −3.63% / 0.09。压力费 post OKX 36.11 vs 57.54。
  - **回退** 1/9 量级：post OKX +10.72% / 0.70，Gate +10.89% / 0.71，月份 0/5。
  - 最好仅 6/9（w450_1100 / w540_1100_long_off），post 同样差约 −20 pp、月份 1/3。
  - 安慰剂：平移 ±7/±14/+180 天与真实几乎一样（post 33～41%），说明拦掉的只是 2026 年这一段多单，不是周期信号。
  - 未调参 new8（近 4500 根）：先验 post OKX 10.80 vs 12.77、Gate 25.28 vs 26.93，更差。
- 结论：**否决**，不实现、不进观察名单、不加模拟盘、不改默认，无代码改动。勿以同一机制换窗口 a/b、侧、换成减半前窗口 / 距下次减半天数 / 区块奖励或通胀率 / stock-to-flow 再测。
- 文件：output/research_btc_halving_cycle_gate_4h.csv、output/research_btc_halving_cycle_gate_4h_new8.csv、output/btc_halving_phase_official_daily.csv；脚本 scratch/halving4h/{build,prereg,patch,run,new8}.py（研究脚本未推送）。
