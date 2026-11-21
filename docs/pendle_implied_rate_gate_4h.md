# Pendle V2 官方隐含利率曲线 → 4h 默认书入场闸门（2026-11-21，先验否决，非先验 slope 弱观察）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（远端 STRATEGY_FORMULAS.md 与本地分叉时以此为准）。


- 背景：上节「下一轮（长线）」所列。机制 = 链上固定利率市场（PT/YT）对未来收益的定价，隐含收益偏高 / 上升 = 杠杆收益 / 积分投机需求（risk-on）。只拦新开仓，出场 / 止损 / 已有同向仓不动。查重：本地 docs/*.md、output/research_*.csv、记忆中 Pendle 隐含利率 0 条（只有计划行与上市漂移表里的 PENDLE-USDT-SWAP 币名），不是重复；也不是已否决的 Lido stETH / rETH 质押 APR（协议已实现收益）、Aave 借款 APY（利用率浮动成本）、Sky SSR/DSR（治理设定）、稳定币 / Ethena 供给、Liquity、Arbitrum 官方桥或交易所资金费（永续 carry）。
- 数据（全部官方链上，`output/pendle_implied_rate_official_daily.csv`）：市场集合 = pendle-finance/pendle-core-v2-public `deployments/1-core.json`、`42161-core.json` 所列官方 PendleMarketFactory V1/V3/V4/V5/V6 的全部 `CreateNewMarket`（以太坊 V1 `0x27b1dAcd74688aF24a64BD3C9C1B143118740784`、V3 `0x1A6fCc85557BC4fB7B534ed835a03EF056552D52`、V4 `0x3d75Bd20C983edb5fD218A1b7e0024F1056c7A2F`、V5 `0x6fcf753f2C67b83f7B09746Bbc4FA0047b35D050`、V6 `0x6d247b1c044fA1E22e6B04fA9F71Baf99EB29A9f`；Arbitrum V1 `0xf5a7De2D276dbda3EEf1b62A9E718EFf4d29dDC8`、V3 `0x2FCb47B58350cD377f94d3821e7373Df60bD9Ced`、V4 `0xd9f5e9589016da862D2aBcE980A5A5B99A94f3E8`、V5 `0xd29e76c6F15ada0150D10A1D3f45aCCD2098283B`、V6 `0x49F2f7002669E0e4425Fa0203975625Ab4af3143`）：以太坊 678 个、Arbitrum 154 个市场，`expiry()` 链上读取。公共 RPC `eth_getLogs` 抓这些市场的 `UpdateImpliedRate(uint256 indexed timestamp, uint256 lnLastImpliedRate)`：**2,959,176 条**（以太坊 1,574,959 / 672 个市场，Arbitrum 1,384,220 / 148 个市场）。官方 deployments 清单里没有 V2 工厂，未用任何非官方清单补。
  - 日度构造：UTC 日 D 每个市场取时间戳 ≤ D 23:59:59 的最后一条事件值（即链上 lastLnImpliedRate 状态，只随该事件变化，不是插值）；候选 = 未到期、剩余期限 14–400 天、过去 7 天事件数 a ≥ 5；「最大」= 两链合并按 a 取前 20（时点内可得，无前视）；r = lnImpliedRate/1e18（ln 隐含年化）。lvl = a 加权均值；cm90 / slope = 加权最小二乘 r = α + β·ln(tte/90) 的 α / β（≥4 个市场且期限比 ≥1.5，否则当天 NaN）。
  - **完整 UTC 日 2022-11-23 → 2026-11-20 共 1,459 天**；lvl 缺 6 天（2022-11-23…28，市场 <3 个），cm90 / slope 缺 34 天（上述 6 天 + 2023-05-09、05-11、06-16…25、07-03…18 期限回归不可识别）。**缺口如实保留，不插值、不回补、不前填到日度序列**（4h 根上只对已知日做 D+1 01:00 UTC 前向使用）。
  - 校验：随机 10 个市场（以太坊 6 / Arbitrum 4）× 3 个历史日终块 archive `eth_call _storage().lastLnImpliedRate` + 最新块 live 调用，**40/40 与重建值逐 wei 一致**。
  - 量级：lvl 峰值 0.767（2022-12-20，早期市场少），全期中位 0.119（≈12.6% APY）；post 段（≥2026-03-05）lvl 均值 0.113（APY 12.0%）、slope 均值 −0.006；2026-11-20 lvl 0.1177（APY 12.5%）、cm90 0.1023、slope −0.0242（20 个市场中以太坊 19 / Arbitrum 1）。
  - 与资金费的区别检查（只报告，不用于选格）：lvl 与 OKX 官方 BTC / ETH 日度年化资金费水平相关 0.22 / 0.24，与资金费 30 日均值相关 0.50 / 0.53，30 日变化相关 0.29 / 0.34；slope 与资金费相关 −0.05…−0.14 → slope 与资金费几乎无关。
- 公式（`scratch/pendle4h/PRE_REGISTER.json` sha256 `672da144…c443`，2026-11-21 07:33 PST 看任何 PnL 前锁定，结果后未改；时移 + 30 天块打乱安慰剂已写在预注册内）：
  - 序列 lvl / cm90 / slope；形式 trend（值 > SMA n，n∈{30,90,180}）、chg（n 日变化 > 0，n∈{30,90}）、z365 > k（k∈{1,1.5,2}）；方向 long_off / short_off / both / contra_both / cap_short_off。3 × 8 × 5 = **120 格** + 同脚本基线（当前 S.DEFAULTS 4h 默认书）。
  - 经济先验：flag=1（隐含收益偏高 / 上升）= risk-on → 不开新空。**先验 `lvl_trend_n30_cap_short_off`**，回退 `cm90_trend_n90_cap_short_off`；先验方向 cap_short_off / contra_both，只在 lvl / cm90 上。slope 与其他方向均为非先验。
  - 评分：9 个 Sharpe 片（OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01 × 深未见 < 2024-10-21 / tune_pre / post ≥ 2026-03-05，回测止于 2026-11-14；Pendle 数据 2022-11 才开始，flag 为 NaN 时不拦，所以深未见实际有效段较短，n=180 与 z365 预热更久）；post 月度 ≥ 6/9 两所都更好；post 收益两所不差；新 8 币未调参；邻域；时移安慰剂 ±7/±14/+180/−120/+365/−119 天；30 天块打乱（种子 1/2/3）。真实费用：永续 taker 5.1 bps / maker 2 bps + 官方资金费；压力永续 taker 15.1 bps。
- 结果（`output/research_pendle_implied_rate_gate_4h.csv`）：
  - 基线：OKX d8 深未见 +35.14% / Sharpe 0.71，tune +85.08% / 1.47，post +59.90% / 2.23；Gate d8 −3.63% / 0.09，+84.25% / 1.46，+60.32% / 2.25；OKX d7_noBNB +54.92% / 0.75，+92.93% / 1.56，+50.76% / 2.10。
  - **先验 lvl_trend_n30_cap_short_off = 3/9（只赢 tune）**：OKX 深未见 +22.22% / 0.54、tune +92.93% / 1.56、**post +48.06% / 1.96**（月度 3/6）；Gate −13.22% / −0.08、+97.14% / 1.59、**post +48.25% / 1.96**（3/6）；d7 +36.88% / 0.59、+98.44% / 1.63、+44.92% / 1.96。压力费同形（OKX post +45.36% vs 基线 +55.94%）。时移安慰剂 −7 天、−14 天都是 **9/9**（OKX post +61.83% / +65.73%），+14 天 6/9，比真实序列更好；30 天块打乱 3 个种子 OKX post +63.29% / +44.02% / +61.20%，与真实同级或更好。新 8 币 OKX post +14.51% vs +3.26%（月 5/4），Gate +11.08% vs +16.36%（4/5），而 +7 天时移安慰剂两所都更好（+24.73% / +25.43%）。**否决**。
  - **回退 cm90_trend_n90_cap_short_off = 3/9（只赢 tune）**：OKX tune +135.92% / 1.96，但 post +27.26% / 1.55（月度 3/5），Gate post +27.91% / 1.59（4/4），深未见两所都更差；新 8 币 post 两所为负（OKX −2.78%、Gate −3.42%）。打乱安慰剂 post +62.37% / +43.66% / +30.16% 均不差于真实。**否决**。
  - 120 格分布：9/9 四格、7/9 两格、6/9 十四格，**全部达不到 post 月度 ≥ 6/9 两所**。四个 9/9 全是非先验 slope_*_cap_short_off：`slope_trend_n30_cap_short_off` OKX 深未见 +69.81% / 1.15、tune +133.95% / 1.92、post +67.73% / 2.45（月度 5/3）；Gate +19.56% / 0.40、+131.25% / 1.89、+68.63% / 2.48（5/3）；d7 +88.47% / 1.03、+141.88% / 2.00、+58.34% / 2.35（5/2）。slope_trend_n90 / n180、slope_chg_n30 亦 9/9（post 边际 +0.46 / +0.32 / +0.17 Sharpe 合计，月度 5/4、3/5、3/4）。压力费 slope_trend_n30 OKX post +64.35% / 2.36 vs 基线 +55.94% / 2.12、Gate +65.42% / 2.39 vs +56.78% / 2.15，深未见 1.00 vs 0.56。
  - slope_trend_n30 邻域（事后）：n20 / 25 / 40 / 45 / 60 全部 9/9；n20 月度 6/3、7/2，n25 6/3、6/3，n40 / 45 3/5，n60 5/3、6/2。
  - slope_trend_n30 事后安慰剂（`PLACEBO_ADDENDUM_POSTHOC.txt`，看榜后写，只加安慰剂不加格；`output/research_pendle_implied_rate_gate_4h_shuffle_slope.csv`）：8 个时移在 9 片上最多 2/9（真实 9/9），+180 / −120 / −119 天 post 跌到 +9% … +35%；30 天块打乱 3 个种子 1–3/9，**但打乱的 post 收益 +64.1% … +68.1%（两所）与真实 +67.7% / +68.6% 同级** → post 段增益主要来自「约一半时间不开新空」本身，不是 slope 的信息；深未见 / tune 增益安慰剂复现不了。新 8 币（2024-11-26 起）OKX post +5.76% vs +3.26%（6/3），Gate +19.62% vs +16.36%（6/2），压力费同向。
- 结论：**先验与回退否决**（都只赢 tune，post 两所更差，时移 / 打乱安慰剂不差于甚至好于真实）。非先验 `slope_trend_n30_cap_short_off`（期限斜率高于 30 日均值 → 不开新空）记为 **弱观察**，不是强观察、不实施：9/9 且邻域稳、时移安慰剂 ≤2/9，但非先验、post 月度两所只有 5/3（< 6/9）、post 增益被打乱安慰剂复现。不改默认、不动纸面盘、不加 shadow、不改代码；官方记录器继续累积，样本外再看。**勿以改 n / k / 方向、换序列（lvl ↔ cm90 ↔ slope、中位数、其他期限、按资产分组、TVL 加权、单链）、换 Pendle 其他链 / V2 工厂或 Spectra / Notional / Term Finance 等其他固定利率协议的方式在现有历史上重测本族；slope 弱观察只能用 2026-11-21 之后的新数据确认。**
- 文件：`output/pendle_implied_rate_official_daily.csv`、`output/research_pendle_implied_rate_gate_4h.csv`、`_new8.csv`、`_shuffle.csv`、`_shuffle_slope.csv`（均不入库）；sidecar `docs/pendle_implied_rate_gate_4h.md`；脚本 `scratch/pendle4h/{markets,fetch_logs,build,verify,run,new8,supp,supp2,record}.py`（未推送）。官方记录器 `scratch/pendle4h/record.py` 已后台运行（30 分钟一轮：新市场 + 新事件 → 重建完整 UTC 日，只追加事件检查点，不回补）。
- 下一轮（短线）：Circle 官方 CCTP（TokenMessenger `DepositForBurn` / MessageTransmitter `MessageReceived` + USDC `Mint`）以太坊主网 USDC 跨链流出 / 流入 1h 突发 → 8 币永续篮子顺势 / 逆势。机制 = 跨链美元流动性迁移（资金离开 / 回流以太坊去别链做多），不是已否决的稳定币总供给、Curve 3pool、WETH9、Tornado、Arbitrum 官方桥（长线 ETH）或 Hyperliquid Bridge2（单一交易所保证金桥，弱观察）；文档 / output 中 CCTP 只在 Hyperliquid 段被顺带提及，0 条测试。数据只用 Circle 官方文档列出的合约事件（CCTP V1 2023-04 起、V2 2025 起），预注册须写明 V1→V2 迁移的拼接与缺口。

## 复现

```
cd /workspace/scratch/pendle4h
python markets.py           # 官方工厂 CreateNewMarket + expiry() → markets.json
python fetch_logs.py eth; python fetch_logs.py arb   # 官方 UpdateImpliedRate 日志（检查点 ck/）
python build.py 2026-11-20  # → output/pendle_implied_rate_official_daily.csv
python verify.py            # archive / live eth_call _storage().lastLnImpliedRate 逐 wei 校验
python run.py               # 120 格 + 基线 + 时移安慰剂 + 邻域 + 压力费
python new8.py lvl_trend_n30_cap_short_off cm90_trend_n90_cap_short_off slope_trend_n30_cap_short_off PLC_lvl_trend_n30_cap_short_off_shift7d PLC_lvl_trend_n30_cap_short_off_shift-7d PLC_slope_trend_n30_cap_short_off_shift7d PLC_slope_trend_n30_cap_short_off_shift-7d
python supp.py              # 先验 / 回退 30 天块打乱
python supp2.py             # slope 事后安慰剂（时移 + 打乱）
```
