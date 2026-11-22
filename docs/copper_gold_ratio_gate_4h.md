# 铜价趋势 / 铜金比（增长 vs 恐慌）4h 入场闸门（否决）

## 长线新族：官方 World Bank Pink Sheet 铜 / 金月均价 → 4h 默认书入场闸门（2026-11-21 ~15:55–16:15 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、`output/research_*.csv`（1,120 个）、scratch 与记忆检索 copper / 铜 / PCOPP / HG / copper-to-gold / 铜金比 均无测试条目。已测黄金族（`gold_btc_relative_gate`、`gold_perp_diversifier`、`xaut_gold_shock_event_1h`）用的是金价相对 BTC / 金永续作为分散资产 / XAUT 1h 冲击，从未用铜，也从未用铜金比作为宏观增长-恐慌体制。
- 机制（看 PnL 前锁定的唯一先验）：铜金比 = 全球增长 vs 避险。铜金比 6 个月下跌（增长转恐慌）→ **拦新开多** `cuau_dn_n6_long_off`；回退：铜单独 6 个月下跌 → 拦新开多 `cu_dn_n6_long_off`。只拦新开仓，持仓、止损、退出不变。
- 数据（仅官方，不编造、不补缺）：World Bank Pink Sheet `CMO-Historical-Data-Monthly.xlsx`（2026-11-03 更新）Copper（LME，$/mt）与 Gold（$/troy oz）月均价，1990M01 → 2026M10 共 442 个月、0 缺口。铜与 IMF PCOPPUSDM（FRED）核对 105 个月：中位相对差 0.004%，最大 0.48%。无免费官方日频铜价（FRED 只有 IMF 月度；LME / COMEX 不免费），故用月频。存 `output/copper_gold_official_monthly.csv`（sha256 865e7842…551f，不入库）。只用当前版本（月均价极少修订）。
- 公式（月 M 均值从 M+1 月 10 日 00:00 UTC 起用，Pink Sheet 约 M+1 第 2 个工作日发布，保守；ffill 到 4h）：
  - `cuau = copper / gold`；`cu = copper`；
  - 恐慌 flag = 1 当且仅当 `log(x_M / x_{M−n}) < 0`，n ∈ {1, 3, 6, 12} 月；
  - 侧：long_off（恐慌时不开新多）/ short_off（非恐慌时不开新空）/ both / contra_both（反向）。
- 格子：2 序列 × 4 回看 × 4 侧 = **32 格** + 同脚本基线（= 生产回测默认参数）；`scratch/cuau4h/PRE_REGISTER.csv` 在任何 PnL 前锁定（sha256 f01e4456…5bd3）。harness 同 btcval4h：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（永续 maker 2 / taker 5.1 bps），压力 spot 20 / perp 15.1；官方资金费；安慰剂平移 ±7/±14/+180/−120/+365/−119 天（最佳格另加 ±30 天）；回看邻域 n ∈ {2,4,5,8,9,10,18,24}；未调参 new8。
- 占用率（恐慌月份比例 deep / tune / post）：cuau n6 71% / 100% / 22%；cu n6 33% / 25% / 0%。
- 结果（`output/research_copper_gold_ratio_gate_4h.csv` 207 行；`_new8.csv`；`_plc_best.csv`）：
  - 基线：post OKX d8 +59.90% / Sharpe 2.23，Gate d8 +60.32% / 2.25；deep OKX +35.14% / 0.71、Gate −3.63% / 0.09；tune OKX +85.08% / 1.47。
  - 先验 `cuau_dn_n6_long_off`：**0/9**——deep OKX +3.26% / 0.21、Gate −12.04% / −0.08；tune OKX +24.07%（基线 +85.08%）；post 与基线完全相同（月份 0/0，post 恐慌月里没有新开多被拦）。安慰剂全部 0/9 或 3/9。邻域 n2/4/5/8/9/10/18/24 最多 3/9，n24 post −20 pp。先验不成立。
  - 回退 `cu_dn_n6_long_off`：**3/9**，deep 全输（OKX −9.18%、Gate −21.59%），只 tune 赢，post 不触发（0/0）。
  - 最佳 post 格 `cu_dn_n1_contra_both`（非经济侧，铜上月涨拦新多 / 跌拦新空）：6/9，post OKX +65.86% / 2.58、Gate +66.31% / 2.60，但月份只 4/3（两所），tune 崩塌（OKX +13.28% vs +85.08%）；邻域 n2..n24 全部 ≤3/9 且 post −43~−54 pp；**时间平移安慰剂 −7d / −14d / −30d 同为 6/9、post +63~64%** → 不是铜信息；new8 pre −2.1% vs 基线 +53.4%（post 虽 +15.6% vs +3.3%，月份 6/1、8/1，但 pre 崩塌）。
  - 32 格唯一 8/9 `cuau_dn_n6_contra_both` post 少 −12 pp（+47.86% vs +59.90%），月份 4/3。
  - 压力费不改变结论。
- 结论：**否决**，不实现、不进观察名单、不加模拟盘、不改默认，无代码改动。月频铜价 / 铜金比对默认书新开仓没有稳定增量：经济先验 deep 与 tune 大幅输给基线、post 空转；唯一 post 更好的格是非经济侧 1 个月翻转，被 −7/−14/−30 天平移安慰剂追平、邻域断裂、tune 崩塌。勿以同一机制换回看 / 侧 / 阈值、换铜单独 / 铜金比 / 铜油比 / 铜银比 / 工业金属指数（Pink Sheet base metals index、LMEX）/ IMF PCOPPUSDM / COMEX HG / OKX XCU 永续价格趋势、或换水平 / z 分数 / 均线穿越形式再测。
- 文件：`scratch/cuau4h/{build,prereg,run,new8,plc_best,plog}.py`，`run.log`，`new8.log`，`plc_best.log`，`PRE_REGISTER.csv`（研究脚本未推送）。
- 下一轮（短线）：官方 Solana 主网区块优先费（Compute-Budget priority fee / 每槽费用，官方 RPC getBlock 回溯）1h 冲击 → 8 币永续篮子事件（查重：ETH gas / blob base fee 已否决，Solana 优先费未测；VIX 结算日 VRO 已判定与已否决到期日历同族，不做）；须先确认官方历史可回溯 ≥2 年，否则换题。
