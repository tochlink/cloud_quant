# Bank of Canada BCPI commodity-price 4h entry gate (REJECTED, 2026-11-27)

Long-term idea: official Bank of Canada Valet weekly commodity price index (BCPI) as an entry gate for default #1 (ma_trend 50/150 4h). Gate only blocks new entries; existing same-direction positions are kept.

- Source: `https://www.bankofcanada.ca/valet/observations/W.BCNE,W.MTLS,W.ENER/json` (BCPI ex-energy, metals & minerals, energy). 569 weekly observations 2016-01-06 -> 2026-11-25, 0 gaps (all steps 7d), no NaN. Fetched as-is, no backfill. Current Valet vintage (no historical vintages stored; BCPI is price-weighted, revisions small - disclosed limitation).
- Lag: observation (Wednesday) D usable from D+5d 00:00 UTC (next Monday); official actual availability is ~D+1-2d, so this is conservative.
- Cells (pre-registered, sha in scratch PRE_REGISTER.sha256, 120 cells): series {bcne, mtls, ener} x {trend n in 8/26/52 weeks (index > n-wk mean), chg n in 8/26 weeks (>0), z104 k in 1.0/1.5/2.0} x sides {long_off, short_off, both, contra_both, cap_short_off}.
- Economic prior (locked before PnL): commodity strength = global growth / risk-on -> cap_short_off and contra_both. Fallback prior: bcne_trend_n26_cap_short_off.
- Method: same framework as other *_gate_4h runs; OKX d8 (from 2023-02), Gate d8 (from 2022-07), OKX d7_noBNB; baseline = default #1 ungated in the same script; real fees; stress 15.1/20 bps; slices deep unseen (<2024-10-21), tune-pre (2024-10-21..2026-03-05), post (2026-03-05..2026-11-14). Perp/funding data on disk ends 2026-11-14 (same dataset as prior runs; not extended).

## Results (return %, Sharpe)
| cell | OKX deep | OKX tune | OKX post | Gate deep | Gate post | months better/worse (OKX / Gate) |
|---|---|---|---|---|---|---|
| base (#1 ungated) | +35.14 / 0.71 | +85.08 / 1.47 | +59.90 / 2.23 | -3.63 / 0.09 | +60.32 / 2.25 | - |
| bcne_trend_n8_contra_both (best 9/9, prior side) | +56.11 / 1.04 | +68.60 / 1.55 | +62.47 / 2.35 | +33.55 / 0.58 | +61.57 / 2.36 | 4/5 and 5/4 |
| bcne_trend_n8_cap_short_off (prior) | +35.08 / 0.73 | +69.93 / 1.53 | +60.16 / 2.28 | -1.95 / 0.11 | +59.29 / 2.29 | 4/5 and 5/4 |
| fallback bcne_trend_n26_cap_short_off | not among top boards (<6/9) | | | | | |

- Neighborhood of bcne_trend_n8_contra_both: n10 8/9, n13 7/9, n6 6/9, n4 collapsed (deep Gate -5).
- Placebos (shift of the same flag): +-7d/+-14d shifts equal or beat the real flag in post (OKX shift-14d +65.5 / 2.54, Gate +66.0 / 2.55); shift180d deep OKX +52.9 so deep edge is not specific.
- new8 untuned (last 4500 bars): contra_both pre -9.2 vs base +29.9 (OKX), post +13.4 vs +3.3, months 6/3 OKX, 5/4 Gate; the shift7d placebo post +28.7 / +30.1 is better than the real cell.
- Verdict: REJECTED. Post edge small (+2.6 pp / +1.2 pp, Sharpe +0.12/+0.11), post months 4/5 and 5/4 fail the >=6/9 bar on both venues, tune-pre return is below baseline (+68.6 vs +85.1), placebos match or beat. Default and paper unchanged.
- Never retest: Bank of Canada BCPI (total / ex-energy / metals / energy / other sub-indices, weekly/monthly/daily) as a 4h gate by changing n, side, z, series, or by using similar commodity-price indices from other central banks.
- CSV: output/research_bcpi_commodity_gate_4h.csv (+ _new8.csv); official weekly: output/bcpi_weekly_official.csv (not pushed).
