# 长线：OECD 综合领先指标（CLI）全球景气体制 → 默认 4h 书入场闸门（2026-11-22 ~20:55–21:20 PST，否决）

## 查重
- `ls output/research_*.csv`、`docs/*.md`、`docs/STRATEGY_FORMULAS.md` 轮换记录检索 `OECD` / `composite leading` / `CLI` / `leading index` / `PMI` / `GSCPI` / `CFNAI`：无 OECD CLI 条目（`CLI` 仅为命令行无关命中；`PMI` 仅为 ISM 下架说明）。
- 不是已否决的美国宏观（GDPNow / WEI / CFNAI / GSCPI / 初请 / CPI / M2 / 金融条件 / 美元体制），也不是已上模拟盘的 USDT 借贷利率 / H.4.1 托管 / MSTR 相对强弱 / DTWEXBGS / 人民币中间价闸门。

## 数据（官方，未编造、未回补）
- OECD SDMX：`https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,4.1/G20+CHN+G7.M.LI...AA...H`（CLI，振幅调整，OECD 统一口径，长期趋势 = 100）。
- 月度 2000-01 → 2026-10，三序列各 322 个月，无缺失。本地 `output/oecd_cli_official_monthly.csv`（2026-11-22 抓取的当前版本）。最新 2026-10：G20 99.965、中国 97.131、G7 100.902。
- 发布时滞：月 M 仅于 **M+2 月 1 日 01:00 UTC** 起使用（OECD 约在 M+1 月中旬发布；2026-10 在 2026-11-22 已公开），前向填充到 4h K 线。
- 修订风险：OECD SDMX 无公开实时版本库，使用的是当前版本，修订只会让结果偏乐观；即便通过也只能封顶为观察。

## 公式与预注册（看 PnL 前锁定，`PRE_REGISTER.json` 2026-11-22 20:58 PST）
- 序列 g20 / chn / g7；形式：`lvl100` CLI>100；`chgN` CLI−CLI(N 月前)>0，N∈{1,3,6}；`trendN` CLI>SMA(N 月)，N∈{6,12}；`z60gtK` (CLI−SMA60)/STD60>K，K∈{0.5,1}。
- 五侧：long_off / short_off / both / contra_both / cap_short_off（只拦新开仓，已有同向仓保留）。3×8×5 = 120 格 + 同脚本基线（默认 #1 MA50/150 不加闸门）。
- 经济先验（锁定不翻转）：CLI 上行 / 高于趋势 = 全球景气上行 = risk-on → cap_short_off / contra_both。回退先验格 `g20_chg3_cap_short_off`。
- 验证：官方 OKX 与 Gate 永续 4h（d8，OKX 2023-02 起，Gate 2022-07 起）+ OKX d7_noBNB（2022-04 起）；真实费率（永续 maker 0.02% / taker 0.051%）与压力费（永续 taker 15.1 bps）；深度未见期（起点→2024-10-21）/ 调参期（→2026-03-05）/ post（2026-03-05→2026-11-14）；9 片 Sharpe 胜场；post 月份胜负；邻域；±7/±14/+180/−120/+365/−119 天日历平移安慰剂。

## 结果（`output/research_oecd_cli_gate_4h.csv`）
- 基线：OKX d8 深度 +35.14%/0.71，调参 +85.08%/1.47，post +59.90%/2.23；Gate d8 深度 −3.63%/0.09，调参 +84.25%/1.46，post +60.32%/2.25。
- 120 格 9 片胜场分布：0:53，1:18，2:15，3:17，4:10，5:3，6:4；无 7/9 以上。
- 先验最佳 `g20_chg1_cap_short_off` 5/9：post OKX +64.89%/2.47、Gate +65.35%/2.49（均优于基线），但 post 月份仅 2 好 / 1 差（其余月份未触发），调参期崩（OKX +40.87%/1.10 vs +85.08%/1.47；Gate +41.80%/1.12 vs +84.25%/1.46），Gate 深度 −3.96%/0.06 也略差。安慰剂 −7d / −14d 也是 5/9 且 post 同样 +65%，+14d post 更好（OKX +69.40%/2.61）→ 无时点特异性，post 增益不是 CLI 信息。
- 回退 `g20_chg3_cap_short_off` 0/9：post OKX +55.43%/2.16、Gate +55.53%/2.16（都差于基线），月份 3/6、4/5。
- 6/9 仅非先验 `g7_chg1_short_off` / `g7_trend6_short_off` / `g7_chg3_short_off`（post 期 G7 CLI 一直上行，闸门不触发，post 与基线完全相同、月份 0/0，增益全在 2024 年前，无法样本外验证）与 `chn_z60gt0.5_short_off`（post 崩到 +13.43%/1.07）。g7 邻域 chg2–4 同为 6/9 但 post 依然不触发，chg6 只有 3/9。
- 压力费下结论不变（g7_chg1_short_off post 仍与基线相同）。

## 结论
**否决**。不改代码、不改默认、不加模拟盘。
勿重测：换 N / K / 侧 / 阈值，换 G20↔中国↔G7↔OECD 总体↔欧洲四国，改用 BCI / CCI 等 OECD 其他景气指标，换 OECD 趋势还原 / 正常化口径，或缩短发布时滞。
