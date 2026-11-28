# 短线新族：Gate 官方 USDT 永续保险基金日变动冲击 → 8 币永续篮子（1h 执行，2026-11-28 ~01:55 PST，研究，不改默认；否决）

## 查重与换题
- 原定 Hyperliquid 官方 HLP 金库净值 / account value 1h 冲击：**官方历史不够，不测、不回补**。`api.hyperliquid.xyz/info` `vaultDetails`（HLP `0xdfc24b077bc1425ad1dea75bcb6f8158e10df303`）的 `portfolio.day` 只有最近约 24h（约 15 分钟一点，57 点），`week` 约 3h 一点，`month` 约 1 天一点，`allTime` 只有 104 个粗点（2023-05 起）；stats-data.hyperliquid.xyz 返回 403。已启动官方实时记录器 `scratch/hlpvault1h/record.py`（每小时追加 `hlp_vault_official_15m.csv`），等攒够历史再按预注册测。
- 再查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、scratch 目录名中 insurance / 保险基金：只有 `okx_insurance_fund_shock_event_1h`（OKX 只给约 90 天历史，PENDING-RECORDER，从未看过 PnL；其文档误记「Gate 无同类公开历史」）。Gate 官方 `GET /api/v4/futures/usdt/insurance` 实际给出 2019-11-18 起的**日度**余额。与已否决的 1h 爆仓 / OI / taker / LS 微观事件不同：信号是交易所风控账户余额的**日度**变化（爆仓盈余注入 / 穿仓亏损扣减），不是爆仓成交流。

## 数据（全部官方，不编造、不插值）
- Gate 官方 USDT 永续保险基金日余额 2,564 天（2019-11-18 → 2026-11-28 00:00 UTC，1 个日历缺口，缺口当日不出信号）；`scratch/gateins1h/gate_insurance_usdt_official_daily.csv`（另抓 BTC 本位 2,789 天未用）。最新余额 143,327,522 USDT。负变动日 217 天，最大单日 −27.3%（2024-12-06）。
- 交易：OKX 官方 1h 永续默认 8 币 2022-01-29 → 2026-11-27、未调参 new8（OKX 1h）、Gate 官方 1h 永续默认 8 币（2025-09-24 起）；官方资金费；吃单 5.1 bps / 压力 15.1 bps 每边。

## 公式（`scratch/gateins1h/PRE_REGISTER.json`，sha256 `c35867695590b43b3abfc3be630efd800de9e4ac936e960d7957edbcef546f08`，看任何 PnL 前锁定 162 格）
- `x_t = b_t / b_{t−1d} − 1`；`z = (x − 过去 N 天中位数) / (1.4826 × 过去 N 天 MAD)`（严格过去）。
- 事件：hi `z ≥ k`（爆仓盈余大增 = 级联刚发生）、lo `z ≤ −k`（穿仓亏损）、two `|z| ≥ k`。
- 方向：以快照当日篮子收益 `R = mean O[t]/O[t−24h] − 1` 定方向，contra = −sign(R)、follow = +sign(R)。
- 入场 t + 2h 的 1h 开盘（发布滞后缓冲），持有 H 根后开盘平，等权篮子，持仓中不重复。
- 网格：side {hi, lo, two} × N {60, 120, 250} × k {2, 3, 4} × {contra, follow} × H {12, 24, 48}。先验 `ins_pct_hi_N120_k3.0_contra_H24`；回退 `ins_pct_two_N120_k3.0_contra_H24`。
- 诊断（非格）：延迟 +6h / +24h；整体平移 ±1d / ±7d；随机日安慰剂 300 次；同 N/k 的纯价格对照（|R| 稳健 z）；全日恒多 / 恒空基线。

## 结果（真实费，每事件净 bps，`output/research_gate_insurance_fund_shock_event_1h.csv` 17,590 行）
| 格 | OKX d8 train(深未见) | test | post | new8 train | new8 test | new8 post | Gate post |
|---|---|---|---|---|---|---|---|
| 先验 hi N120 k3 contra H24 | −51.3 (n107) | −18.0 (54) | −89.1 (21) | −37.9 | −21.5 | −88.7 | −89.6 |
| 回退 two N120 k3 contra H24 | −33.1 (169) | −4.3 (70) | −93.5 (29) | −18.3 | −3.0 | −70.0 | −93.9 |
| 非先验镜像 hi N120 k3 follow H24 | +30.9 (t0.9) | −2.4 | +68.7 (t0.75) | +17.5 | +1.1 | +68.3 | +69.2 |
- 先验 / 回退 0/7 片段为正；随机日安慰剂分位 post 只有 3–10%。
- 162 格无一格 7/7；13 格 6/7 全部 t < 1。镜像 follow 格的 post 优势被「事件前移 1 天」安慰剂远超（−1d：post +305 bps），说明只是大波动日后的动量，不是保险基金信息；+7d 平移 −129；N/k 邻域 test 段 k3/k4 全负。
- 结论：**否决**。不实现、不进观察名单、不改默认、不动纸面盘、无代码改动。

## 勿重测（never retest by…）
不要以改 N / k / H / lag / side / contra↔follow、换 BTC 本位保险基金、换美元变动 / 水平 / 回撤、换周度聚合、换 OKX / Binance / Bybit 等其他交易所保险基金日度序列、或改用逐币 / 单币反应来重测「交易所保险基金余额变动 → 篮子」机制。OKX 1 分钟级保险基金记录器（PENDING-RECORDER）累计 ≥ 12 个月后可按其自身预注册一次性评估，不受本条限制。

## 文件
- `output/research_gate_insurance_fund_shock_event_1h.csv`（不入库）；脚本与数据 `scratch/gateins1h/{fetch,prereg,run,analyze}.py`、`gate_insurance_{usdt,btc}_official_daily.csv`、`events_real.csv`。
- HLP 记录器：`scratch/hlpvault1h/record.py` → `hlp_vault_official_15m.csv`。

## 下一轮（长线）
选一个未测过、官方历史 ≥ 2018 的 4h 默认书入场闸门族，先查重。
