# Policy-reward diagnostic under simulator model 2.1.0 (full settlement)

Exploratory; worlds A_on and B_on, development seeds 9301-9305 (shared by the two worlds), replicate 2, 1,000,000 borrowers, batch 50,000, month-0 explorable cohort, window months 0-8. US$ per decision.

* **score** (synthetic evaluation score, unchanged definition): 1{first recovery in months 0-8} x B0 x (1 - d0).
* **cash** (model 2.1.0): the settlement paid at the first recovery, round(B_t x (1 - d_t), 2) on the balance just before the payment; the loan then closes. Not net profit: no channel costs, no time discounting.
* Per world: mean over the 5 seeds, 95% t interval over seeds (4 df), RMS Monte-Carlo SE per seed; a pair is resolved in a seed if |gap| > 1.96 paired SE.

## Score: identical to the model-2.0.0 records

| world | seed | generator_old | generator_new | summary_identical | first_recovery_descriptives_equal | first_recovery_discount_identical | validation_ok_new |
|---|---|---|---|---|---|---|---|
| A_on | 9301 | 2.0.0 | 2.1.0 | True | True | True | True |
| A_on | 9302 | 2.0.0 | 2.1.0 | True | True | True | True |
| A_on | 9303 | 2.0.0 | 2.1.0 | True | True | True | True |
| A_on | 9304 | 2.0.0 | 2.1.0 | True | True | True | True |
| A_on | 9305 | 2.0.0 | 2.1.0 | True | True | True | True |
| B_on | 9301 | 2.0.0 | 2.1.0 | True | True | True | True |
| B_on | 9302 | 2.0.0 | 2.1.0 | True | True | True | True |
| B_on | 9303 | 2.0.0 | 2.1.0 | True | True | True | True |
| B_on | 9304 | 2.0.0 | 2.1.0 | True | True | True | True |
| B_on | 9305 | 2.0.0 | 2.1.0 | True | True | True | True |

## Values (model 2.1.0)

| world | objective | candidate | mean | ci95_low | ci95_high | mc_se_rms | rank_counts |
|---|---|---|---|---|---|---|---|
| A_on | score | pi_b | 276.42 | 262.75 | 290.08 | 2.73 | {"3": 5} |
| A_on | score | pi_near | 289.11 | 274.83 | 303.39 | 2.83 | {"2": 5} |
| A_on | score | pi_far | 260.51 | 247.58 | 273.43 | 2.45 | {"4": 5} |
| A_on | score | pi_stage | 301.40 | 286.60 | 316.20 | 2.97 | {"1": 5} |
| A_on | cash | pi_b | 199.56 | 189.98 | 209.14 | 2.01 | {"4": 5} |
| A_on | cash | pi_near | 200.45 | 191.09 | 209.81 | 2.03 | {"3": 5} |
| A_on | cash | pi_far | 216.59 | 206.22 | 226.95 | 2.09 | {"1": 5} |
| A_on | cash | pi_stage | 200.76 | 191.39 | 210.13 | 2.03 | {"2": 5} |
| B_on | score | pi_b | 275.36 | 260.97 | 289.74 | 2.73 | {"3": 5} |
| B_on | score | pi_near | 290.82 | 276.06 | 305.58 | 2.84 | {"2": 5} |
| B_on | score | pi_far | 255.59 | 242.50 | 268.68 | 2.43 | {"4": 5} |
| B_on | score | pi_stage | 305.49 | 289.78 | 321.19 | 2.99 | {"1": 5} |
| B_on | cash | pi_b | 199.41 | 189.41 | 209.42 | 2.01 | {"4": 5} |
| B_on | cash | pi_near | 203.03 | 193.42 | 212.63 | 2.05 | {"3": 5} |
| B_on | cash | pi_far | 212.11 | 201.77 | 222.45 | 2.07 | {"1": 5} |
| B_on | cash | pi_stage | 205.93 | 195.83 | 216.03 | 2.08 | {"2": 5} |

## Gaps (model 2.1.0)

