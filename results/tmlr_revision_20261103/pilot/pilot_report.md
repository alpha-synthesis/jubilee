# Pilot report — tmlr_pilot_20261103

Development pilot: cost, memory and reference precision (control, chosen confounded condition, world B, original stress cell). Dev seeds only; not confirmatory.

Development seeds [9001, 9002, 9003]; 4 reference replicates per run; population
1,000,000 borrowers per replicate (batch 50,000); every value in
US$ per decision on the month-0 explorable cohort.

## Cost and memory (measured under the pilot's concurrency)

| kind | n | wall_median | wall_max | cpu_median | rss_max_mb |
|---|---|---|---|---|---|
| annotator | 12 | 566 | 616 | 565 | 667 |
| estimate | 12 | 175 | 184 | 336 | 1346 |
| logs | 12 | 277 | 343 | 278 | 1058 |
| reference | 48 | 1.1e+03 | 1.24e+03 | 1.1e+03 | 744 |

CPU seconds per unit: {"logs": 278.2, "annotator_per_target": 188.3, "reference_per_candidate": 182.8, "estimate_per_run": 335.8}.

## Reference precision (one replicate of 1,000,000 borrowers)

Values (SE of one replicate's cohort mean, from the per-loan variance; the
between/within ratio compares the spread of the 4 replicate means with it):

| cond | candidate | mean_value | se_one_replicate_median | se_one_replicate_max | between_over_within_median |
|---|---|---|---|---|---|
| A_off | pi_b | 277 | 2.71 | 2.89 | 1.14 |
| A_off | pi_far | 261 | 2.44 | 2.6 | 1.18 |
| A_off | pi_near | 290 | 2.83 | 3.01 | 1.11 |
| A_off | pi_stage | 303 | 2.97 | 3.16 | 0.995 |
| A_on | pi_b | 285 | 2.76 | 2.95 | 1.05 |
| A_on | pi_far | 269 | 2.47 | 2.63 | 1.08 |
| A_on | pi_near | 299 | 2.86 | 3.05 | 0.992 |
| A_on | pi_stage | 312 | 3 | 3.2 | 0.946 |
| B_on | pi_b | 284 | 2.76 | 2.94 | 0.871 |
| B_on | pi_far | 263 | 2.45 | 2.61 | 0.929 |
| B_on | pi_near | 300 | 2.88 | 3.06 | 0.85 |
| B_on | pi_stage | 315 | 3.03 | 3.22 | 0.938 |
| S18_on | pi_b | 287 | 2.8 | 3.1 | 1.07 |
| S18_on | pi_far | 270 | 2.48 | 2.73 | 1.25 |
| S18_on | pi_near | 298 | 2.86 | 3.16 | 0.919 |
| S18_on | pi_stage | 311 | 3 | 3.32 | 1.06 |

Paired gaps between decision candidates (same population and draws within a
replicate; `variance_reduction` = independent-sampling variance / paired variance):

