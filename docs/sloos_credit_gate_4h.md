# 美联储 SLOOS（高级信贷员调查）C&I 贷款标准 → 4h 默认书入场闸门（长线新族，2026-11-21 ~19:47–20:05 PST）

状态：**否决**。不实现、不加纸面实例、不改默认，仅文档。

## 机制与查重

- 想法：美联储高级信贷员调查（SLOOS）中「收紧 C&I 贷款标准的银行净占比」为正且上升 = 银行信贷收紧 → 风险资产 risk-off → 暂停新开多。
- 查重：`docs/*.md` 中 SLOOS / DRTSCILM 只作为「下一轮」指针出现；`output/research_*.csv` 无 sloos / drtsc / loan-officer 文件。
  已否决的近邻：金融压力 / 信用利差（`financial_stress_credit_gate_4h`）、美国宏观风险体制、联储净流动性、M2、H.6/H.8 现金、H.4.1 外国官方托管、
  住房 / 按揭。SLOOS 是季度银行调查，不是这些序列。不是 ETH 燃烧 / 净发行（2026-11-14 已测）。

## 数据（只用官方，不补缺、不回填）

- FRED 当前 vintage：`DRTSCILM`（大中企业 C&I 标准净收紧 %）、`DRTSCIS`（小企业）、`DRSDCILM`（大中企业 C&I 需求净增强 %）。
  1990-Q2 → 2026-Q4 共 147 个季度点（需求 141 个，1991-Q4 起），季度无缺口。
- **真实发布日**：对 2010-Q3 → 2026-Q4 的 66 个季度，在 ALFRED（`alfredgraph.csv?vintage_date=`）上二分查找每个季度值第一次出现的 vintage；
  并与 federalreserve.gov 各期 SLOOS 页面发布日（2017-04 起 38 期）比对：36 期同日，2 期差 1 天（2021-Q3 Fed 8/3 vs ALFRED 8/2；2026-Q1 Fed 2/2 vs ALFRED 2/3），取两者较晚者。
  **可用时刻 = 发布日 + 1 天 00:00 UTC**（Fed 约 14:00 ET 发布）。发布日距季度首日 29–46 天（中位 34）。
  2010-Q3 之前（ALFRED 无 vintage）用「季度首日 + 3 个月」保守日期，这些点只作滚动历史，不进交易窗口。
- 修订：三条序列 66 个季度首发值 = 当前值（0 修订），无 vintage 前视。最新：2026-Q4（2026-11-02 发布）DRTSCILM 1.7、DRTSCIS 5.1、DRSDCILM −11.7。
- 官方 CSV：`output/sloos_official_quarterly.csv`（含首发值、ALFRED 首发 vintage、Fed 页面发布日、`known_from_utc`；不入库）。
- **样本量**：交易窗口 2022-04 → 2026-11 内只有约 18 次发布（deep 10、tune 6、post 3），flag 体制很长、翻转很少（多数形式 post 期 0–2 次翻转），统计功效很低。

## 公式与预注册（PRE_REGISTER.json 于 2026-11-21 19:47 PST 锁定，sha256 16c9f08b…，先于任何 PnL）

- 序列：tight = DRTSCILM，tights = DRTSCIS，demweak = −DRSDCILM（需求走弱定向为 risk-off）。
- 形式（季度观测上计算）：lvl0（x>0）、lvl20（x>20）、sma4 / sma8（x > SMA(4/8 期)）、chg1 / chg2（x − x[−1/−2] > 0）、lvl0chg1（x>0 且 x − x[−1] > 0）。
- 侧：long_off（flag=1 拦新多）、short_off（flag=0 拦新空）、both、contra_both、cap_short_off（flag=1 拦新空）。只拦新开仓；同向持仓、止损、退出不动。
- 3 × 7 × 5 = **105 格** + 同脚本基线（S.DEFAULTS 默认 4h 书）。
- **唯一先验** `tight_lvl0chg1_long_off`（DRTSCILM > 0 且较上期上升 → 拦新多）；**回退** `tight_lvl0_long_off`。
- harness 同 jgb4h / cboexasset4h：官方 OKX d8（2023-02-01→）/ Gate d8（2022-07-01→）/ OKX d7_noBNB（2022-04-01→）4h 现货 + 永续与官方资金费；
  deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（现货 10 / 永续 taker 5.1、maker 2 bps），压力 20 / 15.1；
  安慰剂：先验与回退的发布时刻平移 ±90 / ±180 / ±365 天 + 5 次打乱（2015 年后 flag 值在发布时刻间随机置换）；邻域；未调参 new8（最近 4500 根 4h）。

## 结果（`output/research_sloos_credit_gate_4h.csv` 462 行；`_new8.csv` 16 行；收益 %，日 Sharpe）

