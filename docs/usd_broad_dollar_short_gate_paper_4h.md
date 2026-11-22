# 美元广义指数做空闸门（FRED DTWEXBGS N20 short_on）——4h 默认书纸面实现（2026-11-22）

状态：**观察 → 纸面前向检验**（不改默认，默认关闭）。新增可选参数 `usd_gate_*`（回测与模拟盘 / 实盘同一函数 `qtw/usd_gate.py`），
独立纸面实例 `127.0.0.1:8796 paper-usdgate`（只做纸面，实盘强制关闭，已加入 paper watchdog 保活）。没有新的参数扫描。

## 来源

2026-11-14 长线研究「美国宏观风险体制闸门」（`docs/STRATEGY_FORMULAS.md` 同名节；`scratch/macro/run.py`、`scratch/macro/nb.py`；
`output/research_us_macro_risk_regime_gate_4h.csv`、`_dollar_nbhd.csv`）：DTWEXBGS N20 short_on 胜 8/9 格，post 段三套数据都 +12 点左右，
但 OKX d7 深历史未见段输、调参前段的增益平移安慰剂也能拿到、对发布滞后敏感（按 14 天已知时 post 只剩 +0 ~ +3 点）→ 列观察。
按 kean 的 t90u 规则（值得前向检验的观察候选必须在官方实时数据上真正纸面交易），本次只做纸面实现。

## 公式

- 数据：FRED `DTWEXBGS` = 美联储 H.10 名义广义美元指数（日度，每周一发布上一周）。只用真实返回值，空值行（美国假日）丢弃。
- `v_d` = 观测日 d 的值；`ma_d` = 最近 n 个有值观测（含 d）的简单均值（= pandas `rolling(n).mean()`），默认 n = 20；不足 n 个 → NaN。
- 可用时刻 `known_d = d + lag_days 天 00:00 UTC`，默认 10 天（保守覆盖周一发布 + 节假日）。
- 闸门：在信号 K 线开盘时间 t 上取 `known ≤ t` 的最新观测；`v − ma ≤ 0`（美元不高于 20 观测均线 = 走弱 / 风险偏好上升）时**不新开空单**
  （包括反手开空）。已有持仓不动，多单不受影响。研究脚本里 `off = v > ma`，short_on 拦空 = `not off`，所以相等时也拦（实际几乎不会相等）。
- 执行口径：与其它闸门一致，第 i 根开盘入场用第 i−1 根（信号 K 线）开盘时间上的状态；回测并入 `DBS`（与方向偏置拦空同一位置）。
- 失败开放：取不到数据 / 最新已知观测的 known 早于 t − stale_days（默认 14 天）/ 历史不足 n 个 → 不拦，并记日志。

## 参数（`strategy.*`，风控 → 策略参数可改，保存后热加载）

| 键 | 默认 | 说明 |
| --- | --- | --- |
| `usd_gate_enabled` | `false` | 总开关；环境变量 `QTW_USD_GATE=1` 强制开启（纸面实例用） |
| `usd_gate_n` | `20` | 均线观测数，5–200 |
| `usd_gate_lag_days` | `10` | 观测日 + N 天才算已知，3–30 |
| `usd_gate_stale_days` | `14.0` | 失败开放的过期阈值，5–60 天 |

`/api/signals` 返回 `usd_gate`（enabled / value / ma / diff / obs_date / known_from / latest_obs_date / blocked / fail_open / n_obs / error），
每行有 `usd_diff`、`usd_block_short`，被拦时 `state = "usd_wait"`。回测 summary 有 `usd_gate`（blocked_bars / nan_bars / bars）；
`run_backtest(..., usd_data=(观测日毫秒, 值))` 可注入真实历史。

## 数据源与缓存

- `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS&cosd=2006-01-01`（公开、免 key）。
  实测：不带 `cosd` 的全量请求在本机会挂起；自定义 User-Agent（`qtw/1`、浏览器 UA）也会挂起超时，Python 默认 UA 正常（< 0.1 秒），所以代码不设自定义 UA。
