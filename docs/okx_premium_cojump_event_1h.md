# 短线新族：OKX 永续溢价（标记价 / 指数价 − 1）8 币同向骤变（co-jump）1h 事件 → 8 币永续篮子（2026-11-21 23:59 – 2026-11-22 ~00:40 PST，研究，不改默认；否决）

- 查重（先做）：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,147 个）、`/workspace/scratch`、记忆检索 basis / premium / mark / index / basis_extreme / funding。最接近的已否决族：
  - `basis_extreme_1h`（2026-11-14）：**逐币**「永续成交收盘 / OKX 现货收盘 − 1」的**水平** z（168h）极端，单币 fade / follow / 期现套；
  - `basket_funding_extreme_event_1h`：8h 结算**资金费率**的水平 / z / 负费率广度；
  - `cross_venue_dislocation_shock_event_1h`（Gate vs OKX 永续收盘价差）、`coin_funding_price_divergence_event_1h`、资金费结算窗口、1h 微结构事件（爆仓 / OI / 主动买卖 / 多空比）。
  - 本族用不同的官方序列（OKX **标记价 vs 指数价** 1h 收盘 = 交易所口径溢价）和不同的事件类型（逐币标准化后的**1h 溢价变化**在 8 币中**同向骤变的广度**，篮子交易）。溢价水平 / 符号广度刻意不测（已被 basis_extreme / 篮子资金费覆盖）。2026-11-21 gatefundcap4h 节把本族列为下一轮短线候选。
- 官方历史深度（实测）：
  - OKX `GET /api/v5/public/premium-history`（官方溢价指数，约每分钟一条）：只给约 6 个月（BTC 最早 2026-05-21 16:01 UTC），**不足 1 年 → 不回测**，改开记录器（见下）。
  - OKX `market/history-mark-price-candles`（X-USDT-SWAP, 1H）：至少到 2020-01（本轮取 2022-01-01 起）；`market/history-index-candles`（X-USDT, 1H）：2022-01 起（BNB 指数 2022-12-22、BNB 标记 2022-12-23 起）。本轮取 2022-01-01 00:00 → 2026-11-22 07:00 UTC 共 42,872 小时，BTC 以外 7 币 0 缺口（BTC 少最后 1 根未确认），只保留 confirm=1。
  - Gate `futures/usdt/candlesticks` `mark_X_USDT` / `index_X_USDT` 1h：只给最近 10,000 根（2025-10-02 起，9,989 小时），只用于 Gate 自身触发的稳健性行。
- 公式（看 PnL 前锁定 `scratch/premjump1h/PRE_REGISTER.json`，文件时间 2026-11-21 23:59 PST，sha256 `a55f6630bbb21b965d16f1f7f55ddae5cafe5f14ca55ed2e235f2e321bba15bd`，128 格）：
  - `p_i,t = (mark_close_i,t / index_close_i,t − 1) × 1e4`（bps，已收盘小时）；`D_i,t = p_i,t − p_i,t−L`；`z_i,t = (D_i,t − mean_168(D_i)) / sd_168(D_i)`（窗口截至 t−1，最少 84）；有效币数 ≥ 7。
  - 上行广度 `#{z ≥ k}/n`、下行广度 `#{z ≤ −k}/n`；广度 ≥ m/8 → 下一根 1h 开盘吃单等权 8 币永续做多 / 做空，持 H 小时后开盘离场，不重叠；官方资金费计入。
  - 网格：L {1, 4} × k {2, 3} × m {6, 8} × side {up, down} × dir {long, short} × H {6, 12, 24, 48}。触发统一用 OKX d8 溢价。
  - 唯一先验 `L1 k2 m6 down long H24`（全篮子永续同时跌到指数下方 = 集中去杠杆 / 强制卖永续 → 24h 反弹）；回退 `L1 k2 m6 up short H24`（同步溢价飙升 = 杠杆追多 → 反向 24h）。
- 交易与验证：OKX 官方 1h 永续 d8（2022-01-29 →）与未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI），Gate 官方 1h 永续 d8（2025-09-24 →）；taker 5.1 bps/边（压力 15.1）；切分 train（深未见，< 2024-10-21）/ test（< 2026-03-05）/ post（→ 2026-11-22）/ gate_window（2025-09-28 →）。同脚本无条件基线、±720h 平移安慰剂、post 9 个月逐月对基线、一步邻域（L/k/m/H）、Gate 自身标记 / 指数触发。
- 结果（`output/research_okx_premium_cojump_event_1h.csv`，5,824 行），每笔净收益 bps（真实费），括号为笔数：

