# Score equivalence of simulator models 2.0.0 and 2.1.0: per-unit results

Grid `settlement_score_equivalence_grid_20261104`: 100,000 borrowers in batches of 50,000; worlds A_on, A_off, B_on, B_off; seeds [7001, 9301]; ε [0.08, 0.0]. Each (unit, model) ran in its own process from one source tree; every check is an exact comparison (no tolerance).

**3944 of 3944 checks equal in 24 units; all units equal: True.**

## Units

| unit | kind | world | seed | ε | checks | equal | loans |
|---|---|---|---|---|---|---|---|
| cohort_A_on_s7001_eps0.08 | cohort | A_on | 7001 | 0.08 | 241 | 241 | 100,000 |
| cohort_A_on_s7001_eps0.0 | cohort | A_on | 7001 | 0.0 | 241 | 241 | 100,000 |
| cohort_A_on_s9301_eps0.08 | cohort | A_on | 9301 | 0.08 | 241 | 241 | 100,000 |
| cohort_A_on_s9301_eps0.0 | cohort | A_on | 9301 | 0.0 | 241 | 241 | 100,000 |
| database_A_on_s9301_pi_b | database | A_on | 9301 | 0.08 | 11 | 11 | 100,000 |
| database_A_on_s9301_pi_stage | database | A_on | 9301 | 0.08 | 11 | 11 | 100,000 |
| cohort_A_off_s7001_eps0.08 | cohort | A_off | 7001 | 0.08 | 241 | 241 | 100,000 |
| cohort_A_off_s7001_eps0.0 | cohort | A_off | 7001 | 0.0 | 241 | 241 | 100,000 |
| cohort_A_off_s9301_eps0.08 | cohort | A_off | 9301 | 0.08 | 241 | 241 | 100,000 |
| cohort_A_off_s9301_eps0.0 | cohort | A_off | 9301 | 0.0 | 241 | 241 | 100,000 |
| database_A_off_s9301_pi_b | database | A_off | 9301 | 0.08 | 11 | 11 | 100,000 |
| database_A_off_s9301_pi_stage | database | A_off | 9301 | 0.08 | 11 | 11 | 100,000 |
| cohort_B_on_s7001_eps0.08 | cohort | B_on | 7001 | 0.08 | 241 | 241 | 100,000 |
| cohort_B_on_s7001_eps0.0 | cohort | B_on | 7001 | 0.0 | 241 | 241 | 100,000 |
| cohort_B_on_s9301_eps0.08 | cohort | B_on | 9301 | 0.08 | 241 | 241 | 100,000 |
| cohort_B_on_s9301_eps0.0 | cohort | B_on | 9301 | 0.0 | 241 | 241 | 100,000 |
| database_B_on_s9301_pi_b | database | B_on | 9301 | 0.08 | 11 | 11 | 100,000 |
| database_B_on_s9301_pi_stage | database | B_on | 9301 | 0.08 | 11 | 11 | 100,000 |
| cohort_B_off_s7001_eps0.08 | cohort | B_off | 7001 | 0.08 | 241 | 241 | 100,000 |
| cohort_B_off_s7001_eps0.0 | cohort | B_off | 7001 | 0.0 | 241 | 241 | 100,000 |
| cohort_B_off_s9301_eps0.08 | cohort | B_off | 9301 | 0.08 | 241 | 241 | 100,000 |
| cohort_B_off_s9301_eps0.0 | cohort | B_off | 9301 | 0.0 | 241 | 241 | 100,000 |
| database_B_off_s9301_pi_b | database | B_off | 9301 | 0.08 | 11 | 11 | 100,000 |
| database_B_off_s9301_pi_stage | database | B_off | 9301 | 0.08 | 11 | 11 | 100,000 |

## Checks of one cohort unit (`cohort_A_on_s7001_eps0.08`)

