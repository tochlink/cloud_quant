# 长线新族：Gate 官方杠杆代币（BTC3L / BTC3S / ETH3L / ETH3S）日成交额多空比 / 相对现货强度 → 4h 默认书 #1 入场闸门（2026-11-27 ~18:00 PST，研究；先验否决，非先验观察 → 新纸面 8802 paper-levtok，默认不变）

- 查重：`docs/STRATEGY_FORMULAS.md`（含全部轮换记录）、`docs/*.md`（约 170 篇）、约 1,365 个 `output/research_*.csv` 文件名、`scratch/` 目录名、`output/paper_candidates_log.csv` 检索 `3L` / `3S` / leveraged token / 杠杆代币 / BTC3L / ETH3L / levtoken：零相关命中（只有 univ3 文档里的 `3L` 误匹配）——**从未测过**。与已否决族的区别：OKX 多空账户比（永续账户持仓人数）、主动买卖失衡、OKX 币币借贷 / Bitfinex 保证金（借贷需求）、资金费 / 基差、现货 vs 永续成交占比、韩国散户成交占比（Upbit KRW）、平台币相对强弱——本族是**现货账户散户买卖 3 倍杠杆 ETF 代币的方向性成交额**。
- 数据（只用官方，不编造、不插值、不回补）：Gate.io 官方公开 API v4 `/spot/candlesticks?interval=1d`（UTC 日 K，第 2 列为 USDT 计价成交额），BTC3L_USDT、BTC3S_USDT、ETH3L_USDT、ETH3S_USDT、BTC_USDT、ETH_USDT，2020-02-27 → 2026-11-27 共 2,466 个完整 UTC 日，日历 0 缺口；2021-08-31 六个交易对同时报 0 成交（交易所数据缺口）→ 记 NaN，不补（7 日和在其附近为 NaN）。**滞后**：日 D 的 K 线 D+1 00:00 UTC 收盘，再多等一根 4h，**D+1 04:00 UTC 起才算已知**。日表 `output/research_gate_leveraged_token_flow_gate_4h_daily.csv`（不入库）。
- 序列：`ls7 = ln(7 日 qv(BTC3L+ETH3L) / 7 日 qv(BTC3S+ETH3S))`；`lsbtc7 = ln(7 日 qv BTC3L / 7 日 qv BTC3S)`；`lt7 = ln(7 日 四个代币 qv / 7 日 BTC_USDT+ETH_USDT 现货 qv)`（投机强度）。最新（2026-11-27）：lsbtc7 = 0.1256，90 日均线 0.2466 → flag 0。
- 公式（看 PnL 前锁定 `scratch/levtok4h/PRE_REGISTER.json`，sha256 `3b1b1c42…2ba3`，2026-11-27 17:35 PST，150 格）：flag = 1 表示**散户杠杆偏多 / 过热**：trend（x > 最近 n 日均值，n 14 / 30 / 60 / 90）、chg（x − x[−n 日] > 0，n 7 / 30）、z（180 日 z > k，k 0.5 / 1 / 1.5 / 2）；侧 long_off（flag → 不新开多）、short_off（非 flag → 不新开空）、both、contra_both（flag → 不新开空、非 flag → 不新开多）、cap_short_off（flag → 不新开空）。闸门只拦新开仓，已有同向仓保留。**经济先验（反向：散户杠杆拥挤 → 拦多）ls7_trend_n30_long_off，回退 lt7_trend_n30_long_off**，安慰剂锚 = 先验。
- 回测：同脚本默认 #1（perp_both 10×、官方资金费；结构同 `scratch/g19cc4h/run.py`），真实费 maker 2 / taker 5.1 bps，压力费 spot 20 / perp 15.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根，2024-12-03 起）。

