# 代币官方排期解锁前做空（BTC 对冲）1h 事件 → 解锁币 USDT 永续（先验否决；非先验 a=−72h→T0 弱观察 → 影子 #17 纸面）

## 短线新族：团队 / 投资人代币排期解锁（token unlock）前后 1h 事件（2026-11-22 ~16:20 PST，研究 + 影子纸面，不改默认）

- 查重：`docs/STRATEGY_FORMULAS.md`（含轮换日志）、`docs/*.md`、`output/research_*.csv`（约 1,200 个）、`scratch/` 目录名检索 unlock / vesting / 解锁 / token unlock / cliff：只有与本题无关的「止损后解锁」「double holdout unlock_b」命中，0 个代币解锁事件测试。与已测的上市后漂移做空、币安 / Upbit 公告、截面动量 / 反转、山寨/BTC 比价趋势都不同：这里的触发是**项目官方文档写死的供给释放日历**，交易标的是解锁币本身。
- 事件（只用项目官方 tokenomics 文档，不用第三方追踪站的日期）：`scratch/tokenunlock1h/unlock_events_official.csv`，共 **164 个**，T0 = 解锁日 00:00 UTC。
  - ARB 每月 16 日（2024-03-16 起，docs.arbitrum.foundation/token-supply）33 个；APT 每月 12 日（2023-11-12 → 2026-10-12 核心贡献者 + 投资人，aptosfoundation.org tokenomics）36 个；STRK 每月 15 日（2024-04-15 起，docs.starknet.io）32 个；JTO 每月 7 日（2024-12-07 悬崖起，jito.network docs）24 个；PYTH 每年 5-20（2024/25/26，docs.pyth.network）3 个；ZK 每月 17 日（2025-06 悬崖起，docs.zknation.io；日 = 2024-06-17 TGE 周年）18 个；ZRO 每月 20 日（2025-06-20 起，LayerZero 官方）18 个。
- 价格 / 资金费（只用官方，不编造、不回补、不插值）：OKX v5 `history-candles` 1H 全历史（7 个币上线 → 2026-11-22 23:00 UTC，0 缺口）；Gate `download.gatedata.org` 月度 1h K 线 + `funding_applies`，2026-11 用 Gate v4 REST（每币 0–5 个官方缺口，缺 bar 的事件跳过）；BTC 对冲腿 OKX 用已有官方 deep1h（2022-01-29 → 2026-11-22 17:00 UTC）。OKX 资金费 API 只保留约 3 个月（287–574 条），更早的 OKX 腿用 Gate 同币官方资金费（与 `scratch/st2/common.py` 口径一致，文档注明）。永续上线后第一周的事件跳过。
- 交易：在 `T0 + a` 小时那根 1h 的开盘入场，`T0 + b` 开盘离场；方向 d；`净 = d·(O_x/O_e − 1) − d·Σ 资金费·价格/O_e − 腿数·2·费率`；hedge=btc 时加同场所等额反向 BTC 永续腿（隔离代币特有的供给效应，去掉大盘 β）。
- 网格（看 PnL 前锁定 `scratch/tokenunlock1h/PRE_REGISTER.json`，2026-11-22 16:00 PST，sha256(json+事件表) `e5ded461693e78fb70bbde5258d7460786e5069393ed6aac67651a94557ecea5`）：15 个 (a,b) 窗口 {(−72,0),(−48,0/12/24),(−24,0/12/24/48),(−12,0/12/24/48),(0,12/24/48)} × 空/多 × 不对冲/BTC 对冲 = **60 格**；费用 taker 5.1 bps、maker 2 bps、压力 15.1 / 20 bps（每边每腿）；安慰剂 = 同币事件平移 −15d / −7d / +7d / +15d；分段 deep < 2024-10-21（28 个事件）、test → 2026-03-05（82 个）、post 之后（54 个）。
- 先验（锁定）short a=−24 b=+24 BTC 对冲：OKX deep +33.6 / test +30.7 / **post −106.8 bps**（t −0.72），Gate +35.7 / +29.3 / −105.2 → **否决**。
- 后备（锁定）short a=−48 b=0 BTC 对冲：6/6 为正（OKX +99.7 / +159.7 / +68.4，Gate +101.6 / +162.9 / +71.0），压力 20 bps 仍正，test、post 胜过全部安慰剂；但 post t 只有 0.89（<1，达不到预注册弱观察线），deep 被 −15d 安慰剂（+122.8）超过 → 不入选。
- 非先验（探索）**short a=−72 b=0 BTC 对冲**（解锁前 3 天做空、解锁时刻平仓）：

