# BTC Coin Days Destroyed / dormancy → 4h default-book entry gate (long-term) — REJECTED 2026-11-21

**Idea.** Old coins waking up (high CDD / dormancy) = long-term holders distributing → block new trend longs on the 4h default book.

**Data.** Blockchair public Bitcoin block dumps (gz.blockchair.com/bitcoin/blocks, per-block `cdd_total`, `input_total`), summed by block-time UTC date. 4,707 days 2014-01-01→2026-11-20, 0 missing calendar days; heights 277,996→976,802 with 2 blocks absent from the dump (854599, 854614 on 2024-07-30), left uncounted, no fill. Spot checks vs mempool.space prevout recomputation. Day D used only from D+1 04:00 UTC. Official daily output: `output/btc_cdd_dormancy_official_daily.csv`.

**Series.** cdd7 = ln(7d mean CDD); cdd30 = ln(30d mean CDD); dorm7/dorm30 = ln(Σ CDD / Σ BTC transferred over 7/30d).
**Forms.** z vs 365d > {0.5,1,1.5,2}; s > SMA{90,180}; s − s.shift{30,90} > 0. **Sides.** long_off, short_off, both, contra_both. 128 cells locked before any PnL (PRE_REGISTER sha256 8face163…dc394).
**Prior.** cdd30_z365gt1_long_off. **Fallback.** dorm30_trend_n180_long_off.

**Validation.** OKX d8, Gate d8, OKX d7_noBNB; deep unseen → 2024-10-21, tune → 2026-03-05, post → 2026-11-14; repo fees (perp taker 5.1 bps) + stress (spot 20 / perp 15.1); official funding; placebo shifts; neighborhood.

**Results (return %, Sharpe).**
- Baseline: OKX d8 deep +35.14/0.71, tune +85.08/1.47, post +59.90/2.23; Gate d8 deep −3.63/0.09, tune +84.25/1.46, post +60.32/2.25.
- Prior 1/9: never fires post-2026-03 (identical to baseline); OKX deep +25.75/0.58, tune +52.52/1.11; Gate deep −2.56/0.11, tune +52.23/1.10 → lost tune badly on both venues.
- Fallback 0/9: post OKX +37.52/1.67, Gate +37.84/1.69; deep Gate −28.04.
- Only 9/9 was non-prior dorm30_trend_n90_contra_both with lower post return (−5.2 pp). Best non-prior cdd30_trend_n90_short_off 7/9 (post OKX +64.62/2.53, months 5/4; Gate deep −1.77) but neighborhood collapsed (n120 −57.6 pp, n150 −89.7 pp, n210/n270/n365 all worse post); stress Gate deep −10.34.
- Placebos (±7/±14/+365 d) on fallback all 0/9; prior +365 d placebo 5/9, better than the real prior.

**Verdict.** Rejected. Defaults and code unchanged. Do not retest by changing window, threshold, SMA length or side, or by swapping CDD/dormancy/liveliness/value-days-destroyed or a different on-chain age metric source.
CSV: `output/research_btc_cdd_dormancy_gate_4h.csv`, prereg `output/research_btc_cdd_dormancy_gate_4h_prereg.csv`.
