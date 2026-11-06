# Import-ready tables (units: US$ per decision, month-0 explorable cohort)

## T0. Tabular DM, IS and SNIPS coincide (largest |difference| over runs and targets)

| cond | abs_dm_minus_is | abs_dm_minus_snips |
|---|---|---|
| A_off | 0.2142 | 0.0508 |
| A_on | 0.2215 | 0.0745 |
| B_off | 0.2111 | 0.0489 |
| B_on | 0.2208 | 0.0776 |

## T1. Reference values (mean over seeds) and Monte-Carlo SE per run

| cond | candidate | seeds | mean_value | sd_across_seeds | median_mc_se | max_mc_se |
|---|---|---|---|---|---|---|
| A_off | π_b | 20 | 278.92 | 17.49 | 1.57 | 1.68 |
| A_off | π_visit | 20 | 263.52 | 16.39 | 1.41 | 1.51 |
| A_off | π_sms | 20 | 292.19 | 18.36 | 1.63 | 1.75 |
| A_off | π_stage | 20 | 305.36 | 19.18 | 1.72 | 1.84 |
| A_on | π_b | 20 | 288.0 | 18.21 | 1.6 | 1.72 |
| A_on | π_visit | 20 | 271.01 | 17.02 | 1.43 | 1.53 |
| A_on | π_sms | 20 | 301.15 | 19.12 | 1.66 | 1.78 |
| A_on | π_stage | 20 | 314.35 | 19.94 | 1.74 | 1.87 |
| B_off | π_b | 20 | 273.61 | 17.2 | 1.56 | 1.67 |
| B_off | π_visit | 20 | 254.37 | 15.94 | 1.39 | 1.49 |
| B_off | π_sms | 20 | 289.26 | 18.08 | 1.63 | 1.75 |
| B_off | π_stage | 20 | 304.64 | 19.2 | 1.72 | 1.84 |
| B_on | π_b | 20 | 286.43 | 18.13 | 1.6 | 1.71 |
| B_on | π_visit | 20 | 265.32 | 16.76 | 1.42 | 1.52 |
| B_on | π_sms | 20 | 302.45 | 19.07 | 1.66 | 1.78 |
| B_on | π_stage | 20 | 317.96 | 20.2 | 1.75 | 1.88 |

## T2. Reference gaps between candidates (paired Monte-Carlo SE per run)

| cond | pair | seeds | mean_gap | median_paired_se | max_paired_se | median_corr |
|---|---|---|---|---|---|---|
| A_off | pi_b-pi_far | 20 | 15.399 | 0.488 | 0.519 | 0.952 |
| A_off | pi_b-pi_near | 20 | -13.271 | 0.402 | 0.427 | 0.969 |
| A_off | pi_b-pi_stage | 20 | -26.436 | 0.468 | 0.5 | 0.964 |
| A_off | pi_far-pi_stage | 20 | -41.836 | 0.572 | 0.605 | 0.952 |
| A_off | pi_near-pi_far | 20 | 28.67 | 0.497 | 0.525 | 0.958 |
| A_off | pi_near-pi_stage | 20 | -13.166 | 0.362 | 0.386 | 0.978 |
| A_on | pi_b-pi_far | 20 | 16.994 | 0.506 | 0.54 | 0.95 |
| A_on | pi_b-pi_near | 20 | -13.145 | 0.412 | 0.439 | 0.968 |
| A_on | pi_b-pi_stage | 20 | -26.344 | 0.471 | 0.506 | 0.964 |
| A_on | pi_far-pi_stage | 20 | -43.338 | 0.576 | 0.609 | 0.953 |
| A_on | pi_near-pi_far | 20 | 30.139 | 0.5 | 0.528 | 0.959 |
| A_on | pi_near-pi_stage | 20 | -13.199 | 0.365 | 0.388 | 0.978 |
| B_off | pi_b-pi_far | 20 | 19.246 | 0.454 | 0.483 | 0.959 |
| B_off | pi_b-pi_near | 20 | -15.646 | 0.397 | 0.423 | 0.97 |
| B_off | pi_b-pi_stage | 20 | -31.029 | 0.476 | 0.509 | 0.963 |
| B_off | pi_far-pi_stage | 20 | -50.275 | 0.507 | 0.539 | 0.969 |
| B_off | pi_near-pi_far | 20 | 34.892 | 0.44 | 0.467 | 0.97 |
| B_off | pi_near-pi_stage | 20 | -15.383 | 0.402 | 0.425 | 0.973 |
| B_on | pi_b-pi_far | 20 | 21.106 | 0.475 | 0.504 | 0.957 |
| B_on | pi_b-pi_near | 20 | -16.023 | 0.414 | 0.442 | 0.969 |
| B_on | pi_b-pi_stage | 20 | -31.534 | 0.486 | 0.521 | 0.962 |
| B_on | pi_far-pi_stage | 20 | -52.641 | 0.513 | 0.546 | 0.969 |
| B_on | pi_near-pi_far | 20 | 37.129 | 0.445 | 0.471 | 0.971 |
| B_on | pi_near-pi_stage | 20 | -15.511 | 0.406 | 0.428 | 0.973 |

## T3 (tabular). Mean error vs reference ± SE over seeds

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | -1.1 ± 4.8 | +2.0 ± 3.1 | -0.1 ± 6.1 |
| A_off | dm_blind | -1.5 ± 4.1 | +7.4 ± 2.7 | +2.6 ± 5.2 |
| A_off | is | -1.2 ± 4.8 | +1.9 ± 3.1 | -0.3 ± 6.1 |
| A_off | snips | -1.1 ± 4.8 | +2.0 ± 3.1 | -0.1 ± 6.1 |
| A_off | dr | -1.1 ± 4.8 | +2.5 ± 3.2 | -0.3 ± 6.1 |
| A_off | dm_plus_is | -1.0 ± 4.8 | +2.2 ± 3.1 | -0.0 ± 6.1 |
| A_off | pilot_is | -5.3 ± 13.8 | -4.9 ± 14.6 | +4.9 ± 13.6 |
| A_off | pilot_dr | -4.6 ± 13.1 | -3.6 ± 13.6 | +2.7 ± 12.4 |
| A_off | dm_refit | -1.1 ± 4.8 | +2.0 ± 3.1 | -0.1 ± 6.1 |
| A_on | dm | -57.5 ± 3.8 | +4.9 ± 3.7 | -12.6 ± 6.7 |
| A_on | dm_blind | -58.8 ± 3.2 | +8.7 ± 4.1 | -9.4 ± 5.6 |
| A_on | is | -57.7 ± 3.8 | +4.8 ± 3.8 | -12.8 ± 6.7 |
| A_on | snips | -57.5 ± 3.8 | +4.9 ± 3.8 | -12.6 ± 6.7 |
| A_on | dr | -57.5 ± 3.8 | +5.3 ± 3.9 | -12.3 ± 6.8 |
| A_on | dm_plus_is | -57.4 ± 3.8 | +5.1 ± 3.8 | -12.5 ± 6.7 |
| A_on | pilot_is | -4.9 ± 14.1 | -1.2 ± 18.1 | +8.6 ± 15.4 |
| A_on | pilot_dr | -4.9 ± 13.6 | +0.1 ± 17.3 | +6.0 ± 14.5 |
| A_on | dm_refit | -57.5 ± 3.8 | +4.9 ± 3.7 | -12.6 ± 6.7 |
| B_off | dm | -3.9 ± 4.6 | +0.6 ± 3.1 | -1.7 ± 5.5 |
| B_off | dm_blind | -2.7 ± 4.1 | +9.2 ± 2.5 | -0.4 ± 4.7 |
| B_off | is | -4.1 ± 4.6 | +0.4 ± 3.1 | -1.8 ± 5.5 |
| B_off | snips | -4.0 ± 4.6 | +0.6 ± 3.1 | -1.6 ± 5.5 |
| B_off | dr | -4.0 ± 4.7 | +0.8 ± 3.1 | -1.7 ± 5.5 |
| B_off | dm_plus_is | -3.9 ± 4.6 | +0.7 ± 3.1 | -1.6 ± 5.5 |
| B_off | pilot_is | -6.9 ± 13.6 | -10.9 ± 13.6 | +15.9 ± 15.3 |
| B_off | pilot_dr | -6.2 ± 12.8 | -10.0 ± 12.6 | +13.9 ± 13.9 |
| B_off | dm_refit | -3.9 ± 4.6 | +0.6 ± 3.1 | -1.7 ± 5.5 |
| B_on | dm | -56.6 ± 3.6 | +4.9 ± 3.7 | -10.8 ± 6.1 |
| B_on | dm_blind | -56.6 ± 3.3 | +11.8 ± 4.1 | -9.4 ± 5.2 |
| B_on | is | -56.7 ± 3.6 | +4.7 ± 3.7 | -10.9 ± 6.1 |
| B_on | snips | -56.6 ± 3.6 | +4.9 ± 3.7 | -10.8 ± 6.1 |
| B_on | dr | -56.7 ± 3.6 | +5.1 ± 3.8 | -10.3 ± 6.1 |
| B_on | dm_plus_is | -56.5 ± 3.6 | +5.0 ± 3.7 | -10.7 ± 6.1 |
| B_on | pilot_is | -8.6 ± 11.5 | -4.6 ± 18.5 | +15.3 ± 14.6 |
| B_on | pilot_dr | -8.6 ± 11.0 | -3.3 ± 17.5 | +13.0 ± 13.4 |
| B_on | dm_refit | -56.6 ± 3.6 | +4.9 ± 3.7 | -10.8 ± 6.1 |

