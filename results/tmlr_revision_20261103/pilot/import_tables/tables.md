# Import-ready tables (units: US$ per decision, month-0 explorable cohort)

## T0. Tabular DM, IS and SNIPS coincide (largest |difference| over runs and targets)

| cond | abs_dm_minus_is | abs_dm_minus_snips |
|---|---|---|
| A_off | 0.7831 | 0.039 |
| A_on | 0.807 | 0.0544 |
| B_on | 0.8049 | 0.0449 |
| S18_on | 0.7398 | 0.0743 |

## T1. Reference values (mean over seeds) and Monte-Carlo SE per run

| cond | candidate | seeds | mean_value | sd_across_seeds | median_mc_se | max_mc_se |
|---|---|---|---|---|---|---|
| A_off | π_b | 3 | 276.68 | 34.22 | 1.36 | 1.44 |
| A_off | π_visit | 3 | 261.34 | 32.16 | 1.22 | 1.3 |
| A_off | π_sms | 3 | 289.83 | 35.53 | 1.41 | 1.5 |
| A_off | π_stage | 3 | 302.84 | 37.37 | 1.48 | 1.58 |
| A_on | π_b | 3 | 285.29 | 35.39 | 1.38 | 1.47 |
| A_on | π_visit | 3 | 268.6 | 33.03 | 1.24 | 1.32 |
| A_on | π_sms | 3 | 298.51 | 36.56 | 1.43 | 1.53 |
| A_on | π_stage | 3 | 311.52 | 38.39 | 1.5 | 1.6 |
| B_on | π_b | 3 | 284.07 | 35.17 | 1.38 | 1.47 |
| B_on | π_visit | 3 | 263.01 | 32.34 | 1.23 | 1.3 |
| B_on | π_sms | 3 | 300.11 | 36.84 | 1.44 | 1.53 |
| B_on | π_stage | 3 | 315.23 | 38.91 | 1.51 | 1.61 |
| S18_on | π_b | 3 | 287.17 | 59.8 | 1.4 | 1.55 |
| S18_on | π_visit | 3 | 269.51 | 55.27 | 1.24 | 1.37 |
| S18_on | π_sms | 3 | 298.03 | 61.61 | 1.43 | 1.58 |
| S18_on | π_stage | 3 | 311.05 | 64.48 | 1.5 | 1.66 |

## T2. Reference gaps between candidates (paired Monte-Carlo SE per run)

| cond | pair | seeds | mean_gap | median_paired_se | max_paired_se | median_corr |
|---|---|---|---|---|---|---|
| A_off | pi_b-pi_far | 3 | 15.334 | 0.421 | 0.449 | 0.952 |
| A_off | pi_b-pi_near | 3 | -13.149 | 0.34 | 0.368 | 0.97 |
| A_off | pi_b-pi_stage | 3 | -26.159 | 0.399 | 0.429 | 0.964 |
| A_off | pi_far-pi_stage | 3 | -41.493 | 0.495 | 0.523 | 0.951 |
| A_off | pi_near-pi_far | 3 | 28.483 | 0.43 | 0.455 | 0.958 |
| A_off | pi_near-pi_stage | 3 | -13.01 | 0.313 | 0.332 | 0.978 |
| A_on | pi_b-pi_far | 3 | 16.691 | 0.441 | 0.467 | 0.949 |
| A_on | pi_b-pi_near | 3 | -13.218 | 0.351 | 0.381 | 0.968 |
| A_on | pi_b-pi_stage | 3 | -26.229 | 0.402 | 0.433 | 0.964 |
| A_on | pi_far-pi_stage | 3 | -42.92 | 0.498 | 0.527 | 0.952 |
| A_on | pi_near-pi_far | 3 | 29.909 | 0.432 | 0.458 | 0.959 |
| A_on | pi_near-pi_stage | 3 | -13.012 | 0.315 | 0.334 | 0.978 |
| B_on | pi_b-pi_far | 3 | 21.054 | 0.41 | 0.434 | 0.957 |
| B_on | pi_b-pi_near | 3 | -16.041 | 0.356 | 0.379 | 0.969 |
| B_on | pi_b-pi_stage | 3 | -31.169 | 0.419 | 0.441 | 0.962 |
| B_on | pi_far-pi_stage | 3 | -52.223 | 0.445 | 0.47 | 0.969 |
| B_on | pi_near-pi_far | 3 | 37.095 | 0.383 | 0.403 | 0.972 |
| B_on | pi_near-pi_stage | 3 | -15.128 | 0.352 | 0.37 | 0.973 |
| S18_on | pi_b-pi_far | 3 | 17.663 | 0.481 | 0.531 | 0.941 |
| S18_on | pi_b-pi_near | 3 | -10.851 | 0.38 | 0.411 | 0.964 |
| S18_on | pi_b-pi_stage | 3 | -23.872 | 0.428 | 0.462 | 0.959 |
| S18_on | pi_far-pi_stage | 3 | -41.535 | 0.501 | 0.556 | 0.951 |
| S18_on | pi_near-pi_far | 3 | 28.514 | 0.435 | 0.484 | 0.956 |
| S18_on | pi_near-pi_stage | 3 | -13.021 | 0.321 | 0.346 | 0.977 |

