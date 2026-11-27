# 长线新族：旧金山联储官方 Daily News Sentiment Index（经济新闻情绪）→ 4h 默认书入场闸门（2026-11-27 ~08:55 PST，研究，不改默认；否决）

## 机制与公式
- 查重：docs/*.md、docs/STRATEGY_FORMULAS.md、output/research_*.csv 中 FRBSF / San Francisco Fed / news sentiment 0 命中。已否决的相近族：GDELT 新闻冲击 1h（报道量 / tone）、EPU 政策不确定性 4h、GPR 地缘风险 4h、UMich 消费者信心 / 零售销售 / 工业产出 4h。本族是联储官方的「经济新闻正负面情绪」（24 家美国报纸经济类文章的词典情绪、日固定效应），不是不确定性指数、不是问卷、不是 GDELT。本轮先排除：EIA WTI 期货期限结构（EIA 于 2024-04-05 停更，post 无数据）、台湾证交所三大法人（JPX 节勿重测已覆盖）、信用利差 / Bitfinex 保证金 / 泡菜溢价 / NAAIM（已测或无免费历史）。
- 假设：经济新闻情绪显著偏负（30 日均相对 730 日分布 z > 1）→ 宏观悲观 → risk-off → 拦新开多。
- 数据（仅官方）：FRBSF `https://www.frbsf.org/wp-content/uploads/news_sentiment_data.xlsx?2026-11-25`（Data 页），1980-01-01 → 2026-11-22，17,109 个日度观测，0 缺值，18 处 2–3 天空档（不补）。output/frbsf_news_sentiment_official_daily.csv sha256 42fa0c779852a708a3f0a21a7aa294ff2b1880baeae8280029017bb4090d9486。不补缺、无合成。风险：只拿到当前一个版本（Wayback 从本机不可达），模型固定效应可能有小幅历史修订，未能核对。
- 滞后：官方每周更新一次（2026-11-25 的文件数据到周日 11-22）。周一..周日的观测统一从「该周日 + 5 天（周五）00:00 UTC」起才使用，前向填充到 4h 棒。特征在官方日度观测上计算，每个发布批次取最后一天。
- 序列（取负，flag=1 = 新闻偏负面）：neg = −官方日值；neg30 / neg90 = −(30 / 90 个观测的尾随均值)。形式：z730（730 观测窗口，k = 0.5/1/1.5/2）、趋势 s > SMA{90,180}、变化 s − s.shift{30,90} > 0。侧：long_off / short_off（flag=0 拦新空）/ both / contra_both。闸门只拦新开仓，同向持仓、出场、止损不动。
- 96 格预注册（scratch/sfnews4h/PRE_REGISTER.csv，sha256 3ca95b544fd44356ed330f6773490dae9a6593d71c258abb6536afc2ad7c5f8d，2026-11-27 08:36:54 PST 锁定，看 PnL 前）；唯一先验 neg30_z730gt1_long_off；回退 neg30_trend_n90_long_off。
- 验证：同脚本 qtw.backtest 默认 4h 书基线（双均线 50/150），OKX d8（2023-02→）、Gate d8（2022-07→）、OKX d7 去 BNB（2022-04→）；deep 未见 →2024-10-21，tune →2026-03-05，post →2026-11-14；永续 taker 5.1 / maker 2 bps，压力 spot20 / perp15.1；官方资金费；±7/14/180/−120/365/−119 天安慰剂（最佳经济侧格另加 ±30/90 天）；邻域；untuned new8（LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI）。

## 结果（vs 同脚本基线）
基线：OKX d8 deep +35.14% / 0.71、tune +85.08% / 1.47、post +59.90% / 2.23；Gate d8 deep −3.63% / 0.09、tune +84.25% / 1.46、post +60.32% / 2.25；d7 post +50.76% / 2.10。

| 单元 | 9 段 Sharpe 胜 | OKX d8 post | Gate d8 post | 月份更优/更差 OKX · Gate · d7 | 备注 |
|---|---|---|---|---|---|
| 先验 neg30_z730gt1_long_off | 1/9 | +59.90% / 2.23（= 基线） | +60.32% / 2.25（= 基线） | 0/0 · 0/0 · 0/0 | post 闸门从未拦到新多；tune 段 +32.6% vs +85.1%（−52 pp） |
| 回退 neg30_trend_n90_long_off | 3/9 | +55.89% / 2.21 | +56.48% / 2.23 | 1/2 · 1/2 · 1/2 | deep OKX +5.1% vs +35.1%，post 也输 |
| 最佳经济侧 neg_chg_n90_both（非先验） | 6/9 | +71.36% / 2.61 | +71.91% / 2.62 | 4/2 · 4/2 · 3/3 | 月份未达 ≥6/9；deep 边很薄（0.72 vs 0.71、0.20 vs 0.09，d7 输）；tune Gate / d7 输 |
| neg_chg_n30_contra_both（非先验，反向侧） | 6/9 | +70.35% / 2.59 | +71.23% / 2.61 | 3/3 · 3/3 · 5/1 | tune 崩：+29.7% vs +85.1% |
| neg30_trend_n90_short_off（非先验） | 6/9 | +69.57% / 2.58 | +70.72% / 2.61 | 4/3 · 5/2 · 2/4 | Gate deep −9.8% / −0.05 |

- 96 格没有 7/9 以上。
- 安慰剂：最佳经济侧格平移 −7 天达 **9/9**、+7 天 6/9（post +72.6%），都不差于真实信号；±14 / 30 / 90 / −120 天大多 0–3/9 → 边对日期极敏感，不特异。先验各平移 1–3/9；回退 −7 天 6/9 高于真实 3/9。
- 邻域：neg_chg_both n=45 / 60 / 120 / 180 为 0/9、1/9、3/9、2/9（post −19 ~ −165 pp），只有 n=90 一个尖峰。先验 z=0.25–2.5 与 z365 全部 0–6/9，post 均与基线相同（无触发）。contra_both n=14–180 为 0–6/9，仅 n=180 有 6/9。
- new8（untuned，近 4,500 棒）：先验 pre +3.3% vs +30.7%（OKX）、+2.4% vs +28.6%（Gate），post 与基线相同；最佳经济侧 post OKX +4.8% vs +3.3%、Gate +17.4% vs +16.4%，月份 4/3；contra_both post 更好（5/1）但 pre 大幅更差（+11.2% vs +30.7%）。
- 压力费（spot20 / perp15.1）下排序不变：先验 post 仍 = 基线，最佳经济侧 OKX +68.3% vs +55.9%、Gate +68.9% vs +56.8%，deep / tune 照样薄或输。
- 结论：**否决**，不实现、不进观察名单、不改默认、不动纸面实例、无代码改动。
- 勿重测：勿以改 n / z 阈值 / 窗口（z365 / z730）、改方向或侧、在原始日值 ↔ 7 / 30 / 90 日均之间互换、改发布滞后、改用 FRBSF 其他文本指数或其他新闻情绪 / 报纸词典情绪序列（含 GDELT tone、Twitter / Reddit 情绪）来重测「美国经济新闻情绪 → 4h 默认书入场闸门」；也不要改成 1h「FRBSF 每周更新」事件来绕过本条。
- 输出：output/research_frbsf_news_sentiment_gate_4h.csv（399 行）、output/research_frbsf_news_sentiment_gate_4h_new8.csv、output/research_frbsf_news_sentiment_gate_4h_best_placebo_nbhd.csv、output/frbsf_news_sentiment_official_daily.csv（本机，不推送）。脚本 scratch/sfnews4h/{readxlsx,build,prereg,run,new8,plc_best,plog}.py。