| world | objective | gap | mean | ci95_low | ci95_high | mc_se_rms | seeds_resolved | seeds_positive |
|---|---|---|---|---|---|---|---|---|
| A_on | score | pi_near - pi_b | +12.69 | +11.71 | +13.67 | 0.71 | 5 | 5 |
| A_on | score | pi_far - pi_b | -15.91 | -17.23 | -14.59 | 0.87 | 5 | 0 |
| A_on | score | pi_stage - pi_b | +24.98 | +23.50 | +26.46 | 0.82 | 5 | 5 |
| A_on | score | pi_far - pi_near | -28.60 | -30.05 | -27.16 | 0.85 | 5 | 0 |
| A_on | score | pi_stage - pi_near | +12.29 | +11.68 | +12.89 | 0.63 | 5 | 5 |
| A_on | score | pi_far - pi_stage | -40.89 | -42.87 | -38.91 | 0.99 | 5 | 0 |
| A_on | cash | pi_near - pi_b | +0.88 | +0.38 | +1.38 | 0.56 | 2 | 5 |
| A_on | cash | pi_far - pi_b | +17.02 | +15.89 | +18.16 | 0.69 | 5 | 5 |
| A_on | cash | pi_stage - pi_b | +1.20 | +0.67 | +1.72 | 0.64 | 2 | 5 |
| A_on | cash | pi_far - pi_near | +16.14 | +15.05 | +17.23 | 0.72 | 5 | 5 |
| A_on | cash | pi_stage - pi_near | +0.31 | +0.06 | +0.57 | 0.52 | 0 | 5 |
| A_on | cash | pi_far - pi_stage | +15.83 | +14.76 | +16.89 | 0.73 | 5 | 5 |
| B_on | score | pi_near - pi_b | +15.46 | +14.63 | +16.30 | 0.71 | 5 | 5 |
| B_on | score | pi_far - pi_b | -19.76 | -21.37 | -18.16 | 0.82 | 5 | 0 |
| B_on | score | pi_stage - pi_b | +30.13 | +28.59 | +31.67 | 0.84 | 5 | 5 |
| B_on | score | pi_far - pi_near | -35.23 | -37.16 | -33.30 | 0.77 | 5 | 0 |
| B_on | score | pi_stage - pi_near | +14.67 | +13.50 | +15.84 | 0.70 | 5 | 5 |
| B_on | score | pi_far - pi_stage | -49.89 | -52.56 | -47.23 | 0.88 | 5 | 0 |
| B_on | cash | pi_near - pi_b | +3.62 | +3.05 | +4.19 | 0.57 | 5 | 5 |
| B_on | cash | pi_far - pi_b | +12.70 | +11.77 | +13.63 | 0.62 | 5 | 5 |
| B_on | cash | pi_stage - pi_b | +6.52 | +5.90 | +7.15 | 0.67 | 5 | 5 |
| B_on | cash | pi_far - pi_near | +9.08 | +7.89 | +10.27 | 0.61 | 5 | 5 |
| B_on | cash | pi_stage - pi_near | +2.90 | +2.05 | +3.76 | 0.61 | 5 | 5 |
| B_on | cash | pi_far - pi_stage | +6.18 | +5.83 | +6.52 | 0.58 | 5 | 5 |

## Rankings per seed (model 2.1.0)

| world | seed | objective | ranking | top_gap | top_gap_se | top_resolved | adjacent_resolved | winner_change_from_score |
|---|---|---|---|---|---|---|---|---|
| A_on | 9301 | score | pi_stage > pi_near > pi_b > pi_far | 12.16 | 0.63 | True | y/y/y |  |
| A_on | 9301 | cash | pi_far > pi_stage > pi_near > pi_b | 16.72 | 0.75 | True | y/n/y | clear |
| A_on | 9302 | score | pi_stage > pi_near > pi_b > pi_far | 11.73 | 0.62 | True | y/y/y |  |
| A_on | 9302 | cash | pi_far > pi_stage > pi_near > pi_b | 15.00 | 0.70 | True | y/n/n | clear |
| A_on | 9303 | score | pi_stage > pi_near > pi_b > pi_far | 12.20 | 0.62 | True | y/y/y |  |
| A_on | 9303 | cash | pi_far > pi_stage > pi_near > pi_b | 15.31 | 0.72 | True | y/n/y | clear |
| A_on | 9304 | score | pi_stage > pi_near > pi_b > pi_far | 13.08 | 0.65 | True | y/y/y |  |
| A_on | 9304 | cash | pi_far > pi_stage > pi_near > pi_b | 16.79 | 0.73 | True | y/n/n | clear |
| A_on | 9305 | score | pi_stage > pi_near > pi_b > pi_far | 12.26 | 0.62 | True | y/y/y |  |
| A_on | 9305 | cash | pi_far > pi_stage > pi_near > pi_b | 15.30 | 0.73 | True | y/n/n | clear |
| B_on | 9301 | score | pi_stage > pi_near > pi_b > pi_far | 15.85 | 0.70 | True | y/y/y |  |
| B_on | 9301 | cash | pi_far > pi_stage > pi_near > pi_b | 6.58 | 0.60 | True | y/y/y | clear |
| B_on | 9302 | score | pi_stage > pi_near > pi_b > pi_far | 14.06 | 0.67 | True | y/y/y |  |
| B_on | 9302 | cash | pi_far > pi_stage > pi_near > pi_b | 5.86 | 0.56 | True | y/y/y | clear |
| B_on | 9303 | score | pi_stage > pi_near > pi_b > pi_far | 14.18 | 0.70 | True | y/y/y |  |
| B_on | 9303 | cash | pi_far > pi_stage > pi_near > pi_b | 6.11 | 0.58 | True | y/y/y | clear |
| B_on | 9304 | score | pi_stage > pi_near > pi_b > pi_far | 15.50 | 0.72 | True | y/y/y |  |
| B_on | 9304 | cash | pi_far > pi_stage > pi_near > pi_b | 6.31 | 0.58 | True | y/y/y | clear |
| B_on | 9305 | score | pi_stage > pi_near > pi_b > pi_far | 13.74 | 0.71 | True | y/y/y |  |
| B_on | 9305 | cash | pi_far > pi_stage > pi_near > pi_b | 6.02 | 0.59 | True | y/y/y | clear |

## Cash by model (2.0.0 values are historical: partial payments, open balances)

| world | candidate | cash_2_1_0_mean | cash_2_0_0_historical_mean | difference_mean |
|---|---|---|---|---|
| A_on | pi_b | 199.56 | 187.56 | +12.00 |
| A_on | pi_near | 200.45 | 188.28 | +12.16 |
| A_on | pi_far | 216.59 | 203.81 | +12.78 |
| A_on | pi_stage | 200.76 | 188.57 | +12.19 |
| B_on | pi_b | 199.41 | 187.33 | +12.08 |
| B_on | pi_near | 203.03 | 190.63 | +12.40 |
| B_on | pi_far | 212.11 | 199.49 | +12.61 |
| B_on | pi_stage | 205.93 | 193.31 | +12.63 |