| check | scope | compared | equal |
|---|---|---|---|
| population.borrowers | per row, 10 columns | 100,000 | True |
| population.hidden | per row, 5 columns | 100,000 | True |
| population.loans | per row, 13 columns | 100,000 | True |
| population.regional_shocks | per region | 1 | True |
| draws.sha256_per_batch_and_array | every (loan, month) draw of replicate 0, per batch | 1 | True |
| config_effective_sha256 | effective config | 1 | True |
| trajectory.first_recovery_month | per loan | 100,000 | True |
| trajectory.channel0 | per loan | 100,000 | True |
| trajectory.discount0 | per loan | 100,000 | True |
| trajectory.is_exploration0 | per loan | 100,000 | True |
| trajectory.eps0 | per loan | 100,000 | True |
| trajectory.alive (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.status (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.channel (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.discount (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.settlement (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.is_exploration (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.explore_prob (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.loan_age (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.remaining (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.contacts (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.recovered (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.charged_off (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.p_recovery (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.p_chargeoff (months <= first recovery) | per loan-month | 100,000 | True |
| trajectory.dpd_after (months before the first recovery) | per loan-month | 100,000 | True |
| trajectory.liq_after (months before the first recovery) | per loan-month | 100,000 | True |
| trajectory.balance_after (months before the first recovery) | per loan-month | 100,000 | True |
| trajectory.next_status (months before the first recovery) | per loan-month | 100,000 | True |
| trajectory.recovered_amount (months before the first recovery) | per loan-month | 100,000 | True |
| trajectory.alive (loans without a recovery: the whole window) | per loan-month | 100,000 | True |
| trajectory.first_chargeoff_before_recovery | per loan | 100,000 | True |
| logs.cohort (every column, incl. covariates and hidden_*) | per row, 28 columns | 74,439 | True |
| logs.build_logs.terciles | per loan | 2 | True |
| logs.build_logs.context | per loan | 74,439 | True |
| logs.build_logs.action | per loan | 74,439 | True |
| logs.build_logs.propensity | per loan | 74,439 | True |
| logs.build_logs.reward | per loan | 74,439 | True |
| logs.build_logs.explored | per loan | 74,439 | True |
| logs.build_logs.eps | per loan | 74,439 | True |
| logs.design_matrix | per loan | 74,439 | True |
| logs.meta (version keys excluded) | recovery_12m, n_cohort, batches | 1 | True |
| logs.stats | n_cohort, explore_share, logged_mean_reward, paid_rate_h | 1 | True |
| logs.exploration_epsilon equals the unit's epsilon on every cohort row | per loan (new model) | 74,439 | True |
| annotator.table | per row, 6 columns | 74,324 | True |
| annotator.pi_near.loan_id | per loan | 74,324 | True |
| annotator.pi_near.start_balance | per loan | 74,324 | True |
| annotator.pi_near.state | per loan | 74,324 | True |
| annotator.pi_near.dpd | per loan | 74,324 | True |
| annotator.pi_near.liq_days | per loan | 74,324 | True |
| annotator.pi_near.channel_logged | per loan | 74,324 | True |
| annotator.pi_near.discount_logged | per loan | 74,324 | True |
| annotator.pi_near.is_exploration | per loan | 74,324 | True |
| annotator.pi_near.exploration_epsilon | per loan | 74,324 | True |
| annotator.pi_near.paid_within_h | per loan | 74,324 | True |
| annotator.pi_near.first_recovery_month | per loan | 74,324 | True |
| annotator.pi_near.reward | per loan | 74,324 | True |
| annotator.pi_near.truth_matrix | per context x action cell | 36 | True |
| annotator.pi_far.loan_id | per loan | 74,324 | True |
| annotator.pi_far.start_balance | per loan | 74,324 | True |
| annotator.pi_far.state | per loan | 74,324 | True |
| annotator.pi_far.dpd | per loan | 74,324 | True |
| annotator.pi_far.liq_days | per loan | 74,324 | True |
| annotator.pi_far.channel_logged | per loan | 74,324 | True |
| annotator.pi_far.discount_logged | per loan | 74,324 | True |
| annotator.pi_far.is_exploration | per loan | 74,324 | True |
| annotator.pi_far.exploration_epsilon | per loan | 74,324 | True |
| annotator.pi_far.paid_within_h | per loan | 74,324 | True |
| annotator.pi_far.first_recovery_month | per loan | 74,324 | True |
| annotator.pi_far.reward | per loan | 74,324 | True |
| annotator.pi_far.truth_matrix | per context x action cell | 36 | True |
| annotator.pi_stage.loan_id | per loan | 74,324 | True |
| annotator.pi_stage.start_balance | per loan | 74,324 | True |
| annotator.pi_stage.state | per loan | 74,324 | True |
| annotator.pi_stage.dpd | per loan | 74,324 | True |
| annotator.pi_stage.liq_days | per loan | 74,324 | True |
| annotator.pi_stage.channel_logged | per loan | 74,324 | True |
| annotator.pi_stage.discount_logged | per loan | 74,324 | True |
| annotator.pi_stage.is_exploration | per loan | 74,324 | True |
| annotator.pi_stage.exploration_epsilon | per loan | 74,324 | True |
| annotator.pi_stage.paid_within_h | per loan | 74,324 | True |
| annotator.pi_stage.first_recovery_month | per loan | 74,324 | True |
| annotator.pi_stage.reward | per loan | 74,324 | True |
| annotator.pi_stage.truth_matrix | per context x action cell | 36 | True |
| reference.r2_h9.pi_b.loan_id | per loan | 74,332 | True |
| reference.r2_h9.pi_b.start_balance | per loan | 74,332 | True |
| reference.r2_h9.pi_b.state | per loan | 74,332 | True |
| reference.r2_h9.pi_b.dpd | per loan | 74,332 | True |
| reference.r2_h9.pi_b.liq_days | per loan | 74,332 | True |
| reference.r2_h9.pi_b.channel_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_b.discount_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_b.is_exploration | per loan | 74,332 | True |
| reference.r2_h9.pi_b.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h9.pi_b.paid_within_h | per loan | 74,332 | True |
| reference.r2_h9.pi_b.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h9.pi_b.reward | per loan | 74,332 | True |
| reference.r2_h9.pi_near.loan_id | per loan | 74,332 | True |
| reference.r2_h9.pi_near.start_balance | per loan | 74,332 | True |
| reference.r2_h9.pi_near.state | per loan | 74,332 | True |
| reference.r2_h9.pi_near.dpd | per loan | 74,332 | True |
| reference.r2_h9.pi_near.liq_days | per loan | 74,332 | True |
| reference.r2_h9.pi_near.channel_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_near.discount_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_near.is_exploration | per loan | 74,332 | True |
| reference.r2_h9.pi_near.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h9.pi_near.paid_within_h | per loan | 74,332 | True |
| reference.r2_h9.pi_near.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h9.pi_near.reward | per loan | 74,332 | True |
| reference.r2_h9.pi_far.loan_id | per loan | 74,332 | True |
| reference.r2_h9.pi_far.start_balance | per loan | 74,332 | True |
| reference.r2_h9.pi_far.state | per loan | 74,332 | True |
| reference.r2_h9.pi_far.dpd | per loan | 74,332 | True |
| reference.r2_h9.pi_far.liq_days | per loan | 74,332 | True |
| reference.r2_h9.pi_far.channel_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_far.discount_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_far.is_exploration | per loan | 74,332 | True |
| reference.r2_h9.pi_far.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h9.pi_far.paid_within_h | per loan | 74,332 | True |
| reference.r2_h9.pi_far.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h9.pi_far.reward | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.loan_id | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.start_balance | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.state | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.dpd | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.liq_days | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.channel_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.discount_logged | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.is_exploration | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.paid_within_h | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h9.pi_stage.reward | per loan | 74,332 | True |
| reference.r2_h9.means | per candidate | 1 | True |
| reference.r2_h9.cov | per candidate pair | 1 | True |
| reference.r2_h9.paid_rates | per candidate | 1 | True |
| reference.r2_h9.meta (version keys excluded) | simulate_cohort meta | 1 | True |
| reference.r3_h9.pi_b.loan_id | per loan | 74,387 | True |
| reference.r3_h9.pi_b.start_balance | per loan | 74,387 | True |
| reference.r3_h9.pi_b.state | per loan | 74,387 | True |
| reference.r3_h9.pi_b.dpd | per loan | 74,387 | True |
| reference.r3_h9.pi_b.liq_days | per loan | 74,387 | True |
| reference.r3_h9.pi_b.channel_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_b.discount_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_b.is_exploration | per loan | 74,387 | True |
| reference.r3_h9.pi_b.exploration_epsilon | per loan | 74,387 | True |
| reference.r3_h9.pi_b.paid_within_h | per loan | 74,387 | True |
| reference.r3_h9.pi_b.first_recovery_month | per loan | 74,387 | True |
| reference.r3_h9.pi_b.reward | per loan | 74,387 | True |
| reference.r3_h9.pi_near.loan_id | per loan | 74,387 | True |
| reference.r3_h9.pi_near.start_balance | per loan | 74,387 | True |
| reference.r3_h9.pi_near.state | per loan | 74,387 | True |
| reference.r3_h9.pi_near.dpd | per loan | 74,387 | True |
| reference.r3_h9.pi_near.liq_days | per loan | 74,387 | True |
| reference.r3_h9.pi_near.channel_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_near.discount_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_near.is_exploration | per loan | 74,387 | True |
| reference.r3_h9.pi_near.exploration_epsilon | per loan | 74,387 | True |
| reference.r3_h9.pi_near.paid_within_h | per loan | 74,387 | True |
| reference.r3_h9.pi_near.first_recovery_month | per loan | 74,387 | True |
| reference.r3_h9.pi_near.reward | per loan | 74,387 | True |
| reference.r3_h9.pi_far.loan_id | per loan | 74,387 | True |
| reference.r3_h9.pi_far.start_balance | per loan | 74,387 | True |
| reference.r3_h9.pi_far.state | per loan | 74,387 | True |
| reference.r3_h9.pi_far.dpd | per loan | 74,387 | True |
| reference.r3_h9.pi_far.liq_days | per loan | 74,387 | True |
| reference.r3_h9.pi_far.channel_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_far.discount_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_far.is_exploration | per loan | 74,387 | True |
| reference.r3_h9.pi_far.exploration_epsilon | per loan | 74,387 | True |
| reference.r3_h9.pi_far.paid_within_h | per loan | 74,387 | True |
| reference.r3_h9.pi_far.first_recovery_month | per loan | 74,387 | True |
| reference.r3_h9.pi_far.reward | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.loan_id | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.start_balance | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.state | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.dpd | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.liq_days | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.channel_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.discount_logged | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.is_exploration | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.exploration_epsilon | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.paid_within_h | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.first_recovery_month | per loan | 74,387 | True |
| reference.r3_h9.pi_stage.reward | per loan | 74,387 | True |
| reference.r3_h9.means | per candidate | 1 | True |
| reference.r3_h9.cov | per candidate pair | 1 | True |
| reference.r3_h9.paid_rates | per candidate | 1 | True |
| reference.r3_h9.meta (version keys excluded) | simulate_cohort meta | 1 | True |
| reference.r2_h12.pi_b.loan_id | per loan | 74,332 | True |
| reference.r2_h12.pi_b.start_balance | per loan | 74,332 | True |
| reference.r2_h12.pi_b.state | per loan | 74,332 | True |
| reference.r2_h12.pi_b.dpd | per loan | 74,332 | True |
| reference.r2_h12.pi_b.liq_days | per loan | 74,332 | True |
| reference.r2_h12.pi_b.channel_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_b.discount_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_b.is_exploration | per loan | 74,332 | True |
| reference.r2_h12.pi_b.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h12.pi_b.paid_within_h | per loan | 74,332 | True |
| reference.r2_h12.pi_b.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h12.pi_b.reward | per loan | 74,332 | True |
| reference.r2_h12.pi_near.loan_id | per loan | 74,332 | True |
| reference.r2_h12.pi_near.start_balance | per loan | 74,332 | True |
| reference.r2_h12.pi_near.state | per loan | 74,332 | True |
| reference.r2_h12.pi_near.dpd | per loan | 74,332 | True |
| reference.r2_h12.pi_near.liq_days | per loan | 74,332 | True |
| reference.r2_h12.pi_near.channel_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_near.discount_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_near.is_exploration | per loan | 74,332 | True |
| reference.r2_h12.pi_near.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h12.pi_near.paid_within_h | per loan | 74,332 | True |
| reference.r2_h12.pi_near.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h12.pi_near.reward | per loan | 74,332 | True |
| reference.r2_h12.pi_far.loan_id | per loan | 74,332 | True |
| reference.r2_h12.pi_far.start_balance | per loan | 74,332 | True |
| reference.r2_h12.pi_far.state | per loan | 74,332 | True |
| reference.r2_h12.pi_far.dpd | per loan | 74,332 | True |
| reference.r2_h12.pi_far.liq_days | per loan | 74,332 | True |
| reference.r2_h12.pi_far.channel_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_far.discount_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_far.is_exploration | per loan | 74,332 | True |
| reference.r2_h12.pi_far.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h12.pi_far.paid_within_h | per loan | 74,332 | True |
| reference.r2_h12.pi_far.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h12.pi_far.reward | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.loan_id | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.start_balance | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.state | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.dpd | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.liq_days | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.channel_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.discount_logged | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.is_exploration | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.exploration_epsilon | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.paid_within_h | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.first_recovery_month | per loan | 74,332 | True |
| reference.r2_h12.pi_stage.reward | per loan | 74,332 | True |
| reference.r2_h12.means | per candidate | 1 | True |
| reference.r2_h12.cov | per candidate pair | 1 | True |
| reference.r2_h12.paid_rates | per candidate | 1 | True |
| reference.r2_h12.meta (version keys excluded) | simulate_cohort meta | 1 | True |
| pairing: one population per role and replicate (loan ids and start balances) | per role-replicate (new model) | 4 | True |

## Checks of one database unit (`database_A_on_s9301_pi_b`)

| check | scope | compared | equal |
|---|---|---|---|
| db.borrowers | per row, 10 columns | 100,000 | True |
| db.loans | per row, 13 columns | 100,000 | True |
| db.monthly_panel up to each loan's last 2.1.0 row (action_id and the recovery row's next_status, balance, amount excluded) | per row, 11 columns | 1,837,354 | True |
| db.monthly_panel next_status, balance and amount before the first recovery | per row, 3 columns | 1,831,774 | True |
| db.actions up to each loan's last 2.1.0 row (action_id excluded) | per row, 7 columns | 1,837,354 | True |
| db.oracle_truth up to each loan's last 2.1.0 row | per row, 12 columns | 1,837,354 | True |
| db.validate_database (2.1.0 validator on the 2.1.0 database) | database | 1 | True |
| db.load_cohort (score extraction from the database) | per row, 11 columns | 100,000 | True |
| simulate_cohort (all loans, 9-month window) | per row, 12 columns | 100,000 | True |
| old model: load_cohort equals simulate_cohort per loan | per row, 11 columns | 100,000 | True |
| new model: load_cohort equals simulate_cohort per loan | per row, 11 columns | 100,000 | True |

## What the correction changes (expected differences, summed over units)

* **cohort units**: loans: 1600000; loans_recovering_in_window: 67176; old_first_recovery_not_cured: 65304; old_balance_left_after_first_recovery: 66258; old_paid_less_than_offer: 38921; new_paid_equals_offer: True; new_balance_after_zero: True; new_cured: True; new_rows_after_first_recovery: 0; old_rows_after_first_recovery: 377536; old_loans_with_rows_after_first_recovery: 61463; old_recoveries_after_the_first: 2551; cash_months_0_8: {'old': 332480996.39000005, 'new': 354602465.82000005}; cash_months_0_11: {'old': 396267989.04, 'new': 420027582.20000005}
* **database units**: loans: 800000; loans_recovering: 42859; old_rows_after_the_new_last_row: 590568; old_loans_with_such_rows: 41468; rows: {'old': 15298712, 'new': 14708144}; month0_action_ids_renumbered: 799904; cash_months_0_8: {'old': 158648813.78, 'new': 169222738.01}; validate_database: {'old (2.0.0 validator)': True, 'new (2.1.0 validator)': True}

## Eligibility does not depend on ε

| world | seed | cohort loan ids equal | cohort states equal | cohorts |
|---|---|---|---|---|
| A_on | 7001 | True | True | 7 |
| A_on | 9301 | True | True | 7 |
| A_off | 7001 | True | True | 7 |
| A_off | 9301 | True | True | 7 |
| B_on | 7001 | True | True | 7 |
| B_on | 9301 | True | True | 7 |
| B_off | 7001 | True | True | 7 |
| B_off | 9301 | True | True | 7 |

## Provenance

* model 2.0.0 side: roots ['<repo>/outputs/settlement_score_equivalence_20261104/baseline/tree'], generator ['2.0.0']
* model 2.1.0 side: roots ['<repo>'], generator ['2.1.0']

| module | 2.0.0 sha256 | 2.1.0 sha256 | same |
|---|---|---|---|
| collection_simulator | f287036d97a1496e | f287036d97a1496e | True |
| collection_simulator.config | 03ee521333ce2f63 | 03ee521333ce2f63 | True |
| collection_simulator.dictionaries | 2815ada140ba78db | 2815ada140ba78db | True |
| collection_simulator.generator | ea74e30129ace91e | 552215c54711ad9d | False |
| collection_simulator.storage | 6374142ece9bb606 | 6374142ece9bb606 | True |
| collection_simulator.validation | 0bf49b68e6f4c7e9 | f82537cc43251ae6 | False |
| ope_bench | 28b6b777848f360b | 28b6b777848f360b | True |
| ope_bench.annotator | da3873e25ad88887 | da3873e25ad88887 | True |
| ope_bench.bandit | 707bd37fe16a3fe8 | 707bd37fe16a3fe8 | True |
| ope_bench.confidence | 79109f5c94f84f9e | 79109f5c94f84f9e | True |
| ope_bench.estimators | 2aa104c54a1025fe | 2aa104c54a1025fe | True |
| ope_bench.logging_policy | 6d93cf2c5c15db34 | 6d93cf2c5c15db34 | True |
| ope_bench.nontabular | 74b0464b8d27c557 | 74b0464b8d27c557 | True |
| ope_bench.panel | 3989e009c56641ba | 3989e009c56641ba | True |
| ope_bench.value_export | 812d8463cb4056c6 | 812d8463cb4056c6 | True |
| tmlr_campaign | 801dccb2f5d5ed7a | 801dccb2f5d5ed7a | True |

CPU time of all dumps: 2.61 hours.
