# 长线新族：Henry Hub 天然气现货价格（EIA 官方日度）趋势 / 冲击 → 4h 默认书 #1（MA 50/150）入场闸门（2026-11-22 ~19:30–19:50 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md 中「Henry Hub / 天然气价格」只作为「下一轮（长线，未测）」指针出现（hardfork、ercot 节）；`us_rigcount_gate_4h` 的勿重测覆盖的是天然气**钻机数**（资本开支数量），不是气价。约 1,225 个 `output/research_*.csv` 无 henry / natgas 文件；/workspace/scratch 无对应目录。最近的已否决族：`us_rates_oil_trend`（DGS10 / T10Y2Y / WTI 原油 SMA 闸门）、EIA 周度原油库存 1h、ERCOT 电价 1h、钻机数、铜金比、黄金 ETF。
- 数据（仅官方）：EIA Natural Gas Navigator 日度 `RNGWHHD` Henry Hub 现货价（$/MMBtu），https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls（Last-Modified 2026-11-18 14:44 GMT，sha256 e2e8606a40520d94…）。1997-01-07 → 2026-11-17 共 5,732 个观测；只用 2008-01-01 起（4,744 个；2007 年前文件有 >5 天缺口；2015 年后最大间隔 5 天 = 节假日）。不补值、不插值；存 `output/eia_henryhub_official_daily.csv`（不入库）。EIA 的 NYMEX 近月期货日度 `RNGC1` 已于 2024-04 停更，不用。
- **滞后（point-in-time）**：EIA 每周三更新一次日度现货（最坏约 d+8 才可见），保守取日期 d 的值从 **d+10 天 00:00 UTC** 起才使用，ffill 到 4h。
- 公式：hh = ln(现货价)。flag = 1 表示气价走强 / 冲击：`trend_nN`：hh > 近 N 个观测均值（N 20 / 50 / 100 / 200）；`momN_gt0`：hh − hh[−N] > 0（N 20 / 60 / 250）；`z20_n250_gtK`：20 日对数涨幅相对其 250 日滚动均值 / 标准差的 z > K（K 1 / 2）。侧：long_off（flag=1 不开新多）/ short_off（flag=0 不开新空）/ both / contra_both；只拦新开仓，已持仓、止损、离场不变。
- 预注册：1 序列 × 9 形式 × 4 侧 = **36 格** + 同脚本基线（默认书 #1）；`scratch/natgas4h/PRE_REGISTER.json` 于 2026-11-22 19:33:55 PST、任何 PnL（及占用率）之前锁定（sha256 504164f4…82f6）。唯一先验 `hh_z20_n250_gt1_long_off`（气价 20 日急涨 = 能源 / 通胀冲击、美国矿工电费上升 → 拦新多）；回退 `hh_trend_n100_long_off`。
- 验证：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续 + 官方资金费；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（永续 maker 2 / taker 5.1 bps，现货 10），压力费 taker 15.1 bps；安慰剂 = 先验 / 回退各 10 个可得时间平移（±7 / ±14 / ±60 / +180 / −120 / +365 / −119 天）+ 5 个 20 观测块随机打乱；邻域；未调参 new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI，最近 4,500 根）。
- 占用率（flag=1 比例）：先验 z20>1 在 deep 0.11 / tune 0.13 / **post 0.00**；回退 trend_n100 0.47 / 0.53 / 0.24。

## 结果（`output/research_henryhub_natgas_gate_4h.csv` 261 行；`_new8.csv` 16 行）

