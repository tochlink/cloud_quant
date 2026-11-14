# cloud_3d

加密市场实时 3D 看板 · 数据源 Gate.io 公开 API（现货 + USDT 永续），中 / 英文切换。
A real-time 3D crypto-market HUD fed by Gate.io public data (spot + USDT perpetuals), with a Chinese / English toggle.

纯静态页面，无构建步骤、无后端、无需 API Key。Three.js 已内置在 `vendor/`，不依赖 CDN。
Pure static page: no build step, no backend, no API key. Three.js is vendored in `vendor/`, no CDN needed.

## 运行 / Run

```bash
python3 -m http.server 8080
```

然后打开 / then open <http://localhost:8080>。也可以直接部署到任何静态托管（GitHub Pages、Cloudflare Pages、Nginx 等）。
ES modules 需要通过 http(s) 打开，不能直接双击 `file://`。
Any static host works (GitHub Pages, Cloudflare Pages, Nginx…). ES modules need http(s); opening via `file://` will not work.

> 浏览器需要能访问 `api.gateio.ws` 与 `fx-ws.gateio.ws`（部分地区需要代理）。
> The browser must be able to reach `api.gateio.ws` and `fx-ws.gateio.ws`.

## 面板与数据 / Panels & data

| 面板 Panel | 内容 | Gate.io 数据 |
|---|---|---|
| 顶栏 · 市场脉冲 Header pulse (3D) | 成交额前 64 的币种排成旋转的光柱环：上涨向上、下跌向下（高度按当下市场波动幅度自适应），扫描光束、巨鲸成交闪光，正前方的币名实时显示，点击切换 | `/spot/tickers` + WS |
| 顶栏 Header | 选中币种价格、24H 涨跌、上涨占比、现货总成交、永续总持仓、UTC 时钟、连接状态 | `/spot/tickers`, `/futures/usdt/tickers`, `/spot/time` |
| 时区切换 Time zone | 时钟旁选择国家/城市（北京、香港、新加坡、东京、纽约、伦敦…或本机时区），全页所有时间同步切换并记住选择 | 浏览器 Intl |
| 币种选择器 Symbol picker | 可搜索全部 USDT 交易对；每行显示价格 / 24H / 成交额，标出有永续的币；成交额 / 涨幅 / 跌幅 / 有永续 四种排序；↑↓ Enter Esc 键盘操作，任意位置按 `/` 打开 | 本地数据 |
| 市场总览 Market overview | 全部 USDT 交易对的成交额、涨跌家数、平均/加权涨跌、领涨领跌、永续持仓与加权资金费率、24H 涨跌分布直方图与中位数 | REST 每 15s / 30s 轮询 |
| 盘口阶梯 Book ladder | 前 5 档买卖盘 + 近 40 分钟收盘价迷你图 | WS `spot.order_book` |
| 现货 Spot | K 线 1m / 5m / 15m / 1H / 4H / 1D：悬停十字线显示开盘 / 最高 / 最低 / 收盘 / 涨跌额 / 涨跌幅 / 振幅 / 成交额，滚轮缩放、拖拽回看、双击回到最新；8 档深度（悬停看累计数量 / 金额 / 距中间价） | REST `/spot/candlesticks` + WS `spot.candlesticks` |
| 延迟与基差 Latency & basis | 永续-现货基差、标记-指数溢价、现货/永续推送延迟 | WS `futures.tickers`, `spot/futures.trades` |
| 数据流检查器 Wire inspector | WS 原始消息流、消息速率、流量、订阅数 | 全部 WS |
| 神经壳 Neural shell (3D) | 成交额前 40 的币种，每个币一簇针刺：针长 = 24H 涨跌幅，密度 = 成交额，颜色 = 涨跌，亮度 = 实时成交脉冲。拖拽旋转、悬停看详情、点击切换币种。**三种皮肤**可切换（环面 / 地球 / 星系），切换时粒子平滑变形；地球的大陆轮廓来自 Natural Earth 1:110m（world-atlas，公有领域） | WS `spot.tickers` / `spot.trades` / `futures.trades` |
| 输入卡片 Input cards | BTC / ETH / SOL 实时走势，选中币种的基差、资金费率历史、多空人数比 | `/futures/usdt/funding_rate`, `/futures/usdt/contract_stats` |
| 巨鲸成交 Whale fills | **按币种自适应门槛**：同一币种、同方向、同一毫秒的成交合并为一笔主动单；需同时进入该币近 30 分钟（最多 800 笔）订单的前 0.5%、≥ 该币中位单 8 倍、≥ 保底（现货 $1K / 永续 $2K）；样本不足 60 笔时从严估算。卡片显示「×N 中位单」，悬停门槛标签可看各币当前门槛。监听范围：现货成交额前 16、永续前 10 + 当前选中币；每秒成交笔数直方图 | WS trades |
| 全市场爆仓 Liquidations | 打开即从 REST 加载近 1 小时（最新 1000 笔）再接实时推送：1H 多/空爆仓额与笔数、最大单笔、多空占比；气泡时间轴（气泡大小=金额）+ 每 5 分钟合计；1H 爆仓最多的合约；实时爆仓流 | `/futures/usdt/liq_orders`, WS `futures.public_liquidates` |
| 市场热力图 Market heatmap | 成交额前 60 的方块树图：面积 = 成交额，颜色 = 24H 涨跌，实时成交时边框闪烁；悬停看详情，点击切换币种 | `/spot/tickers` + WS trades |
| 永续合约排行 Perp rankings | 总持仓、24H 成交、正/负费率合约数；持仓量 TOP 12；资金费率最高 / 最低各 6 个（含按各合约结算周期折算的年化） | `/futures/usdt/tickers`, `/futures/usdt/contracts` |
| 逐笔成交 Execution tape | 选中币种的现货 + 永续逐笔成交、60s 买卖力量 | WS trades |
| 波动锥 · 爆仓漏斗 Vol cone | 近 60 分钟价格 → 未来 30 分钟 ±1σ / ±2σ 实现波动率锥；选中合约的爆仓以火花落入漏斗；全市场实时爆仓列表；资金费结算倒计时、多空比、近 2H 爆仓额 | WS `futures.public_liquidates` (`!all`), `/futures/usdt/contracts/{c}` |