- 2026-11-22 拉取 5,231 个观测（2006-01-02 → 2026-11-13），与研究存档 `scratch/macro/DTWEXBGS.csv`（到 2026-11-06）逐日相同、没有修订，只是多了 4 个新观测。
- 缓存：`DATA_DIR/fred_DTWEXBGS.csv`（data/ 不入库）；运行中每 6 小时自动刷新（无需重启），数据过旧时每 15 分钟重试；失败时用已有缓存并记日志。

## 同脚本 sanity 回测（不扫参）

`scratch/usdgate/sanity.py` → `output/research_usd_gate_paper_impl_4h.csv`。官方 OKX / Gate 4h 数据（`scratch/deep`，到 2026-11-14 00:00 UTC），
默认参数，基线 vs 基线 + `usd_gate_enabled`（入场层实现），另附研究脚本的信号层写法做对照。收益 %，Sharpe 为日 Sharpe。

| 样本 | 变体 | post（2026-03-05→）收益 / 回撤 / Sharpe | post 逐月 好 / 差 | post 开仓数（其中空） | 调参前段 收益 | 深历史未见 收益 / Sharpe |
| --- | --- | --- | --- | --- | --- | --- |
| OKX d8 | 基线 | +59.90 / −10.61 / 2.234 | — | 59（45） | +85.08 | +35.14 / 0.714 |
| OKX d8 | + 美元闸门 | +72.60 / −10.60 / 2.594 | 5 / 3 | 44（30） | +106.13 | +48.22 / 0.891 |
| Gate d8 | 基线 | +60.32 / −10.55 / 2.250 | — | 59（45） | +84.25 | −3.63 / 0.091 |
| Gate d8 | + 美元闸门 | +73.26 / −10.59 / 2.614 | 5 / 3 | 44（30） | +104.01 | +4.80 / 0.205 |
| OKX d7 去 BNB | 基线 | +50.76 / −10.05 / 2.104 | — | 53（40） | +92.93 | +54.92 / 0.748 |
| OKX d7 去 BNB | + 美元闸门 | +62.69 / −10.07 / 2.497 | 6 / 2 | 40（27） | +107.58 | +29.55 / 0.519 |

- post 段与 2026-11-14 研究数字完全一致（OKX +72.6% vs +59.9%，Gate +73.3% vs +60.3%，d7 +62.7% vs +50.8%），说明接线复现了研究。
- 入场层实现与研究信号层写法的 post / 深历史段相同；调参前段入场层高约 5–6 点（两种写法在止损后同向再入场时略有差别）。
- 深历史未见段 d7 仍输（+29.55 vs +54.92），这正是没有改默认的原因。

## 纸面实例

- `127.0.0.1:8796`，数据目录 `data/paper-usdgate`（自己的 SQLite），输出 `output/paper-usdgate`，日志 `/workspace/scratch/logs/paper-8796.log`。
- 启动：`data/paper-usdgate/run.sh`（幂等；环境 `QTW_ALLOW_LIVE_ORDERS=0 QTW_USD_GATE=1`，实盘强制关闭，不连交易所模拟盘）。
- 账本：1000 U 起始，币种 / 参数与 8788 paper-default（默认 #1）相同，只多开美元闸门。
- 2026-11-22 08:16 PST 开账；08:17 PST 首轮开 8 个空单（8 币信号全为空）。首轮开仓时 FRED 请求因自定义 UA 超时，闸门处于失败开放；
  修正 UA 并重启后核对：信号 K 线开盘 2026-11-22 12:00 UTC 上最新已知观测 2026-11-12 = 122.5433 > MA20 121.6115（差 +0.9318）→ **不拦**，
  所以这 8 个空单在闸门正常时也会开，结果不受影响。
- 预期：只有在美元跌回 20 观测均线以下、同时出现新的空头入场信号时，8796 才会与 8788 不同（少开空）。
- 战绩由本地 `/workspace/scratch/zhanji/report.py` 汇总（已加入 8796 行）；`output/paper_candidates_log.csv` 追加记录。

## 复核规则

不改默认。只用 2026-11-22 之后的前向纸面数据（8796 vs 8788）复核；**不要**以改 n / lag / 方向、换序列（DXY、EUR/USD、其它 H.10 指数）
或换起点的方式在现有历史上重测本族。
