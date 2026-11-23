# 短线：Aave 安全模块（stkAAVE / stkABPT）Cooldown 冷却申请突发 1h 事件 → 8 永续篮子（2026-11-22 ~23:30–23:55 PST，否决）

## 想法
Aave 安全模块质押者（stkAAVE、stkABPT、stkABPTv2）要取回质押必须先调用 `cooldown()`，再等约 20 天才能 `redeem`。某小时 Cooldown 申请数相对过去 L 小时异常放大 = 最懂 DeFi 风险的内部人集中「准备撤离 / 要流动性」→ 先验 risk-off，做空 8 永续篮子。按突发触发、不重叠持有 24/48h，交易频率低，不是费用受限的 1h 吃单族。

去重（2026-11-22 23:30 PST）：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`/workspace/scratch/*` 中 stkAAVE / Safety Module / 安全模块 / cooldown 质押 0 条测试。已否决且不同的：Aave V3 清算 1h、Aave V3 借还流量 1h、Aave 借款年化 4h、DAO 治理提案 1h、EigenLayer / Lido 提款队列 1h、信标自愿退出 1h、闪电贷 1h。

## 数据（仅官方）
- 官方以太坊主网 `eth_getLogs`（主 RPC gateway.tenderly.co 公共节点，地址 + topic0 过滤），不用 Etherscan / Dune / 子图。
- 合约：stkAAVE `0x4da27a545c0c5B758a6BA100e3a049001de870f5`、stkABPT `0xa1116930326D21fB917d5A27F1E9943A9595fb47`、stkABPTv2 `0x9eDA81C21C273a82BE9Bbc19B6A6182212068101`。
- 事件（两代签名都收）：`Cooldown(address)` / `Cooldown(address,uint256)`；`Redeem(address,address,uint256)` / `Redeem(address,address,uint256,uint256)`；`Staked(address,address,uint256)` / `Staked(address,address,uint256,uint256)`。
- 合计：cooldown 61,232（stkAAVE 58,401 / stkABPT 1,724 / v2 1,107）、redeem 32,870、staked 119,621。
- 校验：12 个随机 9,000 块窗口 + 最新 ~13,000 块在独立 RPC（rpc.mevblocker.io / eth.api.pocket.network）上条数 13/13 完全一致。
- 1h 序列 `output/aave_safety_module_official_1h.csv`：53,818 个完整 UTC 小时，2020-10-02 21:00 → 2026-11-23 06:00 UTC，0 缺口；零值为真零。小时 t 的值在 t 收盘后才用，t+1 开盘入场。
- 价格：官方 OKX 1h 永续（2022-01-29 → 2026-11-23 06:00 UTC，本轮已追加官方新 K 线 / 资金费，默认 8 币 + 未调参 new8），官方 Gate 1h 永续（2025-09-24 起），含官方资金费。

## 公式与网格（PRE_REGISTER.json，sha256 2a0138b4c351…96576，23:35 PST 在任何 PnL 之前锁定）
- x_t = log1p(小时事件数)；z_t = (x_t − 过去 L 小时均值) / 过去 L 小时标准差（均不含 t，最少 L/2 个样本）；z_t ≥ k → t+1 开盘入场，持有 H 小时，不重叠。
- 序列 ∈ {log_n_cd（冷却申请）, log_n_redeem（取回）, log_n_staked（新质押）}；L ∈ {168, 720}；k ∈ {2, 3, 4}；方向 多/空；H ∈ {24, 48}；共 72 格。
- 先验格 `log_n_cd_L720_k3_short_H48`；回退格 `log_n_cd_L168_k3_short_H24`。
- 费用：吃单 5.1 bps/边（压力 15.1 bps/边）+ 官方资金费。分段：train（深度未见）OKX 起 → 2024-10-21，test → 2026-03-05，post 之后；Gate 窗口 2025-09-28 起。8 项检查 = OKX d8 train/test/post、new8 train/test/post、Gate post、Gate 窗口 均值 > 0。安慰剂：z 平移 ±720h；每段 200 次同笔数随机入场时刻。

