# 短线新族：美股（NYSE）全日休市假日窗口 → 8 币永续篮子 1h 事件（节前效应 / 休市漂移 / 复市回补，2026-11-23 ~05:35–05:45 PST，研究，不改默认；否决）

状态：先验 `prehol_day long H24 all` **否决**（2/8）；备选 `last_close long H48 all` **否决**（7/8，但 test 低于同脚本基线）；唯一 8/8 非先验格 `hol0 long H48 all` 边际极薄、被平移安慰剂淹没 → **不进观察**。不实现、无代码改动、不改默认、模拟盘不变；live 关，8790/8791 未触碰。

## 选题与查重

- rg `holiday / 节假日 / 假日 / 休市 / Thanksgiving / 感恩节 / Christmas / 圣诞 / pre-holiday` 于 `docs/STRATEGY_FORMULAS.md`、`docs/*.md`、`output/research_*.csv`（约 1,280 个）与 scratch 目录名：只有美股类永续「休市跳空」（每个交易日隔夜，剔除假日）、CME 周末缺口、日历（星期 / 月末 / 到期）闸门、日内时段季节性；**从未把 NYSE 全日休市假日本身做成事件**。记忆检索工具本次不可用（无已安装的 memory 连接器），以文档 / CSV / scratch 查重为准。
- 不同于已否决的 CME 周末缺口（周末、以 CME 缺口方向为信号），本族是无条件方向的假日日历窗口（每年约 9–10 次，单笔持有 12–48h，结构上每笔波动远大于 10 bps 往返费）。

## 数据（只用官方，不补、不插值）

- NYSE 全日休市：SPDR Gold Shares 官方历史档案（`GLD_US_archive`，NYSE Arca 上市 ETF，休市日整行标 `US Holiday`），取工作日 2021-12-24 → 2026-09-07；2026 年 8 个休市日与 nyse.com「Holidays & Trading Hours」官方表逐日一致；另加 nyse.com 前瞻 2026-11-26 / 2026-12-25（尚无 PnL）。含 2025-01-09（卡特国葬）。共 51 个日期 → `scratch/usholiday1h/us_nyse_holidays_official.csv`。
- 行情：官方 OKX USDT 永续 1h（默认 8 币 2022-01-29 → 2026-11-23 06:00 UTC；未调参 new8 LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI）、Gate USDT 永续 1h（2025-09-24 起）、官方资金费（OKX 深历史 / Gate）。

## 公式（`scratch/usholiday1h/PRE_REGISTER.json`，2026-11-23 13:36 UTC = 05:36 PST 锁定，sha256 `0f7b5d87d1643343…83e9`，先于任何 PnL）

- 时钟（America/New_York，自动夏令时）：close = 交易日 16:00 ET 那根 UTC 整点开盘入场；reopen = 假日后首个交易日 10:00 ET；hol0 = 假日当天 00:00 UTC。半日市（感恩节次日、平安夜 13:00 收）仍按 16:00 计。
- 锚点：`prehol_day` = 假日前倒数第 2 个交易日收盘入场（覆盖节前最后一个交易日）；`last_close` = 节前最后收盘入场（覆盖整个休市）；`hol0`；`reopen`。
- side ∈ {long, short}；H ∈ {12, 24, 48}；subset ∈ {all, longwk（周一 / 周五假日）, midwk（周二–周四）}；共 **72 格**；8 币等权，事件不重叠。
- 收益 = 等权 `d·(O_{exit}/O_{entry} − 1) − d·资金费 − 2·fee`，fee 实费 5.1 bps / 压力 15.1 / 20 bps。
- 先验：`prehol_day long H24 all`（经典股票节前效应：休市前风险偏好 / 空头回补外溢到 7×24 加密）；备选：`last_close long H48 all`（美国 ETF / 机构卖盘缺席期间的休市漂移）。
- 同脚本基线：同锚点 / 方向 / H，把**每个非假日 NYSE 交易日**当作伪假日（同 subset 星期规则）= 同时钟无条件漂移。
- 切分：train（深未见）2022-01-30→2024-10-21、test→2026-03-05、post→2026-11-23、gate_window 2025-09-28→。usable = 8 槽全正（OKX d8 三段、new8 三段、Gate post / window）且 OKX d8 train、test 均高于同格基线。安慰剂：假日日期平移 ±7 / ±14 天（同星期，只取交易日）全网格重算。

