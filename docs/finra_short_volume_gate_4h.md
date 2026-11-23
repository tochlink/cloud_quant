# FINRA Reg SHO 官方每日卖空成交占比（美股加密代理股 MSTR / COIN / MARA / RIOT）→ 4h 默认书入场闸门（否决；不改默认、不入纸面）

## 长线新族：加密代理股 5 日卖空成交占比作为 4h 默认书入场闸门（2026-11-22 ~16:30–16:52 PST，研究，不改默认；否决）

- 查重：`docs/`、`docs/STRATEGY_FORMULAS.md`、`output/research_*.csv` 文件名、`scratch/` 目录名与记忆中 regsho / Reg SHO / short volume / short sale / short interest / 卖空 / fails-to-deliver 零命中。本轮建议的候选全部已做：Beacon 进出排队（eth_beacon_staking_gate_4h）、Lido 提款队列（lido_wq_burst_event_1h、lido_steth_apr_gate_4h）、BTC 难度 / 哈希带（btc_difficulty_adj_event_1h、btc_hash_ribbon_gate_4h）、EIP-1559 基础费 / 燃烧（eth_onchain_demand、eth_gas_fullness、eth_blob_basefee）、Sky SSR / DSR（sky_ssr_dsr_gate_4h）。另排除：ECB / BoJ 资产负债表（SNB 节勿重测）、持仓量闸门（research_open_interest_gate）、TIPS 实际利率（us_macro_risk_regime）、GSCPI（美国宏观跳过表）。本族不同于 crypto_equity_relstrength（MSTR / COIN **价格**相对 BTC）、FINRA 融资余额（finra_margin_debt）、CFTC COT（期货持仓）：这里是美股加密代理股的**场外卖空成交流**。
- 机制：加密代理股中卖空成交占比偏高 = 知情 / 对冲型看空压力（Boehmer-Jones-Zhang：重度卖空预示弱收益）。先验：卖空压力高时拦新多。只拦新开仓，已有持仓、止损、离场不变。默认 4h 书（#1 双均线 50/150，8 币永续）。
- 数据（只用官方，不编造、不回补、不插值）：FINRA 官方 Reg SHO 每日卖空量文件 `https://cdn.finra.org/equity/regsho/daily/CNMSshvolYYYYMMDD.txt`（合并 NMS），2020-07-01 → 2026-11-20 所有工作日：**1,607 个文件 HTTP 200**，61 个工作日 HTTP 403（美股休市日，官方无文件，不填）。COIN 2021-04-14 上市前 197 天无记录（按不存在处理）。每文件另记全部证券合计卖空量 / 总量。日度表 `output/finra_regsho_crypto_equity_daily.csv`（不入库），原始 JSON 在 `scratch/finrashvol4h/raw/`。最新 2026-11-20：c4 5 日占比 0.5378（60 日 z −0.53）、rel +0.0639（z60 +0.27）。
- 滞后：FINRA 约 18:00 ET（22:00–23:00 UTC）发布当日文件；保守按 **D+1 08:00 UTC 4h 开盘**才可用，前向填充。
- 公式（看 PnL 前写入 `scratch/finrashvol4h/PRE_REGISTER.json` 锁定，sha256 `129b47183599d054ad94029f200108b310f4e540bd4ecd69027e6e3c5e5eeeee`，120 格）：
  - 序列（flag=1 一律 = 卖空压力高）：`c4` = MSTR+COIN+MARA+RIOT 5 个营业日卖空量合计 / 总量合计；`mstr` = 仅 MSTR；`miners` = MARA+RIOT；`rel` = c4 − 全部证券 5 日卖空占比（加密特有超额）。
  - 形式：`chg`：s − s.shift(n 个营业日) > 0，n 20 / 60 / 120；`z`：(s − SMA_n) / STD_n > 1，n 20 / 60 / 120。
  - 侧：long_off / short_off / both / contra_both / tight_short_off（同 SHIBOR 节语义）。4 × 6 × 5 = 120 格 + 同脚本基线。
  - 先验格（锁定）：`c4_z60gt1_long_off`，兼作安慰剂锚；回退 `rel_z60gt1_long_off`；long_off / both 为经济先验侧。
