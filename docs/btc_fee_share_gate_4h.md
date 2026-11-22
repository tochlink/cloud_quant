# BTC miner fee share (fees ÷ (fees + block subsidy)) → 4h default-book entry gate (long-term) — REJECTED 2026-11-21

**Idea.** Fee-share spikes = on-chain congestion / speculative mania → fragile regime for new trend longs on the 4h default book (#1 dual MA 50/150, 8-coin perp book). Gate only blocks new entries; exits/stops/held positions untouched.

**Dedupe.** docs/*.md, STRATEGY_FORMULAS.md, output/research_*.csv: no prior fees/(fees+subsidy) gate (only a "next idea" note in coinbase_us_volume_share_shock_event_1h.md). Different from rejected Puell multiple (total revenue / 365d mean), BTC on-chain fee 1h shock, mempool congestion 1h burst, CBECI miner margin, hash ribbon, difficulty-adjustment event, halving cycle.

**Formula.** fee_share_w(D) = Σ fees / (Σ fees + Σ subsidy) over the last w UTC days (block time), subsidy = 50 BTC >> (height // 210000) per block; series = ln(fee_share_w), w ∈ {1, 7, 30, 90}.

**Data.** Blockchair public Bitcoin block dumps (gz.blockchair.com/bitcoin/blocks, per-block `fee_total`), heights 277,996→976,966, 0 height gaps after adding the two blocks absent from the dump (854599, 854614) with their real coinbase outputs − subsidy from blockstream.info Esplora (method verified exact on 854600). Cross-check vs mempool.space `/api/v1/mining/blocks/fees/all`: 4,702 overlapping days, median ratio 1.0000, 100% within 5%. 4,708 complete UTC days 2014-01-01→2026-11-21, 0 calendar gaps, no fill. Day D used only from D+1 01:00 UTC. Official daily: `output/btc_fee_share_official_daily.csv`. Yearly median fee share: 2017 10.8%, 2020 5.5%, 2024 3.7%, 2025 0.96%, 2026 0.62% (max 75.4% on 2024-04-20 halving/Runes day).

**Grid.** 4 series × 8 forms (z vs 365d > {0.5,1,1.5,2}; s > SMA{90,180}; s − s.shift{30,90} > 0) × 4 sides (long_off, short_off, both, contra_both) = 128 cells locked before any PnL (scratch/btcfeeshare4h/PRE_REGISTER.json sha256 e0e35501…4661; output/research_btc_fee_share_gate_4h_prereg.csv). **Prior** fs7_z365gt1_long_off; **fallback** fs30_trend_n180_long_off.

**Validation.** Same harness as btc_cdd_dormancy_gate_4h: OKX d8 (from 2023-02-01), Gate d8 (2022-07-01), OKX d7_noBNB (2022-04-01); deep unseen → 2024-10-21, tune → 2026-03-05, post → 2026-11-14; repo fees (perp taker 5.1 bps) + stress (spot 20 / perp 15.1 bps); official funding; placebo shifts ±7/±14/+180/−120/+365/−119 d; neighborhood; untuned new8.

**Results (return %, Sharpe).**
- Baseline: OKX d8 deep +35.14/0.71, tune +85.08/1.47, post +59.90/2.23; Gate d8 deep −3.63/0.09, tune +84.25/1.46, post +60.32/2.25.
- Prior 3/9: wins deep only (OKX +40.91/0.80, Gate +4.79/0.21); flag never on in tune (0%) and ~5% of post days, post identical to baseline, months 0/0 → no live evidence. new8 ≈ baseline.
- Fallback 3/9: post OKX +38.93/1.74, Gate +39.46/1.76 (−21 pp), months 1/3 both venues.
- Best cell (non-prior) fs30_z365gt0.5_long_off 8/9 but post edge thin (OKX +60.81/2.26, Gate +61.83/2.29; +0.9/+1.5 pp), months 1/3 both; neighborhood collapses (z>0.25 post −14.9 pp, z252>0.5 −20 pp, z>0.75 never fires post). new8 post better (OKX +16.0 vs +3.3, Gate +31.1 vs +16.4) but non-prior and unstable.
- Placebos beat the real cells: fallback shifted −120 d / −119 d = 6/9 vs real 3/9.
- Highest post Sharpe cells (fs90_chg_n30 / fs30_chg_n90 contra_both, post +64.66/2.54) gutted tune (+16.1 vs +85.1).

**Verdict.** Rejected. Defaults, code and paper unchanged. Fee share has fallen to <1% after the 2024 halving, so a z/trend flag is regime-structural, not a timing signal.
**Never retest** by changing window w, z threshold / z window, SMA or change length, or side; or by swapping to raw fees (BTC/USD), fees per tx, sats/vB, miner revenue, Puell, hashprice or another fee-share source.
CSV: `output/research_btc_fee_share_gate_4h.csv`, `output/research_btc_fee_share_gate_4h_new8.csv`. Scripts: scratch/btcfeeshare4h (build.py, run.py, new8.py).
