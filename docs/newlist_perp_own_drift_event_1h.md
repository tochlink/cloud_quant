## 短线新族：新上线永续合约自身上线后漂移（OKX / Gate 新币永续，1h，2026-11-27 ~09:55 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、1,300+ 个 `output/research_*.csv`、scratch 目录名中检索 新上线 / listTime / newly listed / 上线后：只有「perp_listing_pace_gate_4h」（上线数量作为宏观闸门）、token_unlock、binance_delist_shadow（下架）与此不同；没有「新上线币种自身在上线后 N 小时的价格漂移」测试。原手交棒候选「SEC 13D/13G 加密股申报」未做：SEC EDGAR 同族已测 MSTR 8-K、COIN 等财报 8-K Item 2.02、Form 4、ETF S-1、网络安全 8-K，且 13D/13G 对加密股极稀疏，视为重复。
- 机制假设：新币永续上线初期热度过度 → 随后回吐，做空上线后 D 小时、持有 H 小时；单笔期望幅度大（几百 bps），不依赖 1h 薄边际。
- 预注册：看任何收益前锁在 `scratch/newlist1h/PRE_REGISTER.json`（sha256 f73066e79ff15298634cc222606c4607f75ae3190128e09a53cc3701f4d1ef1c，36 格，`output/research_newlist_perp_own_drift_event_1h_prereg.csv`）。方向 {short,long} × 入场延迟 D {1,6,24}h × 持有 H {24,72,168}h × 过滤 {f0 无, f1 仅上线后已上涨}。先验 short_D6_H72_f0，备选 short_D24_H72_f0。
- 数据（只用官方）：OKX `/public/instruments`（listTime，539 个 USDT 永续）+ `/market/history-candles` 1H 上线后前 360 根；Gate `/futures/usdt/contracts`（create_time）+ candlesticks 1h。Gate 只提供最近 10,000 根 1h，所以只含约 2025-10 以后上线（无 train 段，打分改为 5 个槽：OKX train/test/post + Gate test/post，相对预注册 6 槽的唯一偏差）。分段按上线时间：train < 2024-10-21，test 至 2026-03-05，post 之后。样本：OKX 109/134/270，Gate 52/79（test/post）。
- 局限：实时合约列表不含已下架合约（幸存者偏差，对做空保守、对做多偏乐观）；新币无资金费历史，未建模（压力 = 每边 15.1 bps + 每 8h 1 bp）；真实 taker 5.1 bps/边。对照 = 同入场/出场时刻的 OKX d8 等权篮子（2022 前上线无对照）。
- 结果：36 格中最高 4/5 槽为正（long_D1_H24_f0 等），无一格 ≥5/5，且无一格超额收益（减篮子）≥5/5；先验 short_D6_H72_f0：OKX train −363 bps（中位 +79）、test +383、post −54（t −0.5，月 5/9），Gate test −401、post −95（月 5/9）；备选 short_D24_H72_f0：OKX train −148、test +542（t 2.2）、post −25，Gate post −260。逐单标准差 20–50%，极端尾部（−300%）主导均值，各段符号不一致 → 无稳健边际。
- 结论：**否决**（不加入 shadow / paper，默认与纸面不变）。永不通过「改 D/H/过滤、换 long/short、换 OKX 与 Gate、用 5m 分辨率、只取 pump 币、改持有期」重测同族。
- 产出：`output/research_newlist_perp_own_drift_event_1h.csv`（36 格汇总）、`output/research_newlist_perp_own_drift_event_1h_trades.csv`（逐单）、`output/research_newlist_perp_own_drift_event_1h_prereg.csv`。