## T4 (tabular). RMSE ± bootstrap-over-seeds SE

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | 21.1 ± 2.8 | 13.7 ± 1.7 | 26.7 ± 4.1 |
| A_off | dm_blind | 18.0 ± 2.2 | 13.9 ± 1.5 | 22.6 ± 2.4 |
| A_off | dm_plus_is | 21.1 ± 2.8 | 13.7 ± 1.7 | 26.7 ± 4.1 |
| A_off | dm_refit | 21.1 ± 2.8 | 13.7 ± 1.7 | 26.7 ± 4.1 |
| A_off | dr | 21.1 ± 2.8 | 14.0 ± 1.7 | 26.6 ± 4.0 |
| A_off | is | 21.1 ± 2.8 | 13.7 ± 1.7 | 26.7 ± 4.1 |
| A_off | pilot_dr | 57.4 ± 11.3 | 59.5 ± 6.6 | 54.2 ± 8.0 |
| A_off | pilot_is | 60.3 ± 10.9 | 63.7 ± 7.2 | 59.4 ± 9.1 |
| A_off | snips | 21.1 ± 2.8 | 13.7 ± 1.7 | 26.7 ± 4.1 |
| A_on | dm | 59.8 ± 3.6 | 17.1 ± 1.9 | 31.9 ± 4.0 |
| A_on | dm_blind | 60.5 ± 3.2 | 20.0 ± 2.9 | 26.2 ± 3.8 |
| A_on | dm_plus_is | 59.7 ± 3.6 | 17.1 ± 1.9 | 31.8 ± 4.0 |
| A_on | dm_refit | 59.8 ± 3.6 | 17.1 ± 1.9 | 31.9 ± 4.0 |
| A_on | dr | 59.8 ± 3.6 | 17.6 ± 2.2 | 32.0 ± 4.0 |
| A_on | is | 60.0 ± 3.6 | 17.0 ± 1.9 | 31.9 ± 4.0 |
| A_on | pilot_dr | 59.5 ± 11.3 | 75.4 ± 9.0 | 63.4 ± 9.0 |
| A_on | pilot_is | 61.6 ± 11.2 | 79.1 ± 9.7 | 67.6 ± 8.8 |
| A_on | snips | 59.8 ± 3.6 | 17.1 ± 1.9 | 31.9 ± 4.0 |
| B_off | dm | 20.6 ± 2.5 | 13.3 ± 1.7 | 24.1 ± 3.7 |
| B_off | dm_blind | 18.3 ± 1.9 | 14.2 ± 1.5 | 20.5 ± 2.9 |
| B_off | dm_plus_is | 20.6 ± 2.4 | 13.4 ± 1.7 | 24.1 ± 3.6 |
| B_off | dm_refit | 20.6 ± 2.5 | 13.3 ± 1.7 | 24.1 ± 3.7 |
| B_off | dr | 20.7 ± 2.5 | 13.3 ± 1.7 | 24.0 ± 3.6 |
| B_off | is | 20.6 ± 2.5 | 13.4 ± 1.7 | 24.1 ± 3.7 |
| B_off | pilot_dr | 56.3 ± 11.0 | 55.7 ± 5.5 | 62.1 ± 7.6 |
| B_off | pilot_is | 59.5 ± 10.8 | 60.3 ± 5.8 | 68.5 ± 8.6 |
| B_off | snips | 20.6 ± 2.5 | 13.3 ± 1.7 | 24.1 ± 3.7 |
| B_on | dm | 58.7 ± 3.4 | 16.9 ± 2.2 | 28.6 ± 4.5 |
| B_on | dm_blind | 58.4 ± 3.2 | 21.4 ± 3.4 | 24.4 ± 4.4 |
| B_on | dm_plus_is | 58.6 ± 3.4 | 17.0 ± 2.3 | 28.6 ± 4.5 |
| B_on | dm_refit | 58.7 ± 3.4 | 16.9 ± 2.2 | 28.6 ± 4.5 |
| B_on | dr | 58.9 ± 3.4 | 17.4 ± 2.7 | 28.5 ± 4.4 |
| B_on | is | 58.9 ± 3.4 | 16.9 ± 2.2 | 28.6 ± 4.5 |
| B_on | pilot_dr | 48.7 ± 8.2 | 76.2 ± 7.8 | 59.9 ± 7.6 |
| B_on | pilot_is | 50.9 ± 8.3 | 80.6 ± 8.5 | 65.3 ± 7.5 |
| B_on | snips | 58.8 ± 3.4 | 17.0 ± 2.2 | 28.6 ± 4.5 |

## T3 (nontabular). Mean error vs reference ± SE over seeds

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | -4.3 ± 1.9 | +1.9 ± 1.3 | -9.3 ± 1.5 |
| A_off | is | +14.1 ± 5.2 | +11.4 ± 5.8 | +8.6 ± 6.0 |
| A_off | snips | -0.7 ± 4.9 | +1.6 ± 5.7 | +2.4 ± 5.8 |
| A_off | dr | -3.9 ± 5.1 | +1.6 ± 5.7 | +1.3 ± 6.1 |
| A_off | pilot_dr | -5.9 ± 13.7 | -3.3 ± 14.0 | +2.4 ± 13.1 |
| A_on | dm | -53.0 ± 1.9 | +3.0 ± 1.9 | -7.2 ± 2.6 |
| A_on | is | -43.9 ± 3.9 | +17.3 ± 6.8 | -8.4 ± 6.8 |
| A_on | snips | -53.5 ± 3.7 | +6.6 ± 6.6 | -10.3 ± 6.8 |
| A_on | dr | -55.3 ± 3.9 | +6.5 ± 6.5 | -10.2 ± 7.2 |
| A_on | pilot_dr | -4.8 ± 13.8 | +0.7 ± 17.4 | +6.7 ± 14.9 |
| B_off | dm | -3.7 ± 1.9 | +1.4 ± 1.1 | -14.2 ± 1.3 |
| B_off | is | +10.7 ± 5.0 | +9.4 ± 4.8 | +9.0 ± 6.0 |
| B_off | snips | -3.5 ± 4.7 | -0.3 ± 4.7 | +2.8 ± 5.8 |
| B_off | dr | -7.3 ± 4.8 | -0.4 ± 4.7 | +1.7 ± 6.1 |
| B_off | pilot_dr | -7.5 ± 13.1 | -10.1 ± 13.3 | +13.9 ± 14.4 |
| B_on | dm | -50.3 ± 2.0 | +3.9 ± 1.8 | -9.3 ± 2.2 |
| B_on | is | -42.9 ± 3.9 | +17.5 ± 6.8 | -3.8 ± 6.7 |
| B_on | snips | -52.3 ± 3.8 | +6.8 ± 6.6 | -5.8 ± 6.6 |
| B_on | dr | -53.8 ± 4.0 | +6.7 ± 6.5 | -5.9 ± 7.0 |
| B_on | pilot_dr | -8.8 ± 11.2 | -3.2 ± 18.1 | +12.1 ± 14.1 |

## T4 (nontabular). RMSE ± bootstrap-over-seeds SE

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | 9.2 ± 1.9 | 6.0 ± 0.7 | 11.4 ± 1.6 |
| A_off | dr | 22.5 ± 3.3 | 25.0 ± 4.3 | 26.8 ± 3.8 |
| A_off | is | 26.7 ± 5.4 | 27.9 ± 5.3 | 27.7 ± 4.6 |
| A_off | pilot_dr | 60.0 ± 12.0 | 61.3 ± 6.9 | 57.0 ± 8.2 |
| A_off | snips | 21.3 ± 3.5 | 24.9 ± 4.3 | 25.2 ± 3.5 |
| A_on | dm | 53.6 ± 1.9 | 8.7 ± 1.3 | 13.4 ± 2.6 |
| A_on | dr | 57.9 ± 3.7 | 29.1 ± 6.6 | 33.0 ± 3.4 |
| A_on | is | 47.0 ± 3.7 | 34.2 ± 7.3 | 30.8 ± 3.4 |
| A_on | pilot_dr | 60.1 ± 11.9 | 75.9 ± 8.6 | 65.5 ± 9.0 |
| A_on | snips | 55.9 ± 3.6 | 29.5 ± 6.3 | 31.2 ± 3.4 |
| B_off | dm | 9.2 ± 1.7 | 5.2 ± 0.4 | 15.3 ± 1.4 |
| B_off | dr | 22.3 ± 2.2 | 20.4 ± 2.9 | 26.5 ± 2.0 |
| B_off | is | 24.3 ± 3.9 | 22.9 ± 3.9 | 27.7 ± 2.5 |
| B_off | pilot_dr | 57.8 ± 11.7 | 58.9 ± 5.9 | 64.1 ± 7.2 |
| B_off | snips | 20.9 ± 2.4 | 20.4 ± 3.0 | 25.3 ± 1.8 |
| B_on | dm | 51.0 ± 1.9 | 8.7 ± 1.4 | 13.3 ± 2.1 |
| B_on | dr | 56.6 ± 3.6 | 29.1 ± 7.3 | 31.1 ± 3.8 |
| B_on | is | 46.1 ± 3.5 | 34.3 ± 7.9 | 29.4 ± 3.8 |
| B_on | pilot_dr | 49.7 ± 8.9 | 79.0 ± 8.0 | 62.5 ± 7.6 |
| B_on | snips | 54.8 ± 3.5 | 29.6 ± 6.9 | 29.5 ± 3.8 |

