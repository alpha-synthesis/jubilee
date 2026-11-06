# Candidate values, gaps and rankings under three rewards (exploratory diagnostic)

US$ per decision on the month-0 explorable cohort. Per world: mean over the 5 development seeds, 95% t interval over seeds (4 df), root-mean-square Monte-Carlo SE per seed. A pair is resolved in a seed if |gap| > 1.96 SE. Worlds share seeds.

## Values

| world | objective | candidate | mean | ci95_low | ci95_high | sd_between_seeds | mc_se_rms | rank_counts |
|---|---|---|---|---|---|---|---|---|
| A_on | benchmark | pi_b | 276.42 | 262.75 | 290.08 | 11.01 | 2.73 | {"3": 5} |
| A_on | benchmark | pi_far | 260.51 | 247.58 | 273.43 | 10.41 | 2.45 | {"4": 5} |
| A_on | benchmark | pi_near | 289.11 | 274.83 | 303.39 | 11.50 | 2.83 | {"2": 5} |
| A_on | benchmark | pi_stage | 301.40 | 286.60 | 316.20 | 11.92 | 2.97 | {"1": 5} |
| A_on | cash | pi_b | 199.56 | 189.98 | 209.14 | 7.72 | 2.01 | {"4": 5} |
| A_on | cash | pi_far | 216.59 | 206.22 | 226.95 | 8.34 | 2.09 | {"1": 5} |
| A_on | cash | pi_near | 200.45 | 191.09 | 209.81 | 7.54 | 2.03 | {"3": 5} |
| A_on | cash | pi_stage | 200.76 | 191.39 | 210.13 | 7.54 | 2.03 | {"2": 5} |
| A_on | first_recovery_discount | pi_b | 193.02 | 183.74 | 202.30 | 7.47 | 1.95 | {"4": 5} |
| A_on | first_recovery_discount | pi_far | 210.09 | 200.02 | 220.15 | 8.11 | 2.03 | {"1": 5} |
| A_on | first_recovery_discount | pi_near | 193.91 | 184.85 | 202.97 | 7.30 | 1.97 | {"3": 5} |
| A_on | first_recovery_discount | pi_stage | 194.22 | 185.15 | 203.29 | 7.30 | 1.98 | {"2": 5} |
| B_on | benchmark | pi_b | 275.36 | 260.97 | 289.74 | 11.59 | 2.73 | {"3": 5} |
| B_on | benchmark | pi_far | 255.59 | 242.50 | 268.68 | 10.54 | 2.43 | {"4": 5} |
| B_on | benchmark | pi_near | 290.82 | 276.06 | 305.58 | 11.88 | 2.84 | {"2": 5} |
| B_on | benchmark | pi_stage | 305.49 | 289.78 | 321.19 | 12.65 | 2.99 | {"1": 5} |
| B_on | cash | pi_b | 199.41 | 189.41 | 209.42 | 8.06 | 2.01 | {"4": 5} |
| B_on | cash | pi_far | 212.11 | 201.77 | 222.45 | 8.33 | 2.07 | {"1": 5} |
| B_on | cash | pi_near | 203.03 | 193.42 | 212.63 | 7.74 | 2.05 | {"3": 5} |
| B_on | cash | pi_stage | 205.93 | 195.83 | 216.03 | 8.13 | 2.08 | {"2": 5} |
| B_on | first_recovery_discount | pi_b | 192.92 | 183.23 | 202.61 | 7.80 | 1.96 | {"4": 5} |
| B_on | first_recovery_discount | pi_far | 205.65 | 195.62 | 215.68 | 8.08 | 2.01 | {"1": 5} |
| B_on | first_recovery_discount | pi_near | 196.54 | 187.25 | 205.83 | 7.48 | 2.00 | {"3": 5} |
| B_on | first_recovery_discount | pi_stage | 199.45 | 189.66 | 209.24 | 7.88 | 2.02 | {"2": 5} |

## Gaps (first minus second candidate)