## 结果（`output/research_gate_leveraged_token_flow_gate_4h.csv` 531 行；`_supp.csv` 66 行 邻域 + 安慰剂（事后、已标注）；`_new8.csv` 20 行）

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | OKX post 收益 / Sharpe | Gate d8 深未见 / 调参 | Gate post | post 月胜 / 负（OKX、Gate） | new8 pre Sharpe（OKX、Gate） |
|---|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | +59.90% / 2.23 | 0.09 / 1.46 | +60.32% / 2.25 | — | 0.75、0.73 |
| **先验 ls7_trend_n30_long_off** | 0/9 | 0.02 / 1.31 | +37.28% / 1.57 | −0.35 / 1.25 | +37.97% / 1.60 | 0/4、0/4 | 0.70、0.65 |
| **回退 lt7_trend_n30_long_off** | 0/9 | 0.67 / 1.36 | +48.79% / 1.94 | −0.10 / 1.34 | +49.41% / 1.96 | 0/3、0/3 | 0.95、0.91 |
| **观察 lsbtc7_trend_n90_contra_both** | **9/9** | **1.09 / 1.49** | **+64.79% / 2.42** | **0.81 / 1.48** | **+65.23% / 2.43** | 4/5、4/4 | **1.07、1.19** |
| 9 段并列 lsbtc7_z180gt1_cap_short_off | 9/9 | 0.94 / 1.49 | +68.99% / 2.50 | 0.21 / 1.47 | +69.77% / 2.52 | 3/4、4/3 | 0.76、0.74 |
| ls7_trend_n90_contra_both（BTC+ETH 合并） | 2/9 | 0.86 / 0.81 | +65.63% / 2.47 | 0.16 / 0.82 | +66.10% / 2.48 | 4/4、4/4 | — |

- **先验（反向：散户 3 倍做多代币成交占比高于 30 日均值 → 不新开多）**：三组九段全输（OKX 深未见 0.02 vs 0.71、post +37.28% vs +59.90%），压力费同向；8 个时间平移安慰剂 post +36% ~ +60%，深未见大多更高 → 无信息，**否决**。回退（杠杆代币相对现货成交强度高于 30 日均值 → 不新开多）同样 0/9，**否决**。散户杠杆代币「拥挤」不是反向信号。
- **非先验 lsbtc7_trend_n90_contra_both（确认式：BTC 3L/3S 7 日成交额比高于 90 日均线 → 不新开空，低于 → 不新开多）**：9/9；深未见三组大幅更好（OKX 1.09 vs 0.71、Gate 0.81 vs 0.09、d7 1.08 vs 0.75），调参窗只小胜（1.49 / 1.48 / 1.67 vs 1.47 / 1.46 / 1.56），post OKX +64.79% / 2.42、Gate +65.23% / 2.43（基线 +59.90 / +60.32），d7 +57.65% vs +50.76%；post 回撤略深（−11.5% vs −10.6%）。压力费保持（OKX post +62.46% vs +55.94%、Gate +63.20% vs +56.78%）。未调参 new8：pre Sharpe 1.07 / 1.19 vs 0.75 / 0.73，post OKX 1.06 vs 0.28（月 6/3）、Gate 1.07 vs 1.00（收益 +15.93% vs +16.36%，月 5/4）。邻域 n45 / 60 / 75 / 90 / 120 / 150 / 180 的 post Sharpe 全部高于基线（2.34–2.49 / 2.36–2.49），但 n45 / n60 post 收益略低于基线（OKX +58.22% / +57.98%）；n75 三窗全胜，n120–180 OKX 深未见转弱（0.64 / 0.63 / 0.35）。8 个平移安慰剂（±30 / ±90 / 180 / −120 / 365 / −119 天）post 全部更差（OKX +31% ~ +58%、Gate +31% ~ +56%），但 +30 / −30 / +90 / +180 天平移在调参窗 Sharpe 反而更高（1.64–1.97 vs 1.49），−119 / −120 天在 d7 深未见略高——调参窗那部分优势不是时点特有。
- **为什么不改默认**：post 逐月只 4/5（OKX）、4/4（Gate），不满足「≥6/9 月两所都更好」；方向是事后翻转的非先验格（反向先验已失败）；150 格里挑出的 9/9，存在多重比较风险。→ **观察（非默认）**：按 kean 要求把有希望的候选放上纸面前向检验。
- lsbtc7_z180gt1_cap_short_off（BTC 比值 180 日 z > 1 → 不新开空）也是 9/9，post +69.0% / +69.8%，k 0.25–1.25 邻域 post 稳定（+68.6% ~ +69.6%），但深未见 Gate 只 0.21 vs 0.09、调参窗只 +0.02，k ≥ 1.75 回到基线，逐月 3/4、4/3，new8 只微胜（0.76 / 0.74），+30 / +90 天平移 post 大幅更差、−30 天平移与真实相当（+65.4%）→ 不单列观察（与上一格同属「确认式」机制，纸面只跑一格）。

## 实现（默认关闭，仅纸面前向检验）