## T3 (tabular). Mean error vs reference ± SE over seeds

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | +3.7 ± 8.7 | -12.4 ± 10.1 | -3.8 ± 9.8 |
| A_off | dm_blind | +1.1 ± 6.1 | -7.6 ± 5.5 | -8.8 ± 3.1 |
| A_off | is | +3.5 ± 8.7 | -12.7 ± 9.9 | -3.9 ± 9.7 |
| A_off | snips | +3.6 ± 8.7 | -12.4 ± 10.1 | -3.8 ± 9.8 |
| A_off | dr | +3.9 ± 8.6 | -11.0 ± 10.9 | -3.5 ± 10.0 |
| A_off | dm_plus_is | +4.5 ± 8.3 | -11.0 ± 9.7 | -2.9 ± 10.4 |
| A_off | pilot_is | -83.0 ± 18.2 | -36.5 ± 30.1 | -30.3 ± 15.6 |
| A_off | pilot_dr | -71.2 ± 17.8 | -32.0 ± 32.0 | -17.4 ± 13.9 |
| A_off | dm_refit | +3.7 ± 8.7 | -12.4 ± 10.1 | -3.8 ± 9.8 |
| A_on | dm | -51.2 ± 12.4 | -6.0 ± 13.5 | -12.9 ± 16.8 |
| A_on | dm_blind | -53.9 ± 9.8 | -4.2 ± 13.2 | -20.9 ± 15.2 |
| A_on | is | -51.3 ± 12.4 | -6.4 ± 13.3 | -13.0 ± 16.8 |
| A_on | snips | -51.2 ± 12.4 | -6.0 ± 13.5 | -12.9 ± 16.8 |
| A_on | dr | -51.1 ± 12.1 | -4.7 ± 13.9 | -12.8 ± 17.0 |
| A_on | dm_plus_is | -50.3 ± 11.9 | -4.7 ± 12.9 | -12.0 ± 17.1 |
| A_on | pilot_is | -79.5 ± 21.7 | -37.4 ± 37.0 | -43.9 ± 9.5 |
| A_on | pilot_dr | -68.6 ± 22.6 | -32.1 ± 38.7 | -29.6 ± 11.0 |
| A_on | dm_refit | -51.2 ± 12.4 | -6.0 ± 13.5 | -12.9 ± 16.8 |
| B_on | dm | -46.0 ± 15.3 | -13.0 ± 11.3 | -5.8 ± 12.1 |
| B_on | dm_blind | -46.1 ± 13.8 | -8.4 ± 12.9 | -20.0 ± 10.1 |
| B_on | is | -46.1 ± 15.4 | -13.3 ± 11.2 | -6.0 ± 12.1 |
| B_on | snips | -46.0 ± 15.4 | -12.9 ± 11.3 | -5.8 ± 12.1 |
| B_on | dr | -45.9 ± 15.0 | -11.7 ± 11.7 | -5.8 ± 12.3 |
| B_on | dm_plus_is | -45.1 ± 14.8 | -11.6 ± 10.7 | -5.0 ± 12.5 |
| B_on | pilot_is | -79.2 ± 23.4 | -56.5 ± 14.1 | -39.6 ± 6.7 |
| B_on | pilot_dr | -67.8 ± 24.3 | -51.4 ± 16.1 | -25.0 ± 4.8 |
| B_on | dm_refit | -46.0 ± 15.3 | -13.0 ± 11.3 | -5.8 ± 12.1 |
| S18_on | dm | -111.5 ± 4.7 | -15.3 ± 4.0 | -18.4 ± 11.7 |
| S18_on | dm_blind | -113.9 ± 4.6 | -9.5 ± 3.6 | -21.8 ± 8.6 |
| S18_on | is | -111.6 ± 4.7 | -15.7 ± 3.9 | -18.6 ± 11.6 |
| S18_on | snips | -111.5 ± 4.7 | -15.3 ± 4.0 | -18.4 ± 11.7 |
| S18_on | dr | -111.3 ± 5.1 | -13.3 ± 5.4 | -17.6 ± 11.6 |
| S18_on | dm_plus_is | -110.8 ± 5.0 | -14.0 ± 3.5 | -17.8 ± 11.7 |
| S18_on | pilot_is | -72.3 ± 14.2 | -31.0 ± 8.6 | -46.5 ± 15.5 |
| S18_on | pilot_dr | -64.4 ± 6.1 | -25.5 ± 7.8 | -33.7 ± 14.1 |
| S18_on | dm_refit | -111.5 ± 4.7 | -15.3 ± 4.0 | -18.4 ± 11.7 |

## T4 (tabular). RMSE ± bootstrap-over-seeds SE

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | 12.9 ± 4.8 | 18.9 ± 7.8 | 14.3 ± 2.4 |
| A_off | dm_blind | 8.7 ± 2.5 | 10.8 ± 5.1 | 9.8 ± 2.1 |
| A_off | dm_plus_is | 12.6 ± 5.2 | 17.6 ± 6.8 | 15.0 ± 2.5 |
| A_off | dm_refit | 12.9 ± 4.8 | 18.9 ± 7.8 | 14.3 ± 2.4 |
| A_off | dr | 12.8 ± 4.9 | 18.9 ± 7.1 | 14.6 ± 2.3 |
| A_off | is | 12.9 ± 4.7 | 18.9 ± 7.9 | 14.3 ± 2.4 |
| A_off | pilot_dr | 75.5 ± 12.9 | 55.4 ± 8.9 | 26.2 ± 12.9 |
| A_off | pilot_is | 86.9 ± 15.1 | 56.1 ± 11.1 | 37.4 ± 14.3 |
| A_off | snips | 12.9 ± 4.8 | 18.9 ± 7.8 | 14.3 ± 2.4 |
| A_on | dm | 54.1 ± 9.3 | 20.0 ± 7.9 | 27.0 ± 10.2 |
| A_on | dm_blind | 55.6 ± 7.5 | 19.2 ± 5.7 | 30.0 ± 12.6 |
| A_on | dm_plus_is | 53.1 ± 8.9 | 18.8 ± 6.8 | 27.0 ± 10.4 |
| A_on | dm_refit | 54.1 ± 9.3 | 20.0 ± 7.9 | 27.0 ± 10.2 |
| A_on | dr | 53.9 ± 9.1 | 20.2 ± 7.1 | 27.2 ± 10.4 |
| A_on | is | 54.3 ± 9.3 | 19.9 ± 8.1 | 27.1 ± 10.3 |
| A_on | pilot_dr | 75.6 ± 15.7 | 63.5 ± 20.1 | 33.4 ± 8.3 |
| A_on | pilot_is | 85.2 ± 16.8 | 64.3 ± 21.8 | 45.9 ± 7.0 |
| A_on | snips | 54.2 ± 9.3 | 20.0 ± 7.9 | 27.0 ± 10.2 |
| B_on | dm | 50.8 ± 11.6 | 20.6 ± 10.5 | 18.1 ± 7.0 |
| B_on | dm_blind | 50.1 ± 10.5 | 20.1 ± 6.6 | 24.6 ± 8.8 |
| B_on | dm_plus_is | 49.7 ± 11.1 | 19.1 ± 10.0 | 18.3 ± 6.7 |
| B_on | dm_refit | 50.8 ± 11.6 | 20.6 ± 10.5 | 18.1 ± 7.0 |
| B_on | dr | 50.6 ± 11.3 | 20.3 ± 11.2 | 18.3 ± 7.1 |
| B_on | is | 50.9 ± 11.6 | 20.7 ± 10.4 | 18.1 ± 7.1 |
| B_on | pilot_dr | 76.0 ± 16.6 | 56.2 ± 12.3 | 25.9 ± 3.9 |
| B_on | pilot_is | 85.8 ± 17.9 | 59.9 ± 11.1 | 40.7 ± 5.7 |
| B_on | snips | 50.9 ± 11.6 | 20.6 ± 10.5 | 18.1 ± 7.0 |
| S18_on | dm | 111.7 ± 3.9 | 16.3 ± 3.5 | 24.7 ± 8.4 |
| S18_on | dm_blind | 114.1 ± 3.7 | 10.8 ± 2.9 | 25.0 ± 7.4 |
| S18_on | dm_plus_is | 111.0 ± 4.1 | 14.8 ± 3.0 | 24.3 ± 8.8 |
| S18_on | dm_refit | 111.7 ± 3.9 | 16.3 ± 3.5 | 24.7 ± 8.4 |
| S18_on | dr | 111.6 ± 4.2 | 15.4 ± 4.8 | 24.1 ± 8.4 |
| S18_on | is | 111.8 ± 3.9 | 16.6 ± 3.4 | 24.8 ± 8.5 |
| S18_on | pilot_dr | 65.0 ± 5.1 | 27.8 ± 5.6 | 39.2 ± 12.7 |
| S18_on | pilot_is | 75.0 ± 11.5 | 33.3 ± 6.2 | 51.4 ± 13.7 |
| S18_on | snips | 111.7 ± 3.9 | 16.3 ± 3.5 | 24.7 ± 8.4 |

