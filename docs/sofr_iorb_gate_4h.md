# SOFR − IORB 利差 4h 入场闸门（否决）

## 长线新族：纽约联储官方 SOFR − 美联储官方 IORB（2021-07-29 前 IOER）利差（回购 / 货币市场资金压力）→ 4h 默认书入场闸门（2026-11-20 ~22:00 PST，研究，不改默认；否决）

- 查重：文档 / `output/research_*.csv` 中无 SOFR / IORB / IOER 完成条目（仅上一轮「下一轮」计划）。这是货币市场管道压力，不是已否决的 FRED 净流动性（WALCL / TGA / RRP）、NFCI / STLFSI、高收益利差、政策利率周期或 M2 闸门。
- 数据（只用官方，不编造、不回补）：NY Fed Markets API `https://markets.newyorkfed.org/api/rates/secured/sofr/search.json`（2018-04-02 → 2026-11-19，2,157 个营业日；SOFR 与 FRED `SOFR` 逐日完全一致；含官方成交量加权 p1 / p25 / p75 / p99 分位，其中 2 天官方分位缺失 → 该两序列直接丢弃这两天，不填）；FRED `IOER`（到 2021-07-28）与 `IORB`（2021-07-29 起）。历史覆盖 2024-10-21 前深度段与 2026-03-05 切分。官方日序列 `output/sofr_iorb_official_daily.csv`（不入库）。
- 时滞：D 日 SOFR 于下一官方 SOFR 营业日 ~08:00 ET 发布 → 从该营业日 13:00 UTC 起才使用（比夏令时 12:00 UTC 更保守），再前向填充到 4h 棒；IORB / IOER 为事先公布的管理利率，按当日值。
- 公式（看任何 PnL 前写入 `PRE_REGISTER.json` 锁定，120 格）：`spr = (SOFR − IORB) × 100` bps；`p99spr = (SOFR_p99 − IORB) × 100`（尾部资金压力）；`disp = (SOFR_p99 − SOFR_p1) × 100`（回购利率离散度）。形态 trend n∈{30,90,180} 观测（指标 > SMA(n)）、chg n∈{30,90}（n 期变动 > 0）、z252 k∈{1.0,1.5,2.0}（(指标−SMA252)/STD252 > k）；五侧 long_off / short_off / both / contra_both / cap_short_off，只拦新开仓。经济先验（锁定不翻转）：资金压力高 / 上升 = risk-off → `long_off` 与 `both`；回退先验格 `spr_trend_n90_long_off`。复用 ERC-4337 4h 闸门同一回测脚本（OKX d8 / Gate d8 / OKX d7_noBNB，官方 OKX / Gate 永续 4h，真实费率 + 压力费 20 / 15.1 bps，同脚本基线，9 段 Sharpe，post 月份，安慰剂平移，邻域）。
- 结果：CSV `output/research_sofr_iorb_gate_4h.csv`（435 行）。**没有 7/9、8/9 或 9/9。**
  - 同脚本基线：OKX d8 deep +35.14% / Sharpe 0.71，tune +85.08 / 1.47，post +59.90 / 2.23；Gate d8 deep −3.63 / 0.09，tune +84.25 / 1.46，post +60.32 / 2.25；OKX d7_noBNB deep +54.92 / 0.75，tune +92.93 / 1.56，post +50.76 / 2.10。
  - 回退先验格 `spr_trend_n90_long_off` 只有 3/9：OKX post +56.52 / 2.15（月份 1/3），Gate +57.23 / 2.18（0/4），d7 +50.44 / 2.07；deep 赢、tune 与 post 全输。
  - 先验最好 `p99spr_z252gt1_long_off` 6/9，但只是 deep / tune 计赢：2026-03 后 z>1 几乎从未触发（post 占用 0.6%），三条 post 与基线完全相同（月份 0/0），无法通过 post 检验；deep 边很薄（OKX 0.74 vs 0.71，Gate 0.17 vs 0.09，d7 0.76 vs 0.75）。`spr_z252gt1.5_long_off` 同理（post 占用 0%）。
  - 安慰剂：该锚点平移 +7 天与 −14 天同样 6/9（+7 天 deep / tune 甚至比真实更好：OKX deep 0.84、tune 1.65），−7 天 5/9，+365 天 5/9，+180 天 4/9 → 6/9 可被日历平移打出，信号不特异。
  - 邻域：k=0.75 / 1.25 也是 6/9、k=1.75 为 5/9，但全部 post 无触发、与基线相同。
  - 非先验最好 `spr_chg_n30_cap_short_off` 6/9：post OKX +61.21 / 2.27（月份 3/5），Gate +62.06 / 2.30（5/3），但 deep 被打穿（OKX +4.04 / 0.22 vs +35.14 / 0.71；Gate −26.03 / −0.33）；且是看结果后的反向侧，不采用。
  - 压力费：锚点 post 仍与基线相同（OKX +55.94 / 2.12，Gate +56.78 / 2.15）。
- 结论：**否决**，不实现、不进观察名单、不改默认，仅文档。SOFR−IORB 利差在 2026-03 后几乎无压力事件，z 闸门实际空转；趋势 / 变动闸门削减 post 收益。勿以同一机制换 n、k、方向，或换 SOFR 分位（p1/p25/p75/p99）、TGCR / BGCR / EFFR / OBFR、RRP 利率替代 IORB 再测。
- 下一轮（短线）：美国财政部官方 Fiscal Data「Treasury Securities Auctions Data」（`/v1/accounting/od/auctions_query`）10 年 / 30 年附息国债拍卖结果（~13:00 ET 公布的 bid-to-cover、间接投标占比、高收益率相对前次）→ 1h 事件冲击 → 8 币永续篮子。文档中无国债拍卖条目；不是已否决的月度财政收支 4h 闸门、CPI / FOMC 事件或本轮 SOFR 闸门。只用官方拍卖结果与公告时间，先预注册。
- 脚本 `scratch/sofriorb4h/{build,run}.py`、`PRE_REGISTER.json`（研究脚本未推送）。默认策略与纸面实例均未改动，无需拉取或重启。
