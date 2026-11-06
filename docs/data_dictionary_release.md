# Data dictionary of the released records and extracts

All money amounts are in US$. Two objectives are recorded for every decision.
The score is `1{first recovery in months 0-8} × B0 × (1 − d0)`, where `B0` is
the balance at month 0 and `d0` the discount of the month-0 action. Cash is
the sum of the loan's payments in months 0-8. Under full settlement a recovery
is a single payment of the balance at that month net of the discount offered
in that month. Neither objective includes channel costs. The simulator's full
loan-month tables (and the `oracle_truth` table) are described in
`src/collection_simulator/data_dictionary.md`. The files below are the
reduced records the experiments stored.

## Layout of the extract archives

Paths start with `rerun_20261106/<protocol>/`, where `<protocol>` is
`paired`, `grid20` or `grid5`. Each run lies in
`runs/<condition>/seed<S>/`. Paired-study conditions are `A_off`, `A_on`,
`B_off` and `B_on` with seeds 7001-7020, shared by the four conditions. Grid
conditions are the configuration stems (`cell_02_control_eps08`, ...) with
seeds 101-120 or 101-105.

## Data roles

| role | replicate | file | may be given to an estimator |
|---|---|---|---|
| logged data | 0 | `logs.parquet` (all columns except `hidden_*`) | yes |
| hidden factors of the logged population | 0 | `hidden_*` columns of `logs.parquet` | no (diagnostics only) |
| annotation source | 1 | `annotator.parquet` | only to the annotated estimators, after the protocol's bias (+0.25 × scale) and noise (sd 0.25 × scale) are added |
| policy references | 2, 3, 4 | `reference_r{2,3,4}.json` | no (grading, selection and regret only) |

All replicates of a run share the world's regional shocks and nothing else.

## `logs.parquet` (one row per loan in the month-0 explorable cohort)

| column | type | meaning |
|---|---|---|
| `loan_id` | string | loan identifier within one population (`L000001`, ...). Identifiers restart in every replicate, so equal identifiers in `logs.parquet` and `annotator.parquet` do not denote the same loan |
| `start_balance` | float | balance at month 0, `B0` (US$) |
| `state` | string | month-0 state: `delinquent` or `credito_em_liquidacao` (late-stage delinquency) |
| `dpd` | int | days past due at month 0 |
| `liq_days` | int | days in late-stage delinquency at month 0 (0 otherwise, at most 180 in the cohort) |
| `channel_logged` | string | logged month-0 channel: `none`, `sms`, `app_message`, `phone`, `field_visit` |
| `discount_logged` | float | logged month-0 discount `d0` (fraction of the balance) |
| `is_exploration` | bool | the action came from the randomized exploration component |
| `exploration_epsilon` | float | exploration probability of the logging policy (0.08, or 0 in the grid cells without exploration) |
| `paid_within_h` | int | 1 if the first recovery happened in months 0-8 |
| `first_recovery_month` | int | month of the first recovery within the 12 simulated months, -1 if none |
| `product_type` | string | product category |
| `original_principal` | float | principal at origination (US$) |
| `interest_rate_monthly` | float | contractual monthly interest rate |
| `term_months` | int | contractual term |
| `loan_age_months` | int | months since origination at month 0 |
| `remaining_maturity_months` | int | contractual months remaining at month 0 |
| `uf` | string | region code (`R01` ... `R13`), which identifies the region's macroeconomic shock |
| `age` | int | borrower age in years |
| `gender` | string | borrower gender category |
| `income_band` | string | borrower income band (`B1` ... ) |
| `monthly_income` | float | borrower monthly income (US$) |
| `dependents` | int | number of dependents |
| `hidden_borrower_resilience` | float | hidden factor (standardized), not an estimator input |
| `hidden_payment_friction` | float | hidden factor, not an estimator input |
| `hidden_contactability` | float | hidden factor, not an estimator input |
| `hidden_regional_macro_stress` | float | hidden regional factor, not an estimator input, constant within a region and therefore identified by the observed `uf` |
| `reward` | float | score of the logged decision: `paid_within_h × start_balance × (1 − discount_logged)` |
| `cash_within_h` | float | cash of the logged decision: the loan's payments in months 0-8 (US$), 0 when the loan does not recover in the window |

The tabular estimators group rows into 36 contexts (30-day delinquency step,
capped at 12, × start-balance tercile) and 45 action cells (no contact, plus 4
contact channels × 11 discount bins of width 0.05). The gradient-boosted
estimators read the 15 observable covariates listed in
`docs/revision_campaign.md` (`src/ope_bench/nontabular.py`).

## `annotator.parquet` (replicate 1, one row per loan of its cohort)

| column | type | meaning |
|---|---|---|
| `loan_id` | string | loan identifier within the annotation population |
| `start_balance` | float | balance at month 0 (US$) |
| `dpd` | int | days past due at month 0 |
| `reward_pi_near`, `reward_pi_far`, `reward_pi_stage` | float | score of the loan when the target policy acts at month 0 (SMS at 0.125, field visit at 0.275, or the stage rule) and the incumbent with exploration acts afterwards. The grid has no stage rule |
| `cash_pi_near`, `cash_pi_far`, `cash_pi_stage` | float | cash of the loan under the same target policies |

The annotated estimators do not read these values directly. Their annotator is
the per-context mean of the annotation population's values under the target,
degraded with a bias of +0.25 × scale and Gaussian noise of standard deviation
0.25 × scale, where scale is the largest absolute context mean
(`src/ope_bench/panel.py`).

## Run records (JSON, in the repository and in each archive)

| file | content |
|---|---|
| `logs_meta.json` | simulation job of replicate 0: protocol, simulator version and stream scheme, code fingerprint, configuration hashes, seed, batch size, cohort size, exploration share, logged mean score and cash, sha256 of `logs.parquet`, timing |
| `annotator_meta.json` | the same for replicate 1, with per-target means and the sha256 of `annotator.parquet` |
| `reference_r{2,3,4}.json` | one reference replicate: cohort size, per-candidate mean score (`means`) and the per-loan covariance matrix of the candidates' scores (`cov`, order of `candidates`), with the same quantities for cash in the `cash` block. The Monte Carlo standard error of a mean is `sqrt(cov[i][i] / n_cohort)`, and that of a paired gap uses the covariance |
| `panel.json` | estimation output under the score: seeds of the four estimation roles, references, every estimator's value, interval and error for each target in each regime, interval diagnostic, support, selection and regret, timing |
| `panel_cash.json` | the same estimation output under cash |

Both panels record `reward`, `reward_definition` and `reward_column`.

## Formats

Parquet files are written by DuckDB. The pinned environment reads them with
DuckDB, for example `duckdb.sql("select * from 'logs.parquet'").df()`.
`pandas.read_parquet` also works if pyarrow is installed (it is not part of
the pinned environment). JSON files are UTF-8. CSV files have a header row and
use `.` as the decimal separator.