| cond | pair | mean_gap | se_one_replicate_median | se_one_replicate_max | corr_within_median | variance_reduction_median |
|---|---|---|---|---|---|---|
| A_off | pi_b-pi_far | 15.3 | 0.841 | 0.898 | 0.952 | 18.8 |
| A_off | pi_b-pi_near | -13.1 | 0.681 | 0.737 | 0.97 | 32.2 |
| A_off | pi_b-pi_stage | -26.2 | 0.798 | 0.858 | 0.964 | 24.9 |
| A_off | pi_far-pi_stage | -41.5 | 0.989 | 1.05 | 0.951 | 15.1 |
| A_off | pi_near-pi_far | 28.5 | 0.86 | 0.91 | 0.958 | 19 |
| A_off | pi_near-pi_stage | -13 | 0.625 | 0.663 | 0.978 | 42.9 |
| A_on | pi_b-pi_far | 16.7 | 0.881 | 0.934 | 0.949 | 17.7 |
| A_on | pi_b-pi_near | -13.2 | 0.703 | 0.762 | 0.968 | 31 |
| A_on | pi_b-pi_stage | -26.2 | 0.804 | 0.867 | 0.964 | 25.2 |
| A_on | pi_far-pi_stage | -42.9 | 0.996 | 1.05 | 0.952 | 15.3 |
| A_on | pi_near-pi_far | 29.9 | 0.865 | 0.916 | 0.959 | 19.4 |
| A_on | pi_near-pi_stage | -13 | 0.63 | 0.668 | 0.978 | 43.4 |
| B_on | pi_b-pi_far | 21.1 | 0.82 | 0.868 | 0.957 | 20.3 |
| B_on | pi_b-pi_near | -16 | 0.712 | 0.758 | 0.969 | 31.3 |
| B_on | pi_b-pi_stage | -31.2 | 0.838 | 0.882 | 0.962 | 23.9 |
| B_on | pi_far-pi_stage | -52.2 | 0.89 | 0.94 | 0.969 | 19.1 |
| B_on | pi_near-pi_far | 37.1 | 0.766 | 0.807 | 0.972 | 24.8 |
| B_on | pi_near-pi_stage | -15.1 | 0.704 | 0.739 | 0.973 | 35.1 |
| S18_on | pi_b-pi_far | 17.7 | 0.963 | 1.06 | 0.941 | 15.1 |
| S18_on | pi_b-pi_near | -10.9 | 0.76 | 0.823 | 0.964 | 27.8 |
| S18_on | pi_b-pi_stage | -23.9 | 0.855 | 0.924 | 0.959 | 23.1 |
| S18_on | pi_far-pi_stage | -41.5 | 1 | 1.11 | 0.951 | 15 |
| S18_on | pi_near-pi_far | 28.5 | 0.871 | 0.968 | 0.956 | 18.6 |
| S18_on | pi_near-pi_stage | -13 | 0.641 | 0.691 | 0.977 | 41.9 |

## Variation across regional shocks (a separate component, not Monte-Carlo error)

| cond | candidate | mean | std | count |
|---|---|---|---|---|
| A_off | pi_b | 277 | 34.2 | 3 |
| A_off | pi_far | 261 | 32.2 | 3 |
| A_off | pi_near | 290 | 35.5 | 3 |
| A_off | pi_stage | 303 | 37.4 | 3 |
| A_on | pi_b | 285 | 35.4 | 3 |
| A_on | pi_far | 269 | 33 | 3 |
| A_on | pi_near | 299 | 36.6 | 3 |
| A_on | pi_stage | 312 | 38.4 | 3 |
| B_on | pi_b | 284 | 35.2 | 3 |
| B_on | pi_far | 263 | 32.3 | 3 |
| B_on | pi_near | 300 | 36.8 | 3 |
| B_on | pi_stage | 315 | 38.9 | 3 |
| S18_on | pi_b | 287 | 59.8 | 3 |
| S18_on | pi_far | 270 | 55.3 | 3 |
| S18_on | pi_near | 298 | 61.6 | 3 |
| S18_on | pi_stage | 311 | 64.5 | 3 |

## Bin approximation (centre dose minus dose uniform over the bin)

| cond | pair | mean_gap | mean_se | n |
|---|---|---|---|---|
| A_off | pi_far-pi_far_binU | 0.114 | 0.0684 | 3 |
| A_off | pi_near-pi_near_binU | 0.043 | 0.0802 | 3 |
| A_on | pi_far-pi_far_binU | 0.107 | 0.0687 | 3 |
| A_on | pi_near-pi_near_binU | 0.0352 | 0.0802 | 3 |
| B_on | pi_far-pi_far_binU | 0.0897 | 0.0667 | 3 |
| B_on | pi_near-pi_near_binU | 0.0159 | 0.0851 | 3 |
| S18_on | pi_far-pi_far_binU | 0.029 | 0.0709 | 3 |
| S18_on | pi_near-pi_near_binU | 0.0417 | 0.0791 | 3 |

## Sizing against the precision rule (fixed before inspection)

Rule: SE of every candidate value ≤ 2.0 and of every gap between decision
candidates ≤ 1.0 US$/decision per run, with R replicates. Needed R by condition —
values: {'A_off': 3, 'A_on': 3, 'B_on': 3, 'S18_on': 3}; gaps: {'A_off': 2, 'A_on': 2, 'B_on': 1, 'S18_on': 2}.
**R needed = 3.** Projected campaign CPU-hours (80 runs, pilot concurrency):
{1: 42.4, 2: 58.7, 3: 74.9, 4: 91.2, 6: 123.7, 8: 156.2} (ceiling 150.0); largest affordable R =
6.
