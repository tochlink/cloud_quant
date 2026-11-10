# QTW 量化交易控制台 v2（OKX / Gate.io · 页面版）

面向 kean 的**系统化**加密货币交易 Web 控制台：配置 OKX 或 Gate.io API Key、真实历史回测、做多 / 做空 / 现货进出场时机、后台自动买卖（默认纸面）。
界面视觉按 kean 提供的参考稿实现：彩色渐变底 + 悬浮圆角平板 + 深紫胶囊侧栏 + 卡片 / 快速摘要 / 右侧列表。

> ⚠️ **这是系统化纸面 / 研究工具，不构成投资建议。实盘交易可能亏损全部本金。**
>
> **数据：只用 OKX / Gate.io 官方公共接口的真实行情，纸面交易与回测都不需要 API Key；不使用任何模拟 / 合成 / 插值数据，请求失败直接报错。**
> 默认 **纸面模式**；实盘需要通过五道闸门（见下文），本版本开发与测试中**从未发送过任何实盘或交易所模拟盘订单**。

## 一键启动

```bash
cd /workspace/quant-trading-web
./start.sh            # 首次自动创建 .venv 并安装依赖；若已在跑则幂等退出
./ensure_up.sh        # 24/7 保活：health 已 ok 则跳过，否则 nohup 后台拉起并写 data/qtw.pid / data/server.log
# 打开 http://127.0.0.1:8787
```

可选：`QTW_PORT=9000 ./start.sh` 换端口；`QTW_MASTER_PASSPHRASE='你的口令' ./start.sh` 用口令派生主密钥（见“密钥存储”）。`ensure_up.sh` 默认强制 `QTW_ALLOW_LIVE_ORDERS=0`（除非你事先已显式 export=1）。

命令行（不开页面也能用）：

```bash
.venv/bin/python -m qtw backtest --venue okx --bars 1500   # 回测并写 CSV
.venv/bin/python -m qtw signals                              # 打印当前信号
.venv/bin/python -m qtw cycle                                # 执行一次纸面调仓
.venv/bin/python -m pytest -q                                # 单元测试
```

## 页面

| 侧栏 | 页面 | 内容 |
|---|---|---|
| 🏠 | 总览 | 问候语、账户切换（模拟盘 / 交易所）、模拟权益 / 可用现金 / 选择交易所卡片、“+ 配置 API Key”、最近成交与本周摘要、权益 / 盈亏 / 回撤·胜率 / 敞口 四个快速摘要图 |
| ▦ | 信号 / 进出场 | 每个币：做多 / 做空 / 空仓、建议市场（现货多 / 永续空）、入场时机、离场与止损时机、建议名义 / 权重 / 风险、K 线 + 均线 + 交叉标记；导出 signals.csv |
| 📅 | 回测 | 交易所、K 线根数、均线与止损参数；总收益、期末权益、最大回撤、夏普、胜率、盈亏比、基准；权益 + 回撤曲线；逐笔入场 / 离场时间；三份 CSV |
| ◔ | 持仓 | 持久化纸面持仓、止损价、权重、未实现盈亏；CSV |
| 🧾 | 成交 | 纸面成交明细、订单路由日志（纸面 / 实盘被拦截原因）；CSV |
| 🛡 | 风控 / 自动交易 | 开关后台自动交易、检查间隔、立即执行、紧急停止、重置账本；风控参数、策略参数、标的池编辑 |
| ⚙ | API / 设置 | OKX（API Key / Secret / Passphrase / 模拟盘开关）、Gate（API Key / Secret / 合约测试网），加密保存、掩码显示、只读连接测试、删除；实盘开关与闸门状态 |
| ? | 帮助 | 规则、风控、局限说明 |

右侧面板：持仓（无持仓时显示关注币种）+ 搜索 + 底部提醒卡（最新信号 / 风险提示 / 紧急停止）。

## 已约定规则

| 项目 | 设定 |
|---|---|
| 标的池 | BTC / ETH / BNB / SOL / XRP / ADA / DOGE / AVAX 的 USDT 对（页面可改） |
| 行情 | OKX 或 Gate.io 官方**公共** REST（无需密钥） |
| 起始纸面资金 | 1000 USDT |
| 品种 | 现货做多 + USDT 永续做空（**1 倍保证金，不放大**） |
| 单笔最大风险 | 权益 × 5%（只可调低） |
| 单币最大权重 | 20%（只可调低） |
| 总敞口 | ≤ 1 × 权益；同时入场多个币时等比缩放 |
| 手续费假设 | taker 4 bps |
| 交付格式 | CSV |
| 界面时区 | Asia/Shanghai（北京时间）；API 另附 `*_la`（美西）与 `*_sh`（北京时间） |

