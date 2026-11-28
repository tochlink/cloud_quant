# 短线新族：币安官方 USDT 永续持仓量（OI）1h 冲击 → 8 币永续篮子事件（2026-11-27 ~16:20 PST，研究；先验否决，回退 8/8 但仅弱观察，仅文档，不改默认、无纸面变更）

- 换题说明：上一轮提的「比特币 Taproot（P2TR）/ OP_RETURN 每小时占比冲击」**未做**——逐笔输出类型只能从原始区块解析（Taproot 激活后约 27 万块、约 400 GB），Blockchair 区块 dump / mempool.space extras 不含输出类型，且 Ordinals 两次因同样原因放弃；其可行代理（区块见证字节占比 / 每笔字节）同一时间正由另一个代理在 `scratch/btcwitness1h`（`btc_witness_bytes_burst_event_1h`）跑，为免重复改测本族。
- 查重：`docs/*.md`、`docs/STRATEGY_FORMULAS.md`、1,355 个 `output/research_*.csv`、轮换日志中无持仓量 1h 冲击事件；不同于已否决的 4h 持仓量闸门（OKX rubik oiCcy 24h 变化作入场过滤，2026-03 起）、Aave / GMX 链上清算 1h、价格型投降反弹（#13/#14）、主动买卖失衡、资金费极值。data.binance.vision 此前从未用过。
- 数据（只用官方，不编造、不回补）：币安官方公开数据 `data.binance.vision/data/futures/um/daily/metrics/<SYM>/`（5 分钟快照，`sum_open_interest` 币数口径、`sum_open_interest_value` USDT 口径），16 个币（d8 BTC ETH BNB SOL XRP ADA DOGE AVAX + 未调参 new8 LINK LTC DOT TRX BCH ATOM NEAR UNI）× 2021-12-01 → 2026-11-26 共 29,152 个日文件，逐个用官方 `.CHECKSUM` sha256 校验通过 29,151 个，缺 1 个（NEARUSDT 2023-12-18，官方 404，保持缺失）。8,393,073 条快照，43,728 小时，每币缺小时 29–56 个（NaN 不填）。币安实时 API 在本机所在地区被拒（restricted location），只能用 D+1 的官方日文件 → **本信号无法在本机实时纸面跑**。交易：官方 OKX 1h 永续 + 官方 OKX 资金费（d8 2022-01-29 → 2026-11-27 19:00 UTC；new8 同期），官方 Gate 1h 永续 + 资金费（2025-09-24 →）。
- 公式（看 PnL 前锁定 `scratch/bnoi1h/PRE_REGISTER.json`，sha256 `cae3e8ef…`）：第 t 根 1h K 线用 t+55 分快照（小时内最后一个 5 分钟快照，收盘前已知）；x_s = 每小时 Δlog OI_s，篮子 x = 有值币的均值（8 个中 ≥6 个，否则 NaN）；d8 信号用 d8 自己的 OI（OKX d8 与 Gate d8 共用），new8 信号用 new8 的 OI。z：168h 均值 / 标准差截至 t−1（至少 84h），L 小时突发 z_L = (Σx − L·μ)/(σ·√L)。网格 metric {oi_chg 币数, oi_usd_chg USDT} × L {1,4} × k {2,3} × side {up, down, twosided} × mode {mom, contra} × H {12,24,48} = **144 格**（预注册文件写的 n_cells 288 为算术笔误，网格本身未改）。下一根开盘吃单入场，8 币等权，持有 H，不重叠，计官方资金费。**先验 oi_chg_L4_k3.0_down_contra_H24**（4h 强制去杠杆 → 做多 24h），**回退 oi_chg_L1_k3.0_down_contra_H24**。真实费吃单 5.1 bps/边，压力费 15.1 bps/边；切分 train（深未见）2022-01-29 → 2024-10-21、test → 2026-03-05、post → 末尾、gate_window 2025-09-28 →。可用 = 8 槽（OKX d8 三段、new8 三段、Gate post + gate_window）真实费全 > 0 且 n ≥ 10/8/8；再要压力费、邻域、post 月份 ≥ 6/9 两家、±168h/±720h 平移和 20 次循环移位安慰剂。

## 结果（`output/research_binance_oi_shock_event_1h.csv` 5,832 行；`_shuffle.csv` 84 行；每笔净 bps）