| 格子 | 所 | deep unseen 收益 / Sharpe | tune 收益 / Sharpe | post 收益 / Sharpe | post 月 好/坏 | 9 段 |
|---|---|---|---|---|---|---|
| 基线 | OKX | +35.14% / 0.71 | +85.08% / 1.47 | +59.90% / 2.23 | — | — |
| 基线 | Gate | −3.63% / 0.09 | +84.25% / 1.46 | +60.32% / 2.25 | — | — |
| 先验 hh_z20_n250_gt1_long_off | OKX | +44.01% / 0.84 | +85.08% / 1.47 | +59.90% / 2.23 | 0/0 | 4/9 |
| 先验 | Gate | +2.20% / 0.17 | +84.25% / 1.46 | +60.32% / 2.25 | 0/0 | |
| 回退 hh_trend_n100_long_off | OKX | +21.62% / 0.53 | +115.70% / 1.76 | +59.90% / 2.23 | 0/0 | 3/9 |
| 回退 | Gate | −8.60% / 0.00 | +113.34% / 1.74 | +60.32% / 2.25 | 0/0 | |
| 最好 hh_trend_n20_short_off（非先验） | OKX | +23.71% / 0.56 | +109.49% / 1.67 | +65.08% / 2.46 | 3/6 | 7/9 |
| 最好 | Gate | −8.49% / −0.01 | +98.41% / 1.57 | +65.90% / 2.49 | 4/5 | |

- 先验 4/9：只在 deep 段变好（全程少 4–5 笔交易）；tune 与基线相同，**post 段 0 次触发（= 基线，0/0 月）**，无法前向验证。15 个安慰剂中 9 个 ≥ 4/9，块随机打乱 rnd4 达 9/9、6 个 6/9 —— 真实信号不优于安慰剂。邻域（K 0.5–1.5、L 10–40、N 120/500）3–6/9，post 全部 = 基线。
- 回退 3/9：deep 两所都变差，tune 变好，post = 基线；15 个安慰剂中 10 个 ≥ 3/9。
- 36 格最高 7/9 是非先验 `hh_trend_n20_short_off`（post +5 pp，但 **deep unseen 在 OKX d8 / Gate d8 都变差**，post 月份只有 3/6、4/5，达不到两所 ≥ 6/9）；邻域 n17 / n23 / n26 / n32 都是 post 月份 2–4 好 / 5–7 坏。econ 侧最好 `hh_trend_n20_both` 6/9，tune 段 −38 pp。
- 压力费（taker 15.1 bps）：基线 post OKX +55.94% / 2.12、Gate +56.78% / 2.15；先验 = 基线；最好格 +62.38% / +62.86%，但 deep 仍更差（OKX 0.42 vs 0.56，Gate −0.16 vs −0.07）。
- 未调参 new8：先验 pre Sharpe OKX 1.03 vs 1.02、Gate 1.00 vs 0.99（只拦 1 笔），post = 基线；回退 pre 1.15 / 1.13（拦 27 笔，略好）但 post 只 +0.2 pp（1/1 月）；最好格 pre 0.80 / 0.81 vs 1.02 / 0.99、post OKX −5.2% vs +3.3%、Gate +6.2% vs +16.4%（大幅更差）。

## 结论

**否决**。不实现、不进观察名单、不加模拟盘、不改默认；无代码改动，仅文档。先验在 post 段从未触发、不胜安慰剂；唯一 7/9 的非先验格 deep unseen 两所都变差、post 月份不过半、new8 大幅更差。

- 勿重测（never retest via）：换 N / z 窗口 / 阈值 / 侧 / 方向；换现货 ↔ NYMEX 期货近月 / 远月 / 期限结构；换其他天然气枢纽（TTF、JKM、NBP、AECO、Waha 等）或电价 / 煤价 / 丙烷 / 取暖油等同类能源价格；换气价 / 油价比、季节性调整、同比 z；换 EIA 周度天然气库存（WNGS）水平 / 意外；也不要改成 1h「EIA 周四天然气库存发布」事件来绕过本条。
- 脚本 `scratch/natgas4h/{build,prereg,run,new8}.py`、`PRE_REGISTER.json(.sha256)`（研究脚本未推送）。
- 下一轮（短线）：主链出块停顿 / 链停摆冲击（Solana 官方 RPC slot→blockTime 间隔、以太坊官方区块间隔异常长）→ 8 币永续篮子 1h 事件（先查重 btcinterval1h，只保留未测的链）。
