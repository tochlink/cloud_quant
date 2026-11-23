# 短线新族：OKX 币本位（反向）永续 vs U 本位永续成交额占比冲击 → 8 币永续篮子 1h 事件（2026-11-23 ~02:30–02:50 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（全部 `*_event_1h` 列表）、`/workspace/scratch` 目录名与记忆中，「inverse / 币本位 / coin-margined / USD-SWAP」只出现在 2026-11-10 季度交割合约期限结构（用的是币本位交割合约**价格**做基差闸门），从未用过「币本位 vs U 本位永续的**成交额占比**」。不同于已否决：现货 / 永续成交量占比（spotshare1h，其勿重测范围是现货分子 / OI 分母 / taker 占比，不含保证金币种）、1h 永续成交量冲击、平均单笔、主动买卖失衡、OI / 多空比、Coinbase 美国现货占比、Gate×OKX 跨所、Bitfinex 保证金持仓、资金费 / 基差。
- 换题说明：上一轮提的「比特币 Ordinals 铭文每小时爆发」**未做**——官方小时级铭文历史在时限内拿不到（需对 ord 索引器做约 16 万次逐块请求，或逐块拉原始区块约数百 GB），且 mempool / 手续费占比 / 矿工族已否决。
- 机制：币本位永续用币本身做保证金与结算（BTC / ETH … 抵押），主要是持币大户 / 矿工 / 亚洲老钱包在用；币本位多头有「抵押物与仓位同向」的错向风险（凸性爆仓）。币本位占比突然升高 = 持币者突然活跃。先验：持币杠杆追最近 4h 的行情是脆弱的 → 次日回吐。
- 数据（只用官方，不编造、不插值、不回补）：OKX 公共 `market/history-candles` 1H `<币>-USD-SWAP`（只收 confirm=1；`volCcyQuote` = 美元面值成交额），d8 中有币本位永续的 BTC ETH SOL XRP ADA DOGE（BNB / AVAX 无），new8 中的 LINK LTC DOT BCH UNI（TRX / ATOM / NEAR 无）；11 个币各 42,226 根，2022-01-29 00:00 → 2026-11-23 09:00 UTC，0 缺口。U 本位成交额 = 已有官方 OKX 永续张数 × 收盘价（scratch/deep1h、capit/n8）。PnL 只用官方 USDT 永续开盘价 + 官方资金费（OKX 深历史 / Gate）。Gate 宇宙用 OKX 信号、交易 Gate d8 永续（Gate 官方 1h 自 2025-09-24）。
- 公式：逐币 x_L = ln(Σ_L 币本位美元成交 / Σ_L (U 本位张数×收盘))；z = (x_L − 均值_168(前移 1)) / 标准差_168(前移 1)，最少 84 根；篮子 share_z = 有效币 ≥4 时的均值（合约面值常数在 z 中抵消）。事件：high = share_z ≥ k，low = share_z ≤ −k；方向 follow = 同期 OKX d8 篮子 L 小时收益符号，contra = 反向，long / short 固定。信号小时收盘后下一根开盘吃单入场，等权，持有 H 根，事件不重叠。
- 预注册（`scratch/invshare1h/PRE_REGISTER.json`，2026-11-23 02:35 PST 在任何 PnL 之前锁定，sha256 `b95ed86a…efa12`）：L {1,4,8} × k {2,3} × {high, low} × {follow, contra, long, short} × H {6,12,24,48} = **192 格**；同脚本基线 = side=all（每小时、无占比条件）；先验 `L4 k2 high contra H24`，回退 `L4 k2 high follow H24`。真实费 2×taker 5.1 bps + 资金费，压力 15.1 bps（不假设 maker 2 bps）；安慰剂 = share_z ±720h 循环平移；分段 deep unseen 2022-02-15 → 2024-10-21、test → 2026-03-05、post → 末；Gate post / gate_window（2025-09-28 →）；usable 8/8 规则同 spotshare1h。

## 结果（`output/research_inverse_perp_volume_share_shock_event_1h.csv`，8,832 行；真实费每笔净 bps，括号为事件数）

| 格子 | OKX deep | OKX test | OKX post | new8 deep | new8 test | new8 post | Gate post | Gate 窗口 | 8 槽 |
|---|---|---|---|---|---|---|---|---|---|
| 先验 L4 k2 high contra H24 | −81 (7) | +275 (2) | +67 (1) | +33 | +34 | +278 | +66 (1) | +203 | 7/8 |
| 回退 L4 k2 high follow H24 | +61 (7) | −295 (2) | −87 (1) | −53 | −55 | −298 | −86 (1) | −223 | 1/8 |
| 同脚本基线 all contra L4 H24 | −18 (940) | −11 (480) | −18 (251) | +11 | +14 | −19 | −21 (251) | −31 | 2/8 |
| 同脚本基线 all follow L4 H24 | −3 (940) | −10 (480) | −2 (251) | −32 | −35 | −2 | +1 (251) | +11 | 2/8 |

- 篮子 share_z 标准差只有 0.56（逐币占比冲击大多是个别币的，不同步），|z| ≥ 2 全样本 OKX d8 只有 31 / 20 小时（high / low），k = 3 几乎为零 → 事件极稀。usable 8/8 = **0 / 176**（另 16 格基线不计）。
- 先验：deep unseen −81 bps（7 次，压力费 −101），post 只有 1 次（+67），无法验证；+720h 平移安慰剂 post +236 / train +69，比真实信号更好；邻域 L1 / L8 deep 都负（−96 / −79），H48 test −516。
- 回退：test / post / new8 全负。
- 唯一 n_pos = 8 的 `L4 k2 low long H6` 是 OKX 4 / 11 / 1 次事件、post +27 bps，不满足 n ≥ 10 / 8 / 8，且等同于「低占比时做多 6h」的少量巧合。

## 结论

**否决**。不实现、不进观察名单、不加 shadow、不改默认、无代码改动，仅文档；纸面实例未动。

- 勿重测（never retest via）：不要换 L / k / z 窗口 / H / 方向 / high↔low，不要改为逐币（单币）占比、改用币本位持仓量（OI）或张数、改用币本位交割合约（季度 / 当周）或 Deribit / BitMEX / Binance COIN-M 等其他所的币本位合约、改用 USDC 本位永续占比，不要把「币本位占比」改成 4h 闸门或 15m 周期来重试同一「保证金币种构成」机制。
- 文件：`output/research_inverse_perp_volume_share_shock_event_1h.csv`（不入库）；实时官方记录 `output/okx_inverse_perp_official_1h.csv`（`scratch/invshare1h/record.py`，nohup 每 10 分钟追加已确认 1H 根，不入库）；脚本 `scratch/invshare1h/{fetch,run,analyze,record}.py`、`PRE_REGISTER.json(.sha256)`、`analyze.log`、`prior_events.csv`（研究脚本未推送）。
- 下一轮（长线）：克利夫兰联储官方日度通胀 nowcast（CPI / 核心 CPI 当月环比预测）趋势 / 意外 → 4h 默认书 #1 入场闸门（此前已列指针、未测；先查重 breakeven_inflation_gate_4h、CPI 事件、cpinfp）。
