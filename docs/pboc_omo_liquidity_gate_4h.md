# 长线新族：中国人民银行官方公开市场业务（逆回购 OMO）净投放 / 余额 → 4h 默认书 #1 入场闸门（2026-11-27 ~20:15 PST，否决）

本文件是 docs/STRATEGY_FORMULAS.md 轮换日志同名一节的独立副本（STRATEGY_FORMULAS.md 超过连接器写入上限，只在本地追加）。

- 查重：`docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`、`scratch/ROTATION_LOCK.txt` 检索 pboc / omo / reverse repo / MLF / shibor / hkma / TSF；本次运行记忆检索工具不可用（已说明）。已有：`shibor_liquidity_gate_4h`（银行间**利率**，其勿重测只禁利率与政策利率利差）、`pboc_tsf_credit_gate_4h`（月度社融）、`pboc_cny_fixing_shock_event_1h`（中间价）、`hkma_interbank_liquidity_gate_4h`。PBoC **公开市场操作量 / 净投放 / 逆回购余额**从未测过。
- 数据（只用官方，不编造、不回补）：PBoC 英文官网「Announcement on Open Market Operations」列表 193 页 1,910 篇公告（2019-03-02 → 2026-11-27，1,848 个公告日，2019 年起；官方英文列表在 2019-04-08→05-13 等处有空档，不补）。逐篇解析逆回购期限与中标量（表格中标量，其次句内量；「不开展」= 0），7 天量与第三方日度库抽查 10 个日期一致。到期 = 操作日 + 期限，顺延到下一个公告日；余额 = 累计投放 − 累计到期（首条公告处为 0，前 60 个观测作为预热丢弃）。**只含逆回购**（MLF / 买断式 / 国债买卖 / 央票 / SLF 不含）。可用时点：公告日次日 00:00 UTC 起。官方日表 `output/pboc_omo_reverse_repo_daily.csv`。
- 公式（看 PnL 前锁定 `scratch/pbocomo4h/PRE_REGISTER.json`，sha256 `56fa112c…`，2026-11-27 19:56 PST，120 格）：flag = 1 表示**流动性收紧**。序列 net20（20 个观测净投放和）、bal（逆回购余额）、inj20（20 个观测投放和）；形式 trend_n{20,60}、chg_n{5,20}、z120lt{0.5,1,1.5,2}；侧 long_off / short_off / both / contra_both / cap_short_off。先验 `net20_trend_n60_long_off`，回退 `bal_chg_n20_long_off`；安慰剂 8 个时移。
- 回测：同脚本默认 #1（双均线 50/150，8 币，官方资金费），OKX d8、Gate d8、OKX d7 不含 BNB；深未见 < 2024-10-21，调参窗 → 2026-03-05，post → 2026-11-14；真实费 taker 5.1 / maker 2 bps，压力费 perp 15.1 / spot 20；未调参 new8。

## 结果（`output/research_pboc_omo_liquidity_gate_4h.csv` 435 行；`_supp.csv`；`_new8.csv`）

| 格子 | 9 段 | 深未见 ret（OKX/Gate/d7） | 调参窗 ret（OKX/Gate） | post 收益 / Sharpe（OKX、Gate）；月份 好/差 |
|---|---|---|---|---|
| 基线 默认 #1 | — | +35.1 / −3.6 / +54.9 | +85.1 / +84.3 | +59.90%/2.23、+60.32%/2.25 |
| **先验 net20_trend_n60_long_off** | 3/9 | +50.4 / +8.2 / +72.8 | +45.8 / +44.1（Sharpe 1.02 / 0.99 vs 1.47 / 1.46） | +44.28%/1.90、+44.90%/1.92；1/3、1/3 |
| **回退 bal_chg_n20_long_off** | 3/9 | +46.6 / +12.7 / +66.3 | +54.6 / +52.9 | +50.18%/2.01、+50.57%/2.03；2/2、2/2 |
| 最高 bal_trend_n60_contra_both（非先验） | 8/9 | +60.8 / −1.5 / +31.6 | +128.3 / +137.3 | +55.29%/2.37、+55.74%/2.38；**4/5、4/5** |
| 次高 net20_trend_n60_cap_short_off（非先验） | 8/9 | +34.1 / −7.7 / +66.0 | +93.3 / +100.4 | +62.43%/2.34、+62.77%/2.35；**3/5、3/6** |

- 先验：深未见三处大胜，但「收紧时不新开多」在 2024-11 后拦掉大量新多，调参窗与 post 全面输（post −15.6 pp），否决；该先验与回退均只 3/9。8 个时移安慰剂最高同为 3/9（−90d）。
- 8/9 两个非先验格都过不了门槛：bal_trend_n60_contra_both post 收益比基线低 11.6 pp（Sharpe 略高 +0.14 / +0.13）、月份 4/5 两所；net20_trend_n60_cap_short_off post 边只有 +2.5 / +2.5 pp，月份 3/5、3/6，压力费下 post +59.31 vs +55.94 / +59.99 vs +56.78 月份仍 3/5。要求 post ≥ 6/9 月更好（两所）→ 不满足。
- 邻域（`_supp.csv`，事后）：net20_trend n30–n120 post 收益 56–60%（≈基线），调参 / 深未见 Sharpe 随 n 起伏；bal_trend n30–n120 post 46–58%（全低于基线）。事后时移安慰剂（±30 / ±90 / +180 / −120d，`_supp.csv`）：net20 −30d 位移的 post 收益 +64.4% / +65.1% 反而高于真实 +62.4% / +62.8%，说明该增益无时点特异。
- new8（未调参，最近 4500 根 4h）：bal_trend_n60_contra_both 是唯一亮点（OKX pre +32.0% vs +29.9%，post +22.8% vs +3.3%、月份 7/2；Gate pre +32.0% vs +27.7%，post +31.5% vs +16.4%、月份 8/1），但 d8 主账本两所月份只有 4/5，且 n50 / n90 邻域 post 收益收缩到 52–53%，n75 回到 58.5%，不是稳定平台。记为**弱观察线索，不实现**，不进纸面。
- 结论：**否决**。不改默认、无代码改动、无纸面变更。逆回购量主要反映日常头寸管理 / 节假日 / 月末，2024 年起央行转向买断式与国债买卖，仅逆回购序列的信息量有限。

## 勿重测（never retest by…）

不要通过改 n / k / z 窗 / 侧 / 滞后重测；不要在净投放 / 余额 / 投放量 / 7 天 / 隔夜 / 14 天等期限拆分之间换序列，也不要加入 MLF、SLF、PSL、买断式逆回购、国债买卖、央票、央行资产负债表月度「货币政策工具投放」表重测同一「PBoC 流动性投放 → 默认 #1 入场闸门」机制。bal_trend_n60_contra_both 的 new8 亮点只能用 2026-11-27 之后前向数据复核，不得据此调参。

## 文件
- `output/research_pboc_omo_liquidity_gate_4h.csv`、`_supp.csv`、`_new8.csv`、`output/pboc_omo_reverse_repo_daily.csv`（不入库）。
- 脚本 `scratch/pbocomo4h/{fetch,parse,build,run,supp,new8}.py`、`PRE_REGISTER.json(.sha256)`、`raw/`（官方公告文本，不推送）。

## 下一轮（短线 1h）
改选尚未做过的官方 CBOE / CME 期权到期日（OpEx）前后 1h 事件（先查重 cboe_* / opex 关键词，若判同机制则换题）。