| world | objective | pair | mean | ci95_low | ci95_high | sd_between_seeds | mc_se_rms | seeds_resolved | seeds_positive |
|---|---|---|---|---|---|---|---|---|---|
| A_on | benchmark | pi_b-pi_far | +15.91 | +14.59 | +17.23 | 1.06 | 0.87 | 5 | 5 |
| A_on | benchmark | pi_b-pi_near | -12.69 | -13.67 | -11.71 | 0.79 | 0.71 | 5 | 0 |
| A_on | benchmark | pi_b-pi_stage | -24.98 | -26.46 | -23.50 | 1.19 | 0.82 | 5 | 0 |
| A_on | benchmark | pi_far-pi_stage | -40.89 | -42.87 | -38.91 | 1.59 | 0.99 | 5 | 0 |
| A_on | benchmark | pi_near-pi_far | +28.60 | +27.16 | +30.05 | 1.16 | 0.85 | 5 | 5 |
| A_on | benchmark | pi_near-pi_stage | -12.29 | -12.89 | -11.68 | 0.49 | 0.63 | 5 | 0 |
| A_on | cash | pi_b-pi_far | -17.02 | -18.16 | -15.89 | 0.91 | 0.69 | 5 | 0 |
| A_on | cash | pi_b-pi_near | -0.88 | -1.38 | -0.38 | 0.40 | 0.56 | 2 | 0 |
| A_on | cash | pi_b-pi_stage | -1.20 | -1.72 | -0.67 | 0.42 | 0.64 | 2 | 0 |
| A_on | cash | pi_far-pi_stage | +15.83 | +14.76 | +16.89 | 0.86 | 0.73 | 5 | 5 |
| A_on | cash | pi_near-pi_far | -16.14 | -17.23 | -15.05 | 0.88 | 0.72 | 5 | 0 |
| A_on | cash | pi_near-pi_stage | -0.31 | -0.57 | -0.06 | 0.21 | 0.52 | 0 | 0 |
| A_on | first_recovery_discount | pi_b-pi_far | -17.07 | -18.20 | -15.93 | 0.92 | 0.69 | 5 | 0 |
| A_on | first_recovery_discount | pi_b-pi_near | -0.89 | -1.38 | -0.39 | 0.40 | 0.57 | 2 | 0 |
| A_on | first_recovery_discount | pi_b-pi_stage | -1.20 | -1.72 | -0.67 | 0.42 | 0.64 | 2 | 0 |
| A_on | first_recovery_discount | pi_far-pi_stage | +15.87 | +14.80 | +16.94 | 0.86 | 0.73 | 5 | 5 |
| A_on | first_recovery_discount | pi_near-pi_far | -16.18 | -17.28 | -15.09 | 0.88 | 0.72 | 5 | 0 |
| A_on | first_recovery_discount | pi_near-pi_stage | -0.31 | -0.57 | -0.05 | 0.21 | 0.52 | 0 | 0 |
| B_on | benchmark | pi_b-pi_far | +19.76 | +18.16 | +21.37 | 1.29 | 0.82 | 5 | 5 |
| B_on | benchmark | pi_b-pi_near | -15.46 | -16.30 | -14.63 | 0.67 | 0.71 | 5 | 0 |
| B_on | benchmark | pi_b-pi_stage | -30.13 | -31.67 | -28.59 | 1.24 | 0.84 | 5 | 0 |
| B_on | benchmark | pi_far-pi_stage | -49.89 | -52.56 | -47.23 | 2.15 | 0.88 | 5 | 0 |
| B_on | benchmark | pi_near-pi_far | +35.23 | +33.30 | +37.16 | 1.56 | 0.77 | 5 | 5 |
| B_on | benchmark | pi_near-pi_stage | -14.67 | -15.84 | -13.50 | 0.94 | 0.70 | 5 | 0 |
| B_on | cash | pi_b-pi_far | -12.70 | -13.63 | -11.77 | 0.75 | 0.62 | 5 | 0 |
| B_on | cash | pi_b-pi_near | -3.62 | -4.19 | -3.05 | 0.46 | 0.57 | 5 | 0 |
| B_on | cash | pi_b-pi_stage | -6.52 | -7.15 | -5.90 | 0.50 | 0.67 | 5 | 0 |
| B_on | cash | pi_far-pi_stage | +6.18 | +5.83 | +6.52 | 0.28 | 0.58 | 5 | 5 |
| B_on | cash | pi_near-pi_far | -9.08 | -10.27 | -7.89 | 0.96 | 0.61 | 5 | 0 |
| B_on | cash | pi_near-pi_stage | -2.90 | -3.76 | -2.05 | 0.69 | 0.61 | 5 | 0 |
| B_on | first_recovery_discount | pi_b-pi_far | -12.73 | -13.66 | -11.80 | 0.75 | 0.62 | 5 | 0 |
| B_on | first_recovery_discount | pi_b-pi_near | -3.62 | -4.19 | -3.06 | 0.46 | 0.57 | 5 | 0 |
| B_on | first_recovery_discount | pi_b-pi_stage | -6.53 | -7.16 | -5.91 | 0.50 | 0.67 | 5 | 0 |
| B_on | first_recovery_discount | pi_far-pi_stage | +6.20 | +5.85 | +6.55 | 0.28 | 0.58 | 5 | 5 |
| B_on | first_recovery_discount | pi_near-pi_far | -9.11 | -10.30 | -7.92 | 0.96 | 0.61 | 5 | 0 |
| B_on | first_recovery_discount | pi_near-pi_stage | -2.91 | -3.76 | -2.05 | 0.69 | 0.61 | 5 | 0 |

## Rankings per seed

