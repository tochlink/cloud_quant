# Polymarket 官方小时级隐含概率跳变 → 8 币永续篮子（1h，否决）

## 短线新族：Polymarket 官方小时级隐含概率跳变（BTC 价格阈值市场 / 美联储单次议息市场）→ 8 币永续篮子（1h）（2026-11-21 ~00:23 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、output/research_*.csv（1,032 个）、记忆中无 Polymarket / prediction market / Kalshi / 预测市场 条目。不同于已否决的 FOMC / ECB / 国债拍卖事件（议息日前 24h 起剔除，不测决议本身）、1h 微观结构 / 价格冲击、链上事件族。
- 可行性（先查再测）：官方 clob.polymarket.com/prices-history 对**已结算**市场 `interval=max` 返回空，但传 `startTs/endTs&fidelity=60`（14 天分段）可拿到约每小时一个快照（间隔 3600±2 s，时刻约整点 +0–3 s），最早到 2024-03（BTC）/ 2024-04（Fed）。元数据用官方 gamma-api.polymarket.com `/events/keyset`（tag_slug=bitcoin 158,850 个事件、fed-rates 195 个；/events 大页需 gzip、深分页须 keyset）。无子图 / Dune / 第三方存档，不补、不插值。
- 数据：BTC 市场 10,896 个 Yes token（事件 slug：bitcoin-above-<N>-on-<日>、bitcoin-above-on-<日>、btc-above-on-、what-price-will-bitcoin-hit*、what-price-will-btc-reach*、what-price-will-btc-dip-below*；剔除盘中 am/pm-ET、up/down、区间桶、ETH/BTC；70 个无历史）；Fed 单次议息市场 113 个（fed-interest-rates-<月>-<年>、fed-decision-in-<月>[-数字]）。共 1,917,600 个官方快照。小时序列 `output/polymarket_prob_official_1h.csv`：2024-02-28 17:00 → 2026-11-21 07:00 UTC 共 23,919 小时；btc_bull 有效 23,709（缺 210，不补；2026-03-05 前 17,601 / 后 6,108）；fed_ease 有效 22,070（缺 1,849；前 16,618 / 后 5,452）。
- 公式：快照按最近整点归桶 h；市场在 h 活跃需 start ≤ h−1h 且 h ≤ min(endDate, closedTime)−2h。
  - btc_bull(h) = Σ w·s·(p(h)−p(h−1h)) / Σ w，w = p(h−1h)(1−p(h−1h))，s=+1（above / reach），−1（dip / below / ↓）。不用成交量加权（prices-history 无小时成交量，终值成交量是前视）。
  - btc_bull_resid = btc_bull − (a + b·r)，r = OKX BTC 永续 log(open(h)/open(h−1h))，a、b 为截至 h−1h 的 168h 滚动 OLS。btc_bull 与同小时 BTC 收益相关 **0.76**（主要是价格的映射）。
  - fed_ease(h) = 前月议息事件（endDate−24h 之前最近的一场）内 Σp(降息) − Σp(加息) 的小时变化；前月切换或任一活跃市场缺快照则 NaN。
  - z = (x − μ)/σ，μ/σ 为截至 h−1h 的 W 小时滚动（min W/2）。|z| ≥ k：follow 顺 z 方向、fade 反向；信号值记在开盘时刻 h 的 K 线、**下一根开盘入场**（快照后保守 1h），持有 H 根后开盘平，不重叠。成本 taker 5.1 bps/边（压力 15.1）+ 官方资金费（同 eigenlayer1h evret）。
- 预注册（PRE_REGISTER.json，任何 PnL 前锁定 96 格）：metric {btc_bull, btc_bull_resid, fed_ease} × W {168, 720} × k {3, 4} × {follow, fade} × H {6, 12, 24, 48}。先验 `btc_bull_resid_W168_k3.0_follow_H24`（超出同小时 BTC 变动的预测市场重定价 = 信息 / 关注流 → 跟随），回退 `btc_bull_W168_k3.0_follow_H24`。PnL 前唯一修正：Fed slug 正则放宽到带数字后缀的 2026 场次（覆盖缺口所致，网格 / 先验不变）。切分 train → 2024-10-21（Polymarket 数据仅 2024-03 起，即 unseen 段只有 ~7 个月）、test → 2026-03-05、post → 今；Gate 自 2025-09-28；安慰剂 z 平移 ±720h；post 月度对照 = 同月同方向每小时入场同 H 的漂移基线。
- 结果（真实费，每笔净 bps；`output/research_polymarket_prob_jump_event_1h.csv` 3,072 行）：
  - **先验** `btc_bull_resid_W168_k3.0_follow_H24`：7/8。OKX d8 train **−5.9**（n=56，t −0.14，unseen 失败）/ test +25.9（n=132，t 0.88）/ post +26.3（n=84，t **0.92**，中位 +32.9，每笔 Sharpe 0.10）；new8（未调参）+10.1 / +21.4 / +31.4；Gate post +26.6（n=84，t 0.93）/ gate_window +36.7。post 月份优于漂移基线 6/9（OKX、Gate 相同；6 月 −997、8 月 −773 bps）。压力费 OKX post +6.3（t 0.22）、train −25.9。安慰剂 ±720h post −34.2 / −41.4（真实优于平移）。邻域：W168 k4 +17.7、W720 k3 +20.6、W720 k4 **−38.5**；H6 +4.5、H12 +5.7、H48 +26.2。post t < 1.5、unseen train 为负、压力费近零 → 不达标。
  - 回退 `btc_bull_W168_k3.0_follow_H24`：2/8（train −70.5、post −6.5，月份 4/9），否决。
  - 全网格 usable 8/8 = 2，均非先验：`btc_bull_resid_W168_k3.0_follow_H48`（post +26.2 t 0.57，new8 post +6.9，k4 邻格 post −38.4，−720h 安慰剂 test +80.5 t 1.51）；`btc_bull_W168_k4.0_fade_H6`（post +6.8 t 0.25，中位 −13.9，压力费 post −13.2）。fed_ease 最多 6/8：fade H24/H48 post +50–83（t 1.1–2.0）但 test 为负、unseen train 多为负。不可晋升。
- 结论：**否决**，不实现、不进观察名单、不改默认、无代码改动，仅文档。BTC 阈值市场的小时概率变化基本是 BTC 价格的映射（相关 0.76），去掉价格后的残差只有 ~+26 bps/笔、t < 1，过不了 taker 压力费；Fed 概率变化无稳定方向。勿以同一机制换 W / k / H / follow↔fade、换权重（成交量 / 等权 / 流动性）、换市场子集（up/down、区间桶、盘中、ETH / SOL 阈值、年度 / 月度 reach）、换 Fed 多会议组合 / 降息次数市场、换 Kalshi 等其他预测市场再测。
- 文件：`output/research_polymarket_prob_jump_event_1h.csv`、`output/polymarket_prob_official_1h.csv`；脚本 scratch/polymarket1h/{enum_keyset,fetch,build_series,run,analyze}.py、PRE_REGISTER.json（研究脚本未推送）；侧记 docs/polymarket_prob_jump_event_1h.md。官方历史可随时重拉，未起实时记录器。
- 下一轮（长线）：官方 ICI 每周货币市场基金总资产（ici.org Money Market Fund Assets 周报）或美联储 H.8 每周商业银行存款的周变化 z / 趋势 → 4h 默认书入场闸门（现金囤积激增 → 拦新多），按发布滞后入场，不补数据；docs / output 中 0 条。
