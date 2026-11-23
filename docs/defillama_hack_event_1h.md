# 短线新族：DefiLlama 公开黑客 / 被盗事件库 大额被盗日 → 8 币永续篮子 1h 事件（2026-11-23 ~02:45–03:05 PST，研究，不改默认；否决）

## 选题与查重
- 原定候选：比特币 Ordinals 铭文 / BRC-20 每小时数量爆发。查重通过（docs/*.md、`output/research_*.csv`、记忆中 Ordinals / inscription / BRC-20 只出现在「下一轮」指针里，无完成条目），但**没有可用的全历史官方或可信公开来源**：Hiro Ordinals API（`api.hiro.so/ordinals/v1/*`）已下线（403 Missing Authentication Token），ordinals.com（官方 ord 服务器）被 Cloudflare 挑战页拦截，Ordiscan 收费（402），Unisat 只有逐笔 tx 的 `nNewInscription`（每块数千笔，约 21 万块不可行），自己解析 witness 需要约 400 GB 原始区块。按规则不编造、不回补，换题。
- 改测：DefiLlama 公开黑客事件库（`https://api.llama.fi/hacks`，1,375 条，2015 → 2026-11-22）大额被盗日 → 8 币永续篮子。查重：docs / output / 记忆中 hack / exploit / 被盗 只出现在 Tornado Cash（混币资金流 1h）、USDT/USDC 黑名单（4h 闸门）、硬分叉（紧急分叉剔除）里，从未把「被盗事件本身」当信号。不是已否决的 Tornado 存取、稳定币冻结、清算、闪电贷、交易所事故（exchange_status_incident）。
- 机制（先验，锁定）：大额被盗（≥ 2,500 万美元）= 风险外溢 / 受害方与黑客抛售 → 次日篮子下跌 → 跟随做空。交易稀少（每年约 10–20 次），符合「单笔 edge 大或交易稀少」的短线要求。

## 数据
- 来源：DefiLlama hacks 数据库原始 JSON（`scratch/defihack1h/raw_hacks_20261123.json`，sha256 见 `raw_sha256.txt`）。字段 date（UTC 日，精度到天）、amount（美元）、targetType。65 条 amount 为空的剔除，用 1,310 条。
- 注意（偏差）：这是策展型公开库，不是链上官方源；日期只到天、金额为事后估计、库没有入库时间（无 point-in-time 版本）。为此入场放在事件日 D 结束后（D+1 00:00 UTC）或再晚 24h（lag24）。
- 行情：官方 OKX 1h 永续（d8 8 币 2022-01-29 → 2026-11-23 06:00 UTC 收盘，new8 未调参 8 币同期）、Gate 1h 永续 d8（2025-09-24 起）；官方资金费（OKX deep、Gate）。无 mock、无现货替代。

## 公式与预注册（`scratch/defihack1h/PRE_REGISTER.json`，2026-11-23 02:51:03 PST 在任何 PnL 之前锁定，sha256 `35f2188b…6bc6017`）
- 事件日 D：scope 内当日被盗金额合计 ≥ A。scope ∈ {all, defi（targetType ≠ CEX）}，A ∈ {10, 25, 50, 100} 百万美元。
- 信号根 = D 23:00 UTC +lag（lag ∈ {0, 24}h），下一根 1h 开盘吃单入场等权 8 币，持有 H ∈ {12, 24, 48}h，方向 short（跟随）/ long（反弹），不重叠，计入资金费。
- 2 × 4 × 2 × 3 × 2 = **96 格**。先验 `all_A25M_short_H24_lag0`，回退 `all_A50M_short_H48_lag0`。
- 费用：真实 taker 5.1 bps/边，压力 15.1 bps/边。8 槽：OKX d8 train(2022-02-15→2024-10-21，深度未见) / test / post(2026-03-05→)，OKX new8 三段，Gate d8 post + gate_window(2025-09-28→)。可用 8/8 需 OKX d8 n train≥10、test≥8、post≥8。
- 同脚本基线：每个 UTC 日同一入场时刻、同 H、同方向。安慰剂：事件日 ±720h 平移；200 次随机日匹配抽样（报告真实均值所处分位）。

## 结果（`output/research_defillama_hack_event_1h.csv`，3,504 行；每笔净 bps，真实费；括号为同脚本基线）
| 格 | OKX d8 深度未见 train | test | post | new8 train | new8 post | Gate post | post 压力费 | n tr/te/po | 8 槽 |
|---|---|---|---|---|---|---|---|---|---|
| 先验 all A25M short H24 lag0 | −90.6 (−21.8) | −25.9 (+2.5) | +62.9 (+21.2) | −96.0 (−10.9) | +2.2 (+14.8) | +62.6 (−22.4) | +42.9 | 36/17/14 | 4/8 |
| 回退 all A50M short H48 lag0 | −87.5 (−34.3) | +48.4 (−9.7) | −44.3 (+3.4) | −68.9 (−24.7) | −177.6 (−20.3) | −46.3 (+18.0) | −64.3 | 26/7/9 | 2/8 |
| 非先验最好 all A50M long H24 lag24 | +0.0 (−9.9) | +139.3 (+11.9) | +76.7 (+1.6)，t 1.4 | +5.1 (−2.5) | +129.2 (+14.7) | +78.2 (+2.0) | +56.7 | 26/7/9 | 8/8（n 不够） |

- 分布：96 格 8 槽正收益个数 0:14、1:7、2:16、3:10、4:14、5:8、6:18、7:3、8:6；**可用 8/8 为 0**（6 个 8/8 全是 long lag24 反弹格，test n 只有 2–7）。
- 先验（跟随做空）在深度未见段两套都大亏（−90 / −96 bps，比基线差约 70–85 bps，随机日分位 0.10），被盗后做空不成立。
- 非先验 8/8 `all_A50M_long_H24_lag24`（被盗后第二天抄底）：深度未见 train 只有 +0.0 bps（n 26，随机日分位 0.5 = 与随机日无差别），edge 全来自 test / post 的 7 / 9 笔，post t 1.4；−720h 平移安慰剂 post +42.4、+720h −84.2，+720 / −720 在 train 都为负。
- 邻域：同 long H24 lag24，A25M post +27.3（t 0.5）、A10M post −7.3、A100M train −15.6；long H48 lag24 A25M / A10M post −44.5 / −123.4。对 A、H 不稳定。

## 结论
**否决**。不实现、不进观察名单、不加纸面子账本、不改默认、无代码改动，仅文档。先验（大额被盗 → 跟随做空）在深度未见段为显著负；唯一看着好的「被盗后第二天抄底」在深度未见段等于随机日，事件数不足以过 8/8 可用门槛，邻域崩。数据也有策展库无入库时间的事后偏差。

## 勿重测
不要换 A 阈值 / scope（all / defi / CEX / bridge / 链 / 攻击类型）/ H / lag / 方向，不要改用被盗金额的日 / 周滚动和或 z 分数、单笔最大额、事件笔数、净损失（扣除 returnedFunds）、只看某条链或某类目标，不要换成 Rekt / SlowMist / CertiK / Immunefi / PeckShield 等其他被盗事件库，也不要改成 4h 默认书闸门，以「黑客被盗事件 → 加密篮子」同一机制重测。Ordinals / BRC-20：全历史来源恢复（Hiro 重新开放或 ord 服务器可直接访问）前不要用抽样或部分区块代替。

## 文件
- `output/research_defillama_hack_event_1h.csv`（不入库）；脚本 `scratch/defihack1h/{prereg,run,analyze}.py`、`PRE_REGISTER.json`、`analyze_wide.csv`、`events_used.csv`、原始 JSON（研究脚本未推送）。

## 下一轮（长线）
美联储 H.4.1 央行流动性互换额度使用量（FRED `SWPT` 周度，周四公布，按公布时间滞后）作为离岸美元融资压力体制，做 4h 默认书入场闸门；先检查 2021 年后使用量是否几乎一直为 0，不够形成体制就改测 H.4.1 贴现窗口一级信贷（primary credit）使用量。查重：docs / output 中无 SWPT / swap line 完成条目。
