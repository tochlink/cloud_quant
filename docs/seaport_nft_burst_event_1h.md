<!-- Sidecar for docs/STRATEGY_FORMULAS.md (main file exceeds the GitHub connector 1MB push cap). -->

## 短线新族：OpenSea Seaport 官方链上 NFT 成交 1h 突发 → 8 币永续篮子顺势 / 逆势（1h，持有 12–48h，2026-11-22 ~10:00 PST，研究，不改默认；否决）

- 查重：本轮候选 (a) USDT Issue/Redeem（= 已否决「稳定币供给冲击 1h」2026-11-14 及 4h 增速闸门）、(b) 以太坊基础费 / gas 尖峰（= 已否决 blob / 基础费 1h 冲击、gas 满块率 1h 突发）、(c) Sky/Maker PSM 流量（= 已否决 `research_maker_psm_flow_shock_event_1h.csv`）、(d) Lido 提款队列（= 已否决 `research_lido_wq_burst_event_1h.csv`）全部已测，按规则不跑。改测 Seaport NFT 成交**小时级突发事件**：docs / 侧文档 / `output/research_*.csv` 中 NFT 只做过**长线 4h 日度成交额入场闸门**（`research_seaport_nft_volume_gate_4h.csv`，否决，日度体制过滤默认书），从未做过 1h 事件交易（不同周期、不同用法）。也不是 Uniswap V2 PairCreated、ENS 注册、WETH9、Uniswap v3 兑换、CoW 结算、闪电贷等 1h 突发。
- 机制（先验）：某小时 NFT 花费的 ETH 突增 = 散户 / ETH 富裕钱包把风险资金投向投机品（risk-on 财富效应）→ 随后一天加密篮子上漂 → 做多。
- 预注册：`scratch/seaportnft1h/PRE_REGISTER.json`（2026-11-22 ~09:58 PST，任何 PnL 之前锁定，108 格，sha256 `d669797aa5892896…`；副本 `output/research_seaport_nft_burst_event_1h_prereg.csv`）。
- 数据（只用官方以太坊主网日志，不用聚合器、不回补）：Seaport 1.0–1.6 官方部署地址的 `OrderFulfilled` 日志，区块 14,900,000 → 26,472,000（复用长线轮次的逐区块检查点，并用同一代码把 26,460,001 → 26,472,000 补到链头），共 30,386,702 个事件、29,980,433 笔 ETH / WETH 计价 NFT 成交（一侧 NFT itemType 2–5，另一侧原生 ETH 或 WETH；价格 = 非 NFT 侧 ETH+WETH）。按官方区块时间汇总成 UTC 小时：38,968 根完整小时 2022-06-13 00:00 → 2026-11-22 15:00 UTC，缺口 0，零成交小时 23 根为真实 0。序列 `scratch/seaportnft1h/seaport_nft_official_1h.csv`（不入库）。
- 交易数据：OKX 官方 1h USDT 永续 d8（BTC ETH BNB SOL XRP ADA DOGE AVAX）+ 未调参 new8（LINK LTC DOT TRX BCH ATOM NEAR UNI）+ OKX 官方深历史资金费；Gate 官方 1h 永续 d8（2025-09-24 起）+ Gate 官方资金费。不用现货。
- 公式：x = log1p(小时成交笔数)（sales）或 log1p(小时 ETH 成交额)（ethvol）；z_t = (x_t − median(x_{t−L..t−1})) / (1.4826·MAD)，需满 L 窗且 MAD>0；z ≥ k 触发；follow = 做多 8 币等权篮子，contra = 做空；信号小时收盘后下一根 1h 开盘吃单入场，持有 H 根后开盘离场，不重叠（冷却 = H）。
- 网格：series {sales, ethvol} × L {72, 168, 336} h × k {2, 3, 4} × H {12, 24, 48} × side {follow, contra} = 108 格。先验 `ethvol_L168_k3_follow_H24`，回退 `sales_L168_k3_follow_H24`。
- 成本：吃单 0.051% / 边 + 官方资金费；压力 0.151% / 边、0.20% / 边。切分：train（深历史未见）2022-06-13 → 2024-10-21；test → 2026-03-05；post → 末；Gate 只有 post / gate_window（2025-09-28 起）。安慰剂：信号平移 ±168h、±720h。
- 结果（`output/research_seaport_nft_burst_event_1h.csv`，7,344 行；每笔净 bps，真实费）：
  - 先验 ethvol_L168_k3_follow_H24：**1/8**。OKX d8 train −9.3（n 127，t −0.37）/ test −11.0（n 84）/ post −22.7（n 35，t −0.51，post 逐月 3/9 为正）；Gate post −21.8、gate_window −30.0；new8 train +9.5 / test −9.9 / post −9.8。安慰剂 +168h post +62.9 > 真实。邻域（L×k、H）几乎全负。
  - 回退 sales_L168_k3_follow_H24：4/8。train −23.2、test −36.0 为负；post +46.5（n 40，t 0.82）/ Gate +47.3，逐月 4/8；−720h 安慰剂 post +47.0 ≈ 真实。
  - 全网格 8/8 仅 2 格且都是非先验：sales_L336_k4_follow_H24（OKX train +38.6 / test +20.5 / post +98.2，t 全部 < 1，post n 13；−720h 安慰剂 post +194 > 真实，test 仅 n 41）；ethvol_L72_k3_contra_H24（各段 +1～+25 bps，t ≤ 1，post 中位 −39.6）。
  - 基线（每小时都做多 H24）：OKX post −20.5、Gate post −19.9 bps。
- 结论：**否决**，不实现、不进观察名单、不改默认、不加纸面子账本、无代码改动，仅文档。NFT 小时成交突发对 8 币永续篮子 12–48h 收益没有稳定、超过费用与安慰剂的增量；先验 train / test / post 三段与两所都为负。未起实时记录器（无前向价值）。
- **勿重测**：不要通过改 L / k / H / 方向、换序列（笔数 / ETH 额 / 均价 / 物品数 / 挂单 vs 出价拆分 / 去日内季节）、换 Seaport 版本、或加入 Blur / LooksRare / X2Y2 / Magic Eden / 其他链 NFT 市场、或改成 4h / 日度来重测本族。
- 文件：`output/research_seaport_nft_burst_event_1h.csv`、`output/research_seaport_nft_burst_event_1h_prereg.csv`（不入库）；脚本 `scratch/seaportnft1h/{prereg,fetch,build,run,analyze,baseline}.py`（研究脚本未推送）。
- 下一轮（长线）：Baker Hughes 官方北美钻机数趋势 / 同比 → 4h 默认书入场闸门（先查重）。
