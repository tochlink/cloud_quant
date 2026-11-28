# 长线新族：日本 JVCEA 官方月度统计（现货成交额 / 保证金成交占比 / 利用者金銭預託金 / 稼働口座数）→ 4h 默认书 #1 入场闸门（2026-11-28 ~00:10 PST，研究；否决，仅文档，不改默认、无纸面变更）

- 查重：rg `JVCEA / 暗号資産 / Japan crypto / 日本加密` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`：只有上一轮（`ethbtc_relative_shock_event_1h.md`）写的「下一轮计划」一行，未测过。最接近的已否决族：韩国溢价 / Upbit、Coinbase 美国成交份额、`btc_exchange_trade_volume`、`bitfinex_margin_trend`、CFTC COT、`jpx_short_selling_ratio`（日股空卖比）、`mof_resident_foreign_bond_flow`。日本散户加密参与度（交易所日元成交额、法币预托金、活跃账户）从未测过。
- 数据（只用官方，不编造、不插值、不回补）：一般社団法人日本暗号資産等取引業協会（JVCEA）统计页 `https://jvcea.or.jp/about/statistics/` 的「会員の暗号資産取引状況表（月次）」最新版 `202609-KOUKAI-01-FINAL.pdf`（更新日 2026-11-02）第 1–2 页，**97 个月 2018-09 → 2026-09，0 个日历缺口**。序列：`spot_vol = ln(现货成交额 百万円)`、`margin_share = 保证金成交额 /(现货 + 保证金)`、`cash_dep = ln(利用者預託金 金銭等)`、`act_acct = ln(稼働口座数)`。
- 时滞：月 M 从 **max(M+2 月 10 日, 官方 KOUKAI-02 月报「更新日」+1 天) 00:00 UTC** 起才使用，再做单调 cummax（不让后月早于前月可用）。官方实际发布多在 M+2 月 1–7 日；2024-04~07 月份官方更新日是 2024-11-01，2024-08 是 2024-12-27，均按更晚的官方日期处理（保守）。注意：用的是最新修订版（官方注记 2026-11-02 修订了 2025-04~2026-08 账户数与 2026-08 保证金成交量）；先验用的金銭預託金不在修订清单内。2025-05 保证金成交额 11.67 兆円（约为前后月 10 倍）按官方原样保留。官方月表 `output/jvcea_crypto_official_monthly.csv`（不入库）。
- 公式（看 PnL 前锁定 `scratch/jvcea4h/PRE_REGISTER.json`，sha256 `fc727942…`，run.py `8b08126b…`，build.py `f91eebd0…`，120 格）：flag = 1 表示**日本散户参与度下降**：trend（x < SMA n，n 3 / 6 个月）、chg（x − x[−n] < 0，n 1 / 3）、z（24 个月 z < −k，k 0.5 / 1）；侧 long_off、short_off、both、contra_both、cap_short_off。闸门只拦新开仓，已有同向仓保留。**先验 cash_dep_trend_n6_long_off**（法币预托金跌破 6 月均线 = 散户弹药减少 → 不新开多），**回退 spot_vol_trend_n3_long_off**；安慰剂锚 = 先验（±30 / ±90 / +180 / −120 / +365 / −119 天平移）。
- 回测：与 `scratch/sofrvol4h/run.py` 同一脚本（默认 #1 双均线 50/150、perp_both 10×、OKX / Gate 官方永续 + 资金费），费用 maker 2 / taker 5.1 bps，压力费 spot 20 / perp 15.1 bps；OKX d8（2023-02 →）、Gate d8（2022-07 →）、OKX d7 不含 BNB（2022-04 →）；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14。

## 结果（`output/research_jvcea_crypto_stats_gate_4h.csv` 426 行）

**没有 7/9、8/9 或 9/9。先验、回退都是 0/9。**

