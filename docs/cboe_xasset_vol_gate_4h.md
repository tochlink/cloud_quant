# Cboe 跨资产隐含波动率相对值（GVZ/VIX、OVX/VIX、VXN/RVX）4h 默认书入场闸门（长线，已否决）

日期：2026-11-21（PST）。结论：**否决，不实现、不改默认、不加纸面实例。**

## 机制
黄金隐含波动（GVZ）、原油隐含波动（OVX）相对股指波动（VIX）上升，或纳指波动（VXN）相对小盘股波动（RVX）上升，代表“非股票的宏观压力”。经济先验：flag=1 时不开新多仓（只拦新开仓，已有同向持仓不动）。与已测的 VIX 水平/期限结构（vix_term_structure_gate_4h）、CBOE SKEW、VVIX 不同。

## 数据
- Cboe 官方 `cdn.cboe.com/api/global/us_indices/daily_prices/{OVX,GVZ,VXN,RVX,VIX}_History.csv` 日收盘，2009-09-18 → 2026-11-20（OVX/GVZ 各 4319 个交易日，无坏值，无填充；官方缺失日直接丢弃，最大间隔 5 天=节假日）。
- 日线 CSV：output/cboe_xasset_vol_official_daily.csv。D 日收盘 D+1 04:00 UTC 才可用，ffill 到 4h。
- 交易数据：官方 OKX / Gate 永续 4h K 线 + 官方资金费；费用 perp maker 0.02% / taker 0.051%，压力 15.1 bps。

## 格子（看 PnL 前锁定，PRE_REGISTER.json / .csv，sha256 已存）
3 序列（gvzvix=GVZ/VIX、ovxvix=OVX/VIX、vxnrvx=VXN/RVX）× 8 形式（均值趋势 n∈{20,60,120}；n 期变化 n∈{5,20}；252 期 z>k，k∈{0.5,1,1.5}）× 5 侧（long_off、short_off、both、contra_both、cap_short_off）= 120 格 + 同脚本基线（默认 #1 MA50/150 4h）。先验 gvzvix_trend_n60_long_off，回退 ovxvix_trend_n60_long_off。
评分：9 个 Sharpe 切片（OKX d8、Gate d8、OKX d7_noBNB × deep unseen <2024-10-21 / tune / post ≥2026-03-05）；post 月度 ≥6/9 且两所 d8 更好；邻域；时间平移与洗牌安慰剂。

## 结果
基线（OKX d8）：deep +35.14% / Sharpe 0.71，tune +85.08% / 1.47，post +61.54% / 2.27。Gate d8：deep −3.63% / 0.09，tune +84.25% / 1.46，post +61.96% / 2.29。
- 先验 gvzvix_trend_n60_long_off：deep +17.78%（0.47）、tune +55.15%（1.16）均低于基线，不超过 5/9。回退 ovxvix_trend_n60_long_off：deep +14.05%、tune +58.48%、post +49.98%（OKX），同样输。
- 没有任何 9/9 或 7/9；最好两格 8/9，都是非先验且 post 月度不过关：
  - gvzvix_z0.5_long_off：post OKX +62.26% / 2.30 vs +61.54%，Gate +63.14% vs +61.96%（只多 0.7–1.2 点），post 月度 2 好 /2 差（两所均 2/2），不到 ≥6/9。邻域：z0.75 仍 8/9 但 post 边际仅 +1.4 点，z0.25 掉到 6/9（post −24.8 点），z1.0 掉到 6/9（post −7.5 点），不稳定。
  - vxnrvx_z1_cap_short_off：post +67.21%/+68.64%，但 post 月度 OKX 2 好 /6 差，Gate 3/5，d7 1/7，deep 在 Gate 仅 +4.05%（基线 −3.63%）；邻域 z1.5 仅 6/9，且 Gate deep 为负。
- 安慰剂：gvzvix_z0.5_long_off 平移 ±7、+14、−14、+180 天后 post 反而全部低于基线，但 deep 平移 +14d（OKX deep +68.86%）、+7d（+50.96%）比真实格差不多或更好，shift+7d 甚至仍 6/9；洗牌 deep 为负 → 8/9 与噪声难以区分。
- 压力费用（15.1 bps）行已写入 CSV（variant 后缀 __stress），未单独据此改结论。未跑 untuned new8（没有任何格通过月度门槛，不需要）。

## 结论
**否决**。先验与回退都在 deep/tune 输；8/9 的非先验格 post 优势极薄（≤+1.2 点）或月度为负，邻域塌陷，安慰剂能复现。默认不变，不进纸面。

## never retest by
改 n / k / 窗口 / 侧、换成 OVX、GVZ、VXN、RVX、VIX 之间的其它比值或差值、用日内/期限版本（OVX/GVZ 的 VIX9D 类对应物）、或换 token / 换交易所来重试这个“Cboe 跨资产隐含波动率相对值”机制。

CSV：output/research_cboe_xasset_vol_gate_4h.csv（不入库）。脚本：scratch/cboexasset4h/run.py。
