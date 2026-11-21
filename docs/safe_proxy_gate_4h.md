# Safe（原 Gnosis Safe）官方 ProxyFactory 日度新建多签数 → 4h 默认书入场闸门（2026-11-21，否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（远端 STRATEGY_FORMULAS.md 与本地分叉时以此为准）。


- 背景：上节「下一轮（长线）」所列。机制 = 团队 / DAO / 基金 / 金库新开多签托管（新资金准备上链），新建偏多 / 上升 = 入场 risk-on。只拦新开仓，出场 / 止损 / 已有同向仓不动。查重：本地 docs/*.md、output/research_*.csv、记忆中 Safe / SafeProxyFactory / ProxyCreation / multisig 0 条测试（只有计划行），不是重复；也不是已否决的 ENS 注册、ERC-4337 EntryPoint、gas / 满块、Uniswap V2 PairCreated、稳定币供给、桥流量或交易所资金费。
- 数据（全部官方链上，`output/safe_proxy_official_daily.csv`）：工厂地址全部取自 github.com/safe-global/safe-deployments（main，src/assets）以太坊主网条目：v1.0.0 `0x12302fE9c02ff50939BaAaaf415fc226C078613C`、v1.1.1 `0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B`、v1.3.0 canonical `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` + eip155 `0xC22834581EbC8527d974F8a1c97E1bEA4EF910BC`、v1.4.1 `0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67`、v1.5.0 `0x14F2982D601c9458F93bd70B218933A6f8165e7b`（部署块用 archive `eth_getCode` 二分实测：7,450,116 / 9,084,508 / 12,504,126 / 14,981,216 / 17,440,707 / 22,774,977）。v1.5.0 也计入（任务点名 1.0 / 1.1.1 / 1.3.0 / 1.4.1，但 v1.5.0 是官方主网工厂，不计会在用户迁移时造出假下降；按版本分列）。L2 / 其他链 / zksync 工厂不计入。公共 RPC `eth_getLogs` 只抓这些地址的 `ProxyCreation(address)`（v1.0 / v1.1.1）与 `ProxyCreation(address,address)`（v1.3.0+），带 `blockTimestamp`，块覆盖连续无缺。
  - 日度构造：UTC 日 D 新建数 = 时间戳落在 D 当天的 ProxyCreation 条数；**完整 UTC 日 2019-03-28 → 2026-11-20 共 2,795 天，888,224 条**（v1.0.0 1,329 / v1.1.1 34,787 / v1.3.0 527,695 / v1.3.0 eip155 1,746 / v1.4.1 167,968 / v1.5.0 154,699），覆盖缺口 0；当天真为 0 记 0（2020 年后 14 天），**不插值、不回补、不造数**。D 日值 D+1 01:00 UTC 才使用。
  - 校验：独立 RPC rpc.mevblocker.io（用该节点自己的块时间二分日界）抽 12 天（10 天随机 + 2026-03-14 峰值 + 2026-11-20），**12/12 逐条一致**（首轮 2026-03-14 因单次 >10k 条报错，修好拆分后重跑一致）。
  - 量级：2022–2025 日中位约 155；2026 年结构性抬升（post 段 ≥2026-03-05 中位 801、均值 1,703），2025-12 → 2026-07 有 14 天 >5,000 的突发（最高 2026-03-14 89,117，几乎全是 v1.3.0 批量部署），按官方原值保留；2026-11-20 为 866（v1.3.0 59 / v1.4.1 331 / v1.5.0 476）。
- 公式（`scratch/safe4h/PRE_REGISTER.json` sha256 `b51c524e…2b58`，2026-11-21 08:42 PST 看任何 PnL 前锁定，结果后未改）：
  - 序列 cnt（日新建数）/ ma7（7 日均值）/ ma28（28 日均值，窗口内须全有值）；形式 trend（值 > SMA n，n∈{30,90,180}）、chg（n 日变化 > 0，n∈{30,90}）、z365 > k（k∈{1,1.5,2}）；方向 long_off / short_off / both / contra_both / cap_short_off。3 × 8 × 5 = **120 格** + 同脚本基线（当前 S.DEFAULTS 4h 默认书），闸门代码与 pendle4h / arbbridge4h 相同。
  - 经济先验：flag=1（新建多签偏多 / 上升）= risk-on → 不开新空。**先验 `ma7_trend_n90_cap_short_off`**，回退 `ma28_trend_n180_cap_short_off`；先验方向 cap_short_off / contra_both。
  - 评分同前：9 个 Sharpe 片（OKX d8 自 2023-02-01、Gate d8 自 2022-07-01、OKX d7_noBNB 自 2022-04-01 × 深未见 < 2024-10-21 / tune_pre / post ≥ 2026-03-05，回测止于 2026-11-14）；改默认须未见历史成立且 post 月度两所 ≥ 6/9 更好、post 收益两所不差；新 8 币未调参；邻域；时移安慰剂 ±7/±14/+180/−120/+365/−119 天；30 天块打乱（种子 1/2/3）。真实费用：永续 taker 5.1 bps / maker 2 bps + 官方资金费；压力永续 taker 15.1 bps。
- 结果（`output/research_safe_proxy_gate_4h.csv`）：
  - 基线：OKX d8 深未见 +35.14% / Sharpe 0.71，tune +85.08% / 1.47，post +59.90% / 2.23；Gate d8 −3.63% / 0.09，+84.25% / 1.46，+60.32% / 2.25；OKX d7_noBNB +54.92% / 0.75，+92.93% / 1.56，+50.76% / 2.10。
  - **先验 ma7_trend_n90_cap_short_off = 3/9（只赢 tune Sharpe）**：OKX 深未见 +25.24% / 0.58、post **+51.79% / 2.08**（月度 1/5）；Gate −14.64% / −0.09、post **+52.38% / 2.10**（1/5）；d7 post +44.80% / 1.97（2/4）。压力费同形（OKX post +48.29% vs +55.94%）。时移 −119 天 9/9、−120 / +180 天 6/9，均好于真实；打乱种子 3 post +68.3% / +69.0% 也好于真实。新 8 币 OKX +3.77% vs +3.26%（3/4）、Gate +17.35% vs +16.36%（4/3），几乎无差。**否决**。
  - **回退 ma28_trend_n180_cap_short_off = 3/9（只赢 post Sharpe）**：post 闸门开着的时间只有约 15%，月度 2/0（其余月份与基线相同），OKX post +60.43% / 2.34、Gate +60.95% / 2.35（边 +0.5 / +0.6 pp）；深未见、tune 三组全输。打乱种子 3 post +72.3% / +73.7% 更好。**否决**。
  - 120 格分布：8/9 一格、7/9 两格、6/9 八格，**没有一格 post 月度两所 ≥ 6/9**。最好 `ma28_chg_n30_cap_short_off`（28 日均值 30 日变化 > 0 → 不开新空，先验方向）8/9：OKX 深未见 +68.97% / 1.18、post +62.54% / 2.42（月度 5/2）；Gate +13.33% / 0.33、post +63.24% / 2.44（5/2）；d7 +55.80% / 0.79、post +54.60% / 2.34（4/3）；但 tune 收益三组全低于基线（+70.4 / +65.4 / +66.8 vs +85.1 / +84.3 / +92.9）。压力费 OKX post +59.12% / 2.32 vs +55.94% / 2.12，Gate +60.02% / 2.35 vs +56.78% / 2.15。7/9 两格：cnt_chg_n90_long_off（post 月度 2/2）、cnt_z365gt2_cap_short_off（post 段几乎不触发）。
  - ma28_chg_n30 邻域：n20 5/9、n25 5/9、n40 7/9、n45 6/9、n60 3/9（n40 / n60 深未见 Gate / d7 转负）→ 不稳。
  - ma28_chg_n30 事后安慰剂（`PLACEBO_ADDENDUM_POSTHOC.txt`，看榜后写，只加安慰剂不加格；`output/research_safe_proxy_gate_4h_shuffle_ma28chg.csv`）：**+7 天时移同样 8/9，post +68.70% / +69.55%（月度 5/2、6/1）好于真实**；+14 / +180 / +365 天 post +66.7% … +72.0% 也好于真实；30 天块打乱 1–2/9、post +28% … +36%（差于真实）。新 8 币（2024-11-27 起）**OKX post −2.81% vs +3.26%（4/4）、Gate +10.42% vs +16.36%（4/3）**，两所都更差，压力费同向。
- 结论：**否决**，不实现、不进观察名单、不改默认。先验与回退都只有 3/9 且被时移 / 打乱安慰剂追平或超过；最好的 ma28_chg_n30_cap_short_off 虽 8/9，但 post 月度只有 5/2（< 6/9）、邻域断裂、+7 天时移安慰剂打出同样 8/9 且 post 更好、新 8 币两所都更差 → 连弱观察也不够。不动纸面盘、不加 shadow、不改代码；官方记录器继续累积。**勿以改 n / k / 方向、换序列（日数 / 7 日 / 28 日 / 净增 / 按版本拆分如只看 v1.4.1 / v1.5.0 / 去掉批量部署日 / 阈值去刺）、换链（Base / Arbitrum / Optimism / BNB / Polygon 上的 Safe 工厂、L2 工厂）、或换别的合约钱包工厂（Argent / Ambire / Coinbase Smart Wallet / ERC-4337 账户工厂）的方式在现有历史上重测本族。**
- 文件：`output/safe_proxy_official_daily.csv`、`output/research_safe_proxy_gate_4h.csv`、`_new8.csv`、`_shuffle.csv`、`_shuffle_ma28chg.csv`（均不入库）；sidecar `docs/safe_proxy_gate_4h.md`；脚本 `scratch/safe4h/{common,fetch_logs,build,verify,run,supp,supp2,new8,record,plog_safe}.py`（未推送）。官方记录器 `scratch/safe4h/record.py` 已后台运行（30 分钟一轮：新块 ProxyCreation → 只追加检查点 → 重建完整 UTC 日，不回补）。
- 下一轮（短线）：GMX 官方 Arbitrum 永续 DEX 清算 1h 突发 → 8 币永续篮子顺势 / 逆势。数据只用 GMX 官方仓库（gmx-io/gmx-contracts、gmx-synthetics deployments）列出的 Arbitrum 合约事件：V1 Vault `LiquidatePosition`（2021-08 起）+ V2 EventEmitter `PositionDecrease` 中 orderType = Liquidation（2023-08 起），按小时计清算笔数 / 清算名义额。机制 = 链上永续杠杆被动去杠杆（多空清算方向不对称），不是已否决的 Aave V3 借贷清算（及同机制 Morpho / Compound）、Bitfinex 保证金、Hyperliquid Bridge2 保证金桥、资金费 / 基差极值或篮子投降；文档 / output 中 GMX 0 条。预注册须写明 V1→V2 拼接、多空分开与缺口。（另查过 OKX 官方 insurance-fund 接口：只给最近记录、按类型查返回空，历史不够，不选。）

## 复现

```
cd /workspace/scratch/safe4h
python fetch_logs.py 26464000   # 官方工厂 ProxyCreation 日志（检查点 ck/）
python build.py 2026-11-20      # → output/safe_proxy_official_daily.csv
python verify.py                # 独立 RPC 逐日条数抽查（12 天）
python run.py                   # 120 格 + 基线 + 时移安慰剂 + 邻域 + 压力费
python supp.py                  # 先验 / 回退 30 天块打乱
python supp2.py                 # ma28_chg_n30 事后安慰剂（时移 + 打乱）
python new8.py ma7_trend_n90_cap_short_off ma28_trend_n180_cap_short_off ma28_chg_n30_cap_short_off PLC_ma28_chg_n30_cap_short_off_shift7d PLC_ma28_chg_n30_cap_short_off_shift-7d
```