| 格子 | 9 段 | OKX d8 深未见 / 调参 Sharpe | OKX post 收益 / Sharpe | Gate d8 深未见 / 调参 | Gate post | post 月胜 / 负（OKX、Gate） |
|---|---|---|---|---|---|---|
| 基线 默认 #1 | — | 0.71 / 1.47 | +59.90% / 2.23 | 0.09 / 1.46 | +60.32% / 2.25 | — |
| **先验 cash_dep_trend_n6_long_off** | 0/9 | 0.36 / 1.06 | +39.53% / 1.86 | −0.05 / 1.05 | +39.78% / 1.87 | 1/3、1/3 |
| **回退 spot_vol_trend_n3_long_off** | 0/9 | 0.17 / 0.74 | +59.90% / 2.23（post 不触发拦截差异） | −0.24 / 0.72 | +60.32% / 2.25 | 0/0、0/0 |
| 9 段最高 cash_dep_chg_n1_short_off（非先验） | 6/9 | 0.24 / 1.72 | +64.27% / 2.36 | −0.24 / 1.76 | +64.57% / 2.37 | 2/0、1/1 |

- **先验**：2026-03 后预托金持续低于 6 月均线（post 占用 100%），大量拦多：post 两家都 −20 pp，月份 1/3；深未见 OKX 0.36 vs 0.71、Gate −0.05 vs 0.09、d7 0.45 vs 0.75，九段全输。安慰剂 −119d / −120d 平移有 6/9，比真实好 → 否决。
- **回退**：深未见 / 调参窗大输（调参窗 OKX 0.74 vs 1.47），post 与基线相同 → 0/9。
- **9 段最高 cash_dep_chg_n1_short_off**（预托金环比不降 → 不新开空，非先验侧）：6 胜全来自调参窗 + post，深未见三处都输（OKX 0.24 vs 0.71、Gate −0.24 vs 0.09、d7 0.57 vs 0.75；压力费 Gate −0.37 vs −0.07）；post 多 +4.4 / +4.3 pp，但 post 月份只 2/0、1/1，远低于 6/9；邻域 chg_n2 post 崩到 +29% / 1.37，n6 / n12 ≈ 基线 → 塌陷。其余 6/9 格（spot_vol trend cap_short_off / contra_both）post 大幅低于基线。z 类格调参窗从不触发。act_acct（稼働口座）几乎单调上升，flag 基本恒 0。
- 结论：**否决**，不实现、不进观察名单、不改默认、无纸面变更、无代码改动。日本散户月度参与度是滞后、低频的「价格回声」：成交额 / 预托金跟随币价，用 M+2 发布后已比 50/150 均线更慢，无新信息。
- 勿重测（never retest via）：不要换 n / z 窗 / 阈值 / 侧 / 滞后重测本族；不要在 JVCEA 现货 / 保证金成交额、保证金占比、金銭預託金 / 暗号資産預託金 / 証拠金額、证拠金建玉（売建 / 買建 / 多空比）、全体 / 稼働 / 证拠金口座、个别币种（KOUKAI-02 上位币、BTC 保有状况）、同比 / 水平之间换序列；不要改用 JVCEA 年度统计、日本 FSA 交换业者报告、或 bitFlyer / Coincheck / bitbank 等单家交易所月度成交额替身重测；**日本加密行业月度统计类 4h 闸门视为全部覆盖**。
- 文件：`output/research_jvcea_crypto_stats_gate_4h.csv`、`output/jvcea_crypto_official_monthly.csv`（均不入库）；脚本 `scratch/jvcea4h/{build,run}.py`、`pdf/`（官方 PDF）、`PRE_REGISTER.json(.sha256)`（不推送）。因 `docs/STRATEGY_FORMULAS.md` 超过 GitHub 连接器写入上限，本段写在本 sidecar（本地 STRATEGY_FORMULAS.md 同步追加一行轮换记录）。
- 下一轮（短线）：bitFlyer 官方公开 API 的 BTC/JPY 现货相对 OKX BTC-USDT（官方 USDT/JPY 换算或 OKX 自身报价）1h 溢价跳变（L 小时 z）→ 8 币永续篮子 1h 顺势 / 逆势事件（下一根 1h 入场）。查重：docs / `output/research_*.csv` 无 bitflyer 条目；须先确认不被韩国溢价 / Upbit、Coinbase 溢价 1h、Kraken 欧元溢价、`okx_premium_cojump_event_1h`、`usdjpy` / `yenshock1h` 勿重测覆盖（若被覆盖或官方历史不足 2 年就换题）。
