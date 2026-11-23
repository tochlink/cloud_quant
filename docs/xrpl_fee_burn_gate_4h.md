# XRPL 官方账本 XRP 手续费销毁量 → 4h 默认书入场闸门（否决；不改默认、不入纸面）

## 长线新族：XRP Ledger 每日手续费销毁（total_coins 日差）作为 4h 默认书入场闸门（2026-11-22 ~23:10–00:10 PST，研究，不改默认；否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*`、`scratch/*` 中 XRPL / Ripple / XRP 手续费销毁 / total_coins 均 0 条（ETH 的 EIP-1559 burn 是另一条链、另一机制）。
- 机制（看 PnL 前锁定）：XRP 只能通过交易手续费销毁，日销毁量 = 链上活跃度 / 垃圾交易压力代理；偏高 = 网络忙 = risk-on → flag=1 拦新空（cap_short_off）；contra_both 同时在 flag=0 时拦新多。只拦新开仓，已有持仓、止损、离场不变。默认 4h 书（#1 双均线 50/150，8 个永续）。
- 数据（只用官方、不编造、不回补）：XRP Ledger 公共全历史 rippled JSON-RPC（xrplcluster.com）`ledger` 头，取每个 UTC 零点后第一个账本的 `total_coins`（二分/割线定位，9 次请求/天）。日销毁 = total_coins(D 00:00) − total_coins(D+1 00:00)。2020-01-01 → 2026-11-20 共 2,517 天，0 日历缺口，0 负值，每天 20,802–23,595 个账本；账本头不可变，无修订。原始 `scratch/xrplburn4h/midnight_ledgers.csv`，日度 `output/xrpl_fee_burn_official_daily.csv`。
- 滞后：日 D 值于 D+1 01:00 UTC 起使用，前向填充到 4h。
- 公式（`scratch/xrplburn4h/PRE_REGISTER.json` 于 2026-11-22 23:32 PST 在看任何 PnL 前锁定，sha256 `cb1ed166c85212ee71c637ecee87d7ccab7360e6180f52834714c445c98b7f64`；120 格）：
  - 序列：`b7 = log1p(近 7 天销毁)`、`b28 = log1p(近 28 天销毁)`、`g365 = log(28 天销毁 / 365 天前的 28 天销毁)`。
  - 形式：`chgN` s−s(N 天前)>0，N 7/28/91；`trendN` s>SMA(N)，N 28/91/182；`z365gtK` K 0.5/1。侧：long_off / short_off / both / contra_both / cap_short_off。
  - 锁定先验：`b28_trend91_cap_short_off`（兼安慰剂锚）；回退：`b28_chg28_cap_short_off`。
- 验证：与 wallet-users / MoF / ECB 闸门同一框架（OKX d8 2023-02→、Gate d8 2022-07→、OKX d7_noBNB 2022-04→，官方永续 + 现货 4h，官方资金费；真实费率 maker 2 / taker 5.1 bps，压力 15.1 / 20 bps；深未见 →2024-10-21，调参段 →2026-03-05，post →2026-11-14；平移安慰剂；邻域；new8 未调参）。
- 结果（`output/research_xrpl_fee_burn_gate_4h.csv` 441 行；收益 % / Sharpe，真实费率）：