## 策略：`dual_ma_trend_4h_v1`

* 只用**已收盘**的 4h K 线（OKX 用 `confirm=1`，Gate 用 `window_closed=true`，并再按收盘时间二次过滤）。
* SMA20 > SMA60 → **做多 → 现货**；SMA20 < SMA60 → **做空 → USDT 永续**；否则空仓。
* 仓位：`名义 = 权益 × 5% ÷ (2 × ATR14 / 价格)`，再受 20% 权重与总敞口限制。
* 入场：信号生效后的下一个执行周期，按最新公共价（现货最新价 / 永续标记价）成交。
* 离场：收盘出现反向或归零信号；或价格触及 **入场价 ∓ 2×ATR** 止损。止损后保持空仓，直到信号方向改变。
* 回测：第 t 根收盘信号 → 第 t+1 根**开盘**成交；止损按盘中高低价检查；权益按收盘价计价（单元测试验证无前视）。

## 实时行情（官方公共 WebSocket，无需 Key）

| 交易所 | 连接 | 频道 |
|---|---|---|
| OKX | `wss://ws.okx.com/ws/v5/public`（优先；回退 `:8443` / `wsaws`） | `tickers`（现货）、`mark-price`（永续） |
| OKX | `wss://ws.okx.com/ws/v5/business`（同上回退） | `candle4H`（现货 + 永续） |
| Gate | `wss://api.gateio.ws/ws/v4/` | `spot.tickers`、`spot.candlesticks` |
| Gate | `wss://fx-ws.gateio.ws/v4/ws/usdt` | `futures.tickers`（mark_price）、`futures.candlesticks` |