## 结果（每笔净 bps，真实费；`output/research_us_market_holiday_window_event_1h.csv` 6,624 行）

| 格 | 正槽 | OKX d8 train / test / post（n；t） | new8 train / test / post | Gate post / window | 同格基线 train / test |
| --- | --- | --- | --- | --- | --- |
| 先验 `prehol_day long H24 all` | 2/8 | −28.9 / +45.4 / −208.0（26 / 16 / 5；t −0.53 / 0.60） | −5.2 / +61.9 / −88.8 | −205.9 / −38.2 | +4.8 / −46.5 → **否决** |
| 备选 `last_close long H48 all` | 7/8 | +28.7 / +25.0 / +224.4（t 0.46 / 0.28） | +44.0 / −21.2 / +269.1 | +225.1 / +184.9 | +8.9 / **+66.0**（test 低于基线）→ **否决** |
| 非先验 `hol0 long H48 all`（唯一 usable） | 8/8 | +47.0 / +2.1 / +109.7（t 0.71 / 0.02） | +3.5 / +39.6 / +165.2 | +112.3 / +44.3 | −8.2 / −39.4 |
| 同族邻域 `hol0 long H24 all` | 7/8 | +89.5 / **−31.5** / +59.1 | +83.4 / +0.8 / +96.3 | +60.2 / +30.4 | −2.0 / +18.6 |
| 同族邻域 `hol0 long H12 all` | 5/8 | +51.5 / −7.5 / +9.0 | +64.1 / −7.1 / +19.7 | +9.2 / −19.7 | −2.6 / −5.1 |

- `hol0 long H48 all` 压力 15.1 bps：train +27.0 / test **−17.9** / post +89.7；20 bps test −27.7 → 扣压力费 test 段转负。post 只有 5 笔（4/03、5/25、6/19、7/03、9/07），无法做 ≥6/9 月度检验。
- 72 格正槽分布 0:10 / 1:3 / 2:19 / 3:9 / 4:10 / 5:9 / 6:8 / 7:3 / 8:1；**平移安慰剂 8/8 格数：+7 天 4、−7 天 7、−14 天 5、+14 天 0** → 真实假日（1 格）不比随机挪一周的伪假日多，假日日历本身没有信息。
- longwk / midwk 子集全部不稳（如 `hol0 long H24 longwk` train +150 / test −72；`reopen short H48` post +334 但 test −96）。

## 结论

- **否决，不实现、不进观察名单、不改默认、模拟盘不变。** 节前效应（先验）在加密上不存在甚至为负；休市漂移（备选）不胜同时钟基线；唯一 8/8 格 t ≈ 0、压力费 test 转负、H 邻域不稳，且平移一周的伪假日能产生更多 8/8 格。

## 勿重测（never retest by…）

- 改锚点（节前收盘 / 节前一日 / 假日 00:00 UTC / 复市开盘 / 其它整点）、H、方向、子集（长周末 / 周中 / 单个节日如感恩节、圣诞、耶稣受难日、独立日）重测本族；
- 换日历：美国联邦假日 / CME 休市 / 美债（SIFMA）休市 / 半日市 / 其它国家（中国春节 / 国庆黄金周、日本黄金周、英国银行假日、韩国中秋）交易所休市窗口；
- 改成以休市期间加密涨跌方向为信号的复市回补 / 延续（与已否决 CME 周末缺口 / 美股永续休市跳空同机制）。
- 只能用前向新事件复核（下一次 2026-11-26 感恩节、2026-12-25）；不申请影子子账本。

## 文件

- CSV（不入库）：`output/research_us_market_holiday_window_event_1h.csv`；`scratch/usholiday1h/scorecard.csv`、`prior_events.csv`、`us_nyse_holidays_official.csv`。
- 脚本（不推送）：`scratch/usholiday1h/{build,prereg,hol,analyze}.py`、`PRE_REGISTER.json`、`nyse.html`（官方页面快照，sha256 前缀 8f213c85de7fc30c）。
- 下一轮（短线）：换一个未测、机制不同、每笔边际结构上更大的族（先查重；本条已禁止一切交易所 / 国家休市日历窗口）。
