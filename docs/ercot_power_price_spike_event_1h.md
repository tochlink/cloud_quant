# 短线新族：ERCOT 官方实时电价尖峰（德州电网紧张 → 比特币矿工限电）1h 事件 → 8 币永续篮子（2026-11-22 ~09:05–09:25 PST，研究，不改默认；否决）

状态：**否决**。不改默认、不加可选代码、不加纸面实例 / shadow；纸面 8788/8789/8792/8793/8794/8795/8796 照常运行（只纸面、live 关），8790/8791/8787 未触碰。

## 选题与查重

- 计划题「以太坊 Beacon sync committee 参与率骤降 / reorg 1h 突发」**未跑**：(1) 机制上是链活性代理，与已否决的信标漏槽 1h 突发（`output/research_eth_missed_slot_burst_event_1h.csv`）同族，该节明确「不要用漏槽冒充参与率、勿换形式重测」；(2) 官方数据不可行：ethPandaOps Xatu 无 canonical sync-aggregate 表（`canonical_beacon_block_sync_aggregate` 404），reorg 只有 sentry 观测表（非 canonical、覆盖随节点数变化），逐块 beacon API 取 `sync_aggregate`（Altair 起约 500 万 slot）无法在时限内完成。
- 改选：ERCOT 官方实时结算点电价（RTM SPP）尖峰。rg `ERCOT / 电价 / electricity` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,184 个）、记忆：0 条测试（唯一 1 条是 CBECI 比特币网络功耗长线日度闸门，不同序列、不同机制）。不是已否决的出块间隔 / 空块、难度调整、算力带、矿工 coinbase 支出、链上手续费。
- 机制：德州是美国最大的比特币挖矿州；实时电价飙升时矿工参与需求响应限电（少挖、少卖新币），电网紧张属外生冲击。交易稀少（≥$1000/MWh 的小时 2022 年 33 个、2024 年 8 个、2025 年 3 个、2026 年 1 个），单笔持有 24–48h，满足「少交易 / 结构性大边」的筛选要求。

## 数据（只用官方，不补、不插值）

- ERCOT 报表 13061「Historical RTM Load Zone and Hub Prices」（NP6-785-ER）年度 zip：`https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=13061` → `mirDownload?doclookupId=<DocID>`（2021–2026，2026 文件 2026-11-22 08:47 CST 发布）。同一 SPP 在 NP6-905-CD 每 15 分钟实时发布，所以已收盘 UTC 小时在收盘时可知；信号小时收盘后下一根 1h 永续开盘入场。
- 解析：Delivery Date + Delivery Hour（小时结束，中部时间）+ Delivery Interval（1–4），Repeated Hour Flag=Y 视为秋季回拨的第二个（CST）小时；转 UTC 后按小时取 4 个 15 分钟价格均值。结点：HB_HUBAVG（全网 hub 均价）与 HB_WEST（西德州，矿场集中）。
- 官方 1h 序列 `output/ercot_rtm_hub_official_1h.csv`：**51,624 个完整 UTC 小时 2021-01-01 06:00 → 2026-11-22 05:00 UTC，0 缺口、0 个不足 4 区间的小时**。HB_HUBAVG 中位 $24.9、p99 $321、最大 $9,024（2021-02 寒潮 Uri）；2026-03-05 以后 hub 均价最高 $896、西部 $915（post 段没有任何 ≥$1000 小时）。
- 行情：官方 OKX USDT 永续 1h（默认 8 币 2022-01-29 → 2026-11-22 06:00 UTC；未调参 new8 LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI）、Gate USDT 永续 1h（2025-09-24 起）、官方资金费；数据新鲜，无需追加。

## 预注册（`scratch/ercot1h/PRE_REGISTER.json`，2026-11-22 09:06 PST 锁定，sha256 前缀 `0a3377069c7b1104`，先于任何 PnL）

- 阈值族：小时价 ≥ P，P ∈ {250, 500, 1000, 2000} $/MWh × {long, short} × H {24, 48} × 结点 {hubavg, west} = 32 格。
- z 突发族（harness 与 `scratch/eigenlayer1h/run.py` 逐行相同）：x = log1p(max(价格,0))，168h 滚动均值 / 标准差（截至 t−1，最少 84），z_L = (Σ_L x − Lμ)/(σ√L)；L {1,4,8} × k {3,4,5} × {burst, twosided} × {mom, contra} × H {24,48} × 2 结点 = 144 格。共 **176 格**。
- 先验 `thr_hb_hubavg_P1000_long_H48`（≥$1000 → 做多 48h）；回退 `z_hb_hubavg_L4_k4.0_burst_mom_H48`。
- 费用：taker 5.1 bps × 2 + 官方资金费（压力 15.1 bps）；切分 train（深未见）2022-02-15→2024-10-21、test →2026-03-05、post →2026-11-22 06:00 UTC、gate_window 2025-09-28→；8 槽评分（OKX d8 三段、new8 三段、Gate post / gate_window），usable 8/8 需 OKX d8 n ≥ 10/8/8；安慰剂把信号平移 ±720h、±168h；基线 = 同持有期无条件做多。
- 注：第一次运行因 `ts_ms` 单位错误（秒）全部 0 事件、无任何 PnL 可见，修正为毫秒后重跑，预注册未改。

