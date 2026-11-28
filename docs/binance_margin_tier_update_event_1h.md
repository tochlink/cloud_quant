# 短线族：币安官方 USDⓈ-M 永续「杠杆与保证金档位更新」公告 → 做空被收紧的币（1h，2026-11-28 ~02:10–02:40 PST；先验未过观察线，非先验 H48 弱观察 → 纸面影子 #20）

- 族名：`binance_margin_tier_update_event_1h`；预注册 `scratch/bnblevtier1h/PRE_REGISTER.json`（任何 PnL 前锁定，48 格，sha256 `9a64cfb27363addea140d096aadcd5551e041a57902af16d5cbafb5cd6963109`；事件表 sha256 `e2c69065…`）。脚本 `scratch/bnblevtier1h/{fetch_detail,flat,parse,fetch_px,fetch_fund,run}.py`（不推送）。
- 结果 CSV（不入库）：`output/research_binance_margin_tier_update_event_1h.csv`（2,304 行：48 格 × Gate / OKX × 实费 / 压力费 / 晚 1h 入场 / ±168h（Gate 另 ±720h）时移安慰剂 × all / deep / test / post）。

## 查重
docs / output / 记忆检索 leverage tier / margin tier / 杠杆档位 / 风险限额 / 保证金档位 / max leverage 0 条。不同于已测的币安下架（#15）、监控标签（#19）、上币 / Launchpool / 公告类上市下架、OI 冲击、资金费族：信号是交易所**风控参数动作**（下调最大杠杆 / 压缩各档持仓上限），不是上下架或标签。

## 数据（只用官方，不编造、不回补）
- 信号：币安官方 CMS 公告 catalog 49，标题含 leverage / margin tier 且为 USDⓈ-M / 永续 / Futures、不含 Delist 的 242 篇，逐篇取官方正文（cms/article/detail/query）解析每个 `XXXUSDT` 的档位表（JSON 节点树或 HTML 两种格式，含 NA 单元、多币合并标题）。得到 1,285 个币次（175 篇有表）2022-09 → 2026-11：收紧 828、放宽 283、不变 174。
  - 收紧 tight = 最大杠杆变小，或 1x 档持仓上限 < 0.8×原值；tight_big = 收紧且新最大杠杆 ≤ 0.5×原值；放宽 loose = 反向（> 1.25×）。
- 交易：同币 Gate 官方 1h USDT 永续（bulk 含已下架合约 + API）与 OKX 官方 1h（现存合约）；入场 = release+60s 之后首根 1h 开盘，持 H 根后开盘离场（合约中途终止则取最后收盘），同币持仓未到期不重开；该币须在公告前 ≥24h 已有 K 线。taker 5.1 bps / 边，压力 15.1；资金费仅最近官方可得部分计入（Gate ≤180 天、OKX ~3 个月；post 段 Gate 覆盖 62%、OKX 18%）。
- 推断：同一公告内各币等权平均为一笔，t 按公告数计（聚类）。分段 deep < 2024-10-21（深历史未见）、test → 2026-03-05、post 2026-03-05 →。

## 公式（48 格）
dir ∈ {tight, tight_big, loose} × side {short, long} × H ∈ {4, 12, 24, 48} × hedge {none, btc（反向 BTC 永续同额）}。
先验 `tight_short_H24_none`；回退 `tight_big_short_H48_btc`。观察线（预注册）：两所 deep / test / post 实费全正、post t ≥ 2、压力 post > 0、胜过时移安慰剂、H 邻域同号。

## 结果（实费，每笔净 bps，n = 公告数）
| 格 | Gate deep | Gate test | Gate post (t, 月) | OKX deep | OKX test | OKX post (t) |
|---|---|---|---|---|---|---|
| 先验 tight_short_H24_none | +250 (58) | +125 (67) | +80.5 (24, t 1.03, 3/9) | +160 | +27 | +46.5 (22, t 0.56) |
| tight_short_H12_none | +283 | +122 | +73 (t 1.29, 6/9) | +180 | +52 | +54 (t 0.77) |
| **tight_short_H48_none** | +250 (58) | +202 (66) | **+218 (24, t 2.32, 7/9；压力 +198, t 2.11)** | +102 | +86 | +169 (22, t 1.57, 6/9) |
| tight_short_H48_btc | +218 | +204 | +132 (t 1.58) | +121 | +58 | +98 |
| 回退 tight_big_short_H48_btc | −958 (9) | +391 | +98 | +12 | −177 | −14 |
| 镜像 tight_long_H24_none | −270 | −145 | −101 | −180 | −48 | −67 |
- 48 格里两所六段实费全正的 5 格中 4 格是 tight_short（H12 / H24 / H48 / H48_btc），另一格 tight_big_long_H4；同一网格用 +168h / −168h 时移后 **没有任何 tight_short 格**六段全正（只有 tight_long 格），说明不是这些币本身的空头漂移。
- 先验对每个时移安慰剂都更好（Gate post：真值 +80.5 vs +168h −10 / −168h +16 / +720h −65 / −720h −149），但 post t 只有 1.03、月 3/9、OKX post t 0.56 → **未过预注册观察线**。
- H48：Gate post 中位 +210 bps、胜率 67%（246 个币次），晚 1h 入场仍 +157（t 1.63）；时移安慰剂 post 全部 ≤ −4；唯一例外 Gate test −720h +233。deep t 只有 0.86（Gate）/ 0.64（OKX），深历史样本 58 / 33 篇且尾部重。
- tight_big（更狠的下调）反而不稳（deep n 9），放宽 loose 无一致方向。

## 结论
- 先验 tight_short_H24_none：六段全正但 post t 1.03 → 未过观察线（不进默认）。回退失败。
- 非先验 **tight_short_H48_none：弱观察**（每笔毛利约 2%，交易稀少，taker 压力费仍正，H12/H24/H48 邻域同号、镜像为负、时移安慰剂不复现）。按 kean 要求加入纸面前向检验：**影子子账本 #20 `binance_margin_tier_tight_short_1h`**（`qtw/levtier_shadow.py`，8788 以 `QTW_SHADOW_LEVTIER=1` 打开；每篇公告 0.2×权益在被收紧币之间等权，OKX 优先否则 Gate，持 48h，taker 5.1 bps，资金费不计；状态 `/api/shadow/levtier`）。默认书与其他纸面实例不变。
- 风险：非先验选择（H48 是 4 个 H 中最好的），deep t 低，post 只有 24 篇；前向纸面达到 ≥20 篇且均值 > +60 bps 再考虑升级。

## 不要重测（never-retest）
- 不要改 H / 收紧阈值（0.8 / 0.5）/ 方向 / BTC 对冲重测本族；不要把信号换成生效时间（effective time）、维持保证金率变化、组合保证金抵押率（Portfolio Margin collateral ratio）或其他交易所（OKX / Gate / Bybit）的档位公告再测同一机制；结果只由影子 #20 前向检验决定。