| 格子 | OKX d8 train / test / post | new8 train / test / post | Gate post / gate_window | 8 槽 | 压力费 8 槽 | post t | post 月胜（OKX、Gate） |
|---|---|---|---|---|---|---|---|
| 同脚本基线 一直做多 H24 | +0.5 / −8.1 / −22.0 | −3.0 / −9.5 / −10.8 | −20.1 / −28.1 | — | — | — | — |
| **先验 oi_chg_L4_k3_down_contra_H24** | −24.6 / +28.8 / **−53.6**（n 134/56/33） | +26.3 / −51.8 / +80.9 | −53.0 / −33.8 | 3/8 | 3/8 | −1.07 | 3/9、3/9 |
| **回退 oi_chg_L1_k3_down_contra_H24** | +11.4 / +61.3 / +7.1（n 204/86/60） | +13.9 / +20.4 / +31.3 | +7.3 / +8.8 | **8/8** | 3/8（OKX post −12.9） | 0.19 | 4/9、4/9 |
| 邻域 L1 k3 down contra H12 | +4.8 / +37.2 / +6.3 | +13.2 / +12.3 / +6.0 | +6.4 / +16.0 | 8/8 | 1/8 | 0.27 | 4/9 |
| 邻域 L1 k3 down contra H48 | +15.1 / +103.6 / +59.8 | +41.2 / −8.8 / +23.4 | +60.7 / +36.8 | 7/8 | 6/8 | 1.00 | 5/9、4/9 |
| 邻域 L1 k2 down contra H24 | +9.0 / +42.2 / −19.4 | +3.8 / −20.7 / +19.3 | −19.1 | 4/8 | 1/8 | −0.75 | 4/9 |
| 非先验 oi_usd_chg_L4_k3_up_mom_H48 | +24.4 / +88.2 / +41.9（n 58/29/21） | +34.5 / +23.0 / +152.3 | +44.7 / +55.6 | 8/8 | 8/8 | 0.38 | 4/9、4/9 |
| 非先验 oi_usd_chg_L1_k3_up_mom_H24 | +53.5 / +34.6 / +13.8 | +17.2 / +24.3 / +27.8 | +15.0 / +1.8 | 8/8 | 4/8 | 0.25 | 5/9、5/9 |

- 144 格中可用（真实费 8/8）4 格，没有一格 post 月份 ≥ 6/9，也没有一格 post t ≥ 1。
- **先验（4h 去杠杆 → 做多）**：OKX / Gate post 都 −53 bps、train −24.6 → 否决。
- **回退（1h OI 骤降 ≥3σ → 做多 24h）**：真实费 8/8、比一直做多基线 post 高约 29 bps、test 高约 69 bps；±168h/±720h 平移安慰剂 0/4 三段全正，20 次循环移位 0/20 三段全正、0/20 均值 ≥ 真实。但 post 只有 +7 bps（t 0.19），压力费 OKX d8 train −8.6 / post −12.9、Gate post −12.7，post 月胜 4/9 两家，k=2 与 L=4 邻域 post 全负 → 只算**弱观察（monitor-only）**，不实现、不进纸面。此外 OI 骤降多与急跌同时出现，可能与 #13/#14 投降反弹敞口重叠（未拆分）。
- 非先验 oi_usd_chg up mom（USDT 口径 OI 激增 → 顺势做多）：USDT 口径含价格本身（大涨时 OI 价值自然上升），本质是价格动量的换皮；循环移位 3/20 三段全正、H48 格 4/20 均值 ≥ 真实，post 月胜 4/9–5/9 → 不观察。
- 结论：**先验否决；回退弱观察（monitor-only），无强观察**；不改默认、无代码改动、无纸面变更。即使以后升级，也需要可在本机实时拿到的持仓量来源（币安实时 API 地区受限）。
- 勿重测（never retest via）：不要换 L / k / H / side / mode / z 窗重测本族；不要在币数 OI、USDT 口径 OI、OI/成交量、OI 离散度、单币 OI 之间换序列；不要换成 OKX rubik / Gate contract_stats / Bybit / Deribit / CoinGlass 等其他持仓量来源、或全市场 OI 汇总重测「持仓量骤变 → 篮子」同一机制；不要改用币安 metrics 里的多空账户比 / 大户持仓比 / 主动买卖比作为「同一份文件里的另一列」来绕开（大户与主动买卖已有否决族，多空比若要测须独立查重）；不要改成 4h 默认书闸门（已有 4h OI 闸门否决）。
- 文件：`output/research_binance_oi_shock_event_1h.csv`、`output/research_binance_oi_shock_event_1h_shuffle.csv`（不入库）；脚本与数据 `scratch/bnoi1h/{fetch,build,run,analyze,shuffle}.py`、`binance_oi_coin_1h.csv`、`binance_oi_usd_1h.csv`、`trades_real.csv`、`PRE_REGISTER.json(.sha256)`（不推送）。`docs/STRATEGY_FORMULAS.md` 已超过 GitHub 连接器写入上限，本段写在本 sidecar（本地 STRATEGY_FORMULAS.md 同步追加）。
- 下一轮（长线）：美联储官方 G.19 消费信贷（FRED / ALFRED 首发版本 TOTALSL、REVOLSL 循环信贷，按官方发布日 +1 天已知）→ 4h 默认书入场闸门；`rg G.19 / TOTALSL / REVOLSL / consumer credit` 只有「下一轮」指针，从未测过。须先确认不与已否决的 SLOOS、PBoC 社融、美国 M2、金融压力 / 信用闸门同机制（若判为同一「信贷」机制就换题）。
