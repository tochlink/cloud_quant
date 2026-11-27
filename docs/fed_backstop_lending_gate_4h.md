# 长线新族：美联储后备流动性使用量（H.4.1 贴现窗口一级信贷 / 央行流动性互换）→ 默认 #1 4h 入场闸门（2026-11-27 ~11:20–12:00 PST；弱观察 → 纸面 8799，不改默认）

- 换题说明：本轮原定「台积电月营收（YoY / 3 月趋势）」**不跑**——`docs/kr_customs_exports_gate_4h.md` 勿重测已明确禁止「改用半导体出口」「换成台湾 / 日本 / 中国的出口数据（同一全球贸易周期机制）」，台积电月营收是同一全球芯片 / 贸易周期的月度读数，按查重规则视为同一机制。
- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、记忆中 SWPT / swap line / 央行流动性互换 / discount window / 贴现窗口 / primary credit / 一级信贷 / BTFP 只出现在「下一轮」指针里，0 个完成研究。不同于已测的 H.4.1 外国官方托管（8794，持有量）、联储净流动性 / WALCL、SOFR−IORB、NFCI / STLFSI / HY OAS、H.8、货币基金，也不是 ON RRP / SRF（`nyfed_onrrp_srf_shock_event_1h` 勿重测禁止 SRF / 回购用量做 4h 闸门，本族不含 SRF / 回购）。
- 机制：银行在贴现窗口借一级信贷、外国央行动用美元互换 = 美元融资压力的后备借款；用量升到自身均线以上 = 融资压力上升 = risk-off → 拦新开多（先验 long_off / both）。只拦新开仓，已持仓、止损、退出、再平衡不变。
- 数据（仅官方）：FRED 官方 H.4.1 周三水平 `WLCFLPCL`（一级信贷，百万美元）、`SWPT`（央行流动性互换），2002-12-18 → 2026-11-18 共 1,249 周，日历缺口 0，缺值 0。周三 D 值保守按 D+3 00:00 UTC 才使用（H.4.1 周四 16:30 ET 发布，多留一天吸收节假日顺延）。局限：FRED 当前 vintage（H.4.1 周三水平极少修订）。存 `output/fed_backstop_lending_official_weekly.csv`（不入库）。
- 格子（PnL 前锁定，PRE_REGISTER.json sha256 f6fb150a…616b，120 格）：序列 swp / pcr / tot（= swp + pcr）× 形式 trend（值 > 4 / 13 / 26 周均线）、chg（4 / 13 周变化 > 0）、z52gt（52 周 z > 0.5 / 1 / 2）× 侧 long_off / short_off / both / contra_both / cap_short_off。**先验格 pcr_trend_n13_long_off**，回退 tot_trend_n26_both。
- Harness：复制 `scratch/faofpi4h/run.py`（`qtw.backtest.run_backtest` 默认双均线 50/150 4h，8 币永续）。OKX d8（2023-02 起）/ Gate d8（2022-07 起）/ OKX d7_noBNB（2022-04 起）；deep_unseen → 2024-10-21，tune_pre → 2026-03-05，post → 2026-11-14；官方资金费；永续吃单 5.1 bps，压力 15.1；安慰剂 = 先验格与最佳先验侧格各自平移 ±30 / ±90 / +180 / −120 / +365 / −119 天 + 3 次固定种子周度打乱；邻域；未调参 new8。
- 同脚本基线：post OKX +59.90% / Sharpe 2.23，Gate +60.32% / 2.25；deep OKX +35.14% / 0.71，Gate −3.63% / 0.09；tune OKX +85.08% / 1.47，Gate +84.25% / 1.46。

