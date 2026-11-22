# 中国在岸银行间流动性（CFETS 官方 SHIBOR / FDR007 回购定盘）→ 4h 默认书入场闸门（否决；不改默认、不入纸面）

## 长线新族：SHIBOR 隔夜 / 1W / 3M−隔夜利差 与 FDR007 作为 4h 默认书入场闸门（2026-11-22 ~15:20–15:50 PST，研究，不改默认；否决）

- 查重：`docs/`、`output/` 中 SHIBOR / DR007 / FR007 / FDR007 零命中（研究前已确认）。不是已测的人民币中间价、LPR / MLF、CNH、HIBOR / HKMA、SNB 活期存款、TGA、STLFSI、美国 Fed 流动性等族；本族是人民币在岸银行间货币市场利率（CFETS SHIBOR 与存款类机构 7 天回购定盘 FDR007）。
- 机制：银行间利率上升 / 异常偏高 = 央行收紧流动性 / 季末资金紧张 = risk-off。先验：流动性收紧时拦新多。只拦新开仓，已有持仓、止损、离场不变。默认 4h 书（#1 双均线 50/150，8 币永续）。
- 数据（只用官方，不编造、不回补、不插值）：CFETS 中国货币网 `https://www.chinamoney.com.cn/ags/ms/cm-u-bk-shibor/ShiborHis`（8 个期限 O/N…1Y）与 `https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/FrrHis`（FR001/FR007/FR014/FDR001/FDR007/FDR014），按自然年分块（官网单次最多一年）。2016-01-04 → 2026-11-20，**2,714 个中国工作日**（含调休周六），两套日期完全一致，SHIBOR / FR 0 缺值；FDR 系列 2017-05-31 才上线，之前官网为 `---`（350 行，丢弃不填）。唯一 >10 自然日的间隔是 2020-01-23 → 2020-02-03（官方延长春节假期），非数据缺口。最新 2026-11-20：O/N 1.2612、1W 1.3620、3M 1.4000、FDR007 1.37。存 `output/shibor_official_daily.csv`、`output/cfets_repo_fixing_official_daily.csv`（不入库）；原始 JSON 在 `scratch/shibor4h/raw/`。
- 滞后：北京 11:00（03:00 UTC）发布；保守按**当日 08:00 UTC 4h 开盘**才可用，前向填充到 4h K 线。
- 公式（看 PnL 前写入 `scratch/shibor4h/PRE_REGISTER.json` 锁定，sha256 `ce5899be8cb10a06fa135b1ac9a3b5be34d08daffa5b6c0ffad049c94c237af6`；同目录 `PRE_REGISTER.sha256` 另记 run.py / fetch.py / 两个日度 CSV 的 sha。说明：首次锁定后 run.py 在导入时因 FDR `---` 解析报错（尚未算任何 PnL），改为 `to_numeric(errors=coerce)` 后重新锁定；之后又只改了 locked_at 文本里的时区（盒子时钟为 Asia/Shanghai，改成 PST），网格 / 代码未变。共 120 格）：
  - 序列（flag=1 一律 = 收紧）：`w1` = 1W SHIBOR、`on` = O/N SHIBOR、`m3on` = 3M SHIBOR − O/N SHIBOR、`fdr7` = FDR007。
  - 形式：`chg`：s − s.shift(n 个营业日) > 0，n 20 / 60 / 120；`z`：(s − SMA_n) / STD_n > 1，n 20 / 60 / 120。
  - 侧：long_off（收紧拦新多）/ short_off（宽松拦新空）/ both / contra_both（收紧拦新空、宽松拦新多）/ tight_short_off（收紧拦新空）。4 × 6 × 5 = 120 格 + 同脚本基线。
  - 先验格（锁定）：`w1_z60gt1_long_off`（1W SHIBOR 60 营业日水平 z>1 拦新多），兼作安慰剂锚；回退 `w1_chg_n60_long_off`；long_off / both 作为经济先验侧统计。
- 验证：与 SNB / HKMA 闸门同一框架（OKX d8 2023-02→ / Gate d8 2022-07→ / OKX d7_noBNB 2022-04→，官方永续 + 现货 4h、官方资金费；真实费率永续 maker 2 / taker 5.1 bps，压力永续 15.1 / 现货 20 bps；深未见 →2024-10-21、调参段 →2026-03-05、post →2026-11-14；安慰剂日历平移 +7 / −7 / +14 / −14 / +180 / −120 / +365 / −119 天；邻域 n 10 / 30 / 40 / 90 / 150 / 250（z 另加 k 0.5 / 1.5 / 2）+ 锚上换序列；new8 未调参币 OKX + Gate 最近 4500 根 4h）。
- 默认门槛：深未见 + 调参段 Sharpe 两所都胜，且 post（2026-03-05 后）两所 ≥ 6/9 月更好，并有安慰剂 + 邻域支持。
- 结果（`output/research_shibor_liquidity_gate_4h.csv` 453 行；收益 % / Sharpe，真实费率）：

