# 短线新族：比特币区块见证数据占比 / 平均每笔字节 1h 突发 → 8 币永续篮子（2026-11-27 ~15:50–16:40 PST；先验否决，非先验格弱观察 → 影子 #18 纸面前向）

- 族名：`btc_witness_bytes_burst_event_1h`。预注册 `scratch/btcwitness1h/PRE_REGISTER.json`（15:55 PST 锁定，任何 PnL 之前；16:00 前因数据源限流做过一次**看 PnL 前**的修订，最终 sha256 `c1b33f42…c43ad`）。脚本 `scratch/btcwitness1h/{run,analyze,supp,ext2}.py`（研究脚本不推送）。
- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`（165 篇）、1,355 个 `output/research_*.csv` 搜 witness / 见证 / taproot / OP_RETURN / inscription / 铭文 / runes：只有 `pboc_tsf_credit_gate_4h.md` 的「下一轮」指针与 `defillama_hack_event_1h.md` 里「Ordinals 全历史来源不可得、勿用抽样」一句，从未测过。不同于已否决的出块间隔 / 空块（`btc_block_interval_empty_event_1h`，勿重测只限间隔 vs 空块率）、链上手续费冲击、mempool 拥堵、平均块大小 4h 闸门（占用量，不是**构成**）、手续费占比 4h 闸门。另：BoJ 国债购入（Rinban）先查过——官方逐次结果只保留 2025-01 起，没有深度未见段，放弃。
- 机制：铭文 / Ordinals 把数据写进见证区，Runes / BRC-20 是大量小额交易。区块里见证字节占比（或每笔平均字节）的突变 = BTC 链上投机性「数据承载」活动的突发。

## 数据（只用官方 / 共识数据，不编造、不回补）
- mempool.space 官方 `GET /api/v1/blocks/:h`（已缓存 706,988→975,967，0 缺口）+ 975,968→977,870 用 blockstream.info esplora `/api/blocks/:h`（mempool.space 对带 extras 的分页限流到 0.25 页/秒；与 mempool 重叠的 37 块 timestamp / tx_count / size / weight 逐块相同）。共 270,883 块，2021-10-27 → 2026-11-28 00:10 UTC，0 高度缺口。
- 原预注册的第二指标 `utxo_chg`（extras.utxoSetChange）因限流拿不到全历史 → 看 PnL 前改为 `bytes_per_tx`（同一官方 size / tx_count 字段）；Blockchair 非官方，没用。
- 小时序列 44,573 小时，无出块小时 122 个记 NaN（不补）。见证字节 = (4·size − weight)/3（BIP141）；全样本见证占比均值 0.512，每笔平均 583 字节。官方小时表 `output/btc_witness_utxo_official_1h.csv`（文件名沿用，列为 wit_share / bytes_per_tx）。
- 交易：OKX 官方 1h 永续默认 8 币（2022-01-29 → 2026-11-27 19:00 UTC）、未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，OKX 官方）、Gate 官方 1h 永续 8 币（2025-09-24 起）；官方资金费计入。

## 公式（96 格）
- `x_h` = 该 UTC 小时 Σ见证字节 / Σsize（wit_share）或 Σsize / Σtx（bytes_per_tx）；mu / sd = h−168 … h−1；`z_L = (Σ_{L 小时} x − L·mu)/(sd·√L)`，L ∈ {1, 4}；k ∈ {2, 3}；burst（z ≥ k）/ twosided（|z| ≥ k）；mom（z 高做多）/ contra；持 H ∈ {12, 24, 48}h，下一根 1h 开盘吃单等权 8 币，不重叠。费用 taker 5.1 bps/边（压力 15.1）。分段 deep_unseen 2022-01-29→2024-10-21 / test →2026-03-05 / post →2026-11-27。
- 先验 `wit_share_L4_k3_burst_contra_H24`（数据承载狂热 = 投机泡沫 → 做空）；回退 `bytes_per_tx_L4_k3_burst_contra_H24`。

## 结果（真实费，每事件净 bps；8 槽 = OKX d8 三段、new8 三段、Gate post、Gate 窗口）

| 格 | OKX deep | OKX test | OKX post（t） | new8 deep / test / post | Gate post | 8 槽为正 |
|---|---|---|---|---|---|---|
| 先验 wit L4 k3 burst contra H24 | −12.5（n114） | +20.5 | −44.7（−1.32） | −11.6 / +41.4 / −34.1 | −45.0 | 2/8 |
| 回退 bpt L4 k3 burst contra H24 | −9.8（n239） | −9.4 | −26.6 | −5.7 / −20.0 / −37.5 | −26.9 | 0/8 |
| **非先验 wit L4 k3 twosided mom H48** | **+26.5（n165，t 0.71）** | **+35.8（n104，t 0.83）** | **+135.1（n50，t 2.52）** | +21.7 / +10.9 / +107.7 | **+135.3** | **8/8** |
| 同上 压力费 15.1 bps | +6.5 | +15.8 | +115.1 | +1.7 / −9.1 / +87.7 | +115.3 | 7/8 |
| 同脚本基线 always_long H48（OKX） | −3.2 | +4.6 | −31.4 | — | −15.5 | — |
| 同脚本基线 always_short H48（OKX） | −17.2 | −25.0 | +11.0 | — | −4.9 | — |

- 96 格真实费 8/8 只有 2 格（另一格 bytes_per_tx L4 k2 twosided mom H48：+0.7 / +11.8 / +29.4，t 0.74，噪声级）；压力费 8/8 为 0。
- 非先验格多空两侧都赚：OKX deep 多 88 笔 +29.9 / 空 77 笔 +22.5；post 多 39 笔 +147.7 / 空 11 笔 +90.3。post 月份 OKX 6/9、Gate 7/9 为正（2026-04 +1,539、06 +844、08 +1,664、09 +2,701、10 +619；03 −159、11 −588 bps 合计）。
- 但：Gate 2025-09-24 → 2026-03-05 段 −49.5 bps（n33）；deep 段 t 只有 0.71；方向（mom）与先验（contra）相反。
- 邻域（`_supp.csv`，事后，不算预注册）：k=3 / H48 是一条脊——L3 8/8（+35.1 / +77.6 / +44.2）、L6 7/8、L4 H36 7/8、L4 H72 5/8、k3.5 6/8；但 k=2 / 2.5 全面崩（L4 k2.5 twosided H48 2/8，L4 k2 H48 1/8），H12 / H24 仅 2–4/8。
- 安慰剂：预注册 ±168h / ±720h 里 OKX 三段全正格数 −720h 8 个 > 真实 5 个（整族看没有可区分的信息）；但对这一格本身，14 个平移（±24h … ±2160h）没有一个三段都超过真实，post 最高 +90.9（−2160h）< +135.1。

## 结论：先验否决；非先验格「弱观察」→ 纸面影子 #18，不改默认
- 预注册先验（burst 做空）与回退全部否决，族级安慰剂不弱于真实。
- `wit_share_L4_k3_twosided_mom_H48` 在未见 deep 段与未调参 new8 同号、post 两所强、压力费仍 7/8、胜过单格平移安慰剂，但 deep t 0.71、Gate 2025-09→2026-03 为负、k 邻域崩、方向是事后选的 → 只够弱观察。默认、实盘不变。
- 代码：新增 `qtw/btcwit_shadow.py`（影子子账本 #18 `btc_witness_mom_1h`，默认关；`QTW_SHADOW_BTCWIT=1` 才启动，测试模式永不启动、不联网），`qtw/app.py` 接线 + `GET /api/shadow/btcwit`，`tests/test_btcwit_shadow.py`（z 与研究 pandas 口径逐小时一致，691 个真实小时最大差 6e-14）。全套测试 542 passed。
- 纸面：新实例 **8801**（`data/paper-btcwit/run.sh`，独立 1000U，默认 #1 主账 + #18 影子），只纸面。每整点 +2 分钟用 mempool.space（失败转 blockstream）取新区块，判定刚收盘小时；|z| ≥ 3 且无持仓 → 按 sign(z) 等权开 8 币永续（总名义 1× 权益），48h 到期按 OKX 实时价平；taker 5.1 bps/边，资金费不计（回测含）。回测期望：post 段约每月 5–6 次，约 +135 bps/事件（中位 +73），deep 段约 +26 bps。
- 前向检验门槛：≥10 个新事件、均值 > 0 且多空两侧不全靠一边，才考虑做成默认关闭的可选策略。

## 勿重测（never retest via）
不要通过改 L / k / H / 窗口、burst ↔ twosided、mom ↔ contra，在 wit_share / bytes_per_tx / 区块 weight / size / tx_count / segwit 交易占比 / UTXO 变化 / 输入输出数之间换序列，换 BTC 单币 vs 篮子反应，改用 Ordinals / Runes / BRC-20 计数（任何来源）、OP_RETURN 字节或 Taproot 输出占比，或改成 4h 闸门的方式重测本族；影子 #18 的前向结果出来前也不要在现有历史上再调参数。

## 文件
- `output/research_btc_witness_bytes_burst_event_1h.csv`（3,912 行：96 格 × 真实 / 压力 × 3 宇宙 × 分段 + ±168h / ±720h 安慰剂 + 同脚本基线）；`output/research_btc_witness_bytes_burst_event_1h_supp.csv`（邻域 L3/4/6 × k2.5/3/3.5 × H36/48/72 + 10 个平移安慰剂）；`output/btc_witness_utxo_official_1h.csv`（官方小时序列）。
- 下一轮（长线）：选一个未测过、官方历史够 2024-10-21 / 2026-03-05 切分的 4h 默认书入场闸门族（先查重）。