* 两个交易所都订阅整个标的池；断线指数退避自动重连；任何价格 20 秒没有 WS 更新就改用官方 REST 拉取（`*_public_rest`）。 REST 填隙**优先当前纸面行情源**（`settings.venue`），同批有限并发，僵尸踢掉后纸面标记价不必排在另一所串行 REST 后面。监控别名 `GET /api/paper/book` 与 `GET /api/paper/snapshot` 与 `/api/paper` 同载荷；`GET /api/market/status` ≡ `/api/stream/status`；`GET /api/config` ≡ `/api/settings`（无密钥）。 纸面快照另附 `book_capital`（= `realized` 账面资本）与 `realized_pnl`（= 账面资本 − 起始资金）。 FastAPI 启停改用 lifespan（替代已弃用的 `on_event`），关闭时会停止 worker / 行情 supervisor，并 **join** mark-persist（含盘中止损轮询）且做一次最终标记价落盘，避免清空纸面账本单例时仍有线程在写。`/api/health` 另暴露 `persist_running`、`stream.ws_conn_max_age_sec`、`stream.early_stall_fill_count` / `last_early_stall_fill_*`。 asyncio 循环真卡死时，watchdog 在**后台线程**走官方 REST 填隙（不依赖已冻结 loop 上的 `run_coroutine_threadsafe`，也不阻塞 watchdog 自己每 2 秒的扫描），带合并与约 15 秒冷却，纸面标记价可在踢僵尸之前恢复。WebSocket 握手关闭代理自动探测并只用 IPv4，减轻四路同时重连时的 DNS/代理卡顿。
* **有纸面持仓时不能切换行情源（OKX ↔ Gate）**：入场价 / 止损 / 标记价必须来自同一交易所公共行情；请先紧急停止平仓或重置账本后再切换。加载账本时会把旧持仓缺失的 `venue` 从开仓成交记录回填。
* 心跳：OKX 文本 `pong`、Gate JSON（`channel` 以 `.pong` 结尾，例如 `spot.pong` / `futures.pong`）都算连接活跃并刷新 `last_msg`，不交给行情处理函数。recv 超时会先再发一次应用层 ping 并多等一轮，避免短暂静默就重连。发出订阅 / ping 也有超时，半开连接导致 send 挂起时会主动重连。 已收盘 K 线写库走线程池，避免 SQLite/WAL 卡住事件循环；`status` 把「已连接但 last_msg 过旧」标为 `stale`（无响应）；supervisor 对僵尸套接字优先 `transport.abort()` 硬中断（并行踢掉、短超时 close 兜底），避免 close 握手挂起导致重连卡住；连接成功即写入 `last_msg`，空 `last_msg` 用 `connected_at` 计龄；踢掉后立刻官方 REST 填一次过期报价，不等 10 秒轮询。 supervisor 读配置经线程池，避免 `S.load()`/SQLite 锁卡住事件循环。REST 填隙走独立 IO 线程池 + 短超时报价，并在填隙期间刷新心跳；`rest_fill_inflight` 时 watchdog 不把心跳迟滞当成 loop stall（仍踢超过 ZOMBIE+宽限的真僵尸），避免填隙误杀重连中的套接字。recv/pong 也刷新 loop heartbeat；真 stall 用更短 `STALL_ZOMBIE_SEC` 踢套接字并在后台线程提前 REST 填隙（`EARLY_FILL_COOLDOWN_SEC` 冷却，避免 watchdog 被 32 路 HTTP 堵住）；`rest_fill_inflight` 卡住超过 `FILLING_STALL_SEC` 会取消护盾。握手显式 `proxy=None` + IPv4。另有侧线程 watchdog：当 asyncio 心跳过旧或僵尸套接字超过 ZOMBIE+宽限仍未被踢掉时，先 `shutdown` 底层 TCP 套接字（线程安全），再经 `call_soon_threadsafe` 在行情循环上 `transport.abort()`，由 `connection_lost` 关闭 `recv_messages`；不要在 watchdog 线程直接调用 `set_recv_exc` / `recv_messages.close`，否则会与 `SSLProtocol._do_read` 竞态并触发 `Fatal error on SSL protocol`（2026-11-10 07:11 CST+8 踢除后紧接着 07:12 出现 98 秒 loop stall）。abort 仍失败时再 threadsafe 调度 `close()`，同时调度 REST 填隙。`start()` 在行情线程已存活时也会补拉 watchdog。纸面 `mark` 报价回调经单线程队列旁路，不在 asyncio 线程同步拿 `PaperBook` 锁，避免写库拖死 recv/ping/僵尸踢除。`/api/stream/status` 与 `/api/health` 暴露 `watchdog_running` / `loop_heartbeat_age_sec`。顶部行情 pill 只按当前行情源（OKX / Gate）的连接判断「无响应」，不会被另一所的 stale 误伤。WebSocket 握手除库自带 `open_timeout` 外再包一层超时，避免 DNS / 半开 TCP 让单条连接的状态一直停在 `connecting`。
* `stream.mode` 与 `quotes_ws_fresh` / `quotes_rest_fresh` 按当前行情源（`settings.venue`）统计：OKX 标记价全部来自 REST 时，不会因为 Gate 的 WebSocket 仍在线而显示 `mode=ws`。顶部行情 pill 与该口径一致（只按当前所判断无响应 / 实时 / 恢复中 / REST 兜底）。`mode` 仍带迟滞：`ws`（当前所有新鲜 WS 报价）→ `recovering`（该所插座仍在 / 刚重连、REST 短暂填隙）→ `rest`（该所 WS 路径真正不可用、仅 REST）→ `down`。重连风暴时不会立刻误报「REST 兜底」。
* 收盘确认的 K 线（`confirm=1` / `w=true`）写入 SQLite `candles` 表（`data_source=okx_public_ws / gate_public_ws`）；未收盘 K 线只用于图表最后一根的实时跳动。
* 纸面持仓按同一交易所、同一市场的实时价格计价（现货多 → 现货最新价，永续空 → 永续标记价），每 15 秒落库；落库后对 SQLite WAL 做 `PASSIVE` checkpoint（不阻塞并发读），约每 5 分钟再尝试 `TRUNCATE` 真正缩小 `-wal` 文件（此前仅 PASSIVE 时曾观察到数 MB 的空 WAL）。约每 10 分钟裁剪 K 线缓存（每序列保留最近 1200 根）与账本快照（保留最近约 7 天），避免 24/7 无限膨胀。`mark()` 与落库共用锁，避免 WS 计价与 `save` 竞态。
* 页面通过 **SSE `/api/stream`** 每 1.5 秒收到更新：顶部状态（实时 / 部分重连 / 恢复中 / REST 兜底）、右栏价格与盈亏、总览权益、信号卡片价格、K 线最后一根。
* 冒烟：`GET /api/health` 返回 `ok`、纸面/实盘 `mode`、`venue`、`live_enabled` / `live_gate_open`、`stream.mode`（含 recovering）/ `stream.running`、`quotes_ws_fresh`、`watchdog_running` / `loop_heartbeat_age_sec` / `rest_fill_inflight` / `stall_suspect_count` / `host_freeze_count` / `last_host_freeze_gap_sec`（看门狗线程自身 >15s 未运行＝主机/进程被冻结，如虚拟机暂停；随后的 stall 恢复是冻结后恢复，并非行情代码故障；若自动交易开启，恢复后会立刻补跑一轮信号与止损检查，不等下一个周期） / `last_zombie_kick_age_sec` / `last_zombie_max_age_sec`、`worker.running`、`persist_running`、精简 `paper`（equity / positions / starting_equity）、`btc_perp`（标记价 / age / source）、`time` / `time_sh`；不含密钥或完整设置。`ensure_up.sh` 与 10 分钟打磨例程用它做保活探测；`ensure_up.sh` 还要求 `live_enabled` 与 `live_gate_open` 均为 false 才算 healthy。
* 监控只读别名（复用现有数据，不另造行情或账本计算）：
  * `GET /api/paper` — 纸面账本快照（权益、敞口、持仓、近期成交、账本）
  * `GET /api/positions` — 当前持仓与权益 / 敞口
  * `GET /api/quotes` — 当前行情源的实时报价（`stream.snapshot`，含扁平 `quotes` 列表）
  * `GET /api/risk` — 风控规则与当前单币权重 / 总敞口是否越界
  * `GET /api/worker/status` — 自动交易线程状态（亦接受 `POST /api/worker/status`；避免误打 GET 撞上 `POST /api/worker/{action}` 返回 405）