| 账本 | 格 | 深未见 | 调参段 | post | post 月 好/差 |
|---|---|---|---|---|---|
| OKX d8 | 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | — |
| OKX d8 | 先验 w1_z60gt1_long_off（3/9） | +19.98 / 0.49 | +85.94 / 1.47 | +52.35 / 2.01 | 1/2 |
| OKX d8 | 回退 w1_chg_n60_long_off（3/9） | +12.83 / 0.39 | +98.10 / 1.61 | +50.48 / 2.06 | 1/3 |
| OKX d8 | 非先验 on_z60gt1_tight_short_off（9/9） | +35.41 / 0.72 | +95.24 / 1.60 | +61.79 / 2.29 | 3/4 |
| OKX d8 | 非先验 on_z120gt1_tight_short_off（8/9） | +35.52 / 0.72 | +92.23 / 1.56 | +64.15 / 2.36 | 4/2 |
| Gate d8 | 基线 | −3.63 / 0.09 | +84.25 / 1.46 | +60.32 / 2.25 | — |
| Gate d8 | 先验 | −16.05 / −0.11 | +84.95 / 1.46 | +52.95 / 2.03 | 0/3 |
| Gate d8 | 回退 | −3.77 / 0.08 | +97.39 / 1.60 | +51.21 / 2.09 | 2/2 |
| Gate d8 | on_z60gt1_tight_short_off | −0.94 / 0.13 | +89.37 / 1.55 | +62.29 / 2.31 | 4/3 |
| Gate d8 | on_z120gt1_tight_short_off | −2.75 / 0.10 | +90.70 / 1.54 | +64.91 / 2.38 | 4/2 |
| OKX d7_noBNB | 基线 | +54.92 / 0.75 | +92.93 / 1.56 | +50.76 / 2.10 | — |
| OKX d7_noBNB | 先验 | +39.05 / 0.60 | +95.34 / 1.58 | +43.21 / 1.85 | 1/2 |
| OKX d7_noBNB | 回退 | +46.38 / 0.68 | +103.10 / 1.67 | +44.53 / 1.95 | 1/3 |
| OKX d7_noBNB | on_z60gt1_tight_short_off | +56.27 / 0.76 | +96.28 / 1.63 | +53.34 / 2.19 | 3/3 |
| OKX d7_noBNB | on_z120gt1_tight_short_off | +54.20 / 0.75 | +92.77 / 1.58 | +55.14 / 2.25 | 4/2 |

  - 9 切片 Sharpe 胜数分布（120 格）：0/9 18、1/9 15、2/9 6、3/9 48、4/9 9、5/9 7、6/9 10、7/9 3、8/9 3、9/9 1。经济先验侧（long_off / both，48 格）：0/9 6、1/9 7、2/9 1、3/9 20、4/9 5、5/9 3、6/9 6，**无 7/9+**。所有 7/9 以上都是 tight_short_off（收紧拦新空，与先验方向相反）。
  - 先验 w1_z60gt1_long_off 3/9：深未见三套全输（OKX 0.49 vs 0.71、Gate −0.11 vs 0.09），post 三套都输 −7.5 pp / Sharpe −0.22，月 1/2、0/3。回退 3/9 同形态（调参段胜，深未见 / post 输）。
  - 7/9 的 w1_z60 / fdr7_z60 / fdr7_z120 tight_short_off 在 post 几乎不触发（post +59.64 / +59.90 ≈ 基线）。
  - 压力费率：on_z60gt1_tight_short_off OKX 深未见 +24.79/0.57 vs +24.67/0.56、调参段 +85.40/1.50 vs +75.18/1.35、post +58.18/2.19 vs +55.94/2.12（月 3/4）；Gate −11.37/−0.03 vs −13.77/−0.07、+79.46/1.44 vs +74.07/1.34、+58.95/2.22 vs +56.78/2.15（4/3）。on_z120 压力 post OKX +60.88/2.27、Gate +61.08/2.28（月 4/2）。先验压力 post +48.96 / +49.42（输）。
