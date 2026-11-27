# 长线新族：美联储 H.15 商业票据融资利差（3M AA 金融类 CP − 3M 国库券）→ 4h 默认书 #1 入场闸门（2026-11-27 ~14:55 PST，研究；强观察，纸面前向检验 8800，不改默认）

- 换题说明：上一轮提到的「FOMC SEP 点阵图中位数变化」**不跑**——`docs/fomc_minutes_event_1h.md` 的勿重测已覆盖 SEP 点阵图，且 SEP 每年仅 4 次。`docs/nyfed_onrrp_srf_shock_event_1h.md` 曾列「H.15 商业票据利差」为下一轮长线候选，经查重（STRATEGY_FORMULAS、docs/*.md、1,343 个 research_*.csv 搜 DCPF3M / DCPN3M / CP spread / commercial paper / H.15）从未测过，故用它。
- 数据（只用官方，不编造）：美联储 H.15，经 FRED `fredgraph.csv?id=DCPF3M|DCPN3M|DTB3`，日度，2010-01-04 → 2026-11-24：FIN3 = DCPF3M − DTB3（3 556 个有效日），NFIN3 = DCPN3M − DTB3（2 916 个有效日，缺口较多）；两列任一缺值的日期丢弃，不补。官方日度表 `output/fed_h15_cp_spread_official_daily.csv`（不入库）。**滞后**：观测日 → 下一个工作日 + 1 天 00:00 UTC 才算已知（H.15 次一工作日下午发布，保守）。
- 公式（看 PnL 前锁定 `scratch/cpspread4h/PRE_REGISTER.json`，sha256 `926fcfa1…`，90 格）：x = 利差的 5 个有效观测均值（越高 = 融资压力越大）；序列 FIN3 / NFIN3 / CPAVG（二者 252 观测 z 的均值）；形式 trend（x > 最近 n 个 x 均值，n 20 / 60 / 120）、chg（x − x[−n] > 0，n 20 / 60）、z（252 观测 z > 1）；flag = 1 表示压力上升 / 偏高；侧 long_off（flag → 不新开多）、short_off、both、contra_both、cap_short_off（flag → 不新开空）。先验 CPAVG_trend_n60_long_off，回退 FIN3_trend_n60_long_off。
- 回测：同脚本默认 #1（perp_both 10×、官方资金费），真实费 maker 2 / taker 5.1 bps，压力费 20 / 15.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；未调参 new8（OKX + Gate 最近 4500 根）。

## 结果（`output/research_fed_h15_cp_spread_gate_4h.csv` 438 行；`_supp.csv` / `_supp2.csv` 安慰剂 + 压力费；`_new8.csv` / `_new8b.csv`）

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | OKX post 收益 / Sharpe | Gate d8 深未见 / 调参 | Gate post | post 月胜 / 负（OKX、Gate） |
|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | +59.90% / 2.23 | 0.09 / 1.46 | +60.32% / 2.25 | — |
| 先验 CPAVG_trend_n60_long_off | — | 0.46 / 0.99 | +59.90% / 2.23 | −0.18 / 0.96 | +60.32% / 2.25 | 0/0、0/0 |
| **回退 FIN3_trend_n60_long_off（预注册）** | 4/9 | **1.46 / 1.49** | +59.90% / 2.23 | **0.56 / 1.45** | +60.32% / 2.25 | 0/0、0/0 |
| 同上，压力费 | — | 1.32 / 1.38（基线 0.56 / 1.35） | +55.94%（基线 +55.94%） | 0.41 / 1.34（基线 −0.07 / 1.34） | +56.78%（基线 +56.78%） | — |
| 9 段最高 NFIN3_trend_n120_cap_short_off | 8/9 | 0.85 / 1.90 | +66.75% / 2.49 | 0.19 / 1.88 | +67.00% / 2.50 | 2/1、2/1 |

- **回退格 FIN3_trend_n60_long_off（融资压力上升 → 不新开多）**：深未见收益 OKX +99.11%（基线 +35.14%）、Gate +33.26%（基线 −3.63%）、OKX d7 +120.44%（基线 +54.92%）；2026-03-05 后与基线逐位相同（post 窗内没有任何多单被拦，所以月度 0 胜 0 负——**无增益也无伤害，不满足「post ≥ 6/9 月更好」，因此不改默认**）。调参窗 Sharpe OKX 1.49 / Gate 1.45（基线 1.47 / 1.46，持平）。
  - 安慰剂（平移 ±7 / ±14 / ±30 / ±90 / 180 / −120 / 365 / −119 天 + 5 次洗牌，共 17 个）：深未见 Sharpe 增量真实 +0.74（OKX）/ +0.47（Gate），**0/17 安慰剂不低于真实**（安慰剂中位 −0.09 / +0.20，最大 +0.53 / +0.45）；post 增量 0.00，7/17 安慰剂不低于。
  - 未调参 new8：pre 段 OKX +47.18% / Sharpe 1.07（基线 +33.92% / 0.77）、Gate +44.98% / 1.05（基线 +31.70% / 0.75），post 小幅更好（OKX +3.82% vs +3.26%，Gate +16.97% vs +16.36%）。
  - 邻域（预注册里同序列 long_off 其它形式）深未见都不低于基线：n20 1.09 / 0.37、n120 1.27 / 0.62、chg20 1.13 / 0.43、z>1 0.71 / 0.25（OKX / Gate）；n120 调参窗还略好（1.57 / 1.55 对 1.47 / 1.46）。**但同族其它序列没有同样效果**：NFIN3（非金融 CP）long_off 深未见多数不如基线，CPAVG 的 n60 更差——结论只落在「金融类 CP 利差」这一条序列上，证据面窄。
  - 引擎实现（`qtw/cp_gate.py`，经 LGB 掩码并入回测）与研究脚本口径略有差异（持仓延续的处理）：同一数据下 OKX 深 / 调参 / post = +99.97% / +77.55% / +59.90%（Sharpe 1.47 / 1.44 / 2.23），Gate +33.79% / +74.05% / +60.32%（0.56 / 1.40 / 2.25）；调参窗比基线略差（−0.03 / −0.06 Sharpe）。
- 9 段最高 NFIN3_trend_n120_cap_short_off（利差上升 → 不新开空）：post +66.75% / +67.00%（基线 +59.90% / +60.32%），邻域 n10–n200 都 7–9/9；但月度只 2/1（n10 为 5/2，n30 为 3/2、4/3），均 < 6/9；安慰剂 post 0/17 超过，但深未见增量仅 +0.14 / +0.10；**未调参 new8 pre 明显更差**（OKX +12.59% / 0.39 对 +33.92% / 0.77，Gate +14.43% / 0.43 对 +31.70% / 0.75）→ 否决该格。
- 结论：**强观察，不改默认**。依据：预注册回退格深未见两家同向大幅更好、17 个安慰剂全不及、new8 pre 更好、压力费保持；弱点：post 与调参窗无增益（post 无任何被拦的多单）、仅单一序列成立、引擎口径调参窗略低于基线、post 月度无法满足 ≥ 6/9。→ 作为可选闸门 `cp_gate_enabled`（默认关）加入代码，并开纸面前向检验实例 8800（paper-cpgate，`QTW_CP_GATE=1`，纸面、实盘关闭）。已保存的 风控→策略参数 设置会覆盖代码默认值；本闸门默认关，不影响现有实例。
- 勿重测（never retest via）：不要改 n / smooth / z 窗口 / 阈值 / 侧 / 滞后重测本族；不要在 DCPF3M / DCPN3M / DCPF1M / DCPN30 / DTB3 / DGS3MO / 其它期限 CP、ABCP、CP 发行量（COMPOUT）、CP − OIS / SOFR、FRA-OIS、TED 之间换序列，不要改用其它短端融资压力利差（SOFR − IORB 已测）重测。
- 文件：`output/research_fed_h15_cp_spread_gate_4h*.csv`、`output/fed_h15_cp_spread_official_daily.csv`（均不入库）；脚本 `scratch/cpspread4h/{build,run,supp,supp2,new8,new8b,parity}.py`、`PRE_REGISTER.json(.sha256)`（不推送）；代码 `qtw/cp_gate.py`、`tests/test_cp_gate.py`、`data/paper-cpgate/run.sh`。
- 下一轮（短线）：待定，先查重。