* 后台 `worker.status` 含 `last_run` / `last_run_la` / `last_run_sh`（上海时间 CST+8）。尚未排出下次执行时间（首轮进行中，或上一轮 deadline 已过、正在跑周期）时，`next_run_in_sec` 为 `null`，不再误报「0 秒后」。

## 自动交易与紧急停止

* 后台线程**随服务 7×24 运行**（默认开启，每 60 秒一次）：读真实行情 → 算信号 → 查止损 → 纸面调仓 → 写 SQLite 并导出 CSV。
* **紧急停止（Kill Switch）**：立即停止线程、关闭实盘开关并切回纸面、按最新公共价平掉全部纸面持仓（拿不到报价时用最后一次标记价，并在成交里注明）。紧急停止**不会**向交易所发单。

## 实盘闸门（全部满足才会真正发单）

1. 页面选择“实盘”模式并打开实盘开关；
2. 输入确认语：`我已了解实盘交易可能亏损全部资金`；
3. 启动进程时设置环境变量 `QTW_ALLOW_LIVE_ORDERS=1`；
4. 当前交易所的 API 密钥完整（OKX 三项 / Gate 两项）；
5. 未设置 `QTW_FORBID_LIVE=1`（测试与冒烟时强制禁止）。

任一不满足，调仓只在纸面执行，并在“成交 → 订单路由日志”中记录 `blocked` 与原因。
实盘代码隔离在 `qtw/live/`：OKX v5 签名（HMAC-SHA256 + base64，`x-simulated-trading: 1` 为模拟盘），Gate APIv4 签名（HMAC-SHA512），永续开仓前先设 1 倍杠杆（逐仓）。

## 密钥存储

* 密文：`data/secrets.enc`（Fernet：AES-128-CBC + HMAC-SHA256），文件权限 600。
* 主密钥二选一：
  * 默认：本地密钥文件 `data/vault.key`（首次自动生成，权限 600）；
  * 或：启动时设置 `QTW_MASTER_PASSPHRASE`，用 scrypt + `data/vault.salt` 派生，主密钥不落盘。
* `data/`、`*.enc`、`*.key`、`.env` 已在 `.gitignore`；密钥不写入 CSV / 日志（日志有脱敏过滤），前端只拿到 `abcd••••••wxyz` 形式的掩码，Secret / Passphrase 永不回显。
* 建议在交易所创建 API 时**不开提现权限**，并绑定 IP 白名单。

## SQLite 数据库

`data/qtw.sqlite`（标准库 sqlite3，WAL 模式，`data/` 已在 .gitignore）。表：

| 表 | 内容 |
|---|---|
| `candles` | 真实公共 K 线缓存（venue / market / symbol / interval / open_time / OHLCV / data_source / source_host / fetched_at） |
| `paper_state` `paper_positions` `paper_blocks` | 纸面账本状态、持仓（含标记价来源）、止损锁 |
| `paper_fills` `paper_ledger` `orders` | 纸面成交（含价格来源与时间）、权益快照、订单路由日志 |
| `backtest_runs` `backtest_equity` `backtest_trades` | 每次回测的参数、指标、数据来源、权益曲线、逐笔交易 |
| `settings` `meta` | 非敏感设置、迁移标记 |