| 组 | 段 | 基线 | 先验 tight_lvl0chg1_long_off | 回退 tight_lvl0_long_off | 非先验最优 tights_chg2_cap_short_off |
| --- | --- | --- | --- | --- | --- |
| OKX d8 | deep | +35.14 / 0.71 | **+58.20 / 1.05** | +21.20 / 0.56 | +21.59 / 0.55 |
| OKX d8 | tune | +85.08 / 1.47 | +48.52 / 1.07 | +41.06 / 0.97 | **+92.73 / 1.65** |
| OKX d8 | post | +59.90 / 2.23 | = 基线（月 0/0） | = 基线（0/0） | **+66.49 / 2.49**（月 2/3） |
| Gate d8 | deep | −3.63 / 0.09 | **+14.54 / 0.34** | −4.98 / 0.03 | −1.81 / 0.09（≈） |
| Gate d8 | tune | +84.25 / 1.46 | +48.16 / 1.06 | +39.37 / 0.94 | **+91.86 / 1.64** |
| Gate d8 | post | +60.32 / 2.25 | = 基线（0/0） | = 基线（0/0） | **+66.96 / 2.50**（月 3/2） |
| OKX d7 | deep | +54.92 / 0.75 | **+68.72 / 0.91** | +32.87 / 0.58 | +32.44 / 0.61 |
| OKX d7 | tune | +92.93 / 1.56 | +50.78 / 1.11 | +50.33 / 1.13 | **+94.64 / 1.68** |
| OKX d7 | post | +50.76 / 2.10 | = 基线 | = 基线 | +58.19 / 2.41（月 3/2） |

- 先验 **3/9**：只赢 deep 三段；tune 收益几乎减半（OKX +85→+49）；post 期间 flag=1 的 2026-05→08 未拦到任何新多，与基线逐位相同。回退 **0/9**。
- 105 格分布：7/9 ×1、6/9 ×3、5/9 ×1，其余 ≤4/9；经济侧（long_off / both）最好只有 4/9。
- 非先验 `tights_chg2_cap_short_off` 7/9：输掉 OKX d8 与 d7 的 deep；post 收益 +6.6 pp / Sharpe +0.26，但 post 月份 OKX 2/3、Gate 3/2（远低于 ≥6/9），
  post 只有 3 次发布；邻域 chg3 = 基线（4/9，post 无差异）、chg4 2/9 → 尖峰。压力费 post OKX +63.36 vs +55.94、Gate +64.24 vs +56.78（月 2/2、5/2）。
  new8：post OKX +7.06 vs +3.26（月 2/1）、Gate +22.03 vs +16.36（4/1），pre 持平。
- 安慰剂：先验最高的平移 −90d 达 4/9 > 真实先验 3/9；其余平移 / 打乱 0–3/9；回退的安慰剂 0–3/9（均 ≥ 真实回退 0/9）。
- new8（未调参）：先验 pre OKX +53.40→+34.31、Gate +50.36→+31.69（变差），post 几乎相同。

## 9 项检查（先验）

deep unseen ✓（3/3）｜tune ✗（0/3）｜post 切分 ✗（与基线相同）｜双所 ✗｜new8 ✗（pre 变差）｜post 月份 ≥6/9 ✗（0/0）｜邻域 —（先验未达观察线，邻域转给非先验最优并断裂）｜
安慰剂 ✗（−90d 4/9 超过真实）｜压力费 —（post 不变）。

## 结论

- **否决**，不改默认、不实现、不加纸面实例。季度 SLOOS 信贷收紧对 4h 默认书没有稳定增量：先验只在 2022–2024 加息周期（deep）有效，
  tune 段反转，post 无信息；唯一 7/9 是非先验 cap_short_off，月份与邻域都不支持。
- 以后**不再**通过改阈值（0 / 20 / 其他）、SMA / chg 长度、侧，或换 SLOOS 子序列（小企业 / CRE / 消费贷 / 信用卡 / 住房按揭标准、需求、利差、
  抵押要求、额外问题）、换欧洲 BLS / 日本 / 英国信贷调查、或改发布滞后重测这一族。

- 下一轮（短线）：已知政府 / 破产托管 BTC 地址（Mt.Gox 受托人冷钱包、美国政府 USMS / 司法部没收地址、德国 BKA 地址，地址以法院文件 / 官方公告为准）链上大额转出（尤其转向交易所入金地址）→ 8 币永续篮子 1h 事件（顺势 / 逆势，H 数小时–2 天），数据只用比特币链上官方区块数据（自建节点或 mempool.space / blockstream 公共区块 API），出块时间 + 1 根 1h 后才可用。查重：docs/*.md、`output/research_*.csv`、scratch 目录中 Mt.Gox / 政府钱包 / BKA / USMS / trustee 0 命中；不是已否决的交易所稳定币流、CoinMetrics 交易所供给流、平均成交规模「鲸鱼」15m、BTC CDD 休眠币。事件数可能偏少（2024 年为主），须如实标注。

## 文件

- `scratch/sloos4h/{alfred_probe,build,run,new8,summ,plog}.py`、`PRE_REGISTER.json`、`run.log`、`new8.log`（研究脚本不推送）。
