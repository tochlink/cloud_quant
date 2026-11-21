# GMX V2 official liquidation 1h shock → 8-perp basket (short-term, 2026-11-21 ~11:55 PST, research only; REJECTED)

**Verdict: REJECTED. No default change, no paper / shadow change.**

## Dedup
GMX had appeared only as a planned "next round (short)" line in `docs/STRATEGY_FORMULAS.md`. There were 0 `output/research_*gmx*` files, 0 scratch dirs and no memory entry. The mechanism is forced deleveraging on an on-chain perp DEX, split by side. It is not the rejected Aave V3 lending-liquidation shock, Bitfinex margin, Hyperliquid Bridge2 margin bridge, funding / basis extremes, or the price-defined flash-crash / capitulation families. OKX / Gate insurance-fund history was too short, and OKX / Binance liquidation feeds have no history.

## Data (official only; nothing invented, interpolated or backfilled)
- Source: GMX V2 (gmx-synthetics) Arbitrum, through GMX's own indexer that app.gmx.io uses (`gmx.squids.live/gmx-synthetics-arbitrum:prod`). Query: `tradeActions` with `eventName=OrderExecuted` and `orderType=7` (Liquidation). Fields: `timestamp`, `isLong`, `sizeDeltaUsd/1e30`.
- Row count: 281,653 liquidations, which equals the indexer `totalCount`, with 0 duplicate ids.
- Spot check: a sample transaction receipt on Arbitrum (`arb1.arbitrum.io`) contains logs from the official V2 EventEmitter `0xC8ee91A54287DB53897056e12D9819156D3822Fb`.
- Hourly series: `scratch/gmxliq1h/gmx_v2_liquidations_official_1h.csv`, 29,194 complete UTC hours from 2023-07-24 09:00 to 2026-11-21 18:00 UTC. There are 0 calendar gaps. The 4,092 hours with no liquidations are real zeros.
- Yearly liquidation totals (long / short): 2024 $2.76B / $1.21B, 2025 $2.02B / $0.94B, 2026 YTD $0.54B / $0.28B.
- V1 was not spliced in: V1 shut down after the 2025-07 exploit, so it cannot cover the post period.
- Prices: OKX d8 and the 8 untuned new8 coins (official 1h perp), plus Gate d8 (official 1h perp, from 2025-09-24). Funding: OKX deep official and Gate official.

## Formula
- `long_liq_usd` / `short_liq_usd` = per-UTC-hour sum of liquidated position size in USD, across all markets.
- Metrics:
  - `log_long_liq = log1p(LL)`
  - `log_short_liq = log1p(SL)`
  - `net_liq_imb = asinh((LL − SL)/1e5)`; positive means longs are being liquidated.
- z-score: for L=1, `z = (x−μ)/σ`; for L>1, `z = (Σ_L x − Lμ)/(σ√L)`. μ and σ are rolling 168h (minimum 84) and end at h−1.
- Execution: signal on bar h, enter an equal-weight 8-perp basket at the next 1h open, hold H bars, no overlapping events.
- Cost: taker 5.1 bps per side (stress 15.1) plus official funding.

## Pre-registration (`scratch/gmxliq1h/PRE_REGISTER.json`, sha256 f62fa077…183562, locked before any PnL)
- Grid of 128 cells: metric × L {1,4} × k {3,4} × side (high only for the log metrics; high / low for net) × {long, short} × H {6,12,24,48}.
- Splits: train 2023-07-24→2024-10-21 (deep unseen), test →2026-03-05, post →end; Gate window 2025-09-28→end.
- Placebos: ±720h.
- Prior: `log_long_liq L1 k3 high long H24` (contrarian buy after a long-liquidation burst).
- Fallback: `net_liq_imb L4 k3 high long H24`.

## Results (`output/research_gmx_v2_liquidation_shock_event_1h.csv`, 5,120 rows)
- Prior: 1/8. It had only 8 deep-unseen events (−9.9 bps) and 0 events in test and post: log1p of a series that is often zero has a fat lower tail, so z ≥ 3 at L=1 is almost never reached. H6/12/48 neighbours were all negative. Failed.
- Fallback: 3/8.
  - Deep unseen −11.9 bps (n=83), test −59.0 (n=94, t −1.7).
  - Post OKX +20.0 / Gate +20.4 bps (t 0.6, n=44); new8 post +42.3.
  - Stress post ≈ 0. Post months were 6/9 on both venues, but deep unseen and test were negative. Failed.
- Cells by n_pos: 0:36, 1:9, 2:30, 3:14, 4:17, 5:12, 6:4, 7:1, 8:5. The 5 usable 8/8 cells were all non-prior. The best, `net_liq_imb L4 k3 low long H48` (buy after a short-liquidation burst), had:
  - deep unseen +104.8 (t 2.0, n=49), test +147.5 (t 1.8), post OKX +88.3 / Gate +90.1 (t 1.1, n=26), new8 all positive;
  - but the −720h placebo was stronger in post (+162 bps), and the +720h placebo was also positive (long-basket beta at H48);
  - and the H neighbourhood collapsed: H12/H24 post −11.6 / −13.9 bps.
- `log_long_liq L4 k3 high long H48` had only 8 post events, and its L/k neighbours had 0 events.
- Placebo base rate: 6/128 (4.7%) real cells pass the 5-slot rule (OKX train/test/post + Gate post/window all > 0), against 10/240 (4.2%) placebo cells. No better than chance.

## Never retest
Do not retest this family by changing L, k, H or side, swapping in long / short / net / count / notional metrics, splicing V1, switching to GMX Avalanche or another perp DEX (gTrade, Vertex, Hyperliquid liquidation feeds), filtering by market (ETH/BTC only), or using a different z-window.

Scripts: `scratch/gmxliq1h/{fetch_liq,build,run,analyze,extra}.py` (research scripts not pushed).