## 结果（CSV `output/research_fed_backstop_lending_gate_4h.csv`、`_new8.csv`、`_supp.csv`）
- **先验 pcr_trend_n13_long_off**：6/9 Sharpe 片；post OKX +62.02% / 2.36、Gate +62.63% / 2.38（+2.1 / +2.3 pp），但 post 只有 3 个月不同（1 好 / 2 差）；deep 胜（OKX 0.85、Gate 0.27），tune 输（1.32 / 1.28）。安慰剂 −30 天、打乱 1、打乱 3 也到 6/9，打乱 3 的 deep / tune 更好；邻域 n17 / n20 / n39 的 post 与先验完全相同（同一两笔交易），n8 / n10 post 低于基线。压力费 post +58.46% / +59.06% vs 基线 +55.94% / +56.78%。→ 先验格无超出安慰剂的信息。
- **最佳先验侧格 pcr_trend_n13_both**（一级信贷 > 13 周均线拦新多、否则拦新空）：6/9；post OKX **+66.66% / 2.58**、Gate **+67.41% / 2.60**（+6.8 / +7.1 pp，Sharpe +0.35），月份 **5/2、6/1**（d7 4/3）；deep 胜（OKX +35.35% / 0.85 vs 0.71，Gate +3.74% / 0.18 vs 0.09，d7 0.81 vs 0.75）；但 **tune_pre 大幅落后**（OKX +38.34% / 1.03 vs +85.08% / 1.47，Gate +32.27% / 0.94 vs +84.25% / 1.46）。22 个安慰剂 post 全部更差（最好 −30 天 OKX +60.16% / 2.44、Gate +60.48% / 2.45；+90 天 post −6.9%，打乱 2 ≈ 0%）。压力费 post +63.74% / +64.38%（基线 +55.94% / +56.78%）。邻域 n10 / n17 / n20 post 全部更好（n20 OKX +73.33% / 2.80、Gate +74.01% / 2.82，月份 6/1），n8 / n39 post 持平或略差；但 tune 段所有 n 都输（Sharpe 0.15–1.22 < 1.46）。
- new8（未调参）：pcr_trend_n13_both post OKX +10.70% / 0.88 vs +3.26% / 0.28、Gate +24.88% / 1.58 vs +16.36% / 1.00，月份 6/1、6/1；但 pre（2024-12 → 2026-03）OKX −6.25% vs +30.67%、Gate −5.24% vs +28.60%。先验 long_off 在 new8 上 pre / post 都略好（月份 3/0）。
- 其他：唯一 9/9 是非先验 swp_z52gt2_cap_short_off，post 仅 +0.9 / +1.0 pp，月份 3/2，太薄；tot_trend_n26_both 6/9 post +6.1 / +6.7 pp 但 tune 为负。
- 未达默认改动标准：两所 post 月份未同时 ≥ 6/9（OKX 5/9），且 2024-10 → 2026-03 段（OKX / Gate / d7 / new8）一致大幅落后，说明是体制依赖。

## 结论
- 默认不变。pcr_trend_n13_both 达到预注册的「弱观察」（先验侧格 ≥ 6/9、两所 post 不差、月份未达标），post 优势明显好于全部安慰剂、邻域 n10–n20 一致 → 只做纸面前向检验。
- 新增可选 `backstop_gate_*`（默认关闭，`qtw/backstop_gate.py`，回测与引擎同一函数，运行中每 6 小时自动刷新 FRED，失败开放），与研究逐位一致（OKX d8 285 笔 / Gate d8 346 笔，权益最大差 0.0），测试 527 passed。
- 纸面实例 **8799 paper-backstop**（`data/paper-backstop/run.sh`，QTW_BACKSTOP_GATE=1，live 强制关）：1000U，默认 #1 书 + 本闸门。只有 post 逐月两所都 ≥ 6/9、且前向纸面不输 8788 时才再讨论改默认。

## 勿重测
不要靠下面这些办法重测本族：
- 改 trend_n / chg_n / z 阈值 / 侧；在一级信贷、互换、合计之间互换；
- 改用二级信贷、季节性信贷、BTFP、其他 H.4.1 贷款科目、贴现窗口周均值（而非周三水平）；
- 换成 SRF / 回购 / FIMA（已被 ON RRP / SRF 勿重测覆盖）、联邦住房贷款银行（FHLB）预付款、欧央行 / 日银等其他央行的紧急借款；
- 缩短发布时滞；
- 用同一历史再挑 n20 等邻域格。只用 2026-11-27 之后 8799 的前向纸面数据复核。

## 文件
- `output/research_fed_backstop_lending_gate_4h.csv`（525 行）、`_new8.csv`、`_supp.csv`；`output/fed_backstop_lending_official_weekly.csv`（output 不入库）。
- 脚本：`scratch/fedswap4h/{build,run,new8,supp,parity}.py`、`PRE_REGISTER.json`、`PRE_REGISTER.sha256`；日志 `run.log` / `new8.log` / `supp.log` / `pytest_full.log`。
- 代码：`qtw/backstop_gate.py`、`qtw/settings.py`、`qtw/backtest.py`、`qtw/engine.py`、`tests/test_backstop_gate.py`。
