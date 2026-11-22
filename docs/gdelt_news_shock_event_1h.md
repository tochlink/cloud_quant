# GDELT 官方 GKG 加密新闻覆盖度 / 情绪 1h 冲击 → 8 永续篮子（否决；不改默认、不入纸面）

## 短线新族：GDELT 2.0 GKG 加密新闻占比 / 篇数 / 情绪 1h 冲击事件（2026-11-22 ~15:15 PST，研究，否决）

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（1,197 个）、scratch 检索 gdelt / news volume / news tone / 新闻：0 命中。不同于已否决的 Wikipedia 浏览量注意力、Fear&Greed 1h、Polymarket 概率跳变、币安上下架公告、多空比情绪闸门。
- 数据（只用官方，不编造、不回补）：GDELT DOC 2.0 API 从本机每次都返回 HTTP 429，因此改用同一语料的官方原始 GKG 2.1 15 分钟文件（`https://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip`，按官方 masterfilelist.txt 枚举），2022-02-01 → 2026-11-22 18:00 UTC：166,612 个文件可读、91 个官方缺失、0 个失败；合成 **42,139 个 UTC 小时，其中 41,617 个有效**（4 个 15 分钟文件齐全才算有效，否则记 NaN，不插值）。每个文件：`n_total` = 记录数，`n_kw` = 整行匹配 `bitcoin|cryptocurrenc|crypto|ethereum` 的记录数，`tone` = 这些记录 V2Tone[0] 的均值（n_kw < 5 记 NaN）。时序表存 `output/gdelt_crypto_news_official_1h.csv`（不入库）。
- 发布滞后：已核对官方 Last-Modified，文件 T 约在 T−10~12 分钟发布 → 第 h 小时的数据约在 h:38 UTC 前齐全；在 h+1:00 的永续开盘入场，余量至少 20 分钟。
- 序列：`cov_share = ln(n_kw / n_total)`；`cov_raw = ln(1 + n_kw)`；`tone`。
- 信号：L=1 时 `z = (x − μ)/σ`；L>1 时 `z = (Σ_L x − Lμ)/(σ√L)`；μ、σ 取到 t−1 为止的 168h 滚动窗口（至少 84 个点）。high 侧 z ≥ k，low 侧 z ≤ −k。在信号小时收盘后的下一根 1h 永续开盘入场，事件之间不重叠，等权 8 永续篮子（OKX d8、未调参的 new8、Gate d8），持有 H 小时。
- 网格（看 PnL 前锁定在 `scratch/gdeltnews1h/PRE_REGISTER.json`，sha256 `609126b28081d8e0ea042ea39af3b0adf70db51ba3f4591bf2127bb6640d3d56`）：3 个序列 × L{1,4,8} × k{3,4,5} × 2 个触发侧 × 多/空 × H{6,12,24,48} = **432 格**。真实费 = 2×吃单 5.1 bps + 官方资金费；压力费用 15.1 bps。安慰剂：信号平移 ±168h、±720h。分段：train 2022-02-15→2024-10-21（深度未见）、test →2026-03-05、post →末尾；Gate 官方 1h 只从 2025-09-24 开始。
- 先验（锁定）cov_share L4 k3 high short H24（加密新闻占比 4h 内暴涨 = 散户注意力见顶 → 次日拥挤仓位出清）：**只有 5/8 个分段为正**。OKX d8 在 train 上 −12.1 bps、test 上 −49.1、post 上 +33.1（t 1.04，67 个事件），Gate post +32.6；压力费下 train −32、test −69。邻域不稳（L4 k5 的 post −30.7；H6 全负）。安慰剂 −168h 在 test 上 +81，比真实信号还高。
- 后备（锁定）tone L4 k3 low long H24（新闻情绪极端负面 → 逆向反弹）：7/8 个分段为正，但幅度很薄，t 都 ≤ 0.53（train +15.6、test +22.0、post +17.1、Gate post +17.8，52 个事件）。压力费下 post −2.9、Gate gate_window −20.5，转负。安慰剂 +720h 的 post +11.9，和真实信号相近。
- 探索：432 格中只有 11 格 8/8 可用（约 2.5%），全部不是先验格。最好的 tone L4 k4 low long：H24 时 train +90.1 / test +72.0 / post +89.3 / Gate post +89.6 bps，post t 只有 1.5（26 个事件）；H48 时 post +139 bps，t 1.4。它在 post 上能赢过四个安慰剂，压力费下也为正，但 **test 段被 +168h 安慰剂超过**（H24：102 > 72；H48：169 > 85）；从 432 格里挑出来的、post t < 2、事件太少，达不到强观察标准（post t ≥ 2、赢过全部安慰剂、邻域稳定）。
- 结论：**否决**。不改默认，不加纸面盘。以后不要靠改 L、k、H、触发侧或方向，或换 cov_share / cov_raw / tone、换关键词表或 GDELT 主题（ECON_BITCOIN），或改用 DOC API 时间线，再测这一族。
- 结果表：`output/research_gdelt_news_shock_event_1h.csv`（24,192 行，CSV）；脚本 `scratch/gdeltnews1h/{fetch,build,run,analyze}.py`。
