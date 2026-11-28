# 短线新族：OKX 官方 ETH/BTC 1h 相对收益冲击 → 8 币永续篮子（2026-11-27 ~23:50 PST，研究，不改默认；否决）

## 查重与换题
- 原计划：以太坊主网官方合约部署数 1h 突发。检索 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,401 个）、记忆中 contract deployment / contract creation / deploy / new contracts / new pools / token launch / gas / tx count / active addresses / mempool：
  - 同一机制类（以太坊链上活动计数 1h 突发）已否决：`eth_gas_fullness_burst_event_1h`（满块率 / gasUsed）、`univ2_paircreated_burst_event_1h`（新池）、`eth_onchain_demand_gate_4h`（gas / 燃烧 / 交易笔数）、`mempool_congestion_burst_event_1h`；
  - 而且诚实的官方序列需要逐块回执或 trace（约 1,300 万个区块），公共 RPC 一轮做不完，不能用第三方统计补。
  - 因此换题，不测合约部署。
- 新题：ETH 相对 BTC 的 1h 相对收益冲击。此前只测过 4h 的币对 BTC 比价趋势闸门、比价均值回归配对、比价趋势市场中性 sleeve（都否决），没有 1h 比价冲击事件研究。

## 数据
- OKX 官方 USDT 永续 1h K 线 ETH-USDT-SWAP / BTC-USDT-SWAP，2022-01-29 07:00 → 2026-11-27 19:00 UTC，42,325 根完整小时，缺口 0（官方小时序列：`scratch/ethdeploy1h/ethbtc_rel_okx_official_1h.csv`）。
- 回测账本：OKX d8（8 币）、OKX new8（未调参 8 币）、Gate d8（Gate 官方 1h 永续，2025-09-24 起）；资金费用官方历史；Gate 账本也用 OKX 信号。

## 公式
- `rel_t = ln(C_ETH,t / C_ETH,t−1) − ln(C_BTC,t / C_BTC,t−1)`（已收盘小时）。
- z：L=1 时 `(x−μ)/σ`；L>1 时 `(Σ_L x − L·μ)/(σ·√L)`；μ / σ 是截至 t−1 的 168h 滚动值（最少 84 根）。
- up：z ≥ k；down：z ≤ −k；twosided：|z| ≥ k。mom 顺着 ETH 相对强弱方向做篮子（up 做多），contra 反向。下一根 1h 开盘入场，持有 H 小时，不重叠。
- 费用：吃单 2×5.1 bps（真实费）+ 官方资金费；压力费 2×15.1 bps。

## 预注册（`scratch/ethdeploy1h/PRE_REGISTER.json`，任何 PnL 前于 23:47 PST 锁定，sha256 `0a19bbc585e7aa72be731dfa13366339e9a1bdd2d1e0d1d59c6f9b4a5a90c5c1`）
- L {1,4,8} × k {2.5,3,4} × side {up,down,twosided} × mode {mom,contra} × H {24,48} = 108 格。
- 先验（经济逻辑：ETH 突然跑赢 BTC = 风险偏好转向高 beta → 做多篮子）：`rel_L4_k3_up_mom_H48`；回退：`rel_L1_k3_up_mom_H24`。
- 评分沿用近期 1h 事件脚本：8 个切片（OKX d8 train/test/post、new8 train/test/post、Gate d8 post/gate_window）；usable 8/8 需要全部为正，且 OKX d8 的事件数 train ≥ 10、test ≥ 8、post ≥ 8。
- 安慰剂：±720h 平移；先验格另做 500 次随机打乱。

## 结果（真实费，每笔净 bps；`output/research_ethbtc_relative_shock_event_1h.csv`，3,504 行）
- 108 格中 **全正 8/8 为 0 个，usable 为 0 个**；最多 7/8（3 格）。
- **先验 `rel_L4_k3_up_mom_H48` 只有 4/8**：OKX d8 train +169.0（n=78，t 3.26）/ test +77.8（n=41，t 0.83）/ **post −38.3（n=28，t −0.40，中位 −38.4）**；new8 post −5.7；Gate d8 post −35.5、gate_window −6.3。压力费 OKX post −58.3。
  - 安慰剂：−720h 平移 post 为 +79.7，比真实信号好；随机打乱 500 次，post 分位 40（打乱中位 −26.4）；train 分位 100。说明 2024 年前的效应确实存在，但 2026-03 后消失。
- **回退 `rel_L1_k3_up_mom_H24` 只有 3/8**：OKX d8 train +29.5 / test +29.2 / post −60.4（n=40）；new8 post −71.9；Gate post −59.4。
- 整个 up_mom 子族 18 格在 OKX d8 post 有 17 格为负（唯一为正的 L8 k3 H48 是 +9.7，n=14，t 0.06，gate_window −59.8）。前段有效、后段一致翻负，属于体制失效。
- 7/8 非先验格都不达标：`rel_L8_k2.5_down_mom_H48` post +37.3（t 0.54），train t 0.21，+720h 平移 post 也有 +37.4；`rel_L8_k3_up_mom_H48` post +9.7（t 0.06）；`rel_L4_k2.5_twosided_mom_H48` post +1.8。
- 同脚本基线（不看信号，每 H+1 小时开一次）：OKX d8 做多 H48 post −31.4、做空 H48 post +11.0。冲击格没有稳定地跑赢基线。

## 结论
- **否决**：不实现、不进观察名单、不改默认、不动纸面盘，只更新文档。
- 本族勿重测：不要改 L / k / H / 方向 / up↔down↔twosided，不要改用 SOL/BTC 或其他山寨对 BTC 的 1h 比价冲击、Gate 比价，也不要改用成交量加权比价或其他 z 窗口。
- 合约部署数 1h 突发不测：与已否决的以太坊链上活动计数族（满块率 / 新池 / 交易笔数）属同一机制，公共 RPC 也拿不到完整官方历史。
- 不需要新的实时记录器：信号来自本机已在更新的 OKX 官方 1h K 线。

## 下一轮（长线）
- JVCEA（日本暗号資産取引業協会）官方月度统计：日本加密现货 / 保证金交易量、账户数、客户存款 → 4h 默认书入场闸门（日本散户杠杆参与度）。
- 查重：在 docs / output 中检索 JVCEA / 暗号資産，0 命中。这不是已否决的 Korea premium / Upbit、Coinbase 美国成交份额、交易所成交额、CFTC 等族。
- 先确认官方 PDF 历史有多深、发布时滞是多少；不编造、不回补。

## 文件
- CSV（不入库）：`output/research_ethbtc_relative_shock_event_1h.csv`
- 脚本：`scratch/ethdeploy1h/{run,analyze,shuffle}.py`；`analyze.log`、`analyze_wide.csv`
