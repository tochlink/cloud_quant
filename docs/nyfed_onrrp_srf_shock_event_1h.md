# 短线新族：纽约联储官方隔夜逆回购（ON RRP）/ 常备回购（SRF）每日操作冲击 → 8 币永续篮子（1h）

> 侧记，2026-11-21 ~14:15 PST。研究，不改默认；**否决**。无代码改动，纸面实例不动。

- 查重：候选 (a) Lido WithdrawalQueue 1h 突发（`research_lido_wq_burst_event_1h.csv`）与 (b) 信标链 DepositContract 1h 突发（`research_eth_deposit_contract_burst_event_1h.csv`）均已测过并否决，跳过。改用 (c)：docs/mmf_h8_cash_gate_4h.md 留下的短线指针「纽约联储 ON RRP 每日操作结果」。docs / `output/research_*.csv` / scratch 中短线 0 条；只有长线联储净流动性（WALCL − TGA − RRP 水平，4h 闸门）、SOFR−IORB 利差 4h 闸门、FRED 宏观日冲击（VIX/油/2Y/10Y）用过相邻数据，机制不同（这里是每日公布时刻的操作用量冲击，1h 事件）。
- 数据（只用官方，不编造、不插值、不回补）：markets.newyorkfed.org 官方 API `/api/rp/results/search.json`（半年一段，2013-04 → 2026-11-20，共 5,680 次操作）。按操作日：ON RRP = Reverse Repo / Overnight 的 `totalAmtAccepted`（同日多次相加）与 `participatingCpty`；SRF = 当日所有 Repo 操作 `totalAmtAccepted` 之和（无操作即官方 0）。3,295 个 ON RRP 操作日 2013-04-02 → 2026-11-20；除 2013 年试运行期两处空档（125 / 34 天）外只有周末 / 假日缺口。官方日表 `output/nyfed_onrrp_srf_official_daily.csv`。2026-11 ON RRP 只剩约 0.4 bn 美元、2–7 家机构（已近枯竭）。
- 公布与入场：结果在 closeTime 公布（ON RRP 13:15 ET；2025 起 SRF 下午场 13:45 ET）。入场 = 当日最晚 closeTime + 30 分钟后第一根 1h 开盘（14:00 或 15:00 ET），持有 H 根，开盘出场，不重叠。成本 taker 5.1 bps/边（压力 15.1 / 20）+ 官方资金费；OKX 8 币 d8、OKX new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，未调参）、Gate d8。
- 公式：`rrp_dlog = Δ ln(1 + RRP_bn)`；`rrp_dcpty = Δ participatingCpty`；`srf_log = ln(1 + SRF_bn)`（水平尖峰）。`z = (x − 前 N 个操作日均值) / 前 N 个标准差`（不含当日）。
- 预注册（`PRE_REGISTER.json`，sha256 `c937fa37…f8544a1c`，任何 PnL 前锁定 108 格；文件 14:12:33 PST 写入，run.py 之后才启动；JSON 内 registered_at_pst 写成 14:20 为笔误）：metric 3 × N {60, 250} × k {2, 3} × mode {hyp_both：z ≤ −k 做多、z ≥ k 做空；one_sided：RRP 只做多 / SRF 只做空；contra_both 镜像} × H {4, 24, 48}。先验 `rrp_dlog_z_N250_k2.0_hyp_both_H24`（现金撤出 Fed RRP = 流动性释放 → 做多；涌入 = 抽水 → 做空），回退 `rrp_dlog_z_N60_k2.0_hyp_both_H24`。切分 train → 2024-10-21（深度未见，OKX 自 2022-01-29）/ test → 2026-03-05 / post → 今；Gate 自 2025-09-24。
- 结果（真实费，每笔净 bps；`output/research_nyfed_onrrp_srf_shock_event_1h.csv` 5,846 行）：

| 格 | OKX d8 train（深度未见） | test | post | new8 train / test / post | Gate post | post 月正 | 计分 |
|---|---|---|---|---|---|---|---|
| 先验 N250 k2 H24 | −80.0（n49，t −1.96） | +30.6（n67） | −40.5（n21） | −74.8 / +62.0 / +3.3 | −40.4 | 3/9（两所同） | 4/8 |
| 回退 N60 k2 H24 | −43.6（n40） | +0.6（n35） | −59.6（n20） | −25.7 / +20.6 / −12.6 | −59.3 | 4/9 | 3/8 |
| 基线 每日无条件做多 H24 | +5.3（n679） | +3.9 | −37.5（n179） | — | — | — | — |

  - 先验压力费 15.1：train −100.0、post −60.5。±720h 安慰剂 post +7.4 / +1.2（都好于真实 −40.5）；随机工作日 14/15 ET 安慰剂分位 train 7.5%、post 32.6%（要求 ≥ 90%）。
  - 全网格 usable 8/8 = 0/108。最好的 7/8 是 `srf_log_N250_k2_contra_both_H48`（post n=1）与 `rrp_dlog_N60_k3_contra_both_H24`（post n=5，new8 test −60）；6/8 格 post 样本都 ≤ 11、t < 1、train 多为负。邻域（rrp_dlog hyp_both 的 N/k/H）post 全负，只有 N250 k2/k3 H48 为正（n 16 / 4），不成片。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动，仅文档；不加影子子账户。ON RRP 用量在 2026 已近枯竭（~0.4 bn），post 冲击多是小额噪声，深度未见段反向亏损，打不过安慰剂，每笔边也远不够覆盖 1h taker 费。
- 勿重测：不要以同一机制换 N / k / H / 方向 / 单边，换 RRP 金额 ↔ 机构数 ↔ 净变化 ↔ 水平，换 SRF / 回购用量 / 定期回购 / 外国官方回购池（FIMA），换 RRP 授予利率 / 利差，换更早起点或 4h 闸门再测。
- 文件（不入库）：`output/research_nyfed_onrrp_srf_shock_event_1h.csv`、`output/nyfed_onrrp_srf_official_daily.csv`；脚本 `scratch/next_short_1406/{fetch,events,run,analyze}.py`、`PRE_REGISTER.json(.sha256)`（研究脚本未推送）。未起实时记录器（日频、已否决；需要时可用官方 `/api/rp/reverserepo/all/results/lastTwoWeeks.json`）。
- 下一轮（长线）：美联储官方 H.15 商业票据利差（3 个月 AA 金融类 CP − 3 个月国库券，FRED DCPF3M − DTB3，日频）n 日趋势 / z 分位 → 4h 默认书入场闸门（企业短期融资压力）。docs / output 检索 commercial paper / CP 利差 0 条；不同于已否决的 SOFR−IORB、联储净流动性、FRED 宏观日冲击。