## 结果（每笔净 bps，真实费；`output/research_ercot_power_price_spike_event_1h.csv` 12,696 行）

| 格 | 正槽 | OKX d8 train / test / post (n) | new8 train / test / post | Gate post / window | 备注 |
| --- | --- | --- | --- | --- | --- |
| 先验 `thr_hubavg_P1000_long_H48` | 3/8 | −29.1 (28) / +146.1 (6) / 无事件 (0) | +8.3 / +120.7 / — | — / −927.0 (1) | post 无 ≥$1000 小时 |
| 回退 `z_hubavg_L4_k4_burst_mom_H48` | 2/8 | −35.6 (107) / +128.5 (52) / −59.8 (33, t −1.0, 中位 −14) | −44.5 / +110.8 / −8.5 | −58.4 / −60.1 | |
| 最佳非先验 `z_west_L4_k5_burst_mom_H24` | 8/8 usable | +70.2 (41) / +99.7 (9) / +51.4 (9, t 0.5, 中位 +98) | +107.0 / +52.7 / +17.3 | +52.6 / +67.2 | 压力 new8 post −2.7 |
| `z_west_L1_k3_burst_mom_H24` | 8/8 usable | +22.8 (72) / +140.8 (15) / +25.5 (12, t 0.3) | +25.4 / +136.6 / +41.6 | +25.8 / +25.8 | +720h 安慰剂 post +87.7 |
| `z_west_L1_k3_twosided_mom_H24` | 8/8 usable | +13.7 / +80.0 / +25.4 (36, 中位 −5.6) | +18.8 / +90.5 / +10.5 | +25.3 / +14.7 | 压力 train −6.3 |
| `z_west_L1_k4_twosided_mom_H24` | 8/8 usable | +14.8 / +28.8 / +37.3 (19, 中位 −23.3) | +42.6 / +27.6 / +35.0 | +37.0 / +20.0 | 压力 train −5.2 |

- 分布：176 格正槽数 0:19 / 1:15 / 2:42 / 3:19 / 4:26 / 5:21 / 6:25 / 7:4 / 8:5；usable 8/8 = 4，全部为 HB_WEST、mom（尖峰后做多）、H24，post t 0.3–0.7（无一 ≥1.5）。hubavg 结点无 8/8；同一格 H48 或 k4 邻格多为负（回退 L4 k4 H48 post −59.8），邻域不稳。
- 基线（无条件做多）：OKX d8 H24 post −22.7 bps（n=251）、H48 −33.9；Gate H24 post −23.2。
- 最佳非先验 post 逐月（对比同月基线）：OKX 4/7、Gate 4/7（月份太少，低于 ≥6/9 门槛）；9 笔里 10 月单笔 −484 bps。
- 时移安慰剂：+720h usable 8/8 = 11 格、−168h = 7 格、−720h = 1、+168h = 0，真实 usable 4 格 → 真实信号不胜安慰剂。
- 阈值族：post 段几乎没有事件（≥$500 仅 4–5 笔，≥$1000 / $2000 为 0），先验在 post 无法交易；P250 long H48 hubavg 6/8（train −28.5）。

## 结论

**否决**，不实现、不进观察名单、不改默认、无代码改动，只写文档。先验与回退均失败（3/8、2/8）；仅有的 4 个 usable 8/8 都是非先验的西部结点 H24 动量格，post t < 1.5、样本 9–36 笔、压力费或深未见有负槽、邻域断裂，且 ±720h / −168h 时移安慰剂产生的 usable 8/8 比真实还多。2024 年后德州电价尖峰明显变少（电池储能扩张），事件率本身在衰减。数据序列历史完整（2021 起），无需起实时记录器。

## 勿重测（never retest by…）

- 改 P 阈值、L、k、H、burst / twosided、mom / contra、long / short；
- 换结点（HB_NORTH / HOUSTON / SOUTH / 负荷区 LZ_*）、换日前市场 DAM 价、换 15 分钟粒度、换 raw / log / 电价差（RT−DA）或 ORDC 价格加成；
- 换其它电网（PJM / CAISO / MISO / NYISO / 北欧 / 中国）或用 ERCOT 负荷 / 净负荷 / 风光出力、需求响应 / EEA 紧急告警替代；
- 用该序列改做 4h 默认书入场闸门；
- 把 Beacon sync committee 参与率 / reorg 作为漏槽族的同类重开（除非有官方紧凑 1h 参与率且明确不是漏槽代理）。

## 文件

- CSV（不入库）：`output/research_ercot_power_price_spike_event_1h.csv`、官方序列 `output/ercot_rtm_hub_official_1h.csv`。
- 脚本：`scratch/ercot1h/{build,run,analyze,months}.py`、`PRE_REGISTER.json`、`analyze_wide.csv`、`prior_events.csv`、`best_nonprior_post_events.csv`（研究脚本不推送）。
- 下一轮（长线）：Baker Hughes 官方北美钻机数（rigcount.bakerhughes.com 周五发布，美国石油 + 天然气钻机总数）趋势 / 同比 → 4h 默认书入场闸门（此前仅作「下一轮」指针，未测）。
