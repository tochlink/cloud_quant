# Solana priority-fee (leader Fee reward) 1h shock → 8-perp basket — REJECTED (2026-11-21)

Short-term family. Pre-registered before any PnL (PRE_REGISTER sha256 56c40e55…, 288 cells, prior/fallback locked).

## Data (official only)
- Official Solana mainnet RPC `getBlock(slot, {transactionDetails:"none", rewards:true, commitment:"finalized"})`, 2 blocks per UTC hour (targets :15 and :45; slot from linear interpolation between official `getBlockTime` anchors every 500k slots; skipped slot → next slot ≤20).
- Per block: `fee_reward` = Σ rewards[rewardType=="Fee"].lamports (slot leader's fee revenue). Bucketed into the UTC hour of the block's official blockTime (no lookahead). Hours with 0 samples = NaN, never interpolated.
- 60,959 blocks, 30,480 hours 2023-06-01 00:00 → 2026-11-21 23:00 UTC, 4 empty hours, 0 calendar gaps.
- SIMD-0096 (epoch 741, slot 320,112,000, 2025-02-12): leader reward changed from 50% of all fees to 100% priority + 50% base; signals masked for the 168h after the step.
- Perps: official OKX/Gate 1h candles + official funding; universes okx_d8, gate_d8, okx_new8 (untuned LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI).

## Formula
x_h = log1p(mean or max of the hour's sampled fee_reward). μ, σ = rolling 168h (min 84) ending h−1.
z = (Σ_{L} x − L·μ)/(σ·√L), L∈{1,4,8}; event if z ≥ k (high) or z ≤ −k (low), k∈{3,4,5}; enter next 1h open, long or short equal-weight basket, hold H∈{6,12,24,48}h, non-overlapping; cost 2×taker 5.1 bps (stress 15.1) + official funding.
Prior: mean L4 k3 high short H24. Fallback: max L4 k3 high short H24.

## Results (mean bps/event, real fees)
| cell | OKX train | OKX test | OKX post | new8 test | new8 post | Gate post | n_pos/8 |
|---|---|---|---|---|---|---|---|
| prior mean L4 k3 high short H24 | −15.7 | −48.4 | −3.3 | −58.3 | −25.8 | −4.2 | 1 |
| fallback max L4 k3 high short H24 | −19.9 | −19.9 | +40.6 (t 0.99) | −44.9 | +13.2 | +39.9 | 5 |

- Fallback post edge below its own ±720h placebos (+26.6 / +42.1 bps OKX post); post months 5/9 on both venues.
- 5 usable 8/8 cells, all non-prior, n≈10 per split, every t ≤ 1.6; L×k and H neighborhoods gappy (sign flips at adjacent k/L).

## Verdict
REJECTED. No default or paper change. Do not retest by changing L, k, H, side, direction, mean/max, sampling density, or by swapping in compute-unit price, Jito tips, or other Solana fee series.

Outputs (local): output/research_solana_priority_fee_shock_event_1h.csv; official hourly scratch/solprio1h/solana_priority_fee_official_1h.csv. Live recorder (getRecentPrioritizationFees, official RPC) keeps running for forward data.
