# 短线新族：OFAC SDN 加密地址制裁公告 → 8 币永续篮子（1h，持有 12–72h）

2026-11-27 ~13:10–13:25 PST，研究，不改默认；**否决**（8/8 槽位为正，但未过预注册强观察门槛）。

## 查重
`docs/STRATEGY_FORMULAS.md`、`docs/*.md` 和 `output/research_*.csv` 里都没有 OFAC / 制裁类测试。最接近的几个已测族：SEC 8-K、EDGAR S-1、MSTR 8-K、币安 / Upbit 上下架公告、DefiLlama 黑客事件、Tornado Cash 链上使用量突发、交易所状态事件。这几个和本族机制不同：本族是**美国财政部把加密地址列入 SDN 制裁名单**。SEC 执法 / 诉讼公告另有计划，本轮没有做。

## 数据（全部官方，无合成 / 回填）
- 事件：ofac.treasury.gov Recent Actions 站内全文检索 `"Digital Currency Address"`，共 80 页（2018-11-28 → 2026-11-19）。逐页统计 `has/have been added to OFAC's SDN List` 标题下的 `Digital Currency Address - TICKER` 条目。只有 n_addr_added ≥ 1 才算事件；同日多页合并。只有更新 / 移除的页（如 2025-03-21 Tornado 解除）不算事件。去重后共 74 个事件日。官方 CSV：`scratch/ofacsdn1h/ofac_crypto_actions_official.csv`。
- OFAC 页面只有日期没有时刻（通常美东 10:00–16:00 发布），所以入场放在发布日 21:00 UTC 官方 1h 开盘（same_21utc，约美东 16/17 点），或次日 13:00 UTC（next_13utc）。
- 价格：OKX d8 永续官方 1h（2022-01-29 → 2026-11-27 19:00 UTC）；OKX new8 未调参币（LINK LTC DOT TRX BCH ATOM NEAR UNI）；Gate d8 永续官方 1h（2025-09-24 起）；OKX 官方资金费。不用现货。
- 进入 OKX 区间的事件数：all 65 / big（≥ 10 个地址）23；按 train / test / post 分为 31 / 18 / 16；Gate 窗口 22。

## 公式 / 预注册（PRE_REGISTER.json sha256 bcddb380…，看 PnL 之前锁定）
- 32 格 = 集合 {all, big} × 入场 {same_21utc, next_13utc} × 方向 {short, long} × H {12, 24, 48, 72}h；同一格内不重叠。
- 单次收益 = 篮子等权 d·(O[e+H]/O[e]−1) − d·资金费 − 2×0.051%；压力费率 0.151%/边。
- 先验：all_same_21utc_short_H48（制裁 = 加密通道执法收紧 → 合规去风险 / 避险，约 2 天内消化 → 做空）。回退：big_same_21utc_short_H24。
- 强观察门槛：8 槽全 > 0、OKX 全样本 t ≥ 2、随机日期分位 OKX 与 Gate 窗口都 ≥ 95%、邻域同号，否则否决。

## 结果（真实费率，bps / 次）
| 格 | OKX d8 train/test/post | new8 train/test/post | Gate post / 窗口 | OKX 全样本 n / 均值 / t | 压力费 | 随机分位 OKX / Gate |
|---|---|---|---|---|---|---|
| **先验** all_21utc_short_H48 | +34.4 / +121.2 / +100.6 | +26.6 / +15.2 / +146.9 | +99.3 / +189.7 | 61 / +76.3 / 1.51 | +56.3 | 96.2% / 90.3% |
| 邻域 H24 | +28.6 / +91.9 / +111.5 | +28.4 / +50.0 / +132.8 | +110.7 / +146.6 | 65 / +66.6 / 1.12 | +46.6 | 97.9% / 95.3% |
| 邻域 H72 | +37.3 / +138.9 / +77.0 | −0.3 / −5.0 / +111.3 | +74.9 / +144.1 | 60 / +77.1 / 1.14 | +57.1 | 94.0% / 71.9% |
| 邻域 H12 | +5.2 / −14.4 / −2.5 | +9.8 / −6.4 / +21.5 | −2.8 / −21.8 | 65 / −2.1 / −0.08 | — | 80.5% / 21.6% |
| 邻域 next_13utc_short_H48 | −22.0 / +136.2 / +92.7 | −3.7 / +17.0 / +103.1 | +91.8 / +206.9 | 61 / +52.9 / 1.04 | — | 88.6% / 97.1% |
| 回退 big_21utc_short_H24 | +148.6 / −229.6 / −6.7 | +188.4 / −264.8 / +10.5 | −7.5 / −71.4 | 23 / +19.1 / 0.14 | — | 69.8% / 15.5% |

- 同脚本基线（每个工作日 21 UTC 做空 H48，不重叠）：OKX −19.4 bps / 次。
- 平移安慰剂（先验格，OKX 全样本）：−7 天 t 1.40，最高均值 +73.8，几乎追平真实值 +76.3。说明事件扎堆落在下跌期，主要是体制效应，不是公告本身带来的。
- 稳健性：先验 OKX 中位数 +72.9、胜率 54%；去掉最好 2 笔后 +47.9；去掉 LUNA / FTX 附近三天（2022-05-06、2022-11-08/09）后 n 59、均值 +66.4、t 1.29。post 月份 6/9（OKX 和 Gate 都是），但 2026-07 单月 −1,277 bps，11 月 +1,096 bps，波动很大。
- 8 槽全为正的共 5 格，全部做空：all_21utc_short H24 / H48，big_next_13utc_short H12 / H24 / H48。big 集合 OKX test 只有 5 次，不满足 test ≥ 8，所以真正可用的 8/8 只有先验 H48 和 H24 两格。没有一格同时满足 t ≥ 2、两边随机分位 ≥ 95%、且平移安慰剂追不平。

## 结论
否决。先验 8/8 为正、post 月份 6/9，但 t 只有 1.51（门槛 2），Gate 随机分位 90.3%（门槛 95%），−7 天平移安慰剂几乎复现同等收益（体制 / 扎堆效应），H12 邻域为负，回退格失败。无纸面 / 代码 / 默认变更。

## 勿重测
不要换 H / 入场时刻 / 方向 / 地址数门槛 / 币种标签（TRX、USDT、XBT、ETH），不要改用 OFAC 全部 SDN 公告、网络（Cyber）类公告、财政部新闻稿时刻、欧盟 / 英国 OFSI 制裁名单、Tether / Circle 链上冻结（AddedBlackList），也不要改作 4h 闸门。

## 文件
- `output/research_ofac_sdn_crypto_designation_event_1h.csv`（全部格 / 安慰剂 / 基线）
- `output/research_ofac_sdn_crypto_designation_event_1h_random_placebo.csv`
- `output/research_ofac_sdn_crypto_designation_event_1h_score.csv`
- `output/research_ofac_sdn_crypto_designation_event_1h_prior_trades.csv`
- 脚本：scratch/ofacsdn1h/（fetch.py、parse.py、prereg.py、run.py、analyze.py、diag.py）
