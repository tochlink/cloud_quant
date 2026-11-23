# Ethereum Foundation genesis-wallet ETH outflow 1h event → 8-perp basket / ETH perp — REJECTED (2026-11-22)

Short-term family. Pre-registered before any PnL look (scratch/efout1h/PRE_REGISTER.json, sha256 2726e438…2f48, 24 cells, prior + fallback locked at 21:20 PST). Only the event list (times, sizes, recipients) was looked at before the lock.

## Data (official only)
- Official Ethereum-mainnet `eth_getLogs` on the EF genesis / EthDev multisig wallet `0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe`, blocks 0 → 26,475,605 (full history, no Etherscan/Arkham labels, no other EF addresses added).
- Outgoing ETH executions = `SingleTransact(address,uint256,address,bytes)` (topic0 0x92ca3a80…) and `MultiTransact(address,bytes32,uint256,address,bytes)` (0xe7c957c0…) logs, value > 0. 345 outflows in full history; 322 ≥ 100 ETH.
- Since 2022-01-01: 96 qualifying event hours (348,850 ETH total; recipients 0xbc9a…fbc3 ×38, 0xc061…0b6d ×38, 0x4e6b…3cb6 ×17, 0xd864…f079 ×2, 0x9fc3…213e ×1), 48 cluster onsets (no outflow in prior 168h). Only 6 event hours after 2026-03-05.
- Hourly series: 42,893 complete UTC hours 2022-01-01 00:00 → 2026-11-23 04:00 UTC, 0 calendar gaps; hour = official blockTimestamp; zero-event hours are real zeros; incomplete current hour dropped.
- Perps: official OKX 1h candles (from 2022-01-29) + OKX deep official funding; official Gate 1h candles + funding (from 2025-09-24); universes okx_d8, okx_new8 (untuned LINK/LTC/DOT/TRX/BCH/ATOM/NEAR/UNI), gate_d8, plus ETH-only okx_eth / gate_eth.

## Formula
Event hour h = UTC hour with ≥1 qualifying outflow (trigger `all`) or the first such hour after ≥168h with none (trigger `onset168`). Enter at the next 1h perp open, direction short (prior) or long, hold H ∈ {12, 24, 48}h, non-overlapping; target equal-weight 8-perp basket or ETHUSDT perp. Cost 2 × taker 5.1 bps (stress 15.1) + official funding. Splits: train/deep-unseen 2022-02-15→2024-10-21, test →2026-03-05, post →end; Gate window 2025-09-28→end. Placebo: event series shifted ±720h and ±336h.
Prior: `all_short_H24_basket`. Fallback: `onset168_short_H48_basket`.

## Results (mean bps/event, real fees; n in parentheses)
| cell | OKX train | OKX test | OKX post | new8 train/test/post | Gate post | Gate window | n_pos |
|---|---|---|---|---|---|---|---|
| prior all_short_H24_basket | −75.0 (34, t −0.9) | +44.5 (43, t 1.1) | −24.5 (6) | −48.9 / +66.8 / −68.1 | −25.7 (6) | +51.8 (9) | 3/8 |
| fallback onset168_short_H48_basket | −100.2 (28) | −79.1 (12) | +10.0 (6) | −104.5 / −77.9 / +62.0 | +7.0 | +47.5 | 4/8 |
| best all_short_H12_basket | +25.5 (36, t 0.6) | +30.1 (51, t 1.0) | −34.1 (6) | +34.3 / +57.3 / −37.5 | −35.6 | +26.3 | 5/8 |
| ETH-only all_short_H48_eth | −67.2 | −59.5 | +80.7 (6, t 0.5) | — | +78.2 | +111.0 | 3/5 |

- 0 usable cells of 24 (none 8/8 or 5/5; post n = 6 < 8 by construction). Max 5/8.
- Stress fees: prior −95 / +24 / −45 bps train/test/post.
- Placebos (±720h, ±336h) produce means of the same size and either sign (e.g. prior ±720h train −77/+2, post −68/−105), i.e. the event series carries no information beyond noise.
- No stable H neighborhood: short H12 vs H24 vs H48 flip sign in train; long and short mirror each other (no edge on either side).

## Verdict
REJECTED. No default or paper change, no code change. Never retest this family by changing H, direction, the 168h onset window, the ≥100 ETH threshold, basket vs ETH-only, or by adding other EF addresses (0xc061…, 0x9eE4…, Safe/DeFi wallets), EF blog-announced sales, or other foundation/treasury wallets (Arbitrum/Optimism/Solana foundations).

Outputs (local, not pushed): output/research_ef_treasury_outflow_event_1h.csv; official events scratch/efout1h/ef_outflow_official_events.csv; official 1h scratch/efout1h/ef_outflow_official_1h.csv; scripts scratch/efout1h/{probe,build,run,analyze,plog}.py.