| 场所 | deep（n=28） | test（n=82） | post（n=54） | 全样本 |
|---|---|---|---|---|
| OKX 净 bps（taker） | +232.0（t 2.12） | +150.3（t 1.71） | **+220.3（t 2.07）** | +187.3（t 3.17） |
| Gate 净 bps（taker） | +234.6（t 2.14） | +152.5（t 1.73） | **+224.7（t 2.11）** | +190.3（t 3.22） |
| OKX 安慰剂最大值（±7d/±15d） | +104.1 | +96.6 | +56.0 | |
| OKX maker / 压力 15.1 / 压力 20 | +244 / +192 / +172 | +163 / +110 / +91 | +233 / +180 / +161 | |
| 按月聚类（OKX） | 9/12 月为正，t 1.22 | 11/16，t 1.72 | **8/9，t 3.14** | 28/37，t 2.94 |

  - 留一币（post，OKX）：最差 ex_STRK +139，ex_PYTH +203（t 1.89）；单币 post：APT −27、ARB +5、JTO +164、STRK +624、ZK +142、ZRO +284、PYTH +1134（1 个事件）。APT / ARB 最弱，收益并非单币驱动。
  - 不对冲版 a=−72：OKX +147 / +176 / +215（post t 1.67）。
  - 邻域（`output/research_token_unlock_event_1h_supp.csv`，**事后补充、未预注册**，OKX taker，BTC 对冲，b=0）：a=−120 +406/+214/+114；−96 +313/+189/+154；−84 +277/+169/+219；−72 +232/+150/+220；−60 +211/+131/+151；−36 +40/+107/+47；−24 +55/+71/+4。**−60…−120h 平台稳定**，越接近 T0 才入场越弱。
  - 结构：收益集中在**解锁前**；持有越过 T0 就亏（short 0→+24 post −125），解锁后反而有弱反弹（long 0→+24 BTC 对冲 6/6 为正但 post t 0.79）——「解锁前对冲 / 抛压，落地后出清」。
- 结论：**先验否决；非先验 short a=−72→T0 BTC 对冲 = 弱观察**（6/6、三段都胜安慰剂、post t≥2、压力 20 bps 为正、留一币全正、邻域平台稳定；但它是从 60 格里挑出来的、在预注册网格的边缘，post 只有 54 个事件 / 9 个月，按预注册规则非先验最多弱观察）。不改默认。
- 实现：影子子账本 **#17 `token_unlock_short_1h`**（`qtw/unlock_shadow.py`，测试 `tests/test_unlock_shadow.py`，接口 `GET /api/shadow/unlock`）：日历写死同一规则；T0−72h 后第一次检查（每 60 秒）按官方实时价开空该币永续（OKX 优先，否则 Gate）+ 等额做多 BTC 永续，每个事件币腿 0.25×权益、全部币腿 ≤1.0×权益，迟到 >2h 不补开；T0 后第一次检查两腿一起平仓；taker 5.1 bps 每边每腿，资金费不计（与 #13–#15 一致）。默认关闭，只有 `QTW_SHADOW_UNLOCK=1` 才启动（本机只在 8788 paper-default 打开），测试 / `QTW_FORBID_LIVE=1` 下永不启动，不下真实 / 模拟单，不碰默认账本与实盘闸门。下一批：JTO 2026-12-04 00:00 UTC 入场（12-07 解锁），STRK 12-12、ARB 12-13、ZK 12-14、ZRO 12-17。
- 勿重测：不要靠改 a / b / 方向 / 对冲、换费率口径或换安慰剂平移来重测本族；不要把同一日历换成第三方追踪站（Tokenomist / DefiLlama）日期、加入线性日释放代币（WLD / TIA 日释放）或用「解锁占流通比」再挑一遍。可以做的只有：影子 #17 的前向纸面检验，以及（新的独立预注册）把同一规则扩到新上线、官方文档写明日期的新代币。
- 文件：`output/research_token_unlock_event_1h.csv`（15,600 行）、`output/research_token_unlock_event_1h_supp.csv`；脚本 `scratch/tokenunlock1h/{events,fetch,run,analyze,ana2,supp}.py`。
- 下一轮（长线）：欧央行 ECB 官方周度合并财务报表总资产（ECB Data Portal `ILM` 周度序列）+ 日本央行官方营业概况总资产 → 非美央行资产负债表 13 周趋势作为 4h 默认书入场闸门（此前两次作为指针出现，`output/` 无对应 CSV，未测；与已否决的美联储净流动性 / WALCL、SNB 活期存款、HKMA 总结余不同）。
