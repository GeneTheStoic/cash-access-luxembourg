# Results (distance metric: road)

| Scenario | Sites | Mean km | Median km | P90 km | Within 1 km | Within 3 km | Within 5 km | 65+ within 5 km | Residents beyond 5 km |
|---|---|---|---|---|---|---|---|---|---|
| Bancomat network as planned (locator, 5 Nov 2026) | 207 | 1.82 | 1.14 | 4.42 | 42.6% | 81.2% | 92.8% | 93.5% | 46,073 |
| OpenStreetMap ATMs, 2019-07-01 | 210 | 2.07 | 1.22 | 5.56 | 40.9% | 77.6% | 87.7% | 88.1% | 79,057 |
| OpenStreetMap ATMs, 2024-01-01 | 246 | 1.93 | 1.16 | 4.95 | 43.0% | 79.3% | 90.1% | 90.9% | 63,497 |
| OpenStreetMap ATMs, 2026-06-01 | 225 | 2.02 | 1.17 | 5.27 | 43.3% | 77.8% | 88.9% | 89.9% | 71,110 |
| OpenStreetMap ATMs, now | 225 | 2.03 | 1.17 | 5.41 | 43.3% | 77.8% | 88.8% | 89.7% | 72,377 |

## Before (OSM, 1 Jan 2024) vs. after (Bancomat plan)

- pop_farther_0_5km: 66,361
- pop_farther_1km: 30,185
- pop_farther_2km: 14,601
- pop_closer_0_5km: 78,464
- pop_newly_beyond_5km: 10,807
- mean_change_km: -0.110
- mean_change_km_65plus: -0.125
- corr_change_share65: -0.072
- corr_change_log_density: 0.125

Note: OpenStreetMap records fewer ATMs than existed (the banks reported 595 machines in 2019). Missing legacy machines can only shorten the true 'before' distances, so increases in distance are lower bounds and decreases are upper bounds, provided the mapped ATMs existed.

## Placement

- Coverage within 5.0 km now: 92.8%
- After 13 greedy additions: 97.1%
- Same number of sites placed by greedy p-median: mean 0.85 km, 99.3% within 5 km
