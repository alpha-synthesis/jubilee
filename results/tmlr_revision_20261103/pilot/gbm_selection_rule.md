# Gradient-boosting configuration rule — fixed before the development check ran

Recorded: 2026-11-03T19:56:12-03:00. Candidates (scripts/tmlr_evidence/gbm_dev_check.py):
"default" (learning rate 0.1, 200 iterations, 31 leaves, min 200 rows per leaf) and
"regularized" (0.05, 300, 15, 1000); both l2 = 1.0, clip 0.001, two folds.

Criterion (reference-free; uses the development logs only): on the coupling-off
control logs (A_off, seed 9001), where the true behaviour propensity depends on
observed covariates only, take for each configuration the largest deviation of the
mean IS weight from 1 over the three targets. Choose the configuration with the
smaller deviation. If the two deviations differ by less than 0.01, choose
"default" (cheaper). The out-of-fold reward R², calibration by decile and fit time
are reported for both, and on the A_on and B_on logs, but do not enter the choice.
No reference value or estimator error is read for this decision.