- 验证：与 SHIBOR / SNB 闸门同一框架（OKX d8 2023-02→ / Gate d8 2022-07→ / OKX d7_noBNB 2022-04→，官方永续 + 现货 4h、官方资金费；真实费率永续 maker 2 / taker 5.1 bps，压力永续 15.1 / 现货 20 bps；深未见 →2024-10-21、调参段 →2026-03-05、post →2026-11-14；安慰剂日历平移 ±7 / ±14 / +180 / −120 / +365 / −119 天；邻域 n 10 / 30 / 40 / 90 / 150 / 250、z 阈值 0.5 / 1.5 / 2 + 换序列；new8 未调参币 OKX + Gate 最近 4500 根 4h）。
- 默认门槛（9 分）：深未见 / 调参段 / post 三段 × 三套账本 Sharpe 胜同脚本基线；改默认还要 post 两所 ≥ 6/9 月更好，且安慰剂 + 邻域支持。
- 结果（`output/research_finra_short_volume_gate_4h.csv` 444 行；收益 % / Sharpe，真实费率）：

| 账本 | 格 | 深未见 | 调参段 | post | post 月 好/差 |
|---|---|---|---|---|---|
| OKX d8 | 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | — |
| OKX d8 | 先验 c4_z60gt1_long_off（3/9） | +73.63 / 1.17 | +82.84 / 1.46 | +59.90 / 2.23 | 0/0 |
| OKX d8 | 回退 rel_z60gt1_long_off（6/9） | +61.99 / 1.05 | +84.78 / 1.48 | +59.90 / 2.23 | 0/0 |
| OKX d8 | 非先验 rel_chg_n20_both（9/9） | +41.81 / 0.83 | +91.46 / 1.69 | +61.78 / 2.31 | 3/4 |
| Gate d8 | 基线 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / 2.25 | — |
| Gate d8 | 先验 | +17.80 / 0.38 | +80.77 / 1.43 | +60.32 / 2.25 | 0/0 |
| Gate d8 | 回退 | +11.84 / 0.30 | +83.15 / 1.46 | +60.32 / 2.25 | 0/0 |
| Gate d8 | rel_chg_n20_both | +15.97 / 0.36 | +94.21 / 1.73 | +62.26 / 2.33 | 3/4 |
| OKX d7_noBNB | 基线 | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / 2.10 | — |
| OKX d7_noBNB | 先验 | +98.06 / 1.08 | +90.24 / 1.54 | +50.76 / 2.10 | 0/0 |
| OKX d7_noBNB | 回退 | +84.13 / 0.99 | +91.76 / 1.56 | +50.76 / 2.10 | 0/0 |
| OKX d7_noBNB | rel_chg_n20_both | +58.02 / 0.81 | +89.17 / 1.69 | +52.41 / 2.18 | 3/2 |

  - 9 切片胜数分布（120 格）：0/9 26、1/9 12、2/9 4、3/9 45、4/9 3、5/9 6、6/9 22、8/9 1、9/9 1。经济先验侧（long_off / both 48 格）只有 both 侧的 c4_chg_n20_both 8/9 与 rel_chg_n20_both 9/9 超过 6/9；long_off 侧最高 6/9。
  - 先验 c4_z60gt1_long_off 3/9：深未见三套都大胜（OKX 1.17 vs 0.71、Gate 0.38 vs 0.09），但调参段三套都输，post 期间闸门一次都没拦到新多（post 与基线完全相同，月 0/0）。压力费率深未见 OKX +60.84/1.03 vs +24.67/0.56、Gate +6.22/0.23 vs −13.77/−0.07，post 同基线。
  - 回退 rel_z60gt1_long_off 6/9（深未见三套胜、调参段微胜），同样 post 不触发（0/0 月），无法满足 post 月门槛。
  - 非先验 9/9 rel_chg_n20_both：post 边 OKX +1.88 pp / Sharpe +0.08、Gate +1.94 pp / +0.08，月 3/4、3/4（远低于 6/9）。压力费率 post OKX +57.96/2.21 vs +55.94/2.12、Gate +58.84/2.24 vs +56.78/2.15。
