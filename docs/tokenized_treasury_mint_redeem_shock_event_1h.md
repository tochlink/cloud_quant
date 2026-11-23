# 代币化美债基金 申购/赎回 1h 冲击 → 8 币永续篮子（短线，已否决）

记录时间：2026-11-23 00:07 PST。结论：**否决**，不实现，不加模拟盘，默认参数不变。

## 想法
链上代币化短期美债基金（BlackRock BUIDL、Ondo OUSG、Hashnote/Circle USYC、Superstate USTB、Franklin BENJI）是加密原生机构（Ethena USDtb、DAO、做市商）停放闲置美元的地方。某小时赎回（burn）突增 = 机构现金离开美债、准备进入加密风险资产 → 事先认定做多篮子；申购（mint）突增 = 去风险 → 备选做空。此前从未测过这一机制（与 USDT 增发、Maker PSM、Curve 3pool、CCTP 等稳定币族不同：这里是美债基金份额）。

## 数据（只用官方）
- 以太坊主网官方 `eth_getLogs`，ERC-20 `Transfer(from=0x0)` = 申购，`Transfer(to=0x0)` = 赎回；合约：
  BUIDL 0x7712c34205737192402172409a8F7ccef8aA2AEc，OUSG 0x1B19C19393e2d034D8Ff31ff34c81252FcBbee92，USYC 0x136471a34f6ef19fE571EFFC1CA711fdb8E49f2b，USTB 0x43415eB6ff9DB7E26A15b704e7A3eDCe97d31C4e，BENJI 0x3DDc84940Ab509C11B20B76B466933f40b750dc9。
- 49,142 条官方日志，33,517 个完整 UTC 小时（2023-01-26 18:00 → 2026-11-23 06:00），13 段跨节点抽查条数完全一致。按区块时间戳归入 UTC 小时，小时收盘后才可用，下一根 1h 永续开盘入场。
- 行情：OKX / Gate 官方 USDT 永续 1h K 线 + 官方资金费；吃单 0.051%/边，压力 0.151%/边。

## 公式
- 序列：`log_n_burn = log1p(当小时去重赎回交易数)`，`log_n_mint = log1p(当小时去重申购交易数)`，`log_redeem_bps = log1p(Σ 赎回份额 / 赎回前总供给, bps)`。
- `z_t = (x_t − mean(x_{t−L..t−1})) / sd(x_{t−L..t−1})`，z ≥ k 触发，t+1 开盘入场，持有 H 小时，不重叠。
- 网格（看收益前 2026-11-22 23:56 PST 锁定 72 格）：series × L∈{168,720} × k∈{2,3,4} × side∈{long,short} × H∈{24,48}。
- 事先认定格 `log_redeem_bps_L720_k3_long_H48`；备选 `log_n_mint_L720_k3_short_H24`。
- 分段：deep unseen 2023-01-26→2024-10-21，test →2026-03-05，post →末尾；宇宙 okx_d8、okx_new8（未调参）、gate_d8。8 项检查需全部 >0 才算 usable。

## 结果（每笔均值 bps，真实费率）
| 格 | 通过 | OKX 未见 | OKX test | OKX post (n) | Gate post | 新8 post | post 月份 OKX/Gate |
|---|---|---|---|---|---|---|---|
| 事先认定 redeem_bps L720 k3 多 H48 | 3/8 | +37.2 | +5.2 | −46.9 (65) | −45.6 | −7.7 | 3/3 |
| 备选 n_mint L720 k3 空 H24 | 0/8 | 负 | −97.3 | −20.1 (42) | −21.0 | −48.5 | 4/4 |
| 非事先 n_burn L168 k4 多 H24 | 8/8 | +11.8 | +74.5 | +49.1 (12, t 1.0) | +49.6 | +108.2 | 5/5 |
| 非事先 n_mint L168 k3 多 H48 | 8/8 | +73.4 | +37.5 | +29.2 (36, t 0.4) | +30.6 | +1.5 | 4/4 |

- 72 格里只有 2 个 usable，都不是事先认定格；post t 值都 < 1.5，post 月份都没到 6/9。
- 邻域崩：n_burn L168 k4 多 H48 post −54.6、k3 H24 post −34.9；n_mint L168 k3 多 H24 post +1.3。
- n_burn 那格的 +720h 平移安慰剂 post −123.7，但 −720h 平移 +11.1，随机日期分位 83%（未达稳定）。
- 事先认定格整个 redeem_bps 做多邻域 post 全部为负（12/12），压力费率下更差。

## 结论
否决。以后不再换 L、k、H、方向，不换笔数/份额/金额口径，不单拆 BUIDL/OUSG 等单只基金，不换其他链或其他代币化美债/货币基金合约重测。

CSV：`output/research_tokenized_treasury_mint_redeem_shock_event_1h.csv`（本地，不进 git）。
