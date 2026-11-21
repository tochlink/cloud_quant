# 地磁活动（GFZ Kp/ap）4h 入场闸门（否决）

## 长线新族：GFZ 官方地磁活动（Kp / ap 指数）→ 4h 默认书入场闸门（2026-11-20 ~23:20 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md 对「地磁 / geomagnetic / Kp / sunspot / 太阳 / 月相 / lunar / NASA / NOAA / 天文 / 地震 / 天气」无相关条目，output/research_*.csv（1,027 个）无 geomag / solar / lunar 命名，记忆中无空间天气条目；也不属于任何链上、宏观、成交量、日历、维基关注度、期权族。已避开的方向：任何美国宏观 / 利率 / 国债 / Fed 序列，已测链上族，交易所保险基金（无历史）。
- 机制：行为金融里的「地磁风暴情绪」渠道（Krivelyova–Robotti 2003：强地磁活动后股市收益偏低）——高地磁活动 → 风险偏好下降 → 拦新开多（先验侧 long_off / both）。只拦新开仓，已持仓、止损、退出、再平衡不变。
- 数据（仅官方）：GFZ 波茨坦亥姆霍兹中心 `Kp_ap_Ap_SN_F107_since_1932.txt`（https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt），日度 Ap 与 3h Kp 最大值；1932-01-01 → 2026-11-20 共 34,658 天，日历缺口 0，无负值 / 缺失；用 1990-01-01 起 13,473 天，存 `output/geomag_kp_ap_official_daily.csv`（不入库）。D 日值保守按 D+2 天 00:00 UTC 才可用（避开 nowcast→definitive 修订），再 ffill 到 4h。
- 公式：序列 ap1 = 日 Ap、ap3 = 3 日均、ap7 = 7 日均；形式 z365>k（k 0.5/1.0/1.5/2.0）、`s > SMA(n)`（n 90/180）、`s − s[−n] > 0`（n 7/27）；侧 long_off / short_off / both / contra_both / cap_short_off。3 × 8 × 5 = 120 格 + 同脚本基线，PRE_REGISTER.json 在任何 PnL 前锁定；先验侧 long_off / both，回退 ap3_z365gt1_long_off。回测沿用 kwtp4h 同一 harness（OKX d8 / Gate d8 / OKX d7_noBNB；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费 10 / 5.1 bps，压力 20 / 15.1，官方资金费率；安慰剂 ±7 / ±14 / +180 / −120 / +365 / −119 天；邻域；未调参 new8）。
- 结果（CSV `output/research_geomagnetic_activity_gate_4h.csv`，441 行；`_new8.csv`）：
  - 先验最好 `ap7_trend_n90_long_off`（7 日均 Ap 高于 90 日均则拦新多）9 格中 7/9，但**几乎没有效应**：post OKX +58.78 / 2.20 vs 基线 +59.90 / 2.23（月份 1 好 / 3 差），Gate +59.40 / 2.23 vs +60.32 / 2.25（1/3），d7 +53.19 vs +50.76（2/2）；压力费同样略差（OKX +55.11 vs +55.94，Gate +55.42 vs +56.78）。deep 小幅更好（OKX 0.79 vs 0.71，Gate 0.23 vs 0.09）、tune 1.51 / 1.48 vs 1.47 / 1.46，属噪声级，收益差不到 1.2 点，post 月份不到 6/9。
  - 安慰剂：+7 天 OKX deep Sharpe 1.23、Gate 0.76 全面高于真实；−7 天 post 与基线几乎相同；真实并不优于平移 → 信号不特异。
  - 先验回退 `ap3_z365gt1_long_off` post 与基线完全相同（闸门空转，月份 0 / 0）；其余 long_off / both 格 ≤ 6/9 且 post 差异 ≈ 0。
  - 非先验（short_off / both 反向高活动放行）`ap7_trend_n180_short_off`：post 很好（OKX +71.46 / 2.59，Gate +72.56 / 2.62，月份 4/4、5/3），tune 也更好（104.97 / 113.97），但 **deep 被打穿**（OKX +2.88 / 0.19 vs +35.14 / 0.71，Gate −23.29 / −0.32 vs −3.63 / 0.09），邻域 n60–365 同样 deep 为负；属 2026 单段巧合，非先验、不可晋升。
  - 未调参 new8：先验格 post 好看（OKX +14.98 / 1.01 vs +3.26 / 0.28，Gate +30.58 / 1.66 vs +16.36 / 1.00，月份 4/0）但 d8 主账本与 d7 不复现，且 post 只有 9 个月、新币样本小，不能单独采信。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动，仅文档。地磁活动对 4h 趋势账本无增量。勿以同一机制换 n / k / 方向、换 Ap / Kp / Dst / AE 指数、换太阳黑子数 / F10.7 / 太阳风、换月相或其他天文周期再测。
- 下一轮（短线，非宏观）：官方 OKX / Gate 1h K 线上「整点 / 半点 / 资金费率结算前后 N 分钟」之外的新信息——跨币种 1h 收益的横截面离散度（dispersion）骤降 / 骤升（所有币同涨同跌）作为 8 币篮子 1h 事件；先查重 intraday_jump_share、basket_volume_shock、breadth 条目。
- 脚本 `scratch/geomag4h/{build,run,supp,new8}.py`、`PRE_REGISTER.json`（研究脚本未推送）。默认策略与纸面实例均未改动。
