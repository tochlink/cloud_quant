# QTW 量化交易控制台 v2（OKX / Gate.io · 页面版）

面向 kean 的**系统化**加密货币交易 Web 控制台：配置 OKX 或 Gate.io API Key、真实历史回测、做多 / 做空 / 现货进出场时机、后台自动买卖（默认纸面）。
界面视觉按 kean 提供的参考稿实现：彩色渐变底 + 悬浮圆角平板 + 深紫胶囊侧栏 + 卡片 / 快速摘要 / 右侧列表。

> ⚠️ **这是系统化纸面 / 研究工具，不构成投资建议。实盘交易可能亏损全部本金。**
> 默认 **纸面模式**；实盘需要通过五道闸门（见下文），本版本开发与测试中**从未发送过任何实盘或交易所模拟盘订单**。

## 一键启动

```bash
cd /workspace/quant-trading-web
./start.sh            # 首次自动创建 .venv 并安装依赖
# 打开 http://127.0.0.1:8787
```

可选：`QTW_PORT=9000 ./start.sh` 换端口；`QTW_MASTER_PASSPHRASE='你的口令' ./start.sh` 用口令派生主密钥（见“密钥存储”）。

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

## 策略：`dual_ma_trend_4h_v1`

* 只用**已收盘**的 4h K 线（OKX 用 `confirm=1`，Gate 用 `window_closed=true`，并再按收盘时间二次过滤）。
* SMA20 > SMA60 → **做多 → 现货**；SMA20 < SMA60 → **做空 → USDT 永续**；否则空仓。
* 仓位：`名义 = 权益 × 5% ÷ (2 × ATR14 / 价格)`，再受 20% 权重与总敞口限制。
* 入场：信号生效后的下一个执行周期，按最新公共价（现货最新价 / 永续标记价）成交。
* 离场：收盘出现反向或归零信号；或价格触及 **入场价 ∓ 2×ATR** 止损。止损后保持空仓，直到信号方向改变。
* 回测：第 t 根收盘信号 → 第 t+1 根**开盘**成交；止损按盘中高低价检查；权益按收盘价计价（单元测试验证无前视）。

## 自动交易与紧急停止

* 后台线程默认**关闭**；开启后每 `interval_sec`（默认 300 秒）执行一次：拉行情 → 算信号 → 查止损 → 纸面调仓 → 写 CSV。
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

## 输出 CSV（`output/`）

| 文件 | 内容 |
|---|---|
| `signals.csv` | 每币信号、建议市场、参考价、均线、ATR、截至时间、建议仓位、止损、入场 / 离场时机 |
| `paper_positions.csv` | 当前纸面持仓 |
| `paper_fills.csv` | 纸面成交明细（价格来源、手续费、已实现盈亏、原因） |
| `paper_ledger.csv` | 每个周期的权益 / 现金 / 敞口快照 |
| `backtest/backtest_summary.csv` | 回测指标 |
| `backtest/backtest_equity.csv` | 回测权益、回撤、敞口序列 |
| `backtest/backtest_trades.csv` | 回测逐笔交易（入场 / 离场时间与价格、原因） |

纸面账本本体保存在 `data/paper/*.csv`，**重启不丢失**（v1 的局限已解决）。

## 已知局限

* 回测做空用现货 K 线近似永续价格，未计资金费率、滑点与强平；历史表现不代表未来。
* OKX `history-candles` 每次 100 根，首次长回测需要数秒到数十秒（已做 2 分钟缓存与 4 并发）。
* 实盘模式按纸面账本的调仓意图发单，**没有与交易所实际持仓 / 成交对账**，也不处理部分成交；实盘前请先在 OKX 模拟盘或 Gate 合约测试网验证。Gate 现货没有测试网。
* 仅监听 127.0.0.1，没有登录鉴权；不要暴露到公网。
* 若某交易所在你所在地区被限制（HTTP 403 / 451），客户端会尝试官方备用域名（OKX `aws.okx.com`，Gate `api.gate.io`），仍失败就报错——**绝不伪造行情**。

## 目录

```
qtw/market/   OKX / Gate 公共行情、缓存
qtw/strategy.py  dual_ma 指标与信号
qtw/risk.py      仓位与风控
qtw/backtest.py  组合回测
qtw/paper.py     持久化纸面账本（CSV）
qtw/engine.py    信号 → 进出场 → 执行路由、紧急停止
qtw/worker.py    后台自动交易线程
qtw/vault.py     密钥加密存储
qtw/live/        实盘签名与下单（闸门保护）
qtw/app.py       FastAPI 接口
static/          前端页面（原生 JS + lightweight-charts）
tests/           单元测试
```

旧版命令行纸面系统仍在 `/workspace/quant-trading-system/`（Binance 行情，v1）。
