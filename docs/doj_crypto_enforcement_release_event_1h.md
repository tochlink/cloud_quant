# 短线新族：美国司法部（DOJ）官方新闻稿中的加密执法公告 1h 事件 → 8 币永续篮子（2026-11-27 ~16:45 PST，研究；否决，仅文档，不改默认、无纸面变更）

**结论：否决（REJECTED）。** 先验 `opa_G168_D0_short_H24` 3/8，回退 `big_G168_D0_short_H24` 4/8；唯一 8/8 的非先验格 `opa_G168_D0_long_H48` 后段太薄（OKX post +11.0 bps，t 0.06，n13）、压力费后段 −9.0 bps、post 月份 3/8（两所相同）、邻域（H24 / D3 / G24）后段全负、去掉前 3 笔均值从 +102.8 降到 +49.5 → 不到观察。

## 查重
- `docs/*.md`、`docs/STRATEGY_FORMULAS.md`、约 1,360 个 `output/research_*.csv` 对 `doj / justice / 司法部 / press release / litigation` 0 命中。
- 不同于已否决的 OFAC SDN 加密地址制裁（财政部制裁名单）、SEC 8-K 网络安全事件、EDGAR ETF S-1、GDELT 新闻、HN / 维基关注度：本族是**联邦执法机构自己发布的起诉 / 认罪 / 没收 / 判决新闻稿**，时间戳来自 DOJ 官方 API。

## 数据（只用官方，不编造、不回补）
- DOJ 官方 `https://www.justice.gov/api/v1/press_releases.json?sort=created&direction=DESC&pagesize=50`，2,150 页、106,744 条唯一新闻稿（含 755 条翻页重复已按 uuid 去重），created 2021-08-06 → 2026-11-25 UTC。抽样复拉 40 页 2,000 条，0 条不在首轮 → 无漏抓迹象。
- 加密过滤（正文+标题+摘要去 HTML）：`bitcoin|cryptocurrenc|crypto[- ]currenc|virtual currenc|digital asset|digital currenc|ethereum|stablecoin|tether|usdt|blockchain|crypto[- ]asset|crypto exchange|crypto`。命中 1,887 条（OPA 总部 287，提到 ≥1 亿美元 379）。官方事件表：`output/doj_crypto_releases_official.csv`。
- 交易：官方 OKX 1h 永续 + 官方 OKX 资金费（d8 2022-01-29 → 2026-11-27 19:00 UTC；未调参 new8 LINK LTC DOT TRX BCH ATOM NEAR UNI 同期），官方 Gate 1h 永续 + 资金费（2025-09-24 →）。
- 时间戳风险：`created` 可能早于正式发布（如 Binance 认罪稿 created 2023-11-21 15:46 UTC，早于当天下午发布会），故预注册 D=3 小时延迟格作保守对照。

## 公式（看 PnL 前锁定 `scratch/dojcrypto1h/PRE_REGISTER.json`，sha256 `77f5e03d…c7`）
- metric：`all` 任意加密相关稿；`opa` url 含 `/opa/pr/`（总部全国性稿）；`big` 提到 ≥ $100 million。
- 事件：第 i 小时（UTC）有 ≥1 条该类稿，且前 G 小时无同类稿（“新鲜”）；第 i 小时收盘已知，第 i+1+D 根开盘吃单入场，8 币等权，持有 H 根，不重叠，计官方资金费。
- 网格：metric{all,opa,big} × G{24,168} × D{0,3} × side{short,long} × H{12,24,48} = 72 格。先验 `opa_G168_D0_short_H24`（全国性执法 = 风险偏好下降，做空一天）；回退 `big_G168_D0_short_H24`。
- 费用：taker 5.1 bps/边，压力 15.1 bps/边。分段：train（深度未见）2022-01-29→2024-10-21，test →2026-03-05，post 2026-03-05→。安慰剂：事件时间平移 ±168h / ±720h（保留星期与时段）。同脚本基线：无条件每 H 根做多/做空。

## 结果（实盘费，bps/笔，均值）
| 格 | 8 槽为正 | OKX d8 train / test / post | new8 train / test / post | Gate post | 备注 |
|---|---|---|---|---|---|
| 先验 opa_G168_D0_short_H24 | 3/8 | −107.5 / −190.1 / +58.9 | −88.1 / −202.0 / +63.7 | +57.8 | 深度未见反向 |
| 回退 big_G168_D0_short_H24 | 4/8 | −15.1 / −109.4 / +212.1 | −36.8 / −171.9 / +158.7 | +211.3 | 只有 post 好（n10），安慰剂 ≈ |
| 最好 opa_G168_D0_long_H48（非先验） | 8/8 | +81.5 / +198.4 / +11.0 | +58.2 / +198.8 / +7.6 | +12.5 | post t 0.06；压力 post −9.0 |
| 基线 always_long H24 | — | +0.5 / −8.1 / −22.0 | −3.0 / −9.5 / −10.8 | −20.1 | |

- 最好格全段均值 +102.8（n94），平移安慰剂 +58.2 / +20.5 / −60.9 / +51.8，虽胜过安慰剂，但 post 月份 3/8，压力费 post 为负，邻域 `opa_G168_D0_long_H24` post −79.3、`opa_G168_D3_long_H48` −38.5、`opa_G24_D0_long_H48` −81.7。
- `all_G168` 只有 10 个新鲜事件（加密稿几乎每周都有），不可用。
- 全部格见 `output/research_doj_crypto_enforcement_release_event_1h.csv`（逐格 × 段，含安慰剂）与 `..._summary.csv`。

## 不得重测
不要通过改 G / D / H / 方向、换关键词或金额门槛、只用某个检察官办公室、改用 SEC / CFTC / FinCEN / 州检察长新闻稿、或改用发布会时间来重测本族。

## 下一轮（长线）
韩国关税厅 / 产业通商资源部官方月度（含前 20 日）出口、半导体出口同比 → 4h 默认书入场闸门（须先查重 korea export / semiconductor / 出口；若与已否决宏观出口 / PMI 同机制则换题）。本地 STRATEGY_FORMULAS.md 已同步追加；该文件超过连接器上限，故写在本 sidecar。