## T3 (nontabular). Mean error vs reference ± SE over seeds

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | -2.5 ± 4.1 | -4.6 ± 2.8 | -9.8 ± 0.8 |
| A_off | is | +55.9 ± 14.5 | +39.4 ± 38.3 | +41.4 ± 22.8 |
| A_off | snips | +15.0 ± 8.9 | +15.1 ± 33.4 | +11.5 ± 19.0 |
| A_off | dr | +5.0 ± 5.0 | +13.4 ± 40.3 | +12.1 ± 20.6 |
| A_off | pilot_dr | -71.9 ± 19.8 | -32.5 ± 35.8 | -15.6 ± 8.0 |
| A_on | dm | -49.9 ± 4.8 | -4.6 ± 7.9 | -6.5 ± 1.2 |
| A_on | is | -18.6 ± 15.3 | +30.6 ± 43.1 | +17.4 ± 4.7 |
| A_on | snips | -45.5 ± 11.6 | +6.0 ± 36.2 | -7.0 ± 4.0 |
| A_on | dr | -51.5 ± 9.3 | +2.4 ± 42.5 | -14.9 ± 4.1 |
| A_on | pilot_dr | -67.2 ± 23.4 | -30.3 ± 40.3 | -30.1 ± 10.4 |
| B_on | dm | -42.3 ± 6.3 | -4.0 ± 6.8 | -7.2 ± 1.6 |
| B_on | is | -16.7 ± 19.3 | +25.1 ± 44.8 | +21.8 ± 3.9 |
| B_on | snips | -43.2 ± 15.8 | +0.7 ± 37.6 | -3.1 ± 3.5 |
| B_on | dr | -52.6 ± 14.6 | -3.1 ± 44.7 | -6.0 ± 6.0 |
| B_on | pilot_dr | -66.2 ± 26.9 | -55.3 ± 17.6 | -21.9 ± 1.6 |
| S18_on | dm | -105.4 ± 14.5 | -10.5 ± 3.9 | -16.3 ± 4.7 |
| S18_on | is | -94.7 ± 2.7 | +33.7 ± 43.0 | +3.2 ± 10.3 |
| S18_on | snips | -112.8 ± 3.7 | +8.4 ± 35.3 | -21.2 ± 8.6 |
| S18_on | dr | -116.7 ± 6.7 | +4.9 ± 41.8 | -29.5 ± 8.0 |
| S18_on | pilot_dr | -60.9 ± 9.4 | -26.6 ± 5.9 | -33.6 ± 13.7 |

## T4 (nontabular). RMSE ± bootstrap-over-seeds SE

| cond | estimator | π_visit | π_sms | π_stage |
|---|---|---|---|---|
| A_off | dm | 6.3 ± 0.9 | 6.1 ± 2.5 | 9.8 ± 0.7 |
| A_off | dr | 8.7 ± 2.3 | 58.5 ± 10.2 | 31.6 ± 8.7 |
| A_off | is | 59.6 ± 11.8 | 66.9 ± 19.1 | 52.5 ± 15.3 |
| A_off | pilot_dr | 77.2 ± 14.2 | 60.2 ± 7.7 | 19.2 ± 7.2 |
| A_off | snips | 19.6 ± 7.0 | 49.6 ± 10.2 | 29.2 ± 6.7 |
| A_on | dm | 50.4 ± 3.9 | 12.0 ± 3.2 | 6.8 ± 1.0 |
| A_on | dr | 53.1 ± 7.3 | 60.1 ± 14.8 | 16.0 ± 3.0 |
| A_on | is | 28.5 ± 5.4 | 68.2 ± 27.0 | 18.6 ± 3.4 |
| A_on | pilot_dr | 74.9 ± 16.1 | 64.6 ± 21.8 | 33.5 ± 8.5 |
| A_on | snips | 48.4 ± 8.7 | 51.5 ± 14.1 | 8.9 ± 3.4 |
| B_on | dm | 43.2 ± 4.8 | 10.4 ± 2.5 | 7.5 ± 1.3 |
| B_on | dr | 56.5 ± 11.8 | 63.3 ± 13.7 | 10.4 ± 2.8 |
| B_on | is | 32.0 ± 7.0 | 68.2 ± 27.3 | 22.5 ± 3.0 |
| B_on | pilot_dr | 76.3 ± 18.1 | 60.7 ± 13.3 | 22.0 ± 1.3 |
| B_on | snips | 48.6 ± 12.4 | 53.2 ± 12.1 | 5.8 ± 1.6 |
| S18_on | dm | 107.4 ± 11.8 | 11.9 ± 3.5 | 17.7 ± 4.1 |
| S18_on | dr | 117.1 ± 5.5 | 59.3 ± 15.3 | 31.6 ± 6.5 |
| S18_on | is | 94.7 ± 2.2 | 69.5 ± 32.5 | 15.0 ± 2.8 |
| S18_on | pilot_dr | 62.3 ± 7.9 | 27.9 ± 4.4 | 38.8 ± 11.2 |
| S18_on | snips | 113.0 ± 3.0 | 50.6 ± 15.2 | 24.4 ± 7.6 |

## T5. Logged mean of the incumbent minus its independent reference (should be 0 in expectation)

| cond | n_defined | mean_error | se_mean_error |
|---|---|---|---|
| A_off | 3 | 1.36 | 0.74 |
| A_on | 3 | 1.93 | 0.36 |
| B_on | 3 | 2.32 | 0.9 |
| S18_on | 3 | 0.84 | 1.87 |

## T6. Selection over the candidates (regret in recovery US$/decision)

