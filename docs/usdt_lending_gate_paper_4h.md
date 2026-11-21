# OKX USDT 借贷利率体制闸门 —— 纸面前向检验（4h 默认书，2026-11-21 起）

状态：**弱观察族的纸面前向检验**（不改默认，默认关闭）。研究原文见 `docs/STRATEGY_FORMULAS.md`
「长线新族：OKX 官方 USDT 借贷利率（杠杆需求）体制闸门」（2026-11-14 ~13:50 PST）。本轮**不重跑参数扫描**，只固定
研究里的 `long W30 z1.0` 变体，放进独立纸面实例，用实时官方数据看 2026-03 后的失效是否持续。

## 公式（回测与模拟盘同一函数 `qtw/lending.py: block_mask / zscore_at`）

- `r(t)`：时间戳 ≤ t 的最近一条 OKX 小时 `lendingRate`（年化；小时网格前向填充）。
- `z(t) = (r(t) − mean_W) / std_W`，W = 30 天 = 720 个小时点（至少 360 个点才有值），样本标准差 ddof = 1。
- t = **信号 K 线（最近已收盘的 4h K 线）的开盘时间**。回测第 i 根开盘入场用第 i−1 根的信号和 `z(open_{i−1})`；
  模拟盘在第 i−1 根收盘后决策，也用 `z(open_{i−1})`。与研究脚本 `scratch/lend/run.py` 的
  `f.reindex(idx, method="ffill")` 逐位同口径（在研究 CSV 2022-01→2026-11 的 4h 网格上与 pandas 版 z 最大差 4.9e-7，拦截位 0 处不同）。
  只用 ts ≤ t 的利率，没有前视。
- 闸门：`z > q`（q = 1.0）时**不新开多单**（含反手开多 / 止损反手多）；已持多单不平，空单不受影响。
- 失败开放：取不到数据、最新一条利率早于 t − 6h（`lending_gate_stale_hours`）、历史不足 360 点 → z = NaN → 不拦，并写 warning 日志。

## 数据源

- OKX 官方公共接口（不需要密钥）：`GET /api/v5/finance/savings/lending-rate-history?ccy=USDT&limit=100[&after=<ts>]`，
  域名按 `qtw/net.okx_rest_bases()`（openapi.okx.com → www.okx.com）。`after` 向更早分页，每页 100 条。
- 缓存：`$QTW_DATA_DIR/okx_usdt_lending_rate_1h.csv`（data/ 不入库）。首次回补 ≥ 45 天（30 天窗口 + 余量），之后每小时增量刷新；
  最新一条落后 > 2h 时每 5 分钟重试。只保存接口真实返回值，不补造。回测若需要更早历史会按需向前回补到 2021-12-14。

## 设置

| 键（`strategy.*`） | 默认 | 说明 |
| --- | --- | --- |
| `lending_gate_enabled` | `false` | 开关（默认关，默认书不变） |
| `lending_gate_window_days` | `30` | W，7–180 天 |
| `lending_gate_z` | `1.0` | q，0.25–5 |
| `lending_gate_side` | `"long"` | 只支持 long（拦新开多） |
| `lending_gate_stale_hours` | `6.0` | 失败开放的过期阈值，1–72 小时 |

环境变量 `QTW_LENDING_GATE=1`：`settings.load()` 强制 `lending_gate_enabled = true`（纸面检验实例用）。
`/api/signals` 返回 `lending_gate`（enabled / z / rate / rate_time / eval_open / blocked / fail_open / n_rates），
每行有 `lending_z`、`lending_block_long`，被拦时 `state = "lending_wait"`。回测 summary 有 `lending_gate`（blocked_bars / nan_bars / bars）。

## 回测预期（摘自 `output/research_usdt_lending_rate_regime_4h.csv`，收益 %，Sharpe 为日 Sharpe）

段：深历史未见（OKX d8 2023-02→2024-10-21；Gate d8 2022-07→；OKX d7 去 BNB 2022-01→）/ 调参前段（2024-10-21→2026-03-05）/ post（2026-03-05→2026-11-14）。

| 样本 | 变体 | 深历史 收益 / Sharpe | 调参前段 收益 / Sharpe | post 收益 / 回撤 / Sharpe | post 逐月 好 / 差 |
| --- | --- | --- | --- | --- | --- |
| OKX d8 | 基线 | +35.14 / 0.714 | +85.08 / 1.466 | +59.90 / −10.61 / 2.234 | — |
| OKX d8 | long W30 z1.0 | +46.84 / 0.852 | +95.14 / 1.584 | +41.85 / −13.37 / 1.711 | 2 / 2 |
| Gate d8 | 基线 | −3.63 / 0.091 | +84.25 / 1.456 | +60.32 / −10.55 / 2.250 | — |
| Gate d8 | long W30 z1.0 | +4.46 / 0.208 | +92.39 / 1.556 | +42.55 / −13.08 / 1.737 | 2 / 2 |
| OKX d7 | 基线 | +65.26 / 0.769 | +92.93 / 1.558 | +50.76 / −10.05 / 2.105 | — |
| OKX d7 | long W30 z1.0 | +84.80 / 0.893 | +102.20 / 1.671 | +37.58 / −12.93 / 1.621 | 2 / 2 |

平移 90 天安慰剂（`PLC_long_W30_z1.5_shift90d`）深历史 OKX d8 +34.91 / Gate +0.26 / d7 +64.98，基本等于基线。
预期：如果 2026-03 后的失效是常态，纸面账本会在利率冲高（z > 1）时错过多头趋势，跑输 8788；如果只是 post 段偶然，则在过热时少追高、回撤更浅。

## 纸面设置

- 实例：`127.0.0.1:8793`，数据目录 `data/paper-lendgate`（自己的 SQLite），输出 `output/paper-lendgate`，日志 `/workspace/scratch/logs/paper-8793.log`。
- 启动：`data/paper-lendgate/run.sh`（幂等：健康且 `live_gate_open:false` 时直接退出；端口被别的进程占用时不启动），
  环境 `QTW_ALLOW_LIVE_ORDERS=0 QTW_LENDING_GATE=1`，实盘强制关闭。
- 账本：1000 U 起始，币种 / 参数与 8788 paper-default（默认 #1 双均线 50/150，8 币，perp_both 10×，BTC 体制 1200 等）完全相同，只多开借贷利率闸门。
  注意：8793 于 2026-11-21 11:39 PST 才开账，入场价与 8788 不同，比较时看同期增量。
- 启动时闸门状态：信号 K 线开盘 2026-11-21 12:00 UTC（04:00 PST）的 r = 0.0259，z = −0.97，不拦；缓存 1100 条（2026-10-07 00:00 → 2026-11-21 19:00 UTC，连续无缺口）。
  当时 8 币信号全为空，闸门不影响（只拦多）。
- 战绩由本地 `/workspace/scratch/zhanji/report.py` 汇总（已加入 8793 行，不并入三本对照合计）；`output/paper_candidates_log.csv` 追加记录。