## 结果（真实费用，每笔均值 bps）
- 分布：72 格中 8/8 两格、7/8 两格；0~3/8 共 44 格。
- **先验 `log_n_cd_L720_k3_short_H48`：2/8。** OKX d8 train −79.3（n=37，t −1.34）、test −81.4（n=22）、post −90.4（n=13）；new8 post −91.8；Gate post −92.4（Gate 窗口 +13.8）；post 月份 OKX 2/9、Gate 2/9；随机安慰剂分位 train 25 / test 28.5 / post 17.5；压力费 post −110.4。
- **回退 `log_n_cd_L168_k3_short_H24`：0/8。** train −27.0、test −11.0、post −127.9（n=18，t −2.42）；new8 post −200.4；Gate post −129.5；月份 1/9、1/9；随机安慰剂 post 分位 0。
- 先验邻域（log_n_cd 做空 12 格）post 全部为负（−8.3 ~ −127.9）。冷却突发后做空方向整体错误。
- 唯二 usable 8/8 均为非先验「取回突发 → 做多」：
  - `log_n_redeem_L720_k3_long_H48`：OKX d8 train +23.2（n=96，t 0.49，中位 +102.9）、test +68.2（n=39，t 0.83）、post +59.0（n=30，t 0.68）；new8 train +41.4 / test +18.2 / post +75.7；Gate post +60.4、Gate 窗口 +58.1。post 月份仅 3/9（两所），主要来自 2026-08 单月（+2,406 bps 合计）。随机安慰剂分位 train 73 / test 81 / post 91.5（同期随机做多 post 均值 −26.6）；±720h 平移 post +28.7 / −58.3。压力费：train +3.2、test +48.2、post +39.0、new8 test −1.8。
  - `log_n_redeem_L720_k3_long_H24`：train +21.0、test +35.1、post +19.7（n=37，t 0.34）；Gate post +20.7、Gate 窗口 +6.4；月份 4/9；压力费 post −0.3、Gate 窗口 −13.6。
  - 邻域不稳：同序列 L168 k3 H48 post −45.1、L720 k2 H48 −12.7、L720 k4 H24 −21.6、L168 k4 −79 ~ −90。
- 其余：`log_n_cd_L168_k3_long_H24`（与先验方向相反）6/8，post +107.5（n=18，t 2.0，月份 7/9），但 test −9.4、new8 test −6.3，±720h 平移 −720 为 +62.9，非预注册方向，不升级。

## 结论
**否决**。先验（冷却申请突发 → 做空）与回退全部失败，邻域 post 全负。仅有的两个 8/8 是非先验「取回突发 → 做多」：t 全部 < 1、post 月份 3/9 和 4/9（< 6/9）、收益集中于单月、邻域不稳、压力费下 H24 已为零，不进观察名单、不加纸面。默认、纸面、应用代码均不变。

勿重测：不要通过换 L / k / H / 方向、换 cooldown / redeem / staked 或其净额 / 金额 / 唯一地址数、只用 stkAAVE 或只用 stkABPT、加入 stkGHO / Umbrella（2025 新安全模块）/ 其他协议质押冷却（Curve veCRV 解锁、Lido 提款已否决、EigenLayer 已否决），或改成 4h 日度闸门 / 单币 AAVE 反应来重测同一「DeFi 安全模块冷却 / 取回 1h 事件」机制。

结果 CSV：`output/research_aave_safety_module_cooldown_event_1h.csv`（2,520 行，含真实 / 压力费、±720h 平移、随机 200 次安慰剂）；官方 1h 序列 `output/aave_safety_module_official_1h.csv`；脚本 `scratch/stkaavecd1h/{fetch.py,run.py,analyze.py}`（未推送）。

下一轮（长线）：德国 ifo 商业景气 / ZEW 经济景气（官方月度，非美宏观）→ 4h 默认书入场闸门；先查重并确认官方历史可免费下载。
