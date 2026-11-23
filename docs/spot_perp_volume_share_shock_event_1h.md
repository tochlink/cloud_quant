# 短线新族：现货 / 永续成交量占比（现货主导 vs 杠杆主导）大波动 → 8 币永续篮子 1h 事件（2026-11-22 ~19:55–20:05 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、约 1,228 个 `output/research_*.csv`、/workspace/scratch 目录名与记忆中没有「现货 / 永续成交量占比、spot-led / perp-led、现货主导 / 杠杆主导」测试。相近但不同的已否决族：8 币篮子 1h 成交额冲击（只用永续成交量）、平均单笔成交额、主动买卖失衡、1h 期现基差极端（现货 vs 永续**价格**）、投降 / 轧空 / 闪崩（只看价格，本轮作为 `any` 臂 = 同脚本基线复现）、Coinbase 美国现货成交占比（交易所份额）、Gate×OKX 跨所价差。
- 机制：同样幅度的篮子大波动，若由现货驱动（无杠杆真实买卖）应延续；若由永续杠杆驱动（现货占比异常低）应在平仓 / 资金费压力下回吐。
- 数据（只用官方、不编造、不回补）：OKX 公开 `market/history-candles` 1H 现货 `<币>-USDT`（16 币，2022-01-29 → 2026-11-23 02:00 UTC，仅 confirm=1 的已收盘 K 线）与 USDT 永续 `<币>-USDT-SWAP`（已有 deep1h / n8 官方 1h，至 2026-11-22 17:00 UTC）；Gate `api/v4/spot/candlesticks` 1h（官方接口只回 ~9,900 根，2025-10-06 起）与 Gate 官方 USDT 永续 1h。现货量只作信号；PnL 全部用官方永续开盘价 + 官方资金费（OKX 深历史资金费 / Gate 资金费）。任一序列缺小时 → 该币该小时 NaN，不插值。
- 公式：
  - 逐币 x_L = ln(Σ_L 现货量 / Σ_L 永续量)（最近 L 根已收盘 1h）；z = (x_L − 均值_168(x_L, 前移 1)) / 标准差_168(前移 1)，最少 84 根；篮子 share_z = 有效币 ≥5 时的币均值（合约面值常数在 z 中抵消）。
  - 篮子 R_L = 币均 ln(C_t / C_{t−L})（永续收盘）；ret_z = R_L / (篮子 1h 对数收益 168 根滚动标准差（前移 1）× √L)。
  - 事件：|ret_z| ≥ k 且 share 条件（spot_led：share_z ≥ +1；perp_led：share_z ≤ −1；any：不加条件）；方向 follow = sign(R_L)，contra = 反向。信号小时收盘后下一根永续开盘吃单入场，等权 8 币，持有 H 根，事件不重叠。
- 预注册：L {1,4,8} × k {2,3} × 条件 {spot_led, perp_led, any} × 方向 {follow, contra} × H {6,12,24,48} = **144 格**；`scratch/spotshare1h/PRE_REGISTER.json` 于 2026-11-22 19:58 PST 任何 PnL 之前锁定（sha256 7caf069d…652ec）。唯一先验 `L4 k2 perp_led contra H24`（杠杆主导大波动 → 回吐）；回退 `L4 k2 spot_led follow H24`（现货主导 → 延续）。
- 验证：官方 OKX d8 / OKX 未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）/ Gate d8；deep unseen 2022-02-15 → 2024-10-21，test → 2026-03-05，post → 末；Gate post 与 gate_window（2025-09-28 →）；真实费 2×taker 5.1 bps + 资金费，压力费 15.1 bps；安慰剂 = share_z 序列 ±720h 循环平移（价格冲击不动，专测「占比条件」）；`any` 臂 = 同脚本纯价格冲击基线；8 槽 usable 规则同 curve3pool1h。

## 结果（`output/research_spot_perp_volume_share_shock_event_1h.csv` 4,992 行；真实费每笔净 bps）

| 格子 | OKX deep | OKX test | OKX post | new8 deep | new8 test | new8 post | Gate post | Gate 窗口 | 8 槽 | OKX 事件数 deep/test/post |
|---|---|---|---|---|---|---|---|---|---|---|
| 先验 L4 k2 perp_led contra H24 | −115 | −9 | +187 | +66 | −54 | −4 | +69 | +51 | 4/8 | 6 / 4 / 3 |
| 回退 L4 k2 spot_led follow H24 | −94 | −229 | −55 | −172 | −140 | +29 | +112 | +89 | 3/8 | 29 / 14 / 6 |
| 同脚本基线 any contra H24 | −22 | −36 | −16 | 0 | +38 | +24 | −18 | −26 | 3/8 | 350 / 184 / 101 |
| 同脚本基线 any follow H24 | +2 | +16 | −5 | −21 | −59 | −44 | −2 | +6 | 3/8 | 350 / 184 / 101 |

- usable 8/8 = **0 / 144**（spot_led / perp_led / any 各最高 7/8，只各 1–2 格）。
- 先验：OKX 只 6 / 4 / 3 次事件，deep −115、test −9；Gate post +69 bps（15 次）但 share 平移安慰剂 +71 / +66，同等 —— 占比条件没有增量。压力费 OKX deep −135。
- 回退：OKX 三段全负（−94 / −229 / −55），new8 deep −172；Gate post +112 不能单独成立；+720h 安慰剂 OKX post +802。
- 诊断：篮子 share_z 标准差只有 ~0.5，|ret_z| ≥ 2 的大波动中 share_z ≤ −1 的只有 0.8–0.9%，≥ +1 的 1.6–8.2%；|ret_z| 与 share_z 相关 −0.02 / +0.05 / +0.12（L1/4/8）。大波动几乎从不「杠杆主导」，信号稀疏、无稳定方向性。
- 非先验最高 7/8：`L4 k2 perp_led contra H48`（OKX 6 / 4 / 3 次，new8 deep −19，Gate 窗口仅 +3），`L4 k2 spot_led contra H12`（OKX deep −42），`any follow H48`（与先验条件无关的价格冲击，t ≈ 1.2，已被投降 / 轧空族覆盖）—— 全部样本过小或 deep unseen 为负。

## 结论

**否决**。不实现、不进观察名单、不加模拟盘、不改默认；无代码改动，仅文档。

- 勿重测（never retest via）：不要换 L / k / share 阈值 / z 窗口 / H / follow↔contra，不要改用单币（逐币）而非篮子占比、改用成交额（quote）代替成交量、改用 Gate 现货替 OKX 现货、改用 Binance / Coinbase 现货量作分子、改用永续持仓量（OI）作分母，不要把「现货占比」改成「现货 − 永续收益差」或 taker 买卖量占比来重试这个「现货主导 vs 杠杆主导」机制；也不要改 15m 或 4h 周期绕过本条。
- 脚本 `scratch/spotshare1h/{fetch,run,analyze,diag}.py`、`PRE_REGISTER.json(.sha256)`、`analyze.log`、`prior_events.csv`（研究脚本未推送；数据 `scratch/spotshare1h/data/*.pkl` 不入库）。
- 下一轮（长线）：克利夫兰联储官方日度通胀 nowcast（CPI / 核心 CPI 当月环比预测）趋势 / 意外 → 4h 默认书 #1 入场闸门（先查重 breakeven_inflation_gate_4h、CPI 事件、cpinfp）。
