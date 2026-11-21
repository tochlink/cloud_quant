# 长线：官方 ERC-4337 EntryPoint UserOperation → 4h 默认书入场闸门（2026-11-20，否决）

## 机制与数据
- 只用以太坊主网官方 EntryPoint v0.6 0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789、v0.7 0x0000000071727De22E5E9d8BAf0edAc6f37da032、v0.8 0x4337084D9E255Ff0702461CF8895CE9E3b5Ff108、v0.9 0x433709009B8330FDa32311DF1C2AFA402eD8D009 的 UserOperationEvent 日志（地址取自 eth-infinitism/account-abstraction 官方 release）。
- 日序列（UTC）：n_ops = UserOperationEvent 次数；eth_fee = actualGasCost 之和（ETH）；n_pm = paymaster 非零的次数。首个官方事件 2023-04-17 14:09:35 UTC（区块 17066994），1,313 个可用日，截至 2026-11-20 完整日（n_ops=34,540，eth_fee=10.934 ETH，n_pm=21,641）。最后 7 天在两个独立 RPC 上逐日完全一致。不回补、不编造。
- 无前视：UTC 日 D 在 D+1 01:00 UTC 才可用，前向填充到 4h K 线。
- 官方日序列：output/erc4337_entrypoint_official_daily.csv（不入库）。

## 公式（在看任何收益前锁定 120 格，scratch/erc43374h/PRE_REGISTER.json）
- trend：metric > SMA(n)，n ∈ {30,90,180}；chg：n 日变化 > 0，n ∈ {30,90}；z365：(metric − SMA365)/STD365 > k，k ∈ {1,1.5,2}。
- 闸门方向：long_off / short_off / both / contra_both / cap_short_off，只拦新开仓，已有同向持仓保留。
- 先验：活动高或上升 = 风险偏好 → cap_short_off（高时不开新空）和 contra_both（高时只开多，低时只开空）。后备先验格：n_ops_trend_n90_cap_short_off。
- 验证：同脚本默认书基线（4h 永续双向、10 倍、50/150 均线、2×ATR 止损、BTC 1200 均线），OKX 与 Gate 官方永续 K 线，真实费率（永续 maker 0.02%/taker 0.051%）及压力费率 20/15.1 bps，深未见（2024-10-21 前）/ 调参前段 / 2026-03-05 后，d7_noBNB 子篮子，日历平移安慰剂（±7、±14、+180、−120、+365、−119 天）。

## 结果（output/research_erc4337_entrypoint_gate_4h.csv，441 行）
- 基线 d8：OKX 深未见 Sharpe 0.71 / 前段 1.47 / 后段 +59.90%、2.23；Gate 0.09 / 1.46 / +60.32%、2.25。
- 后备先验 n_ops_trend_n90_cap_short_off：后段只有 +23.9% / +24.7%（Sharpe 1.17 / 1.20），月份 3/6，前段 Sharpe 0.91 / 0.92，否决。
- 最好的先验格 eth_fee_trend_n90_contra_both：OKX 深未见 1.14、前段 1.50、后段 +61.10%（2.28）；Gate 0.53 / 1.43（输基线）/ +61.94%（2.30）。后段优势很薄（+1.2 / +1.6 个百分点，Sharpe +0.04 / +0.05），后段月份只有 3/5（OKX）和 4/4（Gate），不到 ≥6/9 的标准。
- 安慰剂：平移 ±7 天的深未见 Sharpe 1.18 / 1.29（OKX）、0.48 / 0.58（Gate），与真实格相当甚至更高，说明深未见的提升不是这条序列特有的。
- 邻域：n30 和 n180 的后段都输基线（n180 月份 1/7、2/6），不稳。
- 其他 2/3 胜的格都是非先验的 short_off 一类，后段月份只有 2–4 个，不采纳。
- 结论：否决。默认和模拟盘不变。

## 勿重测
不要用改 n、k、侧、序列（n_ops / eth_fee / n_pm）、按版本拆分、只看成功次数、净费用、更早起点或别的 AA 合约的方式重测本族，也不要改成 1h 冲击来绕过。

## 脚本
scratch/erc43374h/{probe,fetch,run,record}.py（研究脚本未推送）。docs/STRATEGY_FORMULAS.md 已超过 GitHub 连接器 1MB 写入上限，所以本段写在这个 sidecar 里。
