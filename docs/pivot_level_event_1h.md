# 日线经典枢轴点（Floor Pivot）水平位 1h 事件（逐币永续，研究，否决）

## 短线新族：前一 UTC 日 P / R1-S1 / R2-S2 枢轴位的收盘突破或影线拒绝 → 顺势 / 逆势持有 H 小时（2026-11-21 ~10:40 PST，研究，不改默认；否决）

- 选题与查重：`rg -i 'pivot point|floor pivot|枢轴|Camarilla|Fibonacci|斐波那契'` 检索 docs/*.md 与 `output/research_*.csv`（1,087 个）0 命中；记忆中无枢轴点条目。最近的已测族：前日 / 周 / 月高低点突破 1h（`research_calendar_level_breakout_event_1h.csv`）、整数关口、Donchian / turtle soup、UTC 开盘区间 4h 闸门、1h VWAP 回补、日内时序动量 1h、1h squeeze 突破。枢轴 P=(H+L+C)/3 及其 R/S 投影是不同的价位（R1=2P−L 常落在前日区间内部），影线拒绝触发也是新定义。不是重复。
- 机制（先验）：经典场内枢轴点被散户 / 程序广泛公开计算，挂单与止损聚集在这些价位 → 触及后反转（拒绝），或收盘穿越后止损连锁延续（突破）。
- 数据：官方 OKX USDT 永续 1h d8（`scratch/deep1h`，2022-01-29 → 2026-11-20 23:00 UTC；BNB 较晚开始）、官方 Gate USDT 永续 1h d8（2025-09-24 → 2026-11-20 23:00 UTC）、未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，OKX 官方 1h，2022-01-29 →）；资金费：OKX 官方深历史 `output/okx_funding_history_official_deep.csv`、Gate 官方资金费，逐根结算计入。无模拟、无现货冒充永续、无插值 / 回补（前一日 24 根不全则当天无枢轴位）。
- 公式（`scratch/pivot1h/PRE_REGISTER.json` sha256 `d562215a…8f6625`，看任何 PnL 前锁定；格子表 `output/research_pivot_level_event_1h_prereg.csv`）：
  - 第 d 天只用第 d−1 天 24 根 1h：H=最高、L=最低、C=23 时根收盘。P=(H+L+C)/3，R1=2P−L，S1=2P−H，R2=P+(H−L)，S2=P−(H−L)。
  - 触发（逐币，第 d 天的 1h 根 i）：break：`C[i−1] ≤ U < C[i]` → +1，`C[i−1] ≥ D > C[i]` → −1；reject：`H[i] ≥ U 且 max(O,C) < U` → −1，`L[i] ≤ D 且 min(O,C) > D` → +1。follow = 该方向，contra = 反向。每币每天每格只取首个事件；同币上一笔未平则跳过。
  - 执行：第 i 根收盘出信号，第 i+1 根开盘吃单入场，第 i+1+H 根开盘吃单离场；实费 5.1 bps / 边（压力 15.1）；官方资金费按持仓根结算。
  - 网格 36 格：level P / R1S1 / R2S2 × trigger break / reject × side follow / contra × H 4 / 12 / 24。先验 `R1S1_reject_follow_H12`（教科书：在 R1/S1 处反转），后备 `R1S1_break_follow_H12`（止损连锁延续）。
  - 同脚本基线：无条件每币 00 UTC 开多持有 H（以及不交易 = 0）。
  - 分段：深未见 train 2022-02-15 → 2024-10-21；test → 2026-03-05；post 2026-03-05 → 2026-11-21 00:00 UTC；Gate 窗口 2025-09-28 →。
  - 8 格记分：OKX d8 train/test/post、new8 train/test/post、Gate d8 post、Gate 窗口的逐笔平均净收益 > 0；usable = 8/8 且 OKX d8 每段 n ≥ 30。
  - 安慰剂：用 d−2 天（滞后 24h）和 d−8 天（滞后 168h）的过期枢轴位；逐笔随机符号 200 次。
- 结果（实费，逐笔平均净 bps；CSV `output/research_pivot_level_event_1h.csv`，1,800 行）：

| 格子 | 记分 | OKX train（深未见） | OKX test | OKX post | new8 train | new8 post | Gate post | post t（OKX） | 压力 post OKX / Gate | post 月份为正（OKX / Gate） | 随机符号 p（OKX / Gate） |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 先验 R1S1 reject follow H12 | 2/8 | −2.2 | +1.2 | −8.4（n 1,068） | −3.1 | −24.5 | −13.7（n 1,058） | −1.25 | −28.4 / −33.7 | 3/9 / 3/9 | 0.45 / 0.66 |
| 后备 R1S1 break follow H12 | 0/8 | −8.0 | −1.2 | −19.7（n 1,217） | −16.4 | −15.5 | −18.7 | −3.09 | −39.7 / −38.7 | 2/9 / 2/9 | 0.93 / 0.90 |
| 最佳非先验 R2S2 break contra H24 | 4/8 | −9.7 | −62.6 | +16.1（n 522） | +21.3 | +24.9 | +13.5（n 526） | 1.1 | −3.9 / −6.5 | 5/9 / 5/9 | 0.04 / 0.055 |
| P break contra H12 | 4/8 | −1.9 | +10.6 | +2.1 | −3.4 | −19.6 | +1.5 | 0.4 | −17.9 / −18.5 | 4/9 / 4/9 | 0.01 / 0.01 |
| 基线：00 UTC 无条件开多 H12 | — | +0.8 | −5.0 | −11.3 | −0.3 | −6.4 | −11.0 | — | — | — | — |

  - 记分分布：0/8 13 格、1/8 7 格、2/8 9 格、3/8 4 格、4/8 3 格；**0 个 usable**。按 trigger/side 平均（OKX d8 post）：break follow −22.2、break contra +1.8、reject follow −6.4、reject contra −14.0 bps。
  - 最佳 R2S2 break contra H24 的 post 正值来自 2026 年 post 段的均值回归行情，深未见 train −9.7、test −62.6；滞后 24h 过期枢轴位安慰剂 post +17.0（不比真值 +16.1 差），说明不是枢轴位本身的信息；H12 邻格 3/8、H4 3/8。
- 结论：**否决**。先验 2/8、后备 0/8，无 usable 格，压力费下全部为负，两所 post 月份为正都不到 6/9；安慰剂不比真值差。不进观察名单，不改默认，不加影子子账户，纸面账户不变。
- 勿重测：不要通过换枢轴公式（Camarilla / Woodie / DeMark / 斐波那契枢轴）、换水平位组合、改触发定义（收盘 / 影线 / 缓冲带 / ATR 缓冲）、改 H、改方向、改周 / 月枢轴、或逐币 ↔ 篮子聚合来重测本族。
- 脚本：`scratch/pivot1h/{run,analyze,supp,plog}.py`（研究脚本不入库）。
