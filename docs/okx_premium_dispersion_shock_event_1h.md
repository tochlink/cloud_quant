# 短线新族：OKX 永续溢价（标记价 / 指数价 − 1）8 币横截面离散度冲击 1h 事件 → 8 币永续篮子（2026-11-27 ~14:15 PST，研究，不改默认；否决）

- 查重：`premjump1h`（同向骤变广度，已否决，勿重测条款未列「离散度」）、`basis_extreme_1h`（逐币水平 z）、`hyperliquid_funding_premium_shock_event_1h`（Hyperliquid 溢价，含 prem_disp，仅弱观察、未实现）、`cs_dispersion_herding_shock_event_1h`（收益率离散度，不同序列）。本族是 OKX / Gate 官方标记价 − 指数价溢价的**横截面标准差**冲击，事件类型与数据源均不同。
- 数据（官方，不编造不回补）：OKX `history-mark-price-candles` / `history-index-candles` 1h，8 币，2022-01-01 → 2026-11-27，42,873 小时（复用 `scratch/premjump1h/raw`）；Gate `mark_X_USDT` / `index_X_USDT` 1h，2025-10-02 起约 9,989 小时（只作 Gate 自身触发稳健性）。永续行情：OKX d8（2022-01-29 →）、未调参 new8、Gate d8（2025-09-24 →）。
- 公式（看 PnL 前锁定 `scratch/premdisp1h/PRE_REGISTER.json`，sha256 `fb65a1619c4650986d5ab31e367c82167228d92c230657de134629249426fa1c`，96 格）：`p_i,t=(mark/index−1)·1e4`；`S_t` = 8 币 p（sd_level）或 p 的 1h 变化（sd_chg1）的横截面标准差（有效币 ≥ 7）；`zS=(S−mean168)/sd168`（窗口截至 t−1）；事件 `zS ≥ k`，条件 cond ∈ {any, 溢价中位数 < 0, > 0}；下一根 1h 开盘吃单等权 8 币永续做多 / 做空，持 H 小时，不重叠；官方资金费计入。网格 stat 2 × k {2,3} × cond 3 × dir 2 × H {6,12,24,48}。先验 sd_level k2 med_neg long H24（折价 + 分歧扩大 = 去杠杆，反弹）；回退 sd_chg1 k2 med_neg long H24。
- 验证：taker 5.1 bps/边（压力 15.1）；train（深未见 < 2024-10-21）/ test（< 2026-03-05）/ post（→ 2026-11-27）/ gate_window；同脚本无条件基线；±720h、+168h 平移安慰剂；post 月份对基线；邻域；Gate 自身触发。
- 结果（`output/research_okx_premium_dispersion_shock_event_1h.csv`，5,184 行），每笔净收益 bps（笔数）：

| 格 | OKX d8 train / test / post | new8 train / test / post | Gate d8 post | 8 槽为正 | post 月份胜基线 OKX / Gate |
|---|---|---|---|---|---|
| 先验 sd_level k2 med_neg long H24 | +19.7 (255) / −37.5 (157) / +0.3 (115) | −40.6 / −3.9 / +0.8 | −36.7 | 4/8 | — |
| 回退 sd_chg1 k2 med_neg long H24 | +1.8 / +0.7 / −24.1 | −26.8 / −23.5 / −23.6 | −23.6 | 2/8 | — |
| 唯一 usable 8/8（非先验）sd_level k3 med_neg long H48 | +30.2 (101) / +37.5 (67) / +63.7 (29, t 0.8) | +30.0 / +23.2 / +117.4 | +64.7 | 8/8 | 8/9 · 7/9 |

  - 同脚本基线 long H48：OKX −3.2 / +4.6 / −31.4，Gate post −15.5。
  - 96 格 8 槽为正分布：0:19、1:10、2:33、3:11、4:11、5:4、6:4、7:3、8:1；usable 仅 1 格，且事件数少（post 29 笔）、t 均 < 1。
  - 唯一 8/8 格的稳健性：压力费 OKX post +43.7 / Gate +44.7 仍正，但 t 0.5；**Gate 自身溢价触发 post −6.0（33 笔）、test −44.8**；安慰剂 +720h OKX train / test −54.9 / −48.0（post +29.3）、−720h train / test −48.9 / −37.0（post +77.2，反而更高）、+168h post −115.4；邻域 k2 同 H48 post −19.3 / test −6.6（k2 全部 H 在 test 为负）；k=3 只在 post 约 30 笔，收益由少数大单驱动（post 均值 63.7 vs 中位 11.1）。
  - 安慰剂计数：OKX+Gate 5 槽全正格数 真实 3、+720h 8、−720h 1、+168h 0；≥4/5：真实 9、+720h 11、−720h 8、+168h 7，与安慰剂无区分。
- 结论：**否决**，不实现、不进观察名单、不加模拟盘、不改默认，无代码改动。先验 4/8、回退 2/8；唯一 8/8 为事后非先验格，t < 1、Gate 自身触发为负、邻域不稳、安慰剂同量级。**勿重测**：不要换 stat（水平 / 变化 / MAD / 极差 / 最大−最小 / 最大币偏离）、k、H、cond、方向、z 窗口，换 BTC / 中位数基准，用 Gate 或 Hyperliquid 溢价，15m / 4h 周期，或把离散度与同向骤变 / 溢价水平组合重做同一机制。
- 文件（不入库）：`output/research_okx_premium_dispersion_shock_event_1h.csv`；脚本 `scratch/premdisp1h/{pd_run,an}.py`、`PRE_REGISTER.json`。
- 下一轮（长线）：FOMC 官方经济预测摘要（SEP）点阵图中位数变化 → 4h 默认书入场闸门（先查重 FOMC / SEP / dot plot；国债拍卖已有 1h 事件文档，勿选）。
