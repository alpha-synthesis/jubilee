# Effect of ε-exploration on the benchmark's recovery reward

Units: US$ per decision on the month-0 explorable cohort. Δ = V(ε = 0) − V(ε = 0.08); positive = exploring loses reward. Intervals: 95%, t over seeds (seeds are the independent unit).

| world | n_seeds | replicates_per_seed | mean_value_eps0 | mean_value_eps | delta_mean | delta_ci95_low | delta_ci95_high | relative_delta_mean | delta_sd_between_seeds | mc_se_per_seed_rms | seeds_with_positive_delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_on | 5 | 2 | 278.13 | 276.61 | +1.53 | +1.26 | +1.79 | +0.548% | 0.22 | 0.36 | 5 |
| B_on | 5 | 2 | 276.39 | 275.32 | +1.08 | +0.83 | +1.32 | +0.393% | 0.20 | 0.39 | 5 |

Recovery rate within the window (share of the cohort):

| world | recovery_rate_eps0 | recovery_rate_eps | recovery_rate_delta_mean | recovery_rate_delta_ci95_low | recovery_rate_delta_ci95_high |
|---|---|---|---|---|---|
| A_on | 0.03232 | 0.03250 | -0.00018 | -0.00021 | -0.00015 |
| B_on | 0.03210 | 0.03233 | -0.00023 | -0.00028 | -0.00018 |

Δ split by whether the loan was explored at month 0 (the two parts add to Δ):

| world | delta_from_month0_explored_mean | delta_from_month0_explored_ci95_low | delta_from_month0_explored_ci95_high | delta_from_other_loans_mean | delta_from_other_loans_ci95_low | delta_from_other_loans_ci95_high | month0_explored_share |
|---|---|---|---|---|---|---|---|
| A_on | +2.19 | +2.08 | +2.31 | -0.67 | -0.84 | -0.50 | 0.0801 |
| B_on | +2.16 | +1.99 | +2.32 | -1.08 | -1.33 | -0.83 | 0.0801 |

World contrast (descriptive; the worlds share seeds and month-0 actions):

| contrast | n_seeds | mean | ci95_low | ci95_high | corr_seed_deltas |
|---|---|---|---|---|---|
| B_on - A_on | 5 | -0.45 | -0.91 | +0.02 | -0.646 |
