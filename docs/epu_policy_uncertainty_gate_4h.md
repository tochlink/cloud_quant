# 美国日度经济政策不确定性指数（Baker–Bloom–Davis EPU）4h 入场闸门（否决）

## 长线新族：EPU 日度指数 → 4h 默认书入场闸门（2026-11-21 ~13:40 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md、output/research_*.csv、记忆中无 EPU / policy uncertainty 测试；GPR 侧记明确写"若要测 EPU 须单独立项"。不同于已否决的 GPR 地缘、VIX 期限结构、NFCI、净流动性、利率族。
- 机制（看 PnL 前锁定的唯一先验）：Baker–Bloom–Davis（2016 QJE）——政策不确定性高 → 风险偏好下降 → **拦新开多**：`epu7_z365gt1_long_off`（EPU 7 日均的 365 日 z > 1 时不开新多）；回退 `epu30_trend_n180_long_off`。只拦新开仓，持仓、止损、退出不变。
- 数据（仅官方）：https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv 当前 vintage（sha256 0be42a6c…1b69），1985-01-01 → 2026-11-20 共 15,299 天，日历缺口 0，缺失 0，无补数。FRED USEPUINDXD 仅作交叉核对：15,298 天中 19 天不同（全部在最近 30 天，最大差 39.4，是报纸计数修订）。存 `output/epu_official_daily.csv`（不入库）。**滞后**：D 日值从 D+3 天 00:00 UTC 才使用，ffill 到 4h。**注意**：只有当前 vintage，历史回测存在修订前视偏差（只会偏乐观）。
- 格子：序列 epu1（日值）/ epu7 / epu30（7、30 日均）× 形式 z365>0.5/1/1.5/2、`s>SMA90/180`、`s−s[−7/−30]>0` × 侧 long_off / short_off / both / contra_both = **96 格** + 同脚本基线；`PRE_REGISTER.csv` 在任何 PnL 前锁定（sha256 581cb1ae…c8cec3）。harness 同 gpr4h：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续；deep unseen → 2024-10-21，tune → 2026-03-05，post → 2026-11-14；真实费（现货 10 / 永续 taker 5.1 bps），压力 20 / 15.1；官方资金费；安慰剂 ±7 / ±14 / +180 / −120 / +365 / −119 天；邻域；未调参 new8。
- 结果（`output/research_epu_policy_uncertainty_gate_4h.csv` 402 行；`_new8.csv`）：
  - 基线 post：OKX d8 +59.90% / Sharpe 2.23，Gate d8 +60.32% / 2.25，OKX d7 +50.76% / 2.10。
  - 先验 `epu7_z365gt1_long_off`：**1/9**。post 与基线完全相同（月份 0/0，post 期间 z>1 只占 6.3% 且没拦到新多）；tune 段 OKX +85.08%→+43.58%、Gate +84.25%→+43.05%，几乎减半。new8 pre +56.7→+37.1（OKX）、+53.7→+34.1（Gate），post 不变。
  - 回退 `epu30_trend_n180_long_off`：**3/9**，只赢 deep；tune 变差（+85→+72），post 与基线相同。
  - 96 格无 7/9 以上；最好的经济侧格 `epu30_chg_n30_both` 6/9（非先验）：post OKX +65.01%/2.52、Gate +66.04%/2.55，月份 5/3、5/3、4/4（未达 ≥6/9），deep unseen 三个切片全输（OKX −7.29% vs +35.14%，Gate −24.10% vs −3.63%）；new8 post 6/3 但 pre 变差（+56.7→+27.8）；邻域 n21/n14/n60/n5/n3 全部 0–1/9，只有 n45 6/9 → 尖峰。其余 6/9 多为 contra_both，post 大幅变差。
  - 安慰剂：先验平移 +180d / +7d 达 5/9，高于真实先验 1/9。
- 结论：**否决**，不实现、不加模拟盘、不改默认。以后不再通过改 z 阈值 / 窗口 / SMA / chg 长度 / 侧，或换 EPU 子类（税收、货币政策、贸易政策 EPU、Twitter EPU、各国 EPU、WUI）、换月度 EPU 再测这一族。
- 文件：`scratch/epu4h/{build,run,prereg,new8}.py`，`run.log`，`new8.log`。
