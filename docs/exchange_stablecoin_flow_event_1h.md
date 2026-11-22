# 交易所稳定币流入 / 流出 1h 冲击（推迟）+ 月相（USNO 官方）事件 1h → 8 币永续篮子（研究记录）

## A. 短线「OKX / Binance 官方 PoR 地址的 USDT / USDC 流入 / 流出冲击」——推迟（2026-11-21 ~19:25 PST，未跑 PnL）

- 查重：docs / output/research_*.csv 对 netflow / 净流入 / proof of reserves 无相关短线条目；仅有长线 `okx_por_liability_gate_4h`（OKX PoR 负债）。
- 官方地址来源核查（约 15 分钟内）：
  - **OKX**：`okx.com/en-us/proof-of-reserves/download` 页面列出官方 PoR 地址快照 zip（`static.okx.com/cdn/okx/por/chain/por_csv_YYYYMMDDHH_Vn.zip`，仅 2026-05-07 → 2026-11-01 共 7 个快照）。2026-11-01 快照以太坊网络：USDC 15,996 个地址、ETH 6,959 个、USDT-ERC20 仅 163 个，绝大多数是每用户一个的充值地址，不是少量热 / 冷钱包。
  - **Binance**：binance.com PoR 页面对普通 HTTP 返回 202 空体（WAF / 前端渲染），没有静态文件或公开 API 可取地址表，不用第三方标签（Arkham / Etherscan）替代。
  - 结论：(1) Binance 官方地址表取不到；(2) OKX 的 ~16k 地址无法放进 eth_getLogs topic 过滤，只能全量拉 USDT / USDC Transfer（公共 RPC 数亿条）再本地匹配，不可行；(3) 地址快照最早只到 2026-05，对 2022–2026 历史会有事后偏差。因此**推迟**，不编造、不回补、不用第三方标签。
- 重新开启条件：Binance 或 OKX 发布少量（<数百）可验证的稳定币热 / 冷钱包地址表，且有 2022 起的历史快照。勿以第三方标签替代。

## B. 短线新族：USNO 官方月相（新月 / 满月 / 上弦 / 下弦）→ 8 币永续篮子（1h，2026-11-21 ~19:35 PST，研究，不改默认；否决）

- 查重：docs 仅有地磁 Ap 4h 闸门（含「月相 / lunar」被列为未做）；output/research_*.csv 无 lunar / moon；记忆无。不同于地磁 Ap 闸门。
- 数据（官方）：美国海军天文台 USNO `aa.usno.navy.mil/api/moon/phases/year`，2021–2026 共 297 个相位时刻（UT，分钟精度；新月 74、满月 74、上弦 74、下弦 75），`output/usno_moon_phases_official.csv`。天文确定性，无修订、无事后偏差。OKX d8 永续 1h 2022-01-29 07:00 UTC → 2026-11-21 00:00 UTC。
- 公式：相位时刻所在 1h 的下一根 1h 永续开盘等权入场 8 币（或 new8），持有 H 小时。单相位 4 × {long,short} × H{24,72,168,336} = 32 格；交替（新月→满月）2 × H{72,168,到下一事件}= 6 格，共 38 格。`scratch/exchflow1h/PRE_REGISTER.csv`（sha256 aa6ac8d4…06f4c3，看 PnL 前锁定）。唯一先验 = alt_newlong_fullshort_Hnext（新月做多、满月做空，持有到下一事件）；回退 = new_long_H168。
- 费率：真实永续吃单 5.1bps/边，压力 15.1bps/边；官方资金费；下一根开盘成交。分段：deep_unseen 2022-01-29→2024-10-21、test→2026-03-05、post→2026-11-21；Gate 窗口 2025-09-28→。8/8 = OKX d8 三段 + new8 三段 + Gate post + Gate 窗口均值净 bps > 0。安慰剂：时移 ±120h、±240h（避开 177h 的相位间隔）。
- 结果（真实费，OKX d8，单笔均值 bps）：
  - 38 格 n_pos 分布：8/8 只有 1 格、7/8 1 格、6/8 7 格，其余 ≤ 5/8。
  - 唯一 8/8 为**非先验** alt_newshort_fulllong_H72：deep_unseen +25.9（n 68，t 0.41）/ test +15.8（n 34，t 0.14）/ post +5.3（n 17，t 0.07）；压力费 OKX test −4.2、post −14.7、Gate post −14.7（压力后翻负）；post 逐月月和 > 0 仅 5/9（OKX 与 Gate 相同），不到 ≥ 6/9。邻域 H168 为 7/8（post +40.9，t 0.2，new8 post −2.1）。
  - **先验** alt_newlong_fullshort_Hnext：5/8。deep_unseen **−146.6**（n 68）/ test +73.8 / post +221.3（n 16，t 0.8）；new8 deep_unseen −47.4、test −37.7；Gate post +221.3。深未见为负，不成立。
  - **回退** new_long_H168：1/8。deep_unseen −0.5 / test −131.6 / post −152.3。
  - 安慰剂：OKX d8 三段全为正的格数，真实 4/38；时移 +120h 10/38、+240h 5/38、−240h 4/38、−120h 1/38。真实不优于时移（+120h 反而更多）。
- 结论：**否决**。不实现、不进观察名单、不改默认、不动纸面盘、无代码改动，仅文档。勿以同一机制换相位 / H / 方向，或用月食、近地点（supermoon）、农历日、太阳周期、节气、潮汐等天文周期重测；勿用 ±偏移入场重测。
- 文件（不入库）：`output/research_lunar_phase_event_1h.csv`（1,520 行）、`output/usno_moon_phases_official.csv`；脚本 `scratch/exchflow1h/{fetch,prereg,run,analyze}.py`。
- 下一轮（长线）：以太坊官方净发行（EIP-1559 日度销毁 vs 发行，execution 区块 `baseFeePerGas` × gasUsed 与信标发行重建的日度 ETH 供应变化）→ 4h 默认书入场闸门；开跑前需再查重 docs 中「ultrasound / 燃烧」的 3 + 16 处命中，确认不是已否决的 blob / 基础费 1h 冲击。
