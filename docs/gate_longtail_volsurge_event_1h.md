# 短线新族：Gate 长尾永续 1h 成交量突发广度 → 8 币永续篮子（2026-11-27 ~22:50 PST，研究，不改默认；否决）

- 查重：原候选「Gate bulk 大额主动成交聚簇 1h」已判与 taker flow / whale / Deribit 大宗重复，不跑。本族只用成交量（不看价格方向）的长尾广度，是已否决「长尾价格广度」的近亲，已在报告中标明。
- 数据（官方）：download.gatedata.org futures_usdt candlesticks_1h 月度 bulk（含已下架合约，1,662 个 USDT 合约，排除交易用 d8 / new8），45,214 个 UTC 小时（2021-10-01 起）。不补数、不编造。
- 公式：V_t ≥ X·med168（前 168h 成交量中位数，shift 1，合约上市 ≥336h）记为突发；B_t = 突发数 / 可用数（≥50）；z = (B − mean720)/sd720（截至 t−1，min 360）；z ≥ k 时下一根 1h 开盘 taker 入场，等权 8 币，持有 H，不重叠。X∈{3,5}，k∈{2,3}，cond∈{any, quiet(8 币 24h 平均涨跌 <3%)}，方向 long/short，H∈{12,24,48}，共 48 格，预注册 sha d16b0d9d（PnL 前锁定）。先验 X5 k2 any short H24；回退 X5 k2 any long H24。
- 费用：taker 5.1 bps/边，压力 15.1 bps/边。分段：train 2022-01-01→2024-10-21（深未见）、test →2026-03-05、post 之后；槽位：OKX d8 / OKX 未调参 new8 / Gate d8 / Gate 深 d8。
- 结果：真实费用下 8 槽全正的格子 0 个（可用格 0）；正槽数分布 {0:1,1:7,2:13,3:8,4:16,5:2,7:1}。先验 1/8（OKX train −35.0 bps n285、test −55.7、post +20.3），回退 2/8（train +14.6、test +35.3，post −40.7、t −1.6）。最好的 7/8（quiet long H48 X5 k3）post +5.7 bps、t 0.1，月份 5/9。
- 安慰剂：OKX+Gate 深 6 槽全正格数 真实 1，+720h 0，−720h 2，+168h 2 → 与安慰剂无区分。
- 结论：**否决**，不加纸面、不改默认、代码不变。

## 勿重测

- 改 X / k / H / z 窗口 / cond / 方向，或改用成交额 / 成交笔数、OKX / Binance 长尾成交量广度、成交量萎缩（dry-up）广度、成交量与价格广度组合。

## 文件

- CSV（不入库）：output/research_gate_longtail_volsurge_event_1h.csv；脚本 scratch/gatevolbreadth1h/。
- 下一轮（长线）：PBoC 社融存量 / 美联储 G.19 消费信贷 → 4h 闸门（先确认官方历史可下载）。
