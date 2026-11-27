# 长线新族：Cboe 官方美股期权成交活跃度（投机活跃周期）→ 4h 默认书 #1 入场闸门（2026-11-27 ~07:40 PST，研究，不改默认；否决）

## 查重 / 换题
- 任务候选（a）恒生指数 / 恒生科技趋势：**没有官方全历史，放弃**。hsi.com.hk INdex360 `valueHistory` 接口要 SSO 登录（401）；公开 dailyReport 只列最近约 40 个交易日的 `idx_*.csv`，更早文件取回为空；HKMA `capital-market-statistics` API（月末恒指）只返回最近 15 个月；data.gov.hk 历史存档 0 个版本。（b）Brent 与已否决 WTI 同族，不做。
- rg `options volume / 期权成交量 / 期权总成交 / call volume / 认购成交 / options activity / 0DTE / OCC / speculat` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv` 文件名、scratch、`ROTATION_LOCK.txt`：无「期权成交活跃度水平」测试。不同于已否决 `cboe_putcall_ratio_gate_4h`（认沽/认购**比值**情绪；其勿重测只覆盖各种 P/C 比值互换）、Cboe SKEW、VIX 期限结构、跨资产隐含波动、Deribit 偏斜 / PCR、美股指数趋势（价格）、美股 IPO、FINRA 保证金。

## 机制与公式（看 PnL 前锁定）
- 美股挂牌期权投机活跃周期（散户买认购 / 0DTE 热潮 vs 活跃度退潮）：活跃升温 = 投机 risk-on → 有利加密多头；退潮 = 不利。
- `a = MA_s(log X) − MA_L(log X)`（只在官方交易日上滚动），flag = 1（热）当 a > k，k = 0。
- 序列 X：`eqc` Cboe 股票期权**认购**合约数；`eqt` 股票期权合约数（认购 + 认沽）；`tot` Cboe 全部期权合约数。
- 形式 (s, L) ∈ {(20,120), (20,250), (60,250)}；侧：long_off（冷时不开新多）/ cap_short_off（热时不开新空）/ both / contra_both（反向）。只拦新开仓，已有同向仓位、止损、出场不变。
- 3 × 3 × 4 = **36 格**；`scratch/cboeact4h/PRE_REGISTER.json` 2026-11-27 07:40 PST 锁定，sha256 `af7ac02f00b381c7…d9c72f`（run.py sha 同目录 `PRE_REGISTER.sha256`）。先验 `eqc_s20_L250_both`；回退 `eqt_s20_L250_long_off`。

## 数据（只用官方，不编造、不回补）
- 信号：Cboe 官方每日市场统计 JSON `cdn.cboe.com/data/us/options/market_statistics/daily/YYYY-MM-DD_daily_options`（已解析于 `output/cboe_putcall_official_daily.csv`），1,793 个美股交易日 2019-10-07 → 2026-11-20；2025-01-09（国葬休市，股票期权 0）记 NaN 丢弃。D 日 **D+1 12:00 UTC** 才使用，前向填充到 4h。
- 交易：官方 OKX d8（2023-02→）/ Gate d8（2022-07→）/ OKX d7_noBNB（2022-04→）4h 永续 + 现货信号，官方资金费；默认参数 = 生产回测；同脚本基线。分段 deep_unseen < 2024-10-21、tune 2024-10-21 → 2026-03-05、post 2026-03-05 → 2026-11-23。真实费：永续 maker 2 / taker 5.1 bps；压力：现货 taker 20 / 永续 taker 15.1 bps。
- 占用率（flag=1 比例，deep / tune / post）：eqc s20L250 0.51 / 0.90 / 0.67；eqt s20L250 0.53 / 0.91 / 0.85；tot s20L250 0.84 / 0.89 / **0.96**。

## 结果（`output/research_cboe_options_activity_gate_4h.csv` 213 行；`_months.csv`；`_new8.csv`）
收益 % / 日 Sharpe：

| 格 | OKX d8 deep | OKX d8 tune | OKX d8 post | Gate d8 deep | Gate d8 post | d7 post | 9 切片 | post 月胜/负（OKX/Gate） |
|---|---|---|---|---|---|---|---|---|
| 基线 | +35.14 / 0.71 | +85.08 / 1.47 | +72.98 / 2.49 | −4.32 / 0.08 | +73.40 / 2.51 | +60.96 / 2.34 | — | — |
| 先验 eqc_s20_L250_both | −21.30 / −0.51 | +79.69 / 1.60 | +20.54 / 1.31 | −34.94 / −0.73 | +20.53 / 1.32 | +11.11 / 0.83 | 3/9 | 3/5、3/5 |
| 回退 eqt_s20_L250_long_off | +12.12 / 0.37 | +84.66 / 1.46 | +60.89 / 2.21 | −9.88 / −0.02 | +61.55 / 2.23 | +51.48 / 2.02 | 0/9 | 0/4、0/4 |
| 最佳 tot_s20_L250_long_off（非先验） | +48.88 / 0.91 | +87.64 / 1.50 | = 基线 | +3.68 / 0.20 | = 基线 | = 基线 | 6/9 | 0/0、0/0（post 从不触发） |

- 先验在 2026-06 一个月就比基线少 −24.9 pp（OKX / Gate 同），5、8、10 月也输。
- 安慰剂（锚 tot_s20_L250_long_off，3 套胜数合计）：平移 +30d 6、−30d 6、+60d 2、−60d 6、+180d 3、−120d 3、+365d 4、−365d 3；30 天块洗牌 shuf1 3、shuf2–5 **都是 6/9**——真实格不优于安慰剂。
- 邻域：s10 5/9（post −9.8 pp）、s40 2/9、L180 6/9（post −11.6 pp）、L500 3/9、k−0.05 6/9、k+0.05 3/9（post −11.6 pp）。
- 压力费：最佳格 OKX d8 deep +37.60 / 0.76 vs 基线 +24.67 / 0.56，post 同基线；不改变结论。
- new8 未调参（最近 4500 根 4h，2024-12-02→）：基线 OKX pre +32.45 / 0.79、post +11.64 / 0.78，Gate +30.15 / 0.77、+25.69 / 1.39。先验 pre 崩（OKX +2.12 / 0.20、Gate +0.62 / 0.16），post 较好（+27.1 / 1.88、+27.4 / 1.90，月 5/4）；回退 pre 平、post 好（OKX +19.09、Gate +34.93，月 3/1）；最佳格 post 略输（0/1）。

## 结论
**否决**：不改默认、不进纸面、无代码改动。经济先验 3/9，deep 与 post 大幅输给基线；回退 0/9；唯一 6/9 是非先验 tot_s20_L250_long_off，只在 deep/tune 小幅改善，post 从不触发（Cboe 总成交 2026 年一直在 250 日均线上方），无法满足 post ≥6/9 月份，而且 13 个安慰剂中 9 个同样 6/9。

## 勿重测（never retest by …）
不要通过改 s / L / k / z 窗口 / 侧 / 方向、在股票认购 / 股票合计 / 指数 / ETP / VIX / 全部期权成交量之间互换、改用名义成交额 / 权利金 / 未平仓量 / OCC 清算总量 / 单个交易所（C1/C2/BZX/EDGX）成交量、改用 0DTE 或 SPX 周期权成交占比、或把成交活跃度换成 1h「期权成交冲击」事件的方式重测本族。

## 文件
- 脚本 `scratch/cboeact4h/{run,new8,months,plog}.py`、`PRE_REGISTER.json`、`run.log`、`new8.log`（研究脚本不推送）。
- 下一轮（短线）：Solana 官方主网 pump.fun 程序新币创建（Create 指令）每小时爆发 → 8 币永续篮子 1h 事件（rg pump.fun / pumpfun / memecoin launch 先查重；pump.fun 2024-01 才上线，须确认官方 RPC 可回溯且 train 段够长，否则换题）。Cboe 期权成交量 1h 冲击已被本条禁止，勿选。