- 新模块 `qtw/levtok_gate.py`：Gate 官方 1d K 线（BTC3L_USDT / BTC3S_USDT，`limit=400`）缓存到 `DATA_DIR/gate_levtoken_btc_daily.csv`，每 1 小时运行中自动刷新（无需重启），只用已收盘完整 UTC 日；按连续日历展开，缺日 / 零成交 → NaN 不补；`x = ln(Σ7 3L / Σ7 3S)`、`M = x 的 90 日均值`、`flag = x > M`；`known = 日 + 28h`；`block_mask` 回测与引擎共用：flag 1 拦新开空、flag 0 拦新开多；数据取不到 / 最新已知日早于 3 天 / 历史不足 → 不拦（失败开放并记日志）。
- `qtw/settings.py`：`levtok_gate_enabled=False`、`levtok_gate_sum_n=7`、`levtok_gate_trend_n=90`、`levtok_gate_stale_days=3.0`（校验 1–30 / 5–365 / 2–14）；环境变量 `QTW_LEVTOK_GATE=1` 强制开启。`qtw/engine.py`：每轮刷新状态，信号行写 `levtok_flag` / `levtok_block_long` / `levtok_block_short`，被拦时 `levtok_ok=False`、状态 `levtok_wait` 并给中文说明；`/api/signals` 返回 `levtok_gate`。`qtw/backtest.py`：`run_backtest(..., levtok_data=(日毫秒, 3L 成交额, 3S 成交额))` 可注入真实历史，summary 返回 `levtok_gate`。
- 一致性：生产函数 + 官方日表回放（`scratch/levtok4h/parity.py`）OKX d8 深未见 +61.06% / 1.09（与研究逐位相同）、调参 +75.77% / 1.56、post +64.37% / 2.41；Gate d8 深未见 +56.48% / 0.81（相同）、调参 +75.43% / 1.55、post +64.79% / 2.42。调参 / post 与研究信号过滤器有小差异（引擎「只拦新开仓」与研究 `o[i-1]==g[i]` 续持口径在止损后重入时不同），方向与幅度一致。实时：2026-11-27 日（11-28 04:00 UTC 起已知）x = 0.1256 与研究日表逐位一致。
- 测试：`tests/test_levtok_gate.py` 7 项（与 pandas 研究公式逐值一致、缺日不跳、日 + 28h 无前视、失败开放、状态、K 线解析只用已收盘日、设置校验 / 环境变量）；全套 549 passed。
- 纸面：新实例 **8802 `data/paper-levtok`**（1000U，`QTW_LEVTOK_GATE=1`，live 关，`data/paper-levtok/run.sh`），2026-11-27 17:54 PST 启动即按默认 #1 开 8 个空单（flag 0 只拦新开多，空单不受影响，与 8788 同向）。前向期望：flag 约 50–65% 时间为 1（post 占比 0.65）；与 8788 的差异只在信号翻多 / 翻空且与 BTC 杠杆代币方向不一致时出现；按回测，post 每月对基线平均约 +0.5 pp，但逐月胜率只约一半。8788 / 8789 / 8792 及其他实例未改动。

- 勿重测（never retest via）：不要换 n / 求和窗（1–30 日）/ z 窗 / 阈值 / 侧 / 滞后重测本族；不要在 BTC / ETH / 合并、3L / 3S 成交额比、成交量（币本位）、净值、代币份额 / 申赎、相对现货 / 永续成交强度之间换序列；不要改用 Gate 5 倍代币（BTC5L / 5S）、其他交易所的杠杆代币（Binance BLVT、FTX 旧代币、Bybit 等）或同类「现货杠杆 ETF 代币」替身；不要把反向（拥挤 → 拦多）先验换窗再测；也不要改成 1h「杠杆代币成交额突发 / 调仓（rebalance）」事件绕过本条。只能用 2026-11-27 之后 8802 的前向纸面数据复核 lsbtc7_trend_n90_contra_both。
- 文件：`output/research_gate_leveraged_token_flow_gate_4h.csv`、`_supp.csv`、`_new8.csv`、`_daily.csv`（均不入库）；脚本 `scratch/levtok4h/{fetch,build,run,supp,new8,parity}.py`、`PRE_REGISTER.json(.sha256)`（不推送）。因 `docs/STRATEGY_FORMULAS.md` 已超过 GitHub 连接器写入上限，本段写在本 sidecar（本地 STRATEGY_FORMULAS.md 同步追加一行轮换记录）。
- 下一轮（短线）：中国人民银行官方公开市场操作（逆回购投放 / 到期净投放量，pbc.gov.cn 每个工作日 09:20 北京时间公告，2021 起）大额净投放 / 净回笼冲击 → 8 币永续篮子 1h 顺势 / 逆势事件（公告后下一根 1h 入场）。须先确认不被 `shibor_liquidity_gate_4h`（禁利率 / 利差及其 1h 发布事件）与 `pboc_cny_fixing_shock_event_1h` 勿重测覆盖；本题是**数量**不是利率，若判同机制就换题。