- 安慰剂（先验锚，主 CSV）：+7d 5、−7d 3、+14d 3、−14d 1、+180d 5、−120d 6、+365d 4、−119d 6 → 最好 6/9 > 真实 3/9。
- 安慰剂（rel_chg_n20_both，`_supp.csv`）：+7d 6、−7d 1、+14d 6、−14d 0、+180d 5、−120d 1、+365d 2、−119d 1 → 最大 6/9 < 真实 9/9（时点有一定特异性），但其他门槛不过。
- 邻域（rel_chg_n20_both，主 CSV）：n=10/30/40/90/150/250 胜数 6/3/4/3/0/3，post 全部大输（+38.77 ~ +51.72 vs +59.90，n=10 月 2/7）→ **只在 n=20 一点成立，邻域崩**。
- 邻域（先验 / 回退，`_supp.csv`）：c4 z 窗 10/30/40/90/150/250 胜数 3/3/3/4/5/5，k 0.5/1.5/2 胜数 3/3/0；rel z 窗 3/3/3/6/3/4，k 0.5/1.5/2 胜数 3/0/0。
- new8 未调参（最近 4500 根 4h，2024-11-28→，`_new8.csv`）：基线 OKX pre +49.60/1.02、post +3.26/0.28；Gate pre +46.78/0.99、post +16.36/1.00。先验 pre 两所胜（+55.53/1.11、+53.28/1.09），post = 基线（不触发）。回退 pre 两所胜（+52.60/1.06、+49.90/1.04），post 小胜（+4.53/0.37、+17.77/1.07，月 2/0、2/0）。rel_chg_n20_both pre 收益两所都输（+42.13、+43.45），post 小胜（+4.56/0.39 月 6/3、+16.63/1.09 月 5/3）；其 +180d 平移安慰剂 post 反而更好（+19.00 / +32.47）。
- 结论：**否决**（不改默认、不入纸面、不加代码）。先验 3/9、回退 6/9 都在 post 段完全不触发（post = 基线，月 0/0），只在深未见段有效，无法证明 2026-03 后仍有用；唯一 9/9 rel_chg_n20_both 是非先验，post 边约 +1.9 pp、月 3/4，邻域 n≠20 全崩，new8 pre 输。不满足默认门槛，也不够强观察。
- 勿重测：不要通过改 n / 窗口（5 日合计窗、z 窗 10~250、chg 10~250）、z 阈值 k、方向 / 侧、滞后（当日 / D+1 04:00 / 08:00），换股票篮子（MSTR / COIN / MARA / RIOT / CLSK / HUT / BITF / IBIT / GBTC / BITO / 其他矿企或加密 ETF）、换占比口径（ShortVolume / TotalVolume、含或不含 ShortExempt、相对全市场或 SPY / QQQ 的超额、单交易场所 FNSQ / FNYX / FORF 文件）、换水平 / 变化 / z / 百分位的方式重测本族；也不要改成 FINRA 双周 short interest、SEC fails-to-deliver 或 1h「Reg SHO 文件发布」事件来绕过本条。
- CSV：`output/research_finra_short_volume_gate_4h.csv`（主网格 + 先验安慰剂 + rel_chg_n20_both 邻域 + STRESS，444 行）、`output/research_finra_short_volume_gate_4h_supp.csv`（先验 / 回退邻域 + rel_chg_n20_both 安慰剂）、`output/research_finra_short_volume_gate_4h_new8.csv`（new8 未调参，20 行）、`output/finra_regsho_crypto_equity_daily.csv`（官方日度，不入库）；脚本 `scratch/finrashvol4h/fetch.py`、`build.py`、`run.py`、`supp.py`、`new8.py`。