| 账本 | 格 | 深未见 | 调参段 | post | post 月 好/差 |
|---|---|---|---|---|---|
| OKX d8 | 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | — |
| OKX d8 | 先验 b28_trend91_cap_short_off | +18.29 / 0.49 | +102.80 / 1.64 | +34.03 / 1.60 | 2/3 |
| OKX d8 | 最佳 9/9 b7_z365gt0.5_long_off | +47.77 / 0.89 | +92.26 / 1.55 | +60.96 / 2.27 | 1/2 |
| OKX d8 | 8/9 b28_trend28_short_off | +25.78 / 0.61 | +94.74 / 1.60 | +72.27 / 2.65 | 4/4 |
| Gate d8 | 基线 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / 2.25 | — |
| Gate d8 | 先验 | −19.99 / −0.23 | +100.99 / 1.62 | +34.64 / 1.62 | 2/3 |
| Gate d8 | b7_z365gt0.5_long_off | +4.61 / 0.21 | +90.73 / 1.53 | +61.72 / 2.29 | 2/1 |
| Gate d8 | b28_trend28_short_off | −0.21 / 0.13 | +88.33 / 1.54 | +73.31 / 2.68 | 5/3 |
| OKX d7_noBNB | 基线 | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / 2.10 | — |
| OKX d7_noBNB | 先验 | +41.36 / 0.65 | +106.89 / 1.69 | +29.22 / 1.50 | 2/3 |
| OKX d7_noBNB | b28_trend28_short_off | +50.88 / 0.76 | +91.03 / 1.57 | +60.52 / 2.48 | 2/5 |

  - 9 切片胜数分布：1 格 9/9、2 格 8/9、其余最高 6/9。**锁定先验约 3/9、回退约 3/9**（post 掉 −25 pp / Sharpe −0.6，post 月 2/3）。
  - 9/9 的 `b7_z365gt0.5_long_off` 是非先验格，几乎不触发：post 只比基线多 +1.1 pp，月份 1/2（OKX）、2/1（Gate）；邻域 z>0.75 / 1 / 1.25 post 与基线逐位相同（门槛太高没有触发），z>0 / 0.25 调参段掉到 +59.8 / +78.2%（基线 +85.1%）。
  - 8/9 的 `b28_trend28_short_off`（非先验）：post +12.4 pp / Sharpe +0.42（OKX），月份 4/4、Gate 5/3、d7_noBNB 2/5，未达 6/9；OKX 深未见输基线（+25.8 vs +35.1，Sharpe 0.61 vs 0.71）。属 post 期「少开空单」体制，不是销毁量的稳定信息；先验同一序列 post 反而大输，方向不一致。
  - 压力费率（永续 15.1 / 现货 20 bps）：结论不变（OKX 基线 post +55.94/2.12；b28_trend28_short_off +69.40/2.58 月 4/4；先验 +31.80/1.51）。
  - new8 未调参（2024-11-28 →，`output/research_xrpl_fee_burn_gate_4h_new8.csv`）：OKX 基线 pre +47.16/0.98、post +3.26/0.28；先验 pre +31.30/0.75、post +0.97/0.17（3/2）；b28_trend28_short_off pre +21.42/0.58、post +8.47/0.69（5/3）；b7_z365gt0.5_long_off pre +39.25/0.92、post +6.13/0.47（3/0）。Gate 基线 pre +44.50/0.96、post +16.36/1.00；先验 pre +29.11/0.72、post +13.72/1.06；b28_trend28_short_off pre +23.16/0.61、post +20.69/1.32（4/3）。同样 pre 输、post 赢，形态与 wallet-users 一致。
- 结论：**否决**（不改默认、不入纸面、不加代码；先验 3/9、post 反输；非先验好格深未见分歧、月份不足 6/9、邻域不连续）。
- 勿重测：不要通过改 N（7/28/91/182/365 天）、z 窗口 / K、方向 / 侧、滞后，换 7 / 28 天销毁或同比增速，换成 XRPL 的交易笔数、账户数、支付数、DEX 成交或其他 XRPL 账本头字段，或换成 Stellar / Solana / Cardano 等链的手续费销毁 / 手续费总额来重开本族。
- CSV：`output/research_xrpl_fee_burn_gate_4h.csv`、`output/research_xrpl_fee_burn_gate_4h_new8.csv`、官方日度 `output/xrpl_fee_burn_official_daily.csv`（不入库）；脚本 `scratch/xrplburn4h/{fetch,run,new8,plog}.py`。
- 下一轮（短线）：选一个未测过、官方历史足够覆盖 2024-10-21 / 2026-03-05 切分的 1h 事件族（候选：Hyperliquid 官方 API 的清算 / 资金费极值事件，先查重 docs 中 Hyperliquid 10 条）。