| 格 | OKX d8 train / test / post | new8 train / test / post | Gate d8 post / gate_window | 8 槽为正 | post 月份胜基线（OKX / Gate） | 压力费 OKX post |
|---|---|---|---|---|---|---|
| 先验 L1 k2 m6 down long H24 | −15.2 (9) / −164.0 (4) / −34.2 (3, t −0.2) | +54.6 / −388.4 / +160.9 | −31.1 (3) / −253.2 (4) | 2/8 | 2/9 / 2/9 | −54.2 |
| 回退 L1 k2 m6 up short H24 | +255.3 (6) / −17.5 (5) / +5.7 (2) | +239.3 / −10.6 / −286.1 | +5.4 (2) / −45.4 (4) | 4/8 | 1/9 / 1/9 | −14.3 |
| 最佳 8/8（非先验）L4 k2 m6 down long H48 | +247.6 (14) / +259.2 (8) / +458.1 (1) | +326.6 / +489.5 / +1452.9 | +461.7 (1) / +760.6 (2) | 8/8 | 1/9 / 1/9 | +438.1 |

  - 同脚本基线（long H24）：OKX d8 +0.5 / −8.1 / −22.7，Gate post −23.2；（long H48）OKX −3.2 / +4.6 / −33.9。
  - **事件极稀**：先验触发 5 年只有 9 / 4 / 3 次；k=3 或 m=8 的格在 post 段多为 0 笔。128 格 8 槽为正分布 0:27、1:4、2:47、3:14、4:13、5:9、6:9、7:1、8:4；**可用 8/8（train ≥ 8、test ≥ 6、post ≥ 5 笔）为 0**。4 个 8/8 格 post 都只有 1 笔。
  - 安慰剂：先验 +720h 平移 OKX test / post +154.1 / +90.9、Gate post +92.0（好于真实）；−720h train +127.5。在 OKX+Gate 5 槽全正的格数：真实 4、+720h 2、−720h 1；≥ 4/5：真实 15、+720h 14、−720h 12 —— 与安慰剂无差别。
  - 邻域（先验一步）：H48 6/8 但 test −61.7、H12 5/8、H6 4/8、L4 6/8（train −112.9）、k3 3/8（post 0 笔）、m8 2/8。最佳格邻域：H12 7/8 但 train −22.2，L1 6/8（test −61.7），k3 3/8（train −161.9），m8 5/8（post 0 笔）。
  - Gate 自身标记 / 指数触发（2025-10 →）：先验 post +65.7（6 笔，t 0.7，月 3/9），回退 −64.6，最佳格 post −377.4（2 笔）—— 与 OKX 触发不一致。
  - 探索性（**未预注册**，只为判断是不是阈值过严）：k {1.0, 1.5} × m {4, 5, 6}（`output/research_okx_premium_cojump_event_1h_nbhd.csv`）。唯一像样的 `L1 k1.0 m6 up long H48`（溢价同步上冲 → 做多 48h）8/8：OKX +48.4 (96) / +48.8 (69) / +23.6 (25)，new8 +49.9 / +79.2 / +76.5，Gate post +25.1 / gate_window +11.3，post 月份 6/9 / 6/9；但所有 t < 1.2（OKX post t 0.23），压力费 gate_window 转负，邻域崩（m5 H48 −47.4、m5 H24 −5.2、k1.5 train −160.1、L4 post −102.5、H24 4/8）。事后挑出、非先验，不作观察。
- 结论：**否决**，不实现、不进观察名单、不加模拟盘、不改默认，无代码改动。OKX 标记价 − 指数价的 1h 溢价同步骤变在预注册阈值下 5 年只有十几次，先验 2/8、回退 4/8，没有可用格，真实与 ±720h 安慰剂无差别；放宽阈值后的唯一 8/8 是孤立、t < 1 的事后格。**勿重测**：不要换 L / k / m / H / 方向、换 z 窗口、换成溢价水平 / 符号广度、加权（按 OI / 成交额）广度、单币溢价骤变、Gate 自身溢价、15m / 4h 周期，或用 `premium-history` 分钟溢价重做同一机制（等记录器累积 ≥ 1 年后才可作为新数据源单独立项）。
- 记录器（只前向累积，不回测）：`scratch/premjump1h/record.py`（标准库 + SQLite，RSS 约 28 MB，pid 在 `record.pid`），每 10 分钟拉 OKX 官方 `public/premium-history` 8 币全部可得行写入 `premium_history.sqlite`（首轮回补端点还在服务的约 6 个月：BTC 265,724 行 2026-05-21 16:01 UTC 起），并打印当前 1h 标记 / 指数同步骤变广度（先验信号，仅监控）。
- 文件（不入库）：`output/research_okx_premium_cojump_event_1h.csv`、`_nbhd.csv`；官方 1h 溢价 `output/okx_premium_mark_index_official_1h.csv`；原始 `scratch/premjump1h/raw/*.csv`；脚本 `scratch/premjump1h/{fetch,run,analyze,summarize,nbhd,record}.py`、`PRE_REGISTER.json`（研究脚本未推送）。
- 下一轮（长线）：交易所官方储备证明（OKX 每月 Proof-of-Reserves 用户负债快照，BTC / ETH / USDT，2022-11 起）用户 BTC / USDT 负债的月度变化作为 4h 默认书入场闸门。docs / output 中无 proof-of-reserves / 储备证明条目；不同于已否决的交易所链上流量、稳定币铸造、借贷利率。先确认官方历史快照可下载的月数（约 48 个点，样本小，网格要小），不足则只开记录器。