**API 密钥永远不进数据库**（只在加密的 `data/secrets.enc`）。首次启动时，旧版 `data/paper/*.csv` 账本会自动导入 SQLite，原目录改名为 `data/paper.migrated-to-sqlite` 作为备份。

## 输出 CSV（`output/`）

| 文件 | 内容 |
|---|---|
| `signals.csv` | 每币信号、建议市场、参考价、均线、ATR、截至时间、建议仓位、止损、入场 / 离场时机 |
| `paper_positions.csv` | 当前纸面持仓 |
| `paper_fills.csv` | 纸面成交明细（价格来源、手续费、已实现盈亏、原因） |
| `paper_ledger.csv` | 每个周期的权益 / 现金 / 敞口快照 |
| `paper_orders.csv` | 订单路由日志（纸面 / 实盘被拦截原因） |
| `backtest/backtest_summary.csv` | 回测指标 |
| `backtest/backtest_equity.csv` | 回测权益、回撤、敞口序列 |
| `backtest/backtest_trades.csv` | 回测逐笔交易（入场 / 离场时间与价格、原因） |

CSV 均带 `venue` / `data_source` / `fetched_at` 等来源字段。纸面账本本体在 SQLite 中，**重启不丢失**。

## 已知局限

* 回测未计资金费率、滑点与强平；历史表现不代表未来。
* OKX `history-candles` 每次 100 根，首次长回测需要数秒到数十秒（已做 2 分钟缓存与 4 并发）。
* 实盘模式按纸面账本的调仓意图发单，**没有与交易所实际持仓 / 成交对账**，也不处理部分成交；实盘前请先在 OKX 模拟盘或 Gate 合约测试网验证。Gate 现货没有测试网。
* 仅监听 127.0.0.1，没有登录鉴权；不要暴露到公网。
* OKX WebSocket 优先连 443 端口官方地址；若失败再回退 :8443 / wsaws（部分网络会重置 8443）。
* 持仓 ATR 止损除了后台周期检查外，还会在标记价持久化线程里约每 15 秒用最新公共价轮询一次，缩短止损延迟。
* 信号确认（`confirm_bars`，默认 2）：原始 SMA 方向需连续 N 根已收盘 K 线一致才算有效，否则视为空仓。2026-11-10 在 OKX 与 Gate 官方 4h 历史上做 3 段滚动样本外验证，6 个样本外窗口均优于 1（研究脚本输出不入库）。
* 趋势过滤（`trend_ma`，默认 100，0=关闭）：**只作用于新开仓**，做多需上一根收盘价 > 该市场（现货）SMA100，做空需上一根收盘价 < 该市场（永续）SMA100；不会因此平掉已有持仓，离场仍只看信号反转 / 归零与 ATR 止损。2026-11-10 在 OKX 与 Gate 官方 4h 历史上切 6 段不重叠窗口：只用前 3 段从 {关闭, 100, 200, 300} 中选出 100，后 3 段（未参与选择）在两家交易所、单边 4 / 14 bps 成本下累计收益均高于不过滤（OKX 4bps +12.0% vs +10.4%，14bps +8.9% vs +6.8%）；整段 OKX +34.1% vs +24.7%，Sharpe 1.59 vs 1.27，最大回撤 −17.1% vs −19.0%。注意第 3 段更差（−7.2% vs −4.6%），并非每段都胜出。
* 界面自适应：侧栏与平板同在一个网格里随窗口 / 缩放一起伸缩；≤1180px 右栏变成抽屉（顶部按钮打开），≤760px 底部胶囊导航。
* 若某交易所在你所在地区被限制（HTTP 403 / 451），客户端会尝试官方备用域名（OKX `aws.okx.com`，Gate `api.gate.io`），仍失败就报错——**绝不伪造行情**。

## 目录

```
qtw/market/   OKX / Gate 公共 REST 行情、SQLite K 线缓存
qtw/stream.py 官方公共 WebSocket 实时行情 + REST 兜底
qtw/db.py     SQLite 模式与连接
qtw/strategy.py  dual_ma 指标与信号
qtw/risk.py      仓位与风控
qtw/backtest.py  组合回测
qtw/paper.py     持久化纸面账本（SQLite）
qtw/engine.py    信号 → 进出场 → 执行路由、紧急停止
qtw/worker.py    后台自动交易线程
qtw/vault.py     密钥加密存储
qtw/live/        实盘签名与下单（闸门保护）
qtw/app.py       FastAPI 接口
static/          前端页面（原生 JS + lightweight-charts）
tests/           单元测试
```

旧版命令行纸面系统仍在 `/workspace/quant-trading-system/`（Binance 行情，v1）。