## T5. Logged mean of the incumbent minus its independent reference (should be 0 in expectation)

| cond | n_defined | mean_error | se_mean_error |
|---|---|---|---|
| A_off | 20 | 0.58 | 0.79 |
| A_on | 20 | 0.28 | 0.83 |
| B_off | 20 | -0.04 | 0.71 |
| B_on | 20 | -0.08 | 0.77 |

## T6. Selection over the candidates (regret in recovery US$/decision)

| cond | regime | estimator | n_defined | n_top_resolved | correct_among_resolved | correct_all | mean_regret | se_mean_regret | mean_regret_resolved_runs | mean_gain_vs_incumbent | se_mean_gain_vs_incumbent | n_picks_resolved_worse_than_incumbent | n_picks_resolved_better_than_incumbent | picks | ref_best |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_off | nontabular | dm | 20 | 20 | 11 | 11 | 5.98 | 1.52 | 5.98 | 20.45 | 1.57 | 0 | 20 | {"pi_near": 9, "pi_stage": 11} | {"pi_stage": 20} |
| A_off | nontabular | dr | 20 | 20 | 13 | 13 | 7.3 | 2.67 | 7.3 | 19.14 | 2.73 | 1 | 17 | {"pi_b": 2, "pi_far": 1, "pi_near": 4, "pi_stage": 13} | {"pi_stage": 20} |
| A_off | nontabular | is | 20 | 20 | 11 | 11 | 9.31 | 2.96 | 9.31 | 17.12 | 3.04 | 2 | 17 | {"pi_b": 1, "pi_far": 2, "pi_near": 6, "pi_stage": 11} | {"pi_stage": 20} |
| A_off | nontabular | pilot_dr | 20 | 20 | 6 | 6 | 16.11 | 3.31 | 16.11 | 10.33 | 3.4 | 4 | 14 | {"pi_b": 2, "pi_far": 4, "pi_near": 8, "pi_stage": 6} | {"pi_stage": 20} |
| A_off | nontabular | snips | 20 | 20 | 12 | 12 | 7.93 | 2.65 | 7.93 | 18.5 | 2.7 | 1 | 17 | {"pi_b": 2, "pi_far": 1, "pi_near": 5, "pi_stage": 12} | {"pi_stage": 20} |
| A_off | tabular | dm | 20 | 20 | 12 | 12 | 6.74 | 2.34 | 6.74 | 19.7 | 2.32 | 1 | 19 | {"pi_far": 1, "pi_near": 7, "pi_stage": 12} | {"pi_stage": 20} |
| A_off | tabular | dm_blind | 20 | 20 | 14 | 14 | 4.01 | 1.41 | 4.01 | 22.42 | 1.39 | 0 | 20 | {"pi_near": 6, "pi_stage": 14} | {"pi_stage": 20} |
| A_off | tabular | dm_plus_is | 20 | 20 | 12 | 12 | 6.74 | 2.34 | 6.74 | 19.7 | 2.32 | 1 | 19 | {"pi_far": 1, "pi_near": 7, "pi_stage": 12} | {"pi_stage": 20} |
| A_off | tabular | dr | 20 | 20 | 12 | 12 | 6.74 | 2.34 | 6.74 | 19.7 | 2.32 | 1 | 19 | {"pi_far": 1, "pi_near": 7, "pi_stage": 12} | {"pi_stage": 20} |
| A_off | tabular | is | 20 | 20 | 12 | 12 | 6.74 | 2.34 | 6.74 | 19.7 | 2.32 | 1 | 19 | {"pi_far": 1, "pi_near": 7, "pi_stage": 12} | {"pi_stage": 20} |
| A_off | tabular | pilot_dr | 20 | 20 | 7 | 7 | 14.63 | 3.32 | 14.63 | 11.81 | 3.49 | 4 | 15 | {"pi_b": 1, "pi_far": 4, "pi_near": 8, "pi_stage": 7} | {"pi_stage": 20} |
| A_off | tabular | pilot_is | 20 | 20 | 6 | 6 | 16.07 | 3.31 | 16.07 | 10.36 | 3.41 | 4 | 14 | {"pi_b": 2, "pi_far": 4, "pi_near": 8, "pi_stage": 6} | {"pi_stage": 20} |
| A_off | tabular | snips | 20 | 20 | 12 | 12 | 6.74 | 2.34 | 6.74 | 19.7 | 2.32 | 1 | 19 | {"pi_far": 1, "pi_near": 7, "pi_stage": 12} | {"pi_stage": 20} |
| A_on | nontabular | dm | 20 | 20 | 11 | 11 | 6.12 | 1.56 | 6.12 | 20.22 | 1.43 | 0 | 20 | {"pi_near": 9, "pi_stage": 11} | {"pi_stage": 20} |
| A_on | nontabular | dr | 20 | 20 | 8 | 8 | 9.88 | 2.14 | 9.88 | 16.47 | 2.18 | 0 | 17 | {"pi_b": 3, "pi_near": 9, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | nontabular | is | 20 | 20 | 8 | 8 | 9.88 | 2.14 | 9.88 | 16.47 | 2.18 | 0 | 17 | {"pi_b": 3, "pi_near": 9, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | nontabular | pilot_dr | 20 | 20 | 7 | 7 | 14.2 | 3.22 | 14.2 | 12.14 | 3.34 | 3 | 15 | {"pi_b": 2, "pi_far": 3, "pi_near": 8, "pi_stage": 7} | {"pi_stage": 20} |
| A_on | nontabular | snips | 20 | 20 | 8 | 8 | 9.88 | 2.14 | 9.88 | 16.47 | 2.18 | 0 | 17 | {"pi_b": 3, "pi_near": 9, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | dm | 20 | 20 | 8 | 8 | 8.57 | 1.73 | 8.57 | 17.77 | 1.76 | 0 | 19 | {"pi_b": 1, "pi_near": 11, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | dm_blind | 20 | 20 | 8 | 8 | 8.0 | 1.51 | 8.0 | 18.34 | 1.46 | 0 | 20 | {"pi_near": 12, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | dm_plus_is | 20 | 20 | 8 | 8 | 8.57 | 1.73 | 8.57 | 17.77 | 1.76 | 0 | 19 | {"pi_b": 1, "pi_near": 11, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | dr | 20 | 20 | 8 | 8 | 8.57 | 1.73 | 8.57 | 17.77 | 1.76 | 0 | 19 | {"pi_b": 1, "pi_near": 11, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | is | 20 | 20 | 8 | 8 | 8.57 | 1.73 | 8.57 | 17.77 | 1.76 | 0 | 19 | {"pi_b": 1, "pi_near": 11, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | pilot_dr | 20 | 20 | 8 | 8 | 14.15 | 3.34 | 14.15 | 12.19 | 3.47 | 3 | 14 | {"pi_b": 3, "pi_far": 3, "pi_near": 6, "pi_stage": 8} | {"pi_stage": 20} |
| A_on | tabular | pilot_is | 20 | 20 | 6 | 6 | 14.86 | 3.13 | 14.86 | 11.48 | 3.24 | 3 | 15 | {"pi_b": 2, "pi_far": 3, "pi_near": 9, "pi_stage": 6} | {"pi_stage": 20} |
| A_on | tabular | snips | 20 | 20 | 8 | 8 | 8.57 | 1.73 | 8.57 | 17.77 | 1.76 | 0 | 19 | {"pi_b": 1, "pi_near": 11, "pi_stage": 8} | {"pi_stage": 20} |
| B_off | nontabular | dm | 20 | 20 | 9 | 9 | 8.57 | 1.79 | 8.57 | 22.46 | 1.79 | 0 | 20 | {"pi_near": 11, "pi_stage": 9} | {"pi_stage": 20} |
| B_off | nontabular | dr | 20 | 20 | 16 | 16 | 4.87 | 2.72 | 4.87 | 26.16 | 2.72 | 1 | 19 | {"pi_far": 1, "pi_near": 3, "pi_stage": 16} | {"pi_stage": 20} |
| B_off | nontabular | is | 20 | 20 | 14 | 14 | 6.47 | 2.79 | 6.47 | 24.56 | 2.75 | 1 | 19 | {"pi_far": 1, "pi_near": 5, "pi_stage": 14} | {"pi_stage": 20} |
| B_off | nontabular | pilot_dr | 20 | 20 | 13 | 13 | 7.8 | 2.9 | 7.8 | 23.23 | 3.0 | 1 | 18 | {"pi_b": 1, "pi_far": 1, "pi_near": 5, "pi_stage": 13} | {"pi_stage": 20} |
| B_off | nontabular | snips | 20 | 20 | 16 | 16 | 4.87 | 2.72 | 4.87 | 26.16 | 2.72 | 1 | 19 | {"pi_far": 1, "pi_near": 3, "pi_stage": 16} | {"pi_stage": 20} |
| B_off | tabular | dm | 20 | 20 | 15 | 15 | 3.92 | 1.57 | 3.92 | 27.11 | 1.56 | 0 | 20 | {"pi_near": 5, "pi_stage": 15} | {"pi_stage": 20} |
| B_off | tabular | dm_blind | 20 | 20 | 13 | 13 | 5.58 | 1.76 | 5.58 | 25.45 | 1.66 | 0 | 20 | {"pi_near": 7, "pi_stage": 13} | {"pi_stage": 20} |
| B_off | tabular | dm_plus_is | 20 | 20 | 15 | 15 | 3.92 | 1.57 | 3.92 | 27.11 | 1.56 | 0 | 20 | {"pi_near": 5, "pi_stage": 15} | {"pi_stage": 20} |
| B_off | tabular | dr | 20 | 20 | 15 | 15 | 3.92 | 1.57 | 3.92 | 27.11 | 1.56 | 0 | 20 | {"pi_near": 5, "pi_stage": 15} | {"pi_stage": 20} |
| B_off | tabular | is | 20 | 20 | 15 | 15 | 3.92 | 1.57 | 3.92 | 27.11 | 1.56 | 0 | 20 | {"pi_near": 5, "pi_stage": 15} | {"pi_stage": 20} |
| B_off | tabular | pilot_dr | 20 | 20 | 13 | 13 | 7.8 | 2.9 | 7.8 | 23.23 | 3.0 | 1 | 18 | {"pi_b": 1, "pi_far": 1, "pi_near": 5, "pi_stage": 13} | {"pi_stage": 20} |
| B_off | tabular | pilot_is | 20 | 20 | 12 | 12 | 10.24 | 3.51 | 10.24 | 20.79 | 3.62 | 2 | 17 | {"pi_b": 1, "pi_far": 2, "pi_near": 5, "pi_stage": 12} | {"pi_stage": 20} |
| B_off | tabular | snips | 20 | 20 | 15 | 15 | 3.92 | 1.57 | 3.92 | 27.11 | 1.56 | 0 | 20 | {"pi_near": 5, "pi_stage": 15} | {"pi_stage": 20} |
| B_on | nontabular | dm | 20 | 20 | 11 | 11 | 7.24 | 1.85 | 7.24 | 24.29 | 1.65 | 0 | 20 | {"pi_near": 9, "pi_stage": 11} | {"pi_stage": 20} |
| B_on | nontabular | dr | 20 | 20 | 11 | 11 | 7.05 | 1.8 | 7.05 | 24.48 | 1.77 | 0 | 20 | {"pi_near": 9, "pi_stage": 11} | {"pi_stage": 20} |
| B_on | nontabular | is | 20 | 20 | 10 | 10 | 7.81 | 1.8 | 7.81 | 23.72 | 1.77 | 0 | 20 | {"pi_near": 10, "pi_stage": 10} | {"pi_stage": 20} |
| B_on | nontabular | pilot_dr | 20 | 20 | 9 | 9 | 11.31 | 2.99 | 11.31 | 20.23 | 2.95 | 1 | 18 | {"pi_b": 1, "pi_far": 1, "pi_near": 9, "pi_stage": 9} | {"pi_stage": 20} |
| B_on | nontabular | snips | 20 | 20 | 13 | 13 | 7.2 | 2.48 | 7.2 | 24.33 | 2.37 | 0 | 18 | {"pi_b": 2, "pi_near": 5, "pi_stage": 13} | {"pi_stage": 20} |
| B_on | tabular | dm | 20 | 20 | 10 | 10 | 7.77 | 1.79 | 7.77 | 23.77 | 1.81 | 0 | 20 | {"pi_near": 10, "pi_stage": 10} | {"pi_stage": 20} |
| B_on | tabular | dm_blind | 20 | 20 | 9 | 9 | 8.65 | 1.81 | 8.65 | 22.88 | 1.74 | 0 | 20 | {"pi_near": 11, "pi_stage": 9} | {"pi_stage": 20} |
| B_on | tabular | dm_plus_is | 20 | 20 | 10 | 10 | 7.77 | 1.79 | 7.77 | 23.77 | 1.81 | 0 | 20 | {"pi_near": 10, "pi_stage": 10} | {"pi_stage": 20} |
| B_on | tabular | dr | 20 | 20 | 10 | 10 | 7.77 | 1.79 | 7.77 | 23.77 | 1.81 | 0 | 20 | {"pi_near": 10, "pi_stage": 10} | {"pi_stage": 20} |
| B_on | tabular | is | 20 | 20 | 10 | 10 | 7.77 | 1.79 | 7.77 | 23.77 | 1.81 | 0 | 20 | {"pi_near": 10, "pi_stage": 10} | {"pi_stage": 20} |
| B_on | tabular | pilot_dr | 20 | 20 | 11 | 11 | 8.76 | 2.78 | 8.76 | 22.78 | 2.86 | 1 | 19 | {"pi_far": 1, "pi_near": 8, "pi_stage": 11} | {"pi_stage": 20} |
| B_on | tabular | pilot_is | 20 | 20 | 10 | 10 | 10.5 | 3.03 | 10.5 | 21.04 | 3.0 | 1 | 18 | {"pi_b": 1, "pi_far": 1, "pi_near": 8, "pi_stage": 10} | {"pi_stage": 20} |
| B_on | tabular | snips | 20 | 20 | 10 | 10 | 7.77 | 1.79 | 7.77 | 23.77 | 1.81 | 0 | 20 | {"pi_near": 10, "pi_stage": 10} | {"pi_stage": 20} |

## T7. Interval diagnostic (containment of the reference; counts over seeds)

| cond | target | interval | n_seeds | contains | mean_width | sd_error_across_seeds | mean_error | mean_boot_sd | width_implied_sd | mean_reference_se |
|---|---|---|---|---|---|---|---|---|---|---|
| A_off | π_visit | dm | 20 | 0 | 1.0 | 21.57 | -1.11 | nan | 0.3 | 1.42 |
| A_off | π_visit | dm_plus_is | 20 | 18 | 71.7 | 21.58 | -1.01 | nan | 21.79 | 1.42 |
| A_off | π_visit | dm_refit | 20 | 19 | 70.77 | 21.57 | -1.11 | 22.04 | 21.51 | 1.42 |
| A_off | π_visit | dr | 20 | 18 | 71.53 | 21.61 | -1.15 | nan | 21.74 | 1.42 |
| A_off | π_visit | is | 20 | 18 | 72.31 | 21.58 | -1.25 | nan | 21.98 | 1.42 |
| A_off | π_visit | pilot_dr | 20 | 18 | 181.8 | 58.67 | -4.65 | nan | 55.26 | 1.42 |
| A_off | π_visit | pilot_is | 20 | 18 | 184.65 | 61.67 | -5.32 | nan | 56.13 | 1.42 |
| A_off | π_visit | snips | 20 | 19 | 72.23 | 21.59 | -1.11 | nan | 21.96 | 1.42 |
| A_off | π_sms | dm | 20 | 2 | 1.12 | 13.89 | 2.02 | nan | 0.34 | 1.65 |
| A_off | π_sms | dm_plus_is | 20 | 19 | 61.67 | 13.93 | 2.16 | nan | 18.75 | 1.65 |
| A_off | π_sms | dm_refit | 20 | 19 | 61.69 | 13.89 | 2.02 | 19.0 | 18.75 | 1.65 |
| A_off | π_sms | dr | 20 | 19 | 62.53 | 14.17 | 2.52 | nan | 19.01 | 1.65 |
| A_off | π_sms | is | 20 | 19 | 61.34 | 13.91 | 1.88 | nan | 18.65 | 1.65 |
| A_off | π_sms | pilot_dr | 20 | 19 | 215.09 | 60.97 | -3.61 | nan | 65.38 | 1.65 |
| A_off | π_sms | pilot_is | 20 | 18 | 214.54 | 65.2 | -4.95 | nan | 65.21 | 1.65 |
| A_off | π_sms | snips | 20 | 19 | 60.86 | 13.9 | 2.02 | nan | 18.5 | 1.65 |
| A_off | π_stage | dm | 20 | 0 | 1.16 | 27.39 | -0.13 | nan | 0.35 | 1.73 |
| A_off | π_stage | dm_plus_is | 20 | 19 | 86.04 | 27.39 | -0.02 | nan | 26.15 | 1.73 |
| A_off | π_stage | dm_refit | 20 | 18 | 86.12 | 27.39 | -0.13 | 26.69 | 26.18 | 1.73 |
| A_off | π_stage | dr | 20 | 17 | 86.16 | 27.31 | -0.27 | nan | 26.19 | 1.73 |
| A_off | π_stage | is | 20 | 19 | 86.82 | 27.39 | -0.27 | nan | 26.39 | 1.73 |
| A_off | π_stage | pilot_dr | 20 | 18 | 220.81 | 55.53 | 2.67 | nan | 67.12 | 1.73 |
| A_off | π_stage | pilot_is | 20 | 18 | 223.44 | 60.77 | 4.9 | nan | 67.92 | 1.73 |
| A_off | π_stage | snips | 20 | 19 | 86.36 | 27.41 | -0.11 | nan | 26.25 | 1.73 |
| A_on | π_visit | dm | 20 | 0 | 0.81 | 16.86 | -57.5 | nan | 0.24 | 1.44 |
| A_on | π_visit | dm_plus_is | 20 | 2 | 59.51 | 16.86 | -57.4 | nan | 18.09 | 1.44 |
| A_on | π_visit | dm_refit | 20 | 2 | 58.55 | 16.86 | -57.5 | 18.18 | 17.8 | 1.44 |
| A_on | π_visit | dr | 20 | 2 | 58.71 | 16.84 | -57.52 | nan | 17.85 | 1.44 |
| A_on | π_visit | is | 20 | 2 | 58.61 | 16.87 | -57.65 | nan | 17.81 | 1.44 |
| A_on | π_visit | pilot_dr | 20 | 18 | 183.65 | 60.84 | -4.91 | nan | 55.82 | 1.44 |
| A_on | π_visit | pilot_is | 20 | 17 | 186.29 | 62.96 | -4.95 | nan | 56.63 | 1.44 |
| A_on | π_visit | snips | 20 | 2 | 58.54 | 16.87 | -57.54 | nan | 17.79 | 1.44 |
| A_on | π_sms | dm | 20 | 0 | 1.17 | 16.77 | 4.91 | nan | 0.35 | 1.67 |
| A_on | π_sms | dm_plus_is | 20 | 20 | 65.74 | 16.78 | 5.07 | nan | 19.98 | 1.67 |
| A_on | π_sms | dm_refit | 20 | 19 | 64.48 | 16.77 | 4.91 | 19.68 | 19.6 | 1.67 |
| A_on | π_sms | dr | 20 | 19 | 65.24 | 17.25 | 5.25 | nan | 19.83 | 1.67 |
| A_on | π_sms | is | 20 | 20 | 64.59 | 16.78 | 4.77 | nan | 19.63 | 1.67 |
| A_on | π_sms | pilot_dr | 20 | 16 | 216.56 | 77.32 | 0.05 | nan | 65.83 | 1.67 |
| A_on | π_sms | pilot_is | 20 | 17 | 219.7 | 81.15 | -1.18 | nan | 66.78 | 1.67 |
| A_on | π_sms | snips | 20 | 19 | 64.52 | 16.78 | 4.92 | nan | 19.61 | 1.67 |
| A_on | π_stage | dm | 20 | 1 | 1.19 | 30.03 | -12.61 | nan | 0.36 | 1.75 |
| A_on | π_stage | dm_plus_is | 20 | 17 | 90.65 | 30.05 | -12.49 | nan | 27.55 | 1.75 |
| A_on | π_stage | dm_refit | 20 | 17 | 90.37 | 30.03 | -12.61 | 27.3 | 27.47 | 1.75 |
| A_on | π_stage | dr | 20 | 17 | 90.38 | 30.28 | -12.29 | nan | 27.47 | 1.75 |
| A_on | π_stage | is | 20 | 16 | 89.94 | 30.02 | -12.75 | nan | 27.34 | 1.75 |
| A_on | π_stage | pilot_dr | 20 | 18 | 228.23 | 64.71 | 6.04 | nan | 69.37 | 1.75 |
| A_on | π_stage | pilot_is | 20 | 18 | 229.99 | 68.8 | 8.59 | nan | 69.91 | 1.75 |
| A_on | π_stage | snips | 20 | 16 | 90.0 | 30.05 | -12.6 | nan | 27.36 | 1.75 |
| B_off | π_visit | dm | 20 | 1 | 0.95 | 20.76 | -3.94 | nan | 0.29 | 1.4 |
| B_off | π_visit | dm_plus_is | 20 | 18 | 70.78 | 20.77 | -3.85 | nan | 21.51 | 1.4 |
| B_off | π_visit | dm_refit | 20 | 18 | 69.6 | 20.76 | -3.94 | 21.34 | 21.16 | 1.4 |
| B_off | π_visit | dr | 20 | 17 | 70.06 | 20.83 | -4.03 | nan | 21.29 | 1.4 |
| B_off | π_visit | is | 20 | 17 | 71.04 | 20.76 | -4.08 | nan | 21.59 | 1.4 |
| B_off | π_visit | pilot_dr | 20 | 18 | 176.93 | 57.45 | -6.24 | nan | 53.78 | 1.4 |
| B_off | π_visit | pilot_is | 20 | 18 | 181.3 | 60.68 | -6.9 | nan | 55.11 | 1.4 |
| B_off | π_visit | snips | 20 | 17 | 70.45 | 20.77 | -3.96 | nan | 21.42 | 1.4 |
| B_off | π_sms | dm | 20 | 2 | 1.11 | 13.67 | 0.56 | nan | 0.34 | 1.64 |
| B_off | π_sms | dm_plus_is | 20 | 19 | 60.1 | 13.68 | 0.69 | nan | 18.27 | 1.64 |
| B_off | π_sms | dm_refit | 20 | 19 | 59.25 | 13.67 | 0.56 | 18.17 | 18.01 | 1.64 |
| B_off | π_sms | dr | 20 | 19 | 60.42 | 13.66 | 0.77 | nan | 18.37 | 1.64 |
| B_off | π_sms | is | 20 | 19 | 59.15 | 13.69 | 0.43 | nan | 17.98 | 1.64 |
| B_off | π_sms | pilot_dr | 20 | 18 | 208.46 | 56.22 | -10.0 | nan | 63.37 | 1.64 |
| B_off | π_sms | pilot_is | 20 | 18 | 208.83 | 60.85 | -10.88 | nan | 63.48 | 1.64 |
| B_off | π_sms | snips | 20 | 19 | 59.32 | 13.68 | 0.57 | nan | 18.03 | 1.64 |
| B_off | π_stage | dm | 20 | 0 | 1.14 | 24.69 | -1.66 | nan | 0.35 | 1.73 |
| B_off | π_stage | dm_plus_is | 20 | 19 | 86.11 | 24.68 | -1.56 | nan | 26.17 | 1.73 |
| B_off | π_stage | dm_refit | 20 | 18 | 85.72 | 24.69 | -1.66 | 26.64 | 26.06 | 1.73 |
| B_off | π_stage | dr | 20 | 18 | 85.66 | 24.54 | -1.68 | nan | 26.04 | 1.73 |
| B_off | π_stage | is | 20 | 18 | 87.16 | 24.69 | -1.8 | nan | 26.49 | 1.73 |
| B_off | π_stage | pilot_dr | 20 | 19 | 222.9 | 62.07 | 13.9 | nan | 67.76 | 1.73 |
| B_off | π_stage | pilot_is | 20 | 18 | 225.65 | 68.31 | 15.87 | nan | 68.59 | 1.73 |
| B_off | π_stage | snips | 20 | 18 | 86.14 | 24.7 | -1.65 | nan | 26.18 | 1.73 |
| B_on | π_visit | dm | 20 | 0 | 0.78 | 16.15 | -56.6 | nan | 0.24 | 1.43 |
| B_on | π_visit | dm_plus_is | 20 | 2 | 59.22 | 16.15 | -56.49 | nan | 18.0 | 1.43 |
| B_on | π_visit | dm_refit | 20 | 2 | 58.76 | 16.15 | -56.6 | 17.96 | 17.86 | 1.43 |
| B_on | π_visit | dr | 20 | 2 | 59.18 | 16.18 | -56.7 | nan | 17.99 | 1.43 |
| B_on | π_visit | is | 20 | 2 | 59.69 | 16.17 | -56.75 | nan | 18.14 | 1.43 |
| B_on | π_visit | pilot_dr | 20 | 19 | 181.98 | 49.18 | -8.62 | nan | 55.32 | 1.43 |
| B_on | π_visit | pilot_is | 20 | 19 | 184.09 | 51.5 | -8.62 | nan | 55.96 | 1.43 |
| B_on | π_visit | snips | 20 | 2 | 60.04 | 16.16 | -56.64 | nan | 18.25 | 1.43 |
| B_on | π_sms | dm | 20 | 0 | 1.18 | 16.66 | 4.85 | nan | 0.36 | 1.67 |
| B_on | π_sms | dm_plus_is | 20 | 20 | 63.36 | 16.68 | 5.0 | nan | 19.26 | 1.67 |
| B_on | π_sms | dm_refit | 20 | 20 | 62.72 | 16.66 | 4.85 | 19.29 | 19.07 | 1.67 |
| B_on | π_sms | dr | 20 | 20 | 63.18 | 17.08 | 5.12 | nan | 19.21 | 1.67 |
| B_on | π_sms | is | 20 | 20 | 62.43 | 16.67 | 4.71 | nan | 18.98 | 1.67 |
| B_on | π_sms | pilot_dr | 20 | 16 | 214.8 | 78.15 | -3.3 | nan | 65.29 | 1.67 |
| B_on | π_sms | pilot_is | 20 | 16 | 217.4 | 82.56 | -4.61 | nan | 66.08 | 1.67 |
| B_on | π_sms | snips | 20 | 20 | 62.32 | 16.66 | 4.86 | nan | 18.94 | 1.67 |
| B_on | π_stage | dm | 20 | 0 | 1.2 | 27.18 | -10.79 | nan | 0.37 | 1.76 |
| B_on | π_stage | dm_plus_is | 20 | 16 | 90.34 | 27.18 | -10.68 | nan | 27.46 | 1.76 |
| B_on | π_stage | dm_refit | 20 | 16 | 89.09 | 27.18 | -10.79 | 27.56 | 27.08 | 1.76 |
| B_on | π_stage | dr | 20 | 16 | 89.78 | 27.28 | -10.34 | nan | 27.29 | 1.76 |
| B_on | π_stage | is | 20 | 16 | 89.85 | 27.17 | -10.94 | nan | 27.31 | 1.76 |
| B_on | π_stage | pilot_dr | 20 | 18 | 230.71 | 59.98 | 13.02 | nan | 70.13 | 1.76 |
| B_on | π_stage | pilot_is | 20 | 18 | 232.26 | 65.15 | 15.28 | nan | 70.6 | 1.76 |
| B_on | π_stage | snips | 20 | 16 | 90.64 | 27.19 | -10.78 | nan | 27.55 | 1.76 |

## T10. Spread of the log-based estimators' errors within a regime (max − min per run)

| cond | regime | target | members | n_runs | mean_spread | max_spread | mean_spread_without_is | max_spread_without_is |
|---|---|---|---|---|---|---|---|---|
| A_off | tabular | π_visit | dm/is/snips/dr/dm_plus_is | 20 | 0.58 | 1.3 | 0.5 | 1.13 |
| A_off | tabular | π_sms | dm/is/snips/dr/dm_plus_is | 20 | 1.98 | 5.45 | 1.89 | 5.32 |
| A_off | tabular | π_stage | dm/is/snips/dr/dm_plus_is | 20 | 0.71 | 2.04 | 0.64 | 2.04 |
| A_on | tabular | π_visit | dm/is/snips/dr/dm_plus_is | 20 | 0.57 | 1.79 | 0.5 | 1.79 |
| A_on | tabular | π_sms | dm/is/snips/dr/dm_plus_is | 20 | 1.73 | 5.56 | 1.65 | 5.42 |
| A_on | tabular | π_stage | dm/is/snips/dr/dm_plus_is | 20 | 0.98 | 1.8 | 0.89 | 1.66 |
| B_off | tabular | π_visit | dm/is/snips/dr/dm_plus_is | 20 | 0.59 | 1.12 | 0.52 | 0.98 |
| B_off | tabular | π_sms | dm/is/snips/dr/dm_plus_is | 20 | 1.67 | 5.52 | 1.59 | 5.39 |
| B_off | tabular | π_stage | dm/is/snips/dr/dm_plus_is | 20 | 0.69 | 2.21 | 0.61 | 2.21 |
| B_on | tabular | π_visit | dm/is/snips/dr/dm_plus_is | 20 | 0.59 | 2.15 | 0.52 | 2.15 |
| B_on | tabular | π_sms | dm/is/snips/dr/dm_plus_is | 20 | 1.72 | 5.68 | 1.64 | 5.53 |
| B_on | tabular | π_stage | dm/is/snips/dr/dm_plus_is | 20 | 1.07 | 2.12 | 0.97 | 1.95 |
| A_off | nontabular | π_visit | dm/is/snips/dr | 20 | 26.17 | 73.98 | 15.52 | 56.79 |
| A_off | nontabular | π_sms | dm/is/snips/dr | 20 | 24.15 | 69.02 | 18.97 | 59.97 |
| A_off | nontabular | π_stage | dm/is/snips/dr | 20 | 25.76 | 70.16 | 22.18 | 66.03 |
| A_on | nontabular | π_visit | dm/is/snips/dr | 20 | 19.32 | 39.74 | 13.42 | 31.35 |
| A_on | nontabular | π_sms | dm/is/snips/dr | 20 | 25.29 | 90.01 | 19.36 | 80.95 |
| A_on | nontabular | π_stage | dm/is/snips/dr | 20 | 25.27 | 54.42 | 24.94 | 54.42 |
| B_off | nontabular | π_visit | dm/is/snips/dr | 20 | 25.24 | 58.08 | 16.51 | 42.74 |
| B_off | nontabular | π_sms | dm/is/snips/dr | 20 | 21.87 | 49.46 | 16.91 | 42.32 |
| B_off | nontabular | π_stage | dm/is/snips/dr | 20 | 29.08 | 63.38 | 25.31 | 57.5 |
| B_on | nontabular | π_visit | dm/is/snips/dr | 20 | 17.69 | 40.03 | 12.4 | 31.95 |
| B_on | nontabular | π_sms | dm/is/snips/dr | 20 | 25.09 | 99.39 | 19.61 | 90.5 |
| B_on | nontabular | π_stage | dm/is/snips/dr | 20 | 25.1 | 58.3 | 24.51 | 57.28 |

## T11. Between-replicate variance of the references against the per-loan prediction (ratio 1 = independent loans; per condition, seeds independent)

| kind | cells | min_ratio | max_ratio | min_p |
|---|---|---|---|---|
| gap | 24.0 | 0.662 | 1.303 | 0.099 |
| value | 16.0 | 0.529 | 0.82 | 0.013 |

## T8. Same logs: gradient-boosted minus tabular error

| cond | target | estimator | n_seeds | mean_diff_nontab_minus_tab | se |
|---|---|---|---|---|---|
| A_off | π_visit | dm | 20 | -3.16 | 4.07 |
| A_off | π_sms | dm | 20 | -0.14 | 2.7 |
| A_off | π_stage | dm | 20 | -9.15 | 5.59 |
| A_on | π_visit | dm | 20 | 4.54 | 3.17 |
| A_on | π_sms | dm | 20 | -1.95 | 3.19 |
| A_on | π_stage | dm | 20 | 5.44 | 6.09 |
| B_off | π_visit | dm | 20 | 0.23 | 3.72 |
| B_off | π_sms | dm | 20 | 0.85 | 2.75 |
| B_off | π_stage | dm | 20 | -12.53 | 5.11 |
| B_on | π_visit | dm | 20 | 6.33 | 2.8 |
| B_on | π_sms | dm | 20 | -0.91 | 3.55 |
| B_on | π_stage | dm | 20 | 1.51 | 5.57 |
| A_off | π_visit | is | 20 | 15.39 | 2.09 |
| A_off | π_sms | is | 20 | 9.52 | 4.0 |
| A_off | π_stage | is | 20 | 8.83 | 5.31 |
| A_on | π_visit | is | 20 | 13.76 | 1.16 |
| A_on | π_sms | is | 20 | 12.53 | 4.75 |
| A_on | π_stage | is | 20 | 4.39 | 4.63 |
| B_off | π_visit | is | 20 | 14.76 | 1.95 |
| B_off | π_sms | is | 20 | 8.94 | 3.88 |
| B_off | π_stage | is | 20 | 10.76 | 4.83 |
| B_on | π_visit | is | 20 | 13.81 | 1.26 |
| B_on | π_sms | is | 20 | 12.77 | 4.64 |
| B_on | π_stage | is | 20 | 7.18 | 3.8 |
| A_off | π_visit | snips | 20 | 0.44 | 2.03 |
| A_off | π_sms | snips | 20 | -0.43 | 3.93 |
| A_off | π_stage | snips | 20 | 2.52 | 5.17 |
| A_on | π_visit | snips | 20 | 4.05 | 1.15 |
| A_on | π_sms | snips | 20 | 1.72 | 4.56 |
| A_on | π_stage | snips | 20 | 2.28 | 4.46 |
| B_off | π_visit | snips | 20 | 0.48 | 1.89 |
| B_off | π_sms | snips | 20 | -0.86 | 3.83 |
| B_off | π_stage | snips | 20 | 4.46 | 4.66 |
| B_on | π_visit | snips | 20 | 4.31 | 1.22 |
| B_on | π_sms | snips | 20 | 1.92 | 4.44 |
| B_on | π_stage | snips | 20 | 5.01 | 3.68 |
| A_off | π_visit | dr | 20 | -2.78 | 1.99 |
| A_off | π_sms | dr | 20 | -0.91 | 3.97 |
| A_off | π_stage | dr | 20 | 1.53 | 5.1 |
| A_on | π_visit | dr | 20 | 2.2 | 1.24 |
| A_on | π_sms | dr | 20 | 1.29 | 4.48 |
| A_on | π_stage | dr | 20 | 2.13 | 4.56 |
| B_off | π_visit | dr | 20 | -3.27 | 1.8 |
| B_off | π_sms | dr | 20 | -1.2 | 3.98 |
| B_off | π_stage | dr | 20 | 3.41 | 4.77 |
| B_on | π_visit | dr | 20 | 2.86 | 1.31 |
| B_on | π_sms | dr | 20 | 1.61 | 4.34 |
| B_on | π_stage | dr | 20 | 4.4 | 3.92 |
| A_off | π_visit | pilot_dr | 20 | -1.22 | 1.72 |
| A_off | π_sms | pilot_dr | 20 | 0.28 | 1.39 |
| A_off | π_stage | pilot_dr | 20 | -0.3 | 1.75 |
| A_on | π_visit | pilot_dr | 20 | 0.16 | 1.43 |
| A_on | π_sms | pilot_dr | 20 | 0.61 | 1.65 |
| A_on | π_stage | pilot_dr | 20 | 0.62 | 1.79 |
| B_off | π_visit | pilot_dr | 20 | -1.24 | 1.62 |
| B_off | π_sms | pilot_dr | 20 | -0.13 | 1.52 |
| B_off | π_stage | pilot_dr | 20 | -0.02 | 1.75 |
| B_on | π_visit | pilot_dr | 20 | -0.21 | 1.61 |
| B_on | π_sms | pilot_dr | 20 | 0.15 | 1.7 |
| B_on | π_stage | pilot_dr | 20 | -0.97 | 1.76 |

## T9. Seed-paired condition contrasts of the error

| contrast | regime | estimator | target | n_seeds | mean_diff | se |
|---|---|---|---|---|---|---|
| A_on - A_off | factual | logged_mean | π_b | 20 | -0.3 | 0.21 |
| A_on - A_off | nontabular | dm | π_visit | 20 | -48.7 | 1.48 |
| A_on - A_off | nontabular | dm | π_sms | 20 | 1.09 | 1.19 |
| A_on - A_off | nontabular | dm | π_stage | 20 | 2.11 | 1.74 |
| A_on - A_off | nontabular | dr | π_visit | 20 | -51.4 | 4.63 |
| A_on - A_off | nontabular | dr | π_sms | 20 | 4.94 | 3.35 |
| A_on - A_off | nontabular | dr | π_stage | 20 | -11.42 | 4.74 |
| A_on - A_off | nontabular | is | π_visit | 20 | -58.03 | 4.64 |
| A_on - A_off | nontabular | is | π_sms | 20 | 5.91 | 3.42 |
| A_on - A_off | nontabular | is | π_stage | 20 | -16.92 | 4.68 |
| A_on - A_off | nontabular | pilot_dr | π_visit | 20 | 1.11 | 2.93 |
| A_on - A_off | nontabular | pilot_dr | π_sms | 20 | 3.99 | 4.34 |
| A_on - A_off | nontabular | pilot_dr | π_stage | 20 | 4.28 | 5.95 |
| A_on - A_off | nontabular | snips | π_visit | 20 | -52.82 | 4.45 |
| A_on - A_off | nontabular | snips | π_sms | 20 | 5.06 | 3.25 |
| A_on - A_off | nontabular | snips | π_stage | 20 | -12.72 | 4.58 |
| A_on - A_off | tabular | dm | π_visit | 20 | -56.4 | 3.9 |
| A_on - A_off | tabular | dm | π_sms | 20 | 2.9 | 3.05 |
| A_on - A_off | tabular | dm | π_stage | 20 | -12.48 | 3.78 |
| A_on - A_off | tabular | dm_blind | π_visit | 20 | -57.25 | 3.58 |
| A_on - A_off | tabular | dm_blind | π_sms | 20 | 1.3 | 3.35 |
| A_on - A_off | tabular | dm_blind | π_stage | 20 | -12.02 | 2.74 |
| A_on - A_off | tabular | dm_plus_is | π_visit | 20 | -56.39 | 3.9 |
| A_on - A_off | tabular | dm_plus_is | π_sms | 20 | 2.91 | 3.05 |
| A_on - A_off | tabular | dm_plus_is | π_stage | 20 | -12.47 | 3.78 |
| A_on - A_off | tabular | dm_refit | π_visit | 20 | -56.4 | 3.9 |
| A_on - A_off | tabular | dm_refit | π_sms | 20 | 2.9 | 3.05 |
| A_on - A_off | tabular | dm_refit | π_stage | 20 | -12.48 | 3.78 |
| A_on - A_off | tabular | dr | π_visit | 20 | -56.37 | 3.89 |
| A_on - A_off | tabular | dr | π_sms | 20 | 2.74 | 3.08 |
| A_on - A_off | tabular | dr | π_stage | 20 | -12.02 | 3.9 |
| A_on - A_off | tabular | is | π_visit | 20 | -56.4 | 3.9 |
| A_on - A_off | tabular | is | π_sms | 20 | 2.89 | 3.05 |
| A_on - A_off | tabular | is | π_stage | 20 | -12.48 | 3.78 |
| A_on - A_off | tabular | pilot_dr | π_visit | 20 | -0.27 | 2.87 |
| A_on - A_off | tabular | pilot_dr | π_sms | 20 | 3.67 | 4.42 |
| A_on - A_off | tabular | pilot_dr | π_stage | 20 | 3.36 | 5.97 |
| A_on - A_off | tabular | pilot_is | π_visit | 20 | 0.37 | 2.69 |
| A_on - A_off | tabular | pilot_is | π_sms | 20 | 3.77 | 4.43 |
| A_on - A_off | tabular | pilot_is | π_stage | 20 | 3.7 | 5.85 |
| A_on - A_off | tabular | snips | π_visit | 20 | -56.43 | 3.9 |
| A_on - A_off | tabular | snips | π_sms | 20 | 2.9 | 3.05 |
| A_on - A_off | tabular | snips | π_stage | 20 | -12.48 | 3.78 |
| B_on - B_off | factual | logged_mean | π_b | 20 | -0.04 | 0.22 |
| B_on - B_off | nontabular | dm | π_visit | 20 | -46.56 | 1.4 |
| B_on - B_off | nontabular | dm | π_sms | 20 | 2.54 | 1.31 |
| B_on - B_off | nontabular | dm | π_stage | 20 | 4.91 | 1.67 |
| B_on - B_off | nontabular | dr | π_visit | 20 | -46.54 | 4.69 |
| B_on - B_off | nontabular | dr | π_sms | 20 | 7.16 | 4.12 |
| B_on - B_off | nontabular | dr | π_stage | 20 | -7.67 | 5.34 |
| B_on - B_off | nontabular | is | π_visit | 20 | -53.61 | 4.78 |
| B_on - B_off | nontabular | is | π_sms | 20 | 8.12 | 4.16 |
| B_on - B_off | nontabular | is | π_stage | 20 | -12.72 | 5.38 |
| B_on - B_off | nontabular | pilot_dr | π_visit | 20 | -1.36 | 3.61 |
| B_on - B_off | nontabular | pilot_dr | π_sms | 20 | 6.98 | 6.27 |
| B_on - B_off | nontabular | pilot_dr | π_stage | 20 | -1.83 | 6.06 |
| B_on - B_off | nontabular | snips | π_visit | 20 | -48.86 | 4.56 |
| B_on - B_off | nontabular | snips | π_sms | 20 | 7.07 | 3.96 |
| B_on - B_off | nontabular | snips | π_stage | 20 | -8.58 | 5.26 |
| B_on - B_off | tabular | dm | π_visit | 20 | -52.66 | 4.01 |
| B_on - B_off | tabular | dm | π_sms | 20 | 4.29 | 3.86 |
| B_on - B_off | tabular | dm | π_stage | 20 | -9.13 | 4.46 |
| B_on - B_off | tabular | dm_blind | π_visit | 20 | -53.9 | 3.8 |
| B_on - B_off | tabular | dm_blind | π_sms | 20 | 2.58 | 3.39 |
| B_on - B_off | tabular | dm_blind | π_stage | 20 | -9.01 | 3.69 |
| B_on - B_off | tabular | dm_plus_is | π_visit | 20 | -52.64 | 4.01 |
| B_on - B_off | tabular | dm_plus_is | π_sms | 20 | 4.31 | 3.86 |
| B_on - B_off | tabular | dm_plus_is | π_stage | 20 | -9.12 | 4.46 |
| B_on - B_off | tabular | dm_refit | π_visit | 20 | -52.66 | 4.01 |
| B_on - B_off | tabular | dm_refit | π_sms | 20 | 4.29 | 3.86 |
| B_on - B_off | tabular | dm_refit | π_stage | 20 | -9.13 | 4.46 |
| B_on - B_off | tabular | dr | π_visit | 20 | -52.67 | 4.04 |
| B_on - B_off | tabular | dr | π_sms | 20 | 4.34 | 4.03 |
| B_on - B_off | tabular | dr | π_stage | 20 | -8.66 | 4.54 |
| B_on - B_off | tabular | is | π_visit | 20 | -52.66 | 4.01 |
| B_on - B_off | tabular | is | π_sms | 20 | 4.29 | 3.86 |
| B_on - B_off | tabular | is | π_stage | 20 | -9.14 | 4.46 |
| B_on - B_off | tabular | pilot_dr | π_visit | 20 | -2.39 | 3.67 |
| B_on - B_off | tabular | pilot_dr | π_sms | 20 | 6.7 | 6.34 |
| B_on - B_off | tabular | pilot_dr | π_stage | 20 | -0.88 | 5.97 |
| B_on - B_off | tabular | pilot_is | π_visit | 20 | -1.72 | 3.76 |
| B_on - B_off | tabular | pilot_is | π_sms | 20 | 6.27 | 6.19 |
| B_on - B_off | tabular | pilot_is | π_stage | 20 | -0.59 | 5.75 |
| B_on - B_off | tabular | snips | π_visit | 20 | -52.68 | 4.02 |
| B_on - B_off | tabular | snips | π_sms | 20 | 4.29 | 3.86 |
| B_on - B_off | tabular | snips | π_stage | 20 | -9.13 | 4.46 |
| B_on - A_on | factual | logged_mean | π_b | 20 | -0.36 | 0.28 |
| B_on - A_on | nontabular | dm | π_visit | 20 | 2.69 | 0.72 |
| B_on - A_on | nontabular | dm | π_sms | 20 | 0.98 | 0.89 |
| B_on - A_on | nontabular | dm | π_stage | 20 | -2.12 | 1.06 |
| B_on - A_on | nontabular | dr | π_visit | 20 | 1.49 | 1.74 |
| B_on - A_on | nontabular | dr | π_sms | 20 | 0.19 | 1.44 |
| B_on - A_on | nontabular | dr | π_stage | 20 | 4.22 | 3.26 |
| B_on - A_on | nontabular | is | π_visit | 20 | 0.95 | 1.81 |
| B_on - A_on | nontabular | is | π_sms | 20 | 0.18 | 1.39 |
| B_on - A_on | nontabular | is | π_stage | 20 | 4.6 | 3.25 |
| B_on - A_on | nontabular | pilot_dr | π_visit | 20 | -4.08 | 5.12 |
| B_on - A_on | nontabular | pilot_dr | π_sms | 20 | -3.81 | 4.44 |
| B_on - A_on | nontabular | pilot_dr | π_stage | 20 | 5.4 | 6.43 |
| B_on - A_on | nontabular | snips | π_visit | 20 | 1.16 | 1.72 |
| B_on - A_on | nontabular | snips | π_sms | 20 | 0.14 | 1.35 |
| B_on - A_on | nontabular | snips | π_stage | 20 | 4.54 | 3.24 |
| B_on - A_on | tabular | dm | π_visit | 20 | 0.9 | 1.76 |
| B_on - A_on | tabular | dm | π_sms | 20 | -0.06 | 1.33 |
| B_on - A_on | tabular | dm | π_stage | 20 | 1.82 | 2.89 |
| B_on - A_on | tabular | dm_blind | π_visit | 20 | 2.19 | 1.74 |
| B_on - A_on | tabular | dm_blind | π_sms | 20 | 3.05 | 1.03 |
| B_on - A_on | tabular | dm_blind | π_stage | 20 | 0.06 | 2.11 |
| B_on - A_on | tabular | dm_plus_is | π_visit | 20 | 0.91 | 1.76 |
| B_on - A_on | tabular | dm_plus_is | π_sms | 20 | -0.07 | 1.33 |
| B_on - A_on | tabular | dm_plus_is | π_stage | 20 | 1.82 | 2.89 |
| B_on - A_on | tabular | dm_refit | π_visit | 20 | 0.9 | 1.76 |
| B_on - A_on | tabular | dm_refit | π_sms | 20 | -0.06 | 1.33 |
| B_on - A_on | tabular | dm_refit | π_stage | 20 | 1.82 | 2.89 |
| B_on - A_on | tabular | dr | π_visit | 20 | 0.82 | 1.76 |
| B_on - A_on | tabular | dr | π_sms | 20 | -0.14 | 1.33 |
| B_on - A_on | tabular | dr | π_stage | 20 | 1.96 | 2.9 |
| B_on - A_on | tabular | is | π_visit | 20 | 0.91 | 1.76 |
| B_on - A_on | tabular | is | π_sms | 20 | -0.06 | 1.33 |
| B_on - A_on | tabular | is | π_stage | 20 | 1.82 | 2.89 |
| B_on - A_on | tabular | pilot_dr | π_visit | 20 | -3.71 | 5.12 |
| B_on - A_on | tabular | pilot_dr | π_sms | 20 | -3.35 | 4.52 |
| B_on - A_on | tabular | pilot_dr | π_stage | 20 | 6.98 | 6.37 |
| B_on - A_on | tabular | pilot_is | π_visit | 20 | -3.67 | 5.05 |
| B_on - A_on | tabular | pilot_is | π_sms | 20 | -3.43 | 4.57 |
| B_on - A_on | tabular | pilot_is | π_stage | 20 | 6.69 | 6.38 |
| B_on - A_on | tabular | snips | π_visit | 20 | 0.9 | 1.76 |
| B_on - A_on | tabular | snips | π_sms | 20 | -0.06 | 1.33 |
| B_on - A_on | tabular | snips | π_stage | 20 | 1.82 | 2.9 |
| B_off - A_off | factual | logged_mean | π_b | 20 | -0.62 | 0.26 |
| B_off - A_off | nontabular | dm | π_visit | 20 | 0.55 | 0.62 |
| B_off - A_off | nontabular | dm | π_sms | 20 | -0.46 | 0.55 |
| B_off - A_off | nontabular | dm | π_stage | 20 | -4.92 | 0.9 |
| B_off - A_off | nontabular | dr | π_visit | 20 | -3.37 | 1.91 |
| B_off - A_off | nontabular | dr | π_sms | 20 | -2.03 | 1.65 |
| B_off - A_off | nontabular | dr | π_stage | 20 | 0.47 | 3.38 |
| B_off - A_off | nontabular | is | π_visit | 20 | -3.47 | 1.91 |
| B_off - A_off | nontabular | is | π_sms | 20 | -2.03 | 1.63 |
| B_off - A_off | nontabular | is | π_stage | 20 | 0.4 | 3.48 |
| B_off - A_off | nontabular | pilot_dr | π_visit | 20 | -1.61 | 4.42 |
| B_off - A_off | nontabular | pilot_dr | π_sms | 20 | -6.8 | 5.28 |
| B_off - A_off | nontabular | pilot_dr | π_stage | 20 | 11.51 | 6.36 |
| B_off - A_off | nontabular | snips | π_visit | 20 | -2.8 | 1.8 |
| B_off - A_off | nontabular | snips | π_sms | 20 | -1.87 | 1.58 |
| B_off - A_off | nontabular | snips | π_stage | 20 | 0.4 | 3.4 |
| B_off - A_off | tabular | dm | π_visit | 20 | -2.84 | 1.55 |
| B_off - A_off | tabular | dm | π_sms | 20 | -1.45 | 1.62 |
| B_off - A_off | tabular | dm | π_stage | 20 | -1.53 | 2.77 |
| B_off - A_off | tabular | dm_blind | π_visit | 20 | -1.16 | 1.39 |
| B_off - A_off | tabular | dm_blind | π_sms | 20 | 1.76 | 0.88 |
| B_off - A_off | tabular | dm_blind | π_stage | 20 | -2.95 | 2.29 |
| B_off - A_off | tabular | dm_plus_is | π_visit | 20 | -2.84 | 1.55 |
| B_off - A_off | tabular | dm_plus_is | π_sms | 20 | -1.47 | 1.62 |
| B_off - A_off | tabular | dm_plus_is | π_stage | 20 | -1.53 | 2.77 |
| B_off - A_off | tabular | dm_refit | π_visit | 20 | -2.84 | 1.55 |
| B_off - A_off | tabular | dm_refit | π_sms | 20 | -1.45 | 1.62 |
| B_off - A_off | tabular | dm_refit | π_stage | 20 | -1.53 | 2.77 |
| B_off - A_off | tabular | dr | π_visit | 20 | -2.88 | 1.56 |
| B_off - A_off | tabular | dr | π_sms | 20 | -1.74 | 1.78 |
| B_off - A_off | tabular | dr | π_stage | 20 | -1.4 | 2.74 |
| B_off - A_off | tabular | is | π_visit | 20 | -2.83 | 1.55 |
| B_off - A_off | tabular | is | π_sms | 20 | -1.45 | 1.62 |
| B_off - A_off | tabular | is | π_stage | 20 | -1.53 | 2.77 |
| B_off - A_off | tabular | pilot_dr | π_visit | 20 | -1.59 | 4.34 |
| B_off - A_off | tabular | pilot_dr | π_sms | 20 | -6.39 | 5.27 |
| B_off - A_off | tabular | pilot_dr | π_stage | 20 | 11.23 | 6.59 |
| B_off - A_off | tabular | pilot_is | π_visit | 20 | -1.58 | 4.33 |
| B_off - A_off | tabular | pilot_is | π_sms | 20 | -5.94 | 5.21 |
| B_off - A_off | tabular | pilot_is | π_stage | 20 | 10.98 | 6.57 |
| B_off - A_off | tabular | snips | π_visit | 20 | -2.84 | 1.55 |
| B_off - A_off | tabular | snips | π_sms | 20 | -1.45 | 1.62 |
| B_off - A_off | tabular | snips | π_stage | 20 | -1.53 | 2.77 |
