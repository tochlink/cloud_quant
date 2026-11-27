# 新兴市场汇率压力趋势 → 4h 默认书入场闸门（已否决，2026-11-27）

- 数据：FRED H.10 DEXMXUS / DEXBZUS / DEXSFUS（美联储官方，USD/MXN, USD/BRL, USD/ZAR）；观测日 +10 天才算已知（H.10 每周一发布，保守）。
- 指数：EM3 = 三币 log(p/p0) 等权均值；MXN = 单币 log。指数 > 自身 n 观测均值 = cap（风险偏好下降）。n∈{50,100,200}；侧：long_off / short_off / both / contra_both；安慰剂：EM3 n100 平移 +180d / −120d。
- 预注册：scratch/emfx_gate4h/PRE_REGISTER.json（sha256 8ef88c7d…eea754），先于任何 PnL。
- 回测：同 fx_jpy_cny 闸门脚本框架；OKX d8、Gate d8、OKX d7_noBNB；深度未见 <2024-10-21、调参期 <2026-03-05、post 至 2026-11-14。
- 结果：无任何变体在深度未见、调参期、post 三段 Sharpe 同时优于基线；post 月数最好 5/9（n200 short_off/both，OKX 与 Gate 均 5 好 4 坏），未达 ≥6/9；contra_both 在 post 全面变差（−1.1～−1.7 Sharpe）；long_off 在 post 无任何作用（0 笔差异）；安慰剂与真实变体同量级。结论：REJECTED，默认与 paper 不变。
- CSV（不入库）：output/research_emfx_stress_gate_4h.csv。勿重测：改 n / 侧 / 币种篮（BRL、ZAR 单币、INR、TRY）或换 H.10 其他汇率。