### 鼠标交互 / Mouse interaction

几乎所有图表都可悬停：K 线、盘口 / 阶梯、基差与延迟、涨跌分布（含该区间成交额最大的币）、成交笔数、买卖力量、波动锥历史线、顶栏光柱环（悬停任意光柱、点击切换）、爆仓气泡、热力图、3D 神经壳。顶部滚动行情悬停暂停、点击切换币种；原始消息流悬停冻结便于阅读。

## 结构 / Layout

```
index.html          页面骨架 / page skeleton
css/app.css         HUD 样式与响应式布局 / styles, responsive layout
js/main.js          数据状态、订阅、渲染循环 / state, subscriptions, render loop
js/gate.js          REST + 自动重连、引用计数订阅的 WebSocket 客户端 / REST + reconnecting WS client
js/shell3d.js       Three.js 神经壳（自定义着色器）+ 连线叠加层 / Three.js shell + overlay wires
js/funnel.js        波动锥 / 爆仓漏斗（Canvas 2D 伪 3D）/ vol cone (2D pseudo-3D)
js/pulse3d.js       顶栏 3D 市场脉冲光柱环 / header 3D pulse ring
js/heatmap.js       市场热力图（squarified treemap）/ market heatmap
js/picker.js        可搜索的币种选择器 / searchable symbol picker
js/liqchart.js      可交互的爆仓气泡时间轴 / interactive liquidation timeline
js/tz.js            时区切换 / time-zone switcher
js/tip.js           全页共用的悬浮提示 / shared tooltip + canvas hover helper
js/landmask.js      1° 海陆位图（地球皮肤）/ land mask for the globe skin
js/charts.js        K 线、迷你图、柱状图等 / small chart helpers
js/i18n.js          中英文字典 / zh-en dictionary
js/fmt.js           数字、价格、时间格式化 / formatting
vendor/             three.js r170 (MIT)
```

## 可调参数 / Tuning

`js/main.js` 顶部：`FOCUS_N`（3D 壳上的币种数）、`TRADE_N` / `PERP_N`（订阅逐笔的币种数）、
`SPOT_WHALE` / `PERP_WHALE`（巨鲸阈值）、`HEAT_N`（热力图方块数）、`PULSE_N`（顶栏光柱数）、`INPUTS`（左侧输入卡片）。
Top of `js/main.js`: `FOCUS_N`, `TRADE_N`, `PERP_N`, `SPOT_WHALE`, `PERP_WHALE`, `HEAT_N`, `PULSE_N`, `INPUTS`.

## 说明 / Notes

- "全市场"指 Gate.io 一家交易所的 USDT 交易对；稳定币与杠杆代币（如 `BTC3L`）不计入统计。总市值、市占率需要流通量数据，Gate 不提供，未包含。
  "Whole market" means Gate.io USDT pairs only; stablecoins and leveraged tokens are excluded. Market cap / dominance are not available from Gate.
- 延迟 = 本地接收时间 − 服务器推送时间（`time_ms`），取近 60 条的中位数，只用成交 / 盘口频道。
  页面持续用 WS 消息里的服务器时间校准时钟：本机时钟偏差超过 2 秒（例如电脑时间差了几个小时）时自动改用服务器时间，UTC 时钟和延迟仍然正确。
  Latency is the median of (receive time − server `time_ms`) over trades / book frames. The clock is continuously
  re-synced from the server timestamps in WS frames, so a local clock that is hours off no longer breaks the clock or latency.
- 爆仓方向：`futures.public_liquidates` 中 size < 0（强平卖单）记为多头爆仓。
  Liquidation side: negative size (forced sell) is treated as a long liquidation.
- 仅供展示，不构成投资建议。For display only; not investment advice.

## QTW 集成 / Integration in QTW

- 地址：QTW 启动后打开 `http://127.0.0.1:8002/panorama/`，或点左侧导航「全景」（地球图标）；页脚左侧「‹ QTW」返回主界面。
- 数据仍由浏览器直连 Gate 公共 REST / WS（不经过 QTW 后端，不需要 API Key）；浏览器需要能访问 `api.gateio.ws`、`fx-ws.gateio.ws`。
- 宽度 ≥ 1181px 时改为单屏分页：行情 / 3D 全景 / 爆仓 / 热力 · 永续 / 成交 · 波动锥，页脚标签或键盘 `1`–`5`、`[` `]` 切换，记住上次页面；更窄时保留原来的滚动布局。
- 默认中文（右上角可切 EN，会记住）。
- 资金费倒计时取自 `futures.tickers` 推送里的 `funding_next_apply`，结算发生时才重新拉资金费历史（去掉了 5 分钟轮询）。
- 全市场快照（`/spot/tickers` 15s、`/futures/usdt/tickers` 30s）与多空比 `/contract_stats`（60s）仍是 REST 轮询：Gate 现货没有全市场 ticker 推送频道；永续 `!all` 推送约 60 KB/s，比 30s 一次 REST 重得多。
- `vendor/three.module.min.js` 为 three.js r170 原文件，仅在 `lt.refreshFogUniforms` 前面的 `&&` 后插入一个空格（语义不变），避免同步仓库时这串字符被当成 HTML 实体 “小于号” 解码。
