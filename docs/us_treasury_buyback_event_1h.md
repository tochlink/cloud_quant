# 短线新族：美国财政部官方国债回购（Treasury Buyback）结果 1h 事件 → 8 币永续篮子（2026-11-27 ~19:40 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、`output/research_*.csv`（1,376 个）、`scratch/ROTATION_LOCK.txt` 与记忆中「buyback / 回购」只出现在 `safe_gold_reserves_gate_4h` / `fhfa_house_price_gate_4h` 的下一轮指针里，从未执行。`us_treasury_auction_event_1h` 的勿重测只禁拍卖指标 / 期限 / 入场小时互换，`tga_dts_shock_event_1h` 只禁 TGA 存取，`us_debt_issuance_gate_4h` 是发行量，均不含二级市场回购。机制不同：拍卖是一级发行需求，回购是财政部从交易商手里买回旧券，报价额 / 上限反映交易商卖旧券的意愿（资产负债表压力 / 旧券流动性）。
- 数据（全部官方，未插值未补数）：fiscaldata.treasury.gov `v1/accounting/od/buybacks_operations`（236 条，2024-04 重启后 177 条到 2026-11-19）。主集合＝名义附息券（Liquidity Support + Cash Management）139 次；未调参未见集合＝TIPS 36 次；Small Value 3 次剔除。官方表 `output/us_treasury_buyback_ops_official.csv`（不入库）。价格：OKX 官方 1h 永续 8 币（2022-01-29 起）、OKX 未调参 new8、Gate 官方 1h 8 币（2025-09-24 起）；官方资金费。
- 公式（`scratch/ustbuyback1h/PRE_REGISTER.json`，sha256 c49e3a0a…384c，96 格，任何 PnL 前锁定）：
  - `cov` = total_par_amt_offered / max_par_amt_redeemed；`cov_res` = log(cov) − 同期限桶此前所有操作 log(cov) 中位数（≥2 次）；`take` = total_par_amt_accepted / max_par_amt_redeemed（官方 null 接受额 = 0）。
  - z = 相对本集合此前最多 N 次（N 12 / 24，至少 8 次，严格先前）的标准分；stress = z ≥ k（k 1.0 / 1.5），calm = z ≤ −k。
  - 操作 14:00 ET 截止；保守按截止 +60 分钟可用，下一根整点 1h 开盘入场（19 / 20 UTC），持有 H（4 / 24 / 48）根后开盘平；等权 8 币；重叠事件跳过；taker 5.1 bps/边（压力 15.1）+ 官方资金费。
  - 侧：stress_short / hyp_both（stress 空、calm 多）/ contra_both / stress_long。先验 `cov_z_N12_k1.0_stress_short_H24`（交易商大量甩旧券 = 美债流动性压力 → 次日 risk-off），回退 `take_z_N12_k1.0_stress_short_H24`。
  - 可用格：8 段全正（OKX d8 train/test/post、new8 train/test/post、Gate post/gate_window），且 OKX n train ≥3 / test ≥8 / post ≥5。切分 train(深度未见) <2024-10-21、test →2026-03-05、post →今。安慰剂 ±24h / ±168h 平移、同 UTC 小时（19/20）随机工作日（先验 / 回退 1000 次）。
- 结果（`output/research_us_treasury_buyback_event_1h.csv`，8,232 行；每事件净 bps，真实费）：

| 格 | OKX train | OKX test | OKX post | new8 post | Gate post | TIPS post | post 月份 OKX/Gate |
|---|---|---|---|---|---|---|---|
| 先验 cov_N12_k1.0_stress_short_H24 | n=0 | +276（n11, t2.2） | **−154**（n6） | −204 | −156 | +66（n2） | 2/9、2/9 |
| 回退 take_N12_k1.0_stress_short_H24 | 0 | 0 | 0 | 0 | 0 | — | 不触发 |
| 非先验最好 take_N24_k1.5_contra_both_H24 | +81（n1） | +8（n10） | +152（n9, t1.5） | +114 | +151 | +291 | 5/9、5/9 |

  - 先验：test 很强（随机安慰剂 99.7 分位）但 post 翻负（随机 6 分位），压力费 post −174；邻域 H24 / H48 全部 post 为负（N24 k1.0 H24 −95、H48 −92），只剩 H4 小正（+12 ~ +69，t<1.6）。深度未见段因 2024-05 才重启 + z 需 8 次预热，**0 个事件**，无法验证。
  - 回退：take 几乎总是 = 1（财政部按上限买满），z ≥ k 从不出现，闸门空转。
  - 全格可用 0/96；n_pos 分布 7 格 1 个、6 格 13 个。唯一 7/8 的 `take_z_N24_k1.5_contra_both_H24`（财政部明显少买 → 做空篮子）train 只有 1 笔、test +8（随机 57 分位）、Gate test −39、+168h 平移 post +98 也很好，且同期「每次回购后都做空 H24」基线 post 已有 +54 → 主要是 2026 下行行情，不是回购信息。
  - 基线：所有回购后 always_long H4 在 test / post / gate_window 都为负（−20 ~ −51 bps），属于美股午后时段效应（已否决的日内时段季节性族），不另立格。
- 结论：**否决**，不实现、不进观察名单、不改默认、无策略代码改动、纸面不动。历史太短（2024-05 起，post 只 6–9 笔），先验 test → post 翻转。
- 勿重测（never retest by）：改 N / k / H / 方向，在 cov / cov_res / take / 接受额 / 报价额 / 期限桶 / 发行数之间互换，只做 Liquidity Support 或 Cash Management，换 TIPS，换入场延迟或 15m 入场，把回购累计额做成 4h 闸门，或换财政部回购日程（季度再融资公布的回购计划）。
- 文件：`output/research_us_treasury_buyback_event_1h.csv`、`output/us_treasury_buyback_ops_official.csv`（不入库）；脚本 `scratch/ustbuyback1h/{build,prereg,run,analyze}.py`、`PRE_REGISTER.json(.sha256)`、`ops.json`、`analyze.log`（研究脚本未推送）。
- 下一轮（长线）：日本财务省官方外汇干预实绩（外国為替平衡操作の実施状況，月度 / 日度）作为 4h 默认书入场闸门（日元干预 = 全球美元流动性 / carry 平仓）；先查重 `fed_custody_gate_4h`、`snb_sight_deposits_gate_4h`（只禁 SNB 干预）、`jgb10y_yield_gate_4h`、`jgb_auction_result_event_1h`，若判同机制就换题。
