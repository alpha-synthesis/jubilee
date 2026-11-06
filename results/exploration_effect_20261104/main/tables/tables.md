# Effect of ε-exploration on the benchmark's recovery reward

Units: US$ per decision on the month-0 explorable cohort. Δ = V(ε = 0) − V(ε = 0.08); positive = exploring loses reward. Intervals: 95%, t over seeds (seeds are the independent unit).

| world | n_seeds | replicates_per_seed | mean_value_eps0 | mean_value_eps | delta_mean | delta_ci95_low | delta_ci95_high | relative_delta_mean | delta_sd_between_seeds | mc_se_per_seed_rms | seeds_with_positive_delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_on | 20 | 1 | 290.04 | 288.38 | +1.66 | +1.41 | +1.92 | +0.575% | 0.55 | 0.53 | 20 |
| B_on | 20 | 1 | 288.54 | 287.13 | +1.41 | +1.12 | +1.70 | +0.490% | 0.62 | 0.57 | 20 |

Recovery rate within the window (share of the cohort):

| world | recovery_rate_eps0 | recovery_rate_eps | recovery_rate_delta_mean | recovery_rate_delta_ci95_low | recovery_rate_delta_ci95_high |
|---|---|---|---|---|---|
| A_on | 0.03352 | 0.03371 | -0.00019 | -0.00021 | -0.00017 |
| B_on | 0.03336 | 0.03358 | -0.00023 | -0.00025 | -0.00020 |

Δ split by whether the loan was explored at month 0 (the two parts add to Δ):

| world | delta_from_month0_explored_mean | delta_from_month0_explored_ci95_low | delta_from_month0_explored_ci95_high | delta_from_other_loans_mean | delta_from_other_loans_ci95_low | delta_from_other_loans_ci95_high | month0_explored_share |
|---|---|---|---|---|---|---|---|
| A_on | +2.36 | +2.24 | +2.48 | -0.69 | -0.90 | -0.48 | 0.0800 |
| B_on | +2.39 | +2.28 | +2.49 | -0.98 | -1.23 | -0.73 | 0.0800 |

World contrast (descriptive; the worlds share seeds and month-0 actions):

| contrast | n_seeds | mean | ci95_low | ci95_high | corr_seed_deltas |
|---|---|---|---|---|---|
| B_on - A_on | 20 | -0.26 | -0.39 | -0.12 | 0.885 |
