# 短线新族：OKX 官方永续保险基金（Insurance Fund）余额 1h 冲击 → 同币永续 / 8 币篮子（2026-11-22）

**结论：PENDING-RECORDER（未做 PnL，无法验证；不进 paper，默认与 paper 均不变）。**

## 查重
- docs/*.md、STRATEGY_FORMULAS.md、output/research_*.csv（1219 个）对 `insurance fund / 保险基金 / bankruptcy / auto-deleverag` 均 0 命中；`ADL` 仅偶然出现在无关文档。
- 与已否决的 1h 爆仓流量 / OI / taker / LS 比、篮子 capitulation / flash-crash 不同：本信号是交易所**风控账户余额**（爆仓盈余注入 / 穿仓亏损扣减）的小时变化，而非爆仓成交量。

## 公式（预注册，PRE_REGISTER.json sha256 83e16515…debe，先于任何 PnL）
- 数据：OKX v5 `GET /api/v5/public/insurance-fund?instType=SWAP&instFamily=<COIN>-USDT`，`type=regular_update` 每 60 秒一条 balance。
- 信号：每币小时余额变化 Δ = 本小时末最后一分钟 balance − 上小时末 balance，对过去 L 小时 z 分数；正冲击=爆仓盈余（级联刚发生），负冲击=穿仓/ADL 压力。
- 网格：L∈{168,336}，k∈{3,4,5}，H∈{4,12,24}，方向∈{contra,trend}。Prior = 正冲击 L168 k4 H12 contra；fallback = L336 k4 H12 contra。

## 数据可得性（本轮实测，决定性）
- OKX 只提供约 **90 天**历史（2026-11-22 实测：90 天前有数据，200 天前返回空；type=adl / liquidation_balance_deposit / bankruptcy_loss 在 BTC-USDT/BTC-USD 过去 90 天均 0 条）。
- 因此：无 2026-03-05 前后切分、无 pre-2024-10-21 深度未见区、无 Gate 对照（Gate 无同类公开历史），无法满足 kean 的验证门槛（OKX+Gate、deep unseen、post、邻域、安慰剂）。
- 预注册判定：历史 < 2 年 ⇒ 不可能达到 watch；**本轮不看 PnL**。

## 动作
- 启动官方实时记录器 `/workspace/scratch/okxinsfund1h/record.py`（nohup，pid 见 record.pid；仅追加 OKX 官方返回行，不虚构）。首次运行回填 OKX 提供的约 90 天（约 1 s/页，8 币约 3 小时），之后每 50 分钟增量。
- 重新评估条件：累计 ≥ 12 个月且至少含 20 个以上级联事件后，按同一预注册网格一次性评估；在此之前不得改 L/k/H/方向。
- 未改任何代码，未改 paper。