| world | seed | objective | ranking | top_gap | top_gap_se | top_resolved | adjacent_resolved |
|---|---|---|---|---|---|---|---|
| A_on | 9301 | benchmark | pi_stage > pi_near > pi_b > pi_far | 12.16 | 0.63 | True | y/y/y |
| A_on | 9301 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 16.76 | 0.75 | True | y/n/y |
| A_on | 9301 | cash | pi_far > pi_stage > pi_near > pi_b | 16.72 | 0.75 | True | y/n/y |
| A_on | 9302 | benchmark | pi_stage > pi_near > pi_b > pi_far | 11.73 | 0.62 | True | y/y/y |
| A_on | 9302 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 15.05 | 0.70 | True | y/n/n |
| A_on | 9302 | cash | pi_far > pi_stage > pi_near > pi_b | 15.00 | 0.70 | True | y/n/n |
| A_on | 9303 | benchmark | pi_stage > pi_near > pi_b > pi_far | 12.20 | 0.62 | True | y/y/y |
| A_on | 9303 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 15.36 | 0.72 | True | y/n/y |
| A_on | 9303 | cash | pi_far > pi_stage > pi_near > pi_b | 15.31 | 0.72 | True | y/n/y |
| A_on | 9304 | benchmark | pi_stage > pi_near > pi_b > pi_far | 13.08 | 0.65 | True | y/y/y |
| A_on | 9304 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 16.84 | 0.73 | True | y/n/n |
| A_on | 9304 | cash | pi_far > pi_stage > pi_near > pi_b | 16.79 | 0.73 | True | y/n/n |
| A_on | 9305 | benchmark | pi_stage > pi_near > pi_b > pi_far | 12.26 | 0.62 | True | y/y/y |
| A_on | 9305 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 15.33 | 0.73 | True | y/n/n |
| A_on | 9305 | cash | pi_far > pi_stage > pi_near > pi_b | 15.30 | 0.73 | True | y/n/n |
| B_on | 9301 | benchmark | pi_stage > pi_near > pi_b > pi_far | 15.85 | 0.70 | True | y/y/y |
| B_on | 9301 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 6.60 | 0.60 | True | y/y/y |
| B_on | 9301 | cash | pi_far > pi_stage > pi_near > pi_b | 6.58 | 0.60 | True | y/y/y |
| B_on | 9302 | benchmark | pi_stage > pi_near > pi_b > pi_far | 14.06 | 0.67 | True | y/y/y |
| B_on | 9302 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 5.89 | 0.56 | True | y/y/y |
| B_on | 9302 | cash | pi_far > pi_stage > pi_near > pi_b | 5.86 | 0.56 | True | y/y/y |
| B_on | 9303 | benchmark | pi_stage > pi_near > pi_b > pi_far | 14.18 | 0.70 | True | y/y/y |
| B_on | 9303 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 6.14 | 0.58 | True | y/y/y |
| B_on | 9303 | cash | pi_far > pi_stage > pi_near > pi_b | 6.11 | 0.58 | True | y/y/y |
| B_on | 9304 | benchmark | pi_stage > pi_near > pi_b > pi_far | 15.50 | 0.72 | True | y/y/y |
| B_on | 9304 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 6.34 | 0.58 | True | y/y/y |
| B_on | 9304 | cash | pi_far > pi_stage > pi_near > pi_b | 6.31 | 0.58 | True | y/y/y |
| B_on | 9305 | benchmark | pi_stage > pi_near > pi_b > pi_far | 13.74 | 0.71 | True | y/y/y |
| B_on | 9305 | first_recovery_discount | pi_far > pi_stage > pi_near > pi_b | 6.03 | 0.59 | True | y/y/y |
| B_on | 9305 | cash | pi_far > pi_stage > pi_near > pi_b | 6.02 | 0.59 | True | y/y/y |

## Winner change against the benchmark reward

| world | seed | objective | benchmark_best | objective_best | winner_change |
|---|---|---|---|---|---|
| A_on | 9301 | first_recovery_discount | pi_stage | pi_far | clear |
| A_on | 9301 | cash | pi_stage | pi_far | clear |
| A_on | 9302 | first_recovery_discount | pi_stage | pi_far | clear |
| A_on | 9302 | cash | pi_stage | pi_far | clear |
| A_on | 9303 | first_recovery_discount | pi_stage | pi_far | clear |
| A_on | 9303 | cash | pi_stage | pi_far | clear |
| A_on | 9304 | first_recovery_discount | pi_stage | pi_far | clear |
| A_on | 9304 | cash | pi_stage | pi_far | clear |
| A_on | 9305 | first_recovery_discount | pi_stage | pi_far | clear |
| A_on | 9305 | cash | pi_stage | pi_far | clear |
| B_on | 9301 | first_recovery_discount | pi_stage | pi_far | clear |
| B_on | 9301 | cash | pi_stage | pi_far | clear |
| B_on | 9302 | first_recovery_discount | pi_stage | pi_far | clear |
| B_on | 9302 | cash | pi_stage | pi_far | clear |
| B_on | 9303 | first_recovery_discount | pi_stage | pi_far | clear |
| B_on | 9303 | cash | pi_stage | pi_far | clear |
| B_on | 9304 | first_recovery_discount | pi_stage | pi_far | clear |
| B_on | 9304 | cash | pi_stage | pi_far | clear |
| B_on | 9305 | first_recovery_discount | pi_stage | pi_far | clear |
| B_on | 9305 | cash | pi_stage | pi_far | clear |