| cond | regime | estimator | n_defined | n_top_resolved | correct_among_resolved | correct_all | mean_regret | se_mean_regret | mean_regret_resolved_runs | mean_gain_vs_incumbent | se_mean_gain_vs_incumbent | n_picks_resolved_worse_than_incumbent | n_picks_resolved_better_than_incumbent | picks | ref_best |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_off | nontabular | dm | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 26.16 | 1.83 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| A_off | nontabular | dr | 3 | 3 | 1 | 1 | 8.72 | 4.49 | 8.72 | 17.44 | 4.2 | 0 | 3 | {"pi_near": 2, "pi_stage": 1} | {"pi_stage": 3} |
| A_off | nontabular | is | 3 | 3 | 1 | 1 | 8.72 | 4.49 | 8.72 | 17.44 | 4.2 | 0 | 3 | {"pi_near": 2, "pi_stage": 1} | {"pi_stage": 3} |
| A_off | nontabular | pilot_dr | 3 | 3 | 2 | 2 | 3.75 | 3.75 | 3.75 | 22.41 | 5.32 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_off | nontabular | snips | 3 | 3 | 1 | 1 | 8.72 | 4.49 | 8.72 | 17.44 | 4.2 | 0 | 3 | {"pi_near": 2, "pi_stage": 1} | {"pi_stage": 3} |
| A_off | tabular | dm | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 26.16 | 1.83 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| A_off | tabular | dm_blind | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 26.16 | 1.83 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| A_off | tabular | dm_plus_is | 3 | 3 | 2 | 2 | 3.75 | 3.75 | 3.75 | 22.41 | 5.32 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_off | tabular | dr | 3 | 3 | 2 | 2 | 3.75 | 3.75 | 3.75 | 22.41 | 5.32 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_off | tabular | is | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 26.16 | 1.83 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| A_off | tabular | pilot_dr | 3 | 3 | 2 | 2 | 3.75 | 3.75 | 3.75 | 22.41 | 5.32 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_off | tabular | pilot_is | 3 | 3 | 2 | 2 | 3.75 | 3.75 | 3.75 | 22.41 | 5.32 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_off | tabular | snips | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 26.16 | 1.83 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| A_on | nontabular | dm | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 26.23 | 1.74 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| A_on | nontabular | dr | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | nontabular | is | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | nontabular | pilot_dr | 3 | 3 | 1 | 1 | 13.57 | 8.58 | 13.57 | 12.66 | 7.43 | 0 | 2 | {"pi_b": 1, "pi_near": 1, "pi_stage": 1} | {"pi_stage": 3} |
| A_on | nontabular | snips | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | tabular | dm | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | tabular | dm_blind | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | tabular | dm_plus_is | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | tabular | dr | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | tabular | is | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| A_on | tabular | pilot_dr | 3 | 3 | 1 | 1 | 13.57 | 8.58 | 13.57 | 12.66 | 7.43 | 0 | 2 | {"pi_b": 1, "pi_near": 1, "pi_stage": 1} | {"pi_stage": 3} |
| A_on | tabular | pilot_is | 3 | 3 | 0 | 0 | 22.15 | 5.55 | 22.15 | 4.08 | 4.08 | 0 | 1 | {"pi_b": 2, "pi_near": 1} | {"pi_stage": 3} |
| A_on | tabular | snips | 3 | 3 | 2 | 2 | 4.97 | 4.97 | 4.97 | 21.26 | 3.41 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | nontabular | dm | 3 | 3 | 3 | 3 | 0.0 | 0.0 | 0.0 | 31.17 | 2.16 | 0 | 3 | {"pi_stage": 3} | {"pi_stage": 3} |
| B_on | nontabular | dr | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | nontabular | is | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | nontabular | pilot_dr | 3 | 3 | 2 | 2 | 9.22 | 9.22 | 9.22 | 21.95 | 11.05 | 0 | 2 | {"pi_b": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | nontabular | snips | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | dm | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | dm_blind | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | dm_plus_is | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | dr | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | is | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | pilot_dr | 3 | 3 | 2 | 2 | 9.22 | 9.22 | 9.22 | 21.95 | 11.05 | 0 | 2 | {"pi_b": 1, "pi_stage": 2} | {"pi_stage": 3} |
| B_on | tabular | pilot_is | 3 | 3 | 1 | 1 | 19.47 | 9.77 | 19.47 | 11.7 | 11.7 | 0 | 1 | {"pi_b": 2, "pi_stage": 1} | {"pi_stage": 3} |
| B_on | tabular | snips | 3 | 3 | 2 | 2 | 5.75 | 5.75 | 5.75 | 25.42 | 3.88 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | nontabular | dm | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | nontabular | dr | 3 | 3 | 0 | 0 | 19.67 | 2.18 | 19.67 | 4.2 | 4.2 | 0 | 1 | {"pi_b": 2, "pi_near": 1} | {"pi_stage": 3} |
| S18_on | nontabular | is | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | nontabular | pilot_dr | 3 | 3 | 2 | 2 | 7.87 | 7.87 | 7.87 | 16.0 | 8.45 | 0 | 2 | {"pi_b": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | nontabular | snips | 3 | 3 | 0 | 0 | 19.67 | 2.18 | 19.67 | 4.2 | 4.2 | 0 | 1 | {"pi_b": 2, "pi_near": 1} | {"pi_stage": 3} |
| S18_on | tabular | dm | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | tabular | dm_blind | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | tabular | dm_plus_is | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | tabular | dr | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | tabular | is | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |
| S18_on | tabular | pilot_dr | 3 | 3 | 1 | 1 | 14.31 | 7.26 | 14.31 | 9.56 | 9.56 | 0 | 1 | {"pi_b": 2, "pi_stage": 1} | {"pi_stage": 3} |
| S18_on | tabular | pilot_is | 3 | 3 | 1 | 1 | 14.31 | 7.26 | 14.31 | 9.56 | 9.56 | 0 | 1 | {"pi_b": 2, "pi_stage": 1} | {"pi_stage": 3} |
| S18_on | tabular | snips | 3 | 3 | 2 | 2 | 5.36 | 5.36 | 5.36 | 18.51 | 3.2 | 0 | 3 | {"pi_near": 1, "pi_stage": 2} | {"pi_stage": 3} |

## T7. Interval diagnostic (containment of the reference; counts over seeds)

| cond | target | interval | n_seeds | contains | mean_width | sd_error_across_seeds | mean_error | mean_boot_sd | width_implied_sd | mean_reference_se |
|---|---|---|---|---|---|---|---|---|---|---|
| A_off | π_visit | dm | 3 | 0 | 1.04 | 15.1 | 3.66 | nan | 0.32 | 1.22 |
| A_off | π_visit | dm_plus_is | 3 | 3 | 101.58 | 14.46 | 4.53 | nan | 30.88 | 1.22 |
| A_off | π_visit | dm_refit | 3 | 3 | 69.32 | 15.1 | 3.66 | 21.24 | 21.07 | 1.22 |
| A_off | π_visit | dr | 3 | 3 | 68.42 | 14.96 | 3.9 | nan | 20.8 | 1.22 |
| A_off | π_visit | is | 3 | 3 | 69.96 | 15.13 | 3.54 | nan | 21.26 | 1.22 |
| A_off | π_visit | pilot_dr | 3 | 1 | 159.6 | 30.77 | -71.18 | nan | 48.51 | 1.22 |
| A_off | π_visit | pilot_is | 3 | 2 | 160.37 | 31.51 | -83.04 | nan | 48.75 | 1.22 |
| A_off | π_visit | snips | 3 | 3 | 70.2 | 15.1 | 3.65 | nan | 21.34 | 1.22 |
| A_off | π_sms | dm | 3 | 0 | 1.07 | 17.46 | -12.37 | nan | 0.33 | 1.42 |
| A_off | π_sms | dm_plus_is | 3 | 3 | 98.13 | 16.75 | -11.04 | nan | 29.83 | 1.42 |
| A_off | π_sms | dm_refit | 3 | 2 | 57.21 | 17.46 | -12.37 | 17.27 | 17.39 | 1.42 |
| A_off | π_sms | dr | 3 | 2 | 57.3 | 18.83 | -11.04 | nan | 17.42 | 1.42 |
| A_off | π_sms | is | 3 | 2 | 55.89 | 17.16 | -12.74 | nan | 16.99 | 1.42 |
| A_off | π_sms | pilot_dr | 3 | 3 | 199.76 | 55.48 | -31.96 | nan | 60.72 | 1.42 |
| A_off | π_sms | pilot_is | 3 | 3 | 199.36 | 52.16 | -36.52 | nan | 60.6 | 1.42 |
| A_off | π_sms | snips | 3 | 2 | 55.81 | 17.48 | -12.35 | nan | 16.96 | 1.42 |
| A_off | π_stage | dm | 3 | 0 | 1.18 | 16.9 | -3.81 | nan | 0.36 | 1.49 |
| A_off | π_stage | dm_plus_is | 3 | 3 | 119.68 | 17.96 | -2.93 | nan | 36.38 | 1.49 |
| A_off | π_stage | dm_refit | 3 | 3 | 84.31 | 16.9 | -3.81 | 26.31 | 25.63 | 1.49 |
| A_off | π_stage | dr | 3 | 3 | 85.12 | 17.4 | -3.49 | nan | 25.87 | 1.49 |
| A_off | π_stage | is | 3 | 3 | 88.14 | 16.88 | -3.93 | nan | 26.79 | 1.49 |
| A_off | π_stage | pilot_dr | 3 | 3 | 187.94 | 24.04 | -17.38 | nan | 57.13 | 1.49 |
| A_off | π_stage | pilot_is | 3 | 3 | 199.58 | 26.95 | -30.28 | nan | 60.67 | 1.49 |
| A_off | π_stage | snips | 3 | 3 | 87.3 | 16.9 | -3.8 | nan | 26.54 | 1.49 |
| A_on | π_visit | dm | 3 | 0 | 0.87 | 21.47 | -51.21 | nan | 0.27 | 1.24 |
| A_on | π_visit | dm_plus_is | 3 | 2 | 91.75 | 20.61 | -50.34 | nan | 27.89 | 1.24 |
| A_on | π_visit | dm_refit | 3 | 1 | 55.56 | 21.47 | -51.21 | 17.63 | 16.89 | 1.24 |
| A_on | π_visit | dr | 3 | 1 | 55.79 | 20.94 | -51.07 | nan | 16.96 | 1.24 |
| A_on | π_visit | is | 3 | 1 | 57.94 | 21.5 | -51.33 | nan | 17.61 | 1.24 |
| A_on | π_visit | pilot_dr | 3 | 1 | 161.64 | 39.06 | -68.59 | nan | 49.13 | 1.24 |
| A_on | π_visit | pilot_is | 3 | 2 | 160.23 | 37.66 | -79.46 | nan | 48.7 | 1.24 |
| A_on | π_visit | snips | 3 | 1 | 56.96 | 21.48 | -51.24 | nan | 17.31 | 1.24 |
| A_on | π_sms | dm | 3 | 0 | 1.13 | 23.31 | -6.03 | nan | 0.34 | 1.44 |
| A_on | π_sms | dm_plus_is | 3 | 3 | 102.79 | 22.34 | -4.66 | nan | 31.25 | 1.44 |
| A_on | π_sms | dm_refit | 3 | 2 | 60.34 | 23.31 | -6.03 | 18.47 | 18.34 | 1.44 |
| A_on | π_sms | dr | 3 | 2 | 60.09 | 24.06 | -4.74 | nan | 18.27 | 1.44 |
| A_on | π_sms | is | 3 | 2 | 58.17 | 23.09 | -6.41 | nan | 17.68 | 1.44 |
| A_on | π_sms | pilot_dr | 3 | 3 | 202.54 | 67.04 | -32.1 | nan | 61.57 | 1.44 |
| A_on | π_sms | pilot_is | 3 | 2 | 203.41 | 64.06 | -37.39 | nan | 61.83 | 1.44 |
| A_on | π_sms | snips | 3 | 2 | 60.33 | 23.34 | -6.01 | nan | 18.34 | 1.44 |
| A_on | π_stage | dm | 3 | 0 | 1.26 | 29.1 | -12.88 | nan | 0.38 | 1.51 |
| A_on | π_stage | dm_plus_is | 3 | 2 | 122.97 | 29.56 | -12.01 | nan | 37.38 | 1.51 |
| A_on | π_stage | dm_refit | 3 | 2 | 90.49 | 29.1 | -12.88 | 27.76 | 27.51 | 1.51 |
| A_on | π_stage | dr | 3 | 2 | 89.37 | 29.4 | -12.8 | nan | 27.17 | 1.51 |
| A_on | π_stage | is | 3 | 2 | 91.54 | 29.07 | -13.0 | nan | 27.82 | 1.51 |
| A_on | π_stage | pilot_dr | 3 | 3 | 186.51 | 19.09 | -29.56 | nan | 56.69 | 1.51 |
| A_on | π_stage | pilot_is | 3 | 3 | 193.97 | 16.4 | -43.93 | nan | 58.96 | 1.51 |
| A_on | π_stage | snips | 3 | 2 | 91.57 | 29.12 | -12.87 | nan | 27.83 | 1.51 |
| B_on | π_visit | dm | 3 | 0 | 0.86 | 26.58 | -45.96 | nan | 0.26 | 1.23 |
| B_on | π_visit | dm_plus_is | 3 | 2 | 92.67 | 25.63 | -45.09 | nan | 28.17 | 1.23 |
| B_on | π_visit | dm_refit | 3 | 1 | 56.34 | 26.58 | -45.96 | 17.37 | 17.13 | 1.23 |
| B_on | π_visit | dr | 3 | 1 | 56.3 | 26.04 | -45.92 | nan | 17.11 | 1.23 |
| B_on | π_visit | is | 3 | 1 | 58.43 | 26.61 | -46.08 | nan | 17.76 | 1.23 |
| B_on | π_visit | pilot_dr | 3 | 1 | 159.48 | 42.09 | -67.78 | nan | 48.48 | 1.23 |
| B_on | π_visit | pilot_is | 3 | 1 | 158.18 | 40.52 | -79.21 | nan | 48.08 | 1.23 |
| B_on | π_visit | snips | 3 | 1 | 56.97 | 26.6 | -45.99 | nan | 17.32 | 1.23 |
| B_on | π_sms | dm | 3 | 0 | 1.11 | 19.59 | -12.95 | nan | 0.34 | 1.44 |
| B_on | π_sms | dm_plus_is | 3 | 3 | 99.71 | 18.53 | -11.6 | nan | 30.31 | 1.44 |
| B_on | π_sms | dm_refit | 3 | 2 | 58.16 | 19.59 | -12.95 | 17.9 | 17.68 | 1.44 |
| B_on | π_sms | dr | 3 | 2 | 57.7 | 20.35 | -11.7 | nan | 17.54 | 1.44 |
| B_on | π_sms | is | 3 | 2 | 57.4 | 19.4 | -13.34 | nan | 17.45 | 1.44 |
| B_on | π_sms | pilot_dr | 3 | 3 | 197.16 | 27.81 | -51.39 | nan | 59.93 | 1.44 |
| B_on | π_sms | pilot_is | 3 | 3 | 202.69 | 24.5 | -56.5 | nan | 61.61 | 1.44 |
| B_on | π_sms | snips | 3 | 2 | 57.64 | 19.6 | -12.95 | nan | 17.52 | 1.44 |
| B_on | π_stage | dm | 3 | 0 | 1.29 | 20.98 | -5.84 | nan | 0.39 | 1.52 |
| B_on | π_stage | dm_plus_is | 3 | 3 | 124.31 | 21.59 | -4.97 | nan | 37.79 | 1.52 |
| B_on | π_stage | dm_refit | 3 | 3 | 90.99 | 20.98 | -5.84 | 27.98 | 27.66 | 1.52 |
| B_on | π_stage | dr | 3 | 3 | 90.92 | 21.27 | -5.84 | nan | 27.64 | 1.52 |
| B_on | π_stage | is | 3 | 3 | 89.03 | 20.94 | -5.97 | nan | 27.06 | 1.52 |
| B_on | π_stage | pilot_dr | 3 | 3 | 200.14 | 8.33 | -24.99 | nan | 60.84 | 1.52 |
| B_on | π_stage | pilot_is | 3 | 3 | 204.88 | 11.6 | -39.62 | nan | 62.28 | 1.52 |
| B_on | π_stage | snips | 3 | 3 | 90.74 | 20.99 | -5.83 | nan | 27.58 | 1.52 |
| S18_on | π_visit | dm | 3 | 0 | 0.65 | 8.22 | -111.46 | nan | 0.2 | 1.24 |
| S18_on | π_visit | dm_plus_is | 3 | 0 | 80.97 | 8.69 | -110.78 | nan | 24.61 | 1.24 |
| S18_on | π_visit | dm_refit | 3 | 0 | 49.05 | 8.22 | -111.46 | 15.39 | 14.91 | 1.24 |
| S18_on | π_visit | dr | 3 | 0 | 49.18 | 8.81 | -111.34 | nan | 14.95 | 1.24 |
| S18_on | π_visit | is | 3 | 0 | 50.2 | 8.19 | -111.58 | nan | 15.26 | 1.24 |
| S18_on | π_visit | pilot_dr | 3 | 3 | 168.2 | 10.53 | -64.39 | nan | 51.13 | 1.24 |
| S18_on | π_visit | pilot_is | 3 | 2 | 169.4 | 24.62 | -72.29 | nan | 51.49 | 1.24 |
| S18_on | π_visit | snips | 3 | 0 | 50.0 | 8.2 | -111.52 | nan | 15.2 | 1.24 |
| S18_on | π_sms | dm | 3 | 0 | 1.15 | 6.96 | -15.29 | nan | 0.35 | 1.43 |
| S18_on | π_sms | dm_plus_is | 3 | 3 | 107.45 | 6.1 | -13.99 | nan | 32.66 | 1.43 |
| S18_on | π_sms | dm_refit | 3 | 3 | 64.51 | 6.96 | -15.29 | 19.31 | 19.61 | 1.43 |
| S18_on | π_sms | dr | 3 | 3 | 63.49 | 9.35 | -13.34 | nan | 19.3 | 1.43 |
| S18_on | π_sms | is | 3 | 3 | 63.25 | 6.72 | -15.66 | nan | 19.23 | 1.43 |
| S18_on | π_sms | pilot_dr | 3 | 3 | 214.48 | 13.43 | -25.53 | nan | 65.19 | 1.43 |
| S18_on | π_sms | pilot_is | 3 | 3 | 213.84 | 14.89 | -31.0 | nan | 65.0 | 1.43 |
| S18_on | π_sms | snips | 3 | 3 | 62.42 | 6.96 | -15.29 | nan | 18.97 | 1.43 |
| S18_on | π_stage | dm | 3 | 0 | 1.19 | 20.19 | -18.43 | nan | 0.36 | 1.5 |
| S18_on | π_stage | dm_plus_is | 3 | 2 | 114.74 | 20.27 | -17.75 | nan | 34.88 | 1.5 |
| S18_on | π_stage | dm_refit | 3 | 3 | 91.64 | 20.19 | -18.43 | 27.57 | 27.86 | 1.5 |
| S18_on | π_stage | dr | 3 | 3 | 91.5 | 20.18 | -17.57 | nan | 27.81 | 1.5 |
| S18_on | π_stage | is | 3 | 3 | 93.62 | 20.16 | -18.55 | nan | 28.46 | 1.5 |
| S18_on | π_stage | pilot_dr | 3 | 3 | 197.31 | 24.38 | -33.74 | nan | 59.98 | 1.5 |
| S18_on | π_stage | pilot_is | 3 | 3 | 198.19 | 26.93 | -46.48 | nan | 60.24 | 1.5 |
| S18_on | π_stage | snips | 3 | 3 | 92.64 | 20.19 | -18.43 | nan | 28.16 | 1.5 |

## T8. Same logs: gradient-boosted minus tabular error

| cond | target | estimator | n_seeds | mean_diff_nontab_minus_tab | se |
|---|---|---|---|---|---|
| A_off | π_visit | dm | 3 | -6.14 | 12.17 |
| A_off | π_sms | dm | 3 | 7.72 | 7.8 |
| A_off | π_stage | dm | 3 | -5.95 | 10.24 |
| A_on | π_visit | dm | 3 | 1.28 | 16.19 |
| A_on | π_sms | dm | 3 | 1.47 | 7.97 |
| A_on | π_stage | dm | 3 | 6.33 | 17.58 |
| B_on | π_visit | dm | 3 | 3.68 | 17.31 |
| B_on | π_sms | dm | 3 | 8.98 | 6.19 |
| B_on | π_stage | dm | 3 | -1.34 | 13.05 |
| S18_on | π_visit | dm | 3 | 6.07 | 10.09 |
| S18_on | π_sms | dm | 3 | 4.78 | 1.0 |
| S18_on | π_stage | dm | 3 | 2.09 | 8.91 |
| A_off | π_visit | is | 3 | 52.38 | 6.68 |
| A_off | π_sms | is | 3 | 52.11 | 31.94 |
| A_off | π_stage | is | 3 | 45.32 | 19.5 |
| A_on | π_visit | is | 3 | 32.72 | 3.15 |
| A_on | π_sms | is | 3 | 37.05 | 34.21 |
| A_on | π_stage | is | 3 | 30.38 | 20.72 |
| B_on | π_visit | is | 3 | 29.41 | 3.98 |
| B_on | π_sms | is | 3 | 38.39 | 36.62 |
| B_on | π_stage | is | 3 | 27.81 | 14.45 |
| S18_on | π_visit | is | 3 | 16.91 | 5.14 |
| S18_on | π_sms | is | 3 | 49.35 | 41.03 |
| S18_on | π_stage | is | 3 | 21.74 | 18.18 |
| A_off | π_visit | snips | 3 | 11.33 | 2.8 |
| A_off | π_sms | snips | 3 | 27.46 | 26.84 |
| A_off | π_stage | snips | 3 | 15.33 | 15.56 |
| A_on | π_visit | snips | 3 | 5.72 | 0.91 |
| A_on | π_sms | snips | 3 | 12.01 | 27.07 |
| A_on | π_stage | snips | 3 | 5.89 | 19.28 |
| B_on | π_visit | snips | 3 | 2.82 | 2.06 |
| B_on | π_sms | snips | 3 | 13.62 | 29.32 |
| B_on | π_stage | snips | 3 | 2.71 | 13.05 |
| S18_on | π_visit | snips | 3 | -1.33 | 1.68 |
| S18_on | π_sms | snips | 3 | 23.72 | 33.21 |
| S18_on | π_stage | snips | 3 | -2.79 | 15.96 |
| A_off | π_visit | dr | 3 | 1.13 | 4.76 |
| A_off | π_sms | dr | 3 | 24.42 | 33.23 |
| A_off | π_stage | dr | 3 | 15.62 | 15.91 |
| A_on | π_visit | dr | 3 | -0.4 | 3.19 |
| A_on | π_sms | dr | 3 | 7.14 | 33.38 |
| A_on | π_stage | dr | 3 | -2.11 | 15.8 |
| B_on | π_visit | dr | 3 | -6.66 | 3.26 |
| B_on | π_sms | dr | 3 | 8.63 | 36.04 |
| B_on | π_stage | dr | 3 | -0.17 | 9.31 |
| S18_on | π_visit | dr | 3 | -5.39 | 2.58 |
| S18_on | π_sms | dr | 3 | 18.21 | 38.33 |
| S18_on | π_stage | dr | 3 | -11.91 | 11.12 |
| A_off | π_visit | pilot_dr | 3 | -0.7 | 2.94 |
| A_off | π_sms | pilot_dr | 3 | -0.54 | 4.41 |
| A_off | π_stage | pilot_dr | 3 | 1.81 | 5.9 |
| A_on | π_visit | pilot_dr | 3 | 1.4 | 0.9 |
| A_on | π_sms | pilot_dr | 3 | 1.77 | 2.82 |
| A_on | π_stage | pilot_dr | 3 | -0.5 | 2.25 |
| B_on | π_visit | pilot_dr | 3 | 1.58 | 3.3 |
| B_on | π_sms | pilot_dr | 3 | -3.95 | 1.69 |
| B_on | π_stage | pilot_dr | 3 | 3.11 | 3.22 |
| S18_on | π_visit | pilot_dr | 3 | 3.5 | 3.99 |
| S18_on | π_sms | pilot_dr | 3 | -1.09 | 1.91 |
| S18_on | π_stage | pilot_dr | 3 | 0.14 | 6.21 |

## T9. Seed-paired condition contrasts of the error

| contrast | regime | estimator | target | n_seeds | mean_diff | se |
|---|---|---|---|---|---|---|
| A_on - A_off | factual | logged_mean | π_b | 3 | 0.58 | 0.49 |
| A_on - A_off | nontabular | dm | π_visit | 3 | -47.45 | 1.13 |
| A_on - A_off | nontabular | dm | π_sms | 3 | 0.09 | 5.36 |
| A_on - A_off | nontabular | dm | π_stage | 3 | 3.21 | 0.88 |
| A_on - A_off | nontabular | dr | π_visit | 3 | -56.5 | 7.44 |
| A_on - A_off | nontabular | dr | π_sms | 3 | -10.97 | 13.44 |
| A_on - A_off | nontabular | dr | π_stage | 3 | -27.05 | 18.0 |
| A_on - A_off | nontabular | is | π_visit | 3 | -74.53 | 7.35 |
| A_on - A_off | nontabular | is | π_sms | 3 | -8.74 | 12.74 |
| A_on - A_off | nontabular | is | π_stage | 3 | -24.01 | 18.44 |
| A_on - A_off | nontabular | pilot_dr | π_visit | 3 | 4.69 | 4.02 |
| A_on - A_off | nontabular | pilot_dr | π_sms | 3 | 2.18 | 20.45 |
| A_on - A_off | nontabular | pilot_dr | π_stage | 3 | -14.5 | 12.5 |
| A_on - A_off | nontabular | snips | π_visit | 3 | -60.5 | 6.88 |
| A_on - A_off | nontabular | snips | π_sms | 3 | -9.11 | 10.21 |
| A_on - A_off | nontabular | snips | π_stage | 3 | -18.51 | 15.06 |
| A_on - A_off | tabular | dm | π_visit | 3 | -54.87 | 4.77 |
| A_on - A_off | tabular | dm | π_sms | 3 | 6.34 | 5.24 |
| A_on - A_off | tabular | dm | π_stage | 3 | -9.07 | 15.12 |
| A_on - A_off | tabular | dm_blind | π_visit | 3 | -54.99 | 5.66 |
| A_on - A_off | tabular | dm_blind | π_sms | 3 | 3.4 | 8.87 |
| A_on - A_off | tabular | dm_blind | π_stage | 3 | -12.13 | 14.87 |
| A_on - A_off | tabular | dm_plus_is | π_visit | 3 | -54.87 | 4.77 |
| A_on - A_off | tabular | dm_plus_is | π_sms | 3 | 6.38 | 5.27 |
| A_on - A_off | tabular | dm_plus_is | π_stage | 3 | -9.08 | 15.13 |
| A_on - A_off | tabular | dm_refit | π_visit | 3 | -54.87 | 4.77 |
| A_on - A_off | tabular | dm_refit | π_sms | 3 | 6.34 | 5.24 |
| A_on - A_off | tabular | dm_refit | π_stage | 3 | -9.07 | 15.12 |
| A_on - A_off | tabular | dr | π_visit | 3 | -54.96 | 4.63 |
| A_on - A_off | tabular | dr | π_sms | 3 | 6.3 | 5.3 |
| A_on - A_off | tabular | dr | π_stage | 3 | -9.31 | 15.3 |
| A_on - A_off | tabular | is | π_visit | 3 | -54.87 | 4.77 |
| A_on - A_off | tabular | is | π_sms | 3 | 6.33 | 5.24 |
| A_on - A_off | tabular | is | π_stage | 3 | -9.07 | 15.12 |
| A_on - A_off | tabular | pilot_dr | π_visit | 3 | 2.59 | 4.83 |
| A_on - A_off | tabular | pilot_dr | π_sms | 3 | -0.13 | 15.68 |
| A_on - A_off | tabular | pilot_dr | π_stage | 3 | -12.19 | 15.39 |
| A_on - A_off | tabular | pilot_is | π_visit | 3 | 3.58 | 6.26 |
| A_on - A_off | tabular | pilot_is | π_sms | 3 | -0.88 | 15.28 |
| A_on - A_off | tabular | pilot_is | π_stage | 3 | -13.65 | 13.9 |
| A_on - A_off | tabular | snips | π_visit | 3 | -54.89 | 4.77 |
| A_on - A_off | tabular | snips | π_sms | 3 | 6.35 | 5.25 |
| A_on - A_off | tabular | snips | π_stage | 3 | -9.07 | 15.13 |
| B_on - A_on | factual | logged_mean | π_b | 3 | 0.39 | 0.62 |
| B_on - A_on | nontabular | dm | π_visit | 3 | 7.66 | 3.14 |
| B_on - A_on | nontabular | dm | π_sms | 3 | 0.58 | 1.11 |
| B_on - A_on | nontabular | dm | π_stage | 3 | -0.63 | 0.47 |
| B_on - A_on | nontabular | dr | π_visit | 3 | -1.11 | 6.04 |
| B_on - A_on | nontabular | dr | π_sms | 3 | -5.47 | 2.57 |
| B_on - A_on | nontabular | dr | π_stage | 3 | 8.91 | 2.08 |
| B_on - A_on | nontabular | is | π_visit | 3 | 1.95 | 6.23 |
| B_on - A_on | nontabular | is | π_sms | 3 | -5.58 | 3.42 |
| B_on - A_on | nontabular | is | π_stage | 3 | 4.47 | 1.23 |
| B_on - A_on | nontabular | pilot_dr | π_visit | 3 | 0.99 | 3.84 |
| B_on - A_on | nontabular | pilot_dr | π_sms | 3 | -25.01 | 23.3 |
| B_on - A_on | nontabular | pilot_dr | π_stage | 3 | 8.18 | 9.93 |
| B_on - A_on | nontabular | snips | π_visit | 3 | 2.35 | 5.59 |
| B_on - A_on | nontabular | snips | π_sms | 3 | -5.32 | 3.17 |
| B_on - A_on | nontabular | snips | π_stage | 3 | 3.86 | 1.15 |
| B_on - A_on | tabular | dm | π_visit | 3 | 5.25 | 3.79 |
| B_on - A_on | tabular | dm | π_sms | 3 | -6.93 | 2.62 |
| B_on - A_on | tabular | dm | π_stage | 3 | 7.04 | 5.27 |
| B_on - A_on | tabular | dm_blind | π_visit | 3 | 7.79 | 4.29 |
| B_on - A_on | tabular | dm_blind | π_sms | 3 | -4.21 | 0.48 |
| B_on - A_on | tabular | dm_blind | π_stage | 3 | 0.94 | 5.04 |
| B_on - A_on | tabular | dm_plus_is | π_visit | 3 | 5.26 | 3.79 |
| B_on - A_on | tabular | dm_plus_is | π_sms | 3 | -6.94 | 2.62 |
| B_on - A_on | tabular | dm_plus_is | π_stage | 3 | 7.04 | 5.27 |
| B_on - A_on | tabular | dm_refit | π_visit | 3 | 5.25 | 3.79 |
| B_on - A_on | tabular | dm_refit | π_sms | 3 | -6.93 | 2.62 |
| B_on - A_on | tabular | dm_refit | π_stage | 3 | 7.04 | 5.27 |
| B_on - A_on | tabular | dr | π_visit | 3 | 5.15 | 3.88 |
| B_on - A_on | tabular | dr | π_sms | 3 | -6.96 | 2.56 |
| B_on - A_on | tabular | dr | π_stage | 3 | 6.96 | 5.26 |
| B_on - A_on | tabular | is | π_visit | 3 | 5.25 | 3.79 |
| B_on - A_on | tabular | is | π_sms | 3 | -6.93 | 2.62 |
| B_on - A_on | tabular | is | π_stage | 3 | 7.04 | 5.27 |
| B_on - A_on | tabular | pilot_dr | π_visit | 3 | 0.81 | 1.76 |
| B_on - A_on | tabular | pilot_dr | π_sms | 3 | -19.29 | 22.78 |
| B_on - A_on | tabular | pilot_dr | π_stage | 3 | 4.57 | 9.11 |
| B_on - A_on | tabular | pilot_is | π_visit | 3 | 0.26 | 1.72 |
| B_on - A_on | tabular | pilot_is | π_sms | 3 | -19.11 | 22.92 |
| B_on - A_on | tabular | pilot_is | π_stage | 3 | 4.31 | 8.97 |
| B_on - A_on | tabular | snips | π_visit | 3 | 5.25 | 3.79 |
| B_on - A_on | tabular | snips | π_sms | 3 | -6.94 | 2.63 |
| B_on - A_on | tabular | snips | π_stage | 3 | 7.04 | 5.27 |