- 安慰剂（先验锚 w1_z60gt1_long_off，主 CSV）：+7d 6、−7d 3、+14d 6、−14d 5、+180d 3、−120d 2、+365d 3、−119d 0；**最好 6/9 > 真实 3/9**（平移后 post 段闸门不触发 = 基线）。
- 安慰剂（on_z60gt1_tight_short_off，`_supp.csv`）：+7d 1、**−7d 9/9**（post OKX +60.99 / Gate +61.77，月 4/3、4/3）、+14d 3、−14d 5、+180d 6、−120d 4、+365d 6、−119d 3 → 最大 9/9 = 真实，post 微弱优势不是 SHIBOR 时点特有的。on_z120gt1_tight_short_off 安慰剂：3 / 5 / 3 / 3 / 6 / 2 / 3 / 3，最大 6/9（+180d）。
- 邻域（on_z60gt1_tight_short_off，主 CSV）：z 窗口 n=10/30/40/90/150/250 胜数 9/6/9/8/7/7，k=0.5/1.5/2 胜数 6/8/6；但 n=30 post 崩到 +34.50 / +35.15（月 1/7），其余 post 边 OKX +1.4~+7.3 pp（k=2 不触发 = 基线），月份最好 5/3（n=10、k=0.5）——**没有任何邻居达到 6/9 月**。换序列：w1 7/9（post ≈ 基线）、fdr7 7/9（≈ 基线）、m3on 3/9（post +38.02）。
- 邻域（先验 w1_z60gt1_long_off，`_supp.csv`）：n=10/30/40/90/150/250 胜数 5/3/1/3/4/2，k=0.5/1.5/2 胜数 5/3/1；post 全部 ≤ 基线（+52.35 或 +56.35，或不触发 = 基线）。回退 w1_chg 邻域 n=10/30/40/90/150/250 胜数 5/6/6/3/5/3，post +39.08~+52.35 或 = 基线，全部不胜。
- new8 未调参（最近 4500 根 4h，2024-11-27→，`_new8.csv`）：基线 OKX pre +47.85/1.00、post +3.26/0.28，Gate pre +44.99/0.97、post +16.36/1.00。先验 post = 基线（不触发），pre +51.27 / +48.25。on_z60gt1_tight_short_off：OKX pre +37.67/0.86（输）、post +7.10/0.52（月 6/1）；Gate pre +39.75/0.90（输）、post +16.08/0.99（输，3/3）。on_z120：OKX post +1.86/0.19（输）、Gate +15.26/0.96（输）。回退 w1_chg_n60_long_off 在 new8 反而两所 pre / post 都胜（OKX post +15.21/0.95，Gate +30.45/1.56，月 3/1、2/2），但它在 d8 主书三套 post 都输（3/9），不采纳。+14d 平移安慰剂 post −0.37 / +13.46。
- 当前信号（数据到 2026-11-20，08:00 UTC 起可用）：1W z60 = −0.40（先验 flag=0，不拦）、1W 60 日变化 −0.07 pp（回退 flag=0）、O/N z60 = −1.25、z120 = −1.85（tight_short_off flag=0，不拦）。仅供记录，不进纸面。
- 结论：**否决**（不改默认、不入纸面、不加代码）。先验 w1_z60gt1_long_off 与回退都只有 3/9（深未见、post 都输），弱于自身平移安慰剂（最多 6/9）。唯一 9/9 on_z60gt1_tight_short_off 是非先验、与经济先验方向相反，post 边只有 OKX +1.89 pp / Sharpe +0.06、Gate +1.97 pp / +0.06，月 3/4、4/3（远低于 6/9），深未见几乎不变，−7d 平移安慰剂同样 9/9，邻域 n=30 崩、无一邻居过月份门槛，new8 Gate post 与两所 pre 都输；8/9 on_z120 月 4/2、new8 两所 post 都输。不满足默认门槛，也不够强观察。
- 勿重测：不要通过改 n（10~250 营业日）、z 阈值 k、方向 / 侧、滞后（当日 04:00 / 08:00 / 次日），换期限（O/N / 1W / 2W / 1M / 3M / 6M / 9M / 1Y）或期限利差（3M−O/N、1W−O/N、1Y−3M 等），换 FR001 / FR007 / FR014 / FDR001 / FDR007 / FDR014 / DR007 / R007 / GC007 等回购利率或其与政策利率（7 天逆回购、MLF、LPR）之差，换水平 / 变化 / z / 百分位 / 季末哑变量的方式重测本族；也不要改成 1h「SHIBOR / 回购定盘 11:00 发布」事件来绕过本条。
- CSV：`output/research_shibor_liquidity_gate_4h.csv`（主网格 + 先验安慰剂 + on_z60 邻域 + STRESS，453 行）、`output/research_shibor_liquidity_gate_4h_supp.csv`（先验 / 回退邻域 + on_z60 / on_z120 安慰剂，108 行）、`output/research_shibor_liquidity_gate_4h_new8.csv`（new8 未调参，32 行）、`output/shibor_official_daily.csv`、`output/cfets_repo_fixing_official_daily.csv`（官方日度，不入库）；脚本 `scratch/shibor4h/fetch.py`、`run.py`、`supp.py`、`new8.py`。
