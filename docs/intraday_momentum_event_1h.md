# 日内时序动量 1h 事件 → 8 币永续篮子（研究，否决）

本文件是 `docs/STRATEGY_FORMULAS.md` 同名小节的独立副本（sidecar）。
## 短线新族：日内时序动量（固定 UTC 锚点起 F 小时篮子收益 → 顺势 / 逆势持有到本周期结束）→ 8 币永续篮子 1h 事件（2026-11-21 ~09:15 PST，研究，不改默认；否决）

- 选题与查重：上节计划的 GMX Arbitrum 链上清算突发，判定与已否决的「被动去杠杆突发」同机制（Aave V3 LiquidationCall 1h 冲击、OKX / Gate 爆仓 / OI / 主动买卖失衡等微结构 1h 事件；GMX 清算只是换了一个场所的永续强平），**不做**。L8934 计划过的「跨币 1h 收益横截面离散度」与已否决的单币特质冲击 1h（`research_idiosyncratic_shock_1h_*`）及两两相关尖峰（`research_pairwise_corr_spike_*`）重叠，也不做。改测日内时序动量：`rg -i 'opening range|ORB|开盘区间|日内.{0,6}动量|日内时序|intraday momentum' docs/*.md` 只命中 ORB 作 4h 默认书入场闸门（`research_utc_opening_range_gate_long_history.csv`）、无条件固定时段持仓（`research_intraday_session_seasonality_1h.csv`）、前日 / 周 / 月高低点突破与时段分解 4h 闸门，没有「先看锚点后 F 小时收益、再顺 / 逆势持有到周期末」的独立短线事件测试。不是重复。
- 机制（先验）：Gao–Han–Li–Zhou（2018）日内动量；加密文献（Wen 等 2022）称早段走势会在剩余时段延续（消化消息、迟到资金、趋势单 / 对冲流）。锚点 00 UTC（日线开盘）、08 UTC（欧洲开盘）、13 UTC（美股开盘前后）。
- 数据：官方 OKX USDT 永续 1h（`scratch/deep1h`，2022-01-29 → 2026-11-20 23:00 UTC，42,161 根，连续无缺口；BNB 2022-12 起）、官方 Gate USDT 永续 1h（2025-09-24 起）、未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI，OKX 官方 1h）；资金费用 OKX 官方深历史与 Gate 官方资金费，逐根结算计入。无模拟、无现货冒充永续、无插值。
- 公式（`scratch/intramom1h/PRE_REGISTER.json` sha256 `86a5a8f0…edaa1`，看任何 PnL 前锁定，结果后未改）：
  - 第 d 天、锚点 a、形成期 F：`R = mean_i[ln C_i(a+F−1 时根) − ln O_i(a 时根)]`（≥ 7 币有值）；`σ` = 同 (a,F) 过去 60 天 R 的标准差（≥ 30 天，不含当天）；`z = R/σ`。`|z| ≥ k` 触发；顺势方向 sign(R)，逆势反之。a+F−1 根收盘确认，**下一根开盘**等权 8 币吃单入场，持有 H 根后开盘离场；每格每天至多一笔。
  - 网格：a ∈ {0, 8, 13} × F ∈ {1, 2, 4, 8} × k ∈ {0, 1, 2} × 顺 / 逆 × H ∈ {rest = 24−F, 4} = **144 格**。先验 `a0_F4_k1_follow_Hrest`，回退 `a13_F2_k1_follow_Hrest`（美股开盘动量）。
  - 费用：真实吃单 5.1 bps × 2；压力 15.1 bps × 2；另报吃单入场 + maker 2 bps 离场（不参与选格）。
  - 评分 8 槽：OKX d8 深未见（2022-02-15 → 2024-10-21）/ test（→ 2026-03-05）/ post，OKX new8 三段，Gate d8 post 与 gate_window（2025-09-28 起）；可用 = 8/8 为正且 OKX 每段 ≥ 30 笔。强观察另需 post t ≥ 2、两所压力费 post > 0、post 月度两所 ≥ 6/9、邻域、安慰剂（随机方向 200 次、形成期平移 24h / ±168h）。
- 结果（`output/research_intraday_momentum_event_1h.csv`，8,640 行；`_placebo_months.csv`）：
  - **144 格没有一格 8/8**（7/8 四格、6/8 九格）。顺势按锚点平均每笔约 −1.5 ~ −3 bps（毛收益约等于手续费），逆势平均 −15 ~ −19 bps。
  - **先验 a0_F4_k1_follow_Hrest 6/8**：OKX 深未见 +11.1 bps（214 笔，t 0.42，中位 −2.2）、test **−16.5**、post +16.6（61 笔，t 0.51）；new8 post −3.0；Gate post +17.2；压力费 post 两所为负（−3.4 / −2.8）；post 月度 5/9；随机方向安慰剂 p ≈ 0.18；+168h 平移 post +64.8 反而更好。否决。
  - **回退 a13_F2_k1_follow_Hrest 6/8**：OKX 深未见 +29.6 bps（233 笔，t 1.10）、test **−22.0**（133 笔）、post +43.6（66 笔，t 1.48，月度 7/9）；Gate post +47.1（t 1.65，7/9）；new8 test **−20.6**、post +19.3；压力费 post +23.6 / +27.1；随机方向 p 0.03 / 0.015，平移 24h / ±168h 都更差。但 test 段两套币池都亏，post t < 2，邻域断裂（F2 k2 post −4.5、F4 k1 post −5.1、F1 k0 / F2 k0 / F4 k0 全负）→ 只是 2026 年一段的好运，达不到预注册强观察 / 弱观察线。
  - 7/8 的 a8_F4_k2 / a13_F4_k2 每格只有 16–22 笔 post、new8 test 一正一负，t < 1，不采信。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动，纸面盘与 shadow 均不变。没有新官方序列，不需要记录器。勿以同一机制换锚点小时、F、k、H、顺逆、逐币代替篮子、或加成交量 / 波动过滤再测。
- 文件：`output/research_intraday_momentum_event_1h.csv`、`output/research_intraday_momentum_event_1h_placebo_months.csv`（均不入库）；sidecar `docs/intraday_momentum_event_1h.md`；脚本 `scratch/intramom1h/{run,analyze,supp,plog}.py`（未推送）。
- 下一轮（长线）：CME 官方比特币期货（BTC 月度合约）年化基差 = 近月结算价 / CME CF BRR − 1（按剩余天数年化）的体制 → 4h 默认书入场闸门（只拦新开仓）。数据只用 CME 官方结算价与 `output/cme_cf_brr_official_daily.csv`；先查重 basisgate（永续基差）、CFTC TFF、CME 到期事件；若 CME 官方免费历史不够跨 2026-03-05 切分，则换族。
