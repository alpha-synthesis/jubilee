# Paired study design

The paired study runs on the keyed-stream generator, grades every estimator
against independent reference replicates with reported Monte Carlo error,
adds a gradient-boosted nuisance regime on the same logs, and repeats the
main contrast in a second world. The protocol file (conditions, seeds,
population, replicates, analysis, code fingerprint) is the authority, and
this page explains it.

## Questions

1. **Reference precision.** How precise are the simulated policy values and
   the gaps between candidates, conditional on a world's regional shocks?
2. **Outside the tabular construction.** With gradient-boosted reward and
   propensity models on richer observable covariates (same logs, same folds),
   do the log-based estimators still agree with each other, and do they still
   share the error caused by hidden coupling?
3. **Another world.** Does the pattern of the parameter grid (no detectable
   error without coupling; a shared error of the log-based family with
   coupling; design-based pilots without that error but with wider
   intervals) persist when one outcome mechanism changes?
4. **Selection.** Which candidate does each estimator pick, at what regret
   against the reference, and how often does the reference itself leave the
   ranking unresolved?
5. **Intervals (diagnostic, control first).** How does the fixed-model DM
   interval compare with a bootstrap that refits the model?

No ordering among estimators and no ranking inversion is required for any
question; every condition is reported.

## Estimand

For a candidate policy π and a world (config + seed):

    V(π | shocks) = E[ 1{recovered in months 0–8} · B0 · (1 − d0) ]

over the **month-0 explorable cohort** of the generating population
(loans that are `delinquent`, or in `credito_em_liquidacao` with at most 180
days in liquidation, at month 0). π chooses the month-0 action on those loans;
every later month follows the incumbent + ε (the continuation law); B0 is the
start balance and d0 the month-0 discount. The expectation is over the
population, hidden factors, actions and outcomes **conditional on the world's
realised regional shock vector**. Units: US$ per decision. The reward is
recovery value: it ignores channel costs and is neither cash flow nor profit.
Horizon, eligibility and reward are those of the parameter grid.

**Simulator model.** The campaign ran on simulator model 2.0.0. Model 2.1.0
(full settlement: the whole offer is paid, the remainder written off, the loan
closed) changes only what happens at and after a loan's first recovery. The
population, the decisions and draws before it and its month are unchanged, and
the campaign's pipeline reads nothing after a first recovery. Its logs,
annotator sources, references and estimator outputs for this reward are
therefore what 2.1.0 produces. Evidence: the code argument, an exact
comparison in separate processes on a 24-unit grid (the first two batches of
the four campaign configurations at two seeds;
`scripts/settlement_equivalence.py`), and one complete
campaign run regenerated with 2.1.0; the other runs were not re-executed.
The reward is a synthetic score: its discount is the
month-0 discount even when the recovery happens later under another offer, and
it is not the cash the simulator records.

The incumbent π_b is a candidate too: its value is the same expectation under
the behaviour policy (incumbent + ε at every month, month 0 included). The
logged cohort mean is an estimate of it (used for decisions), not its
reference value.

## Random roles

Each world seed has independent replicates sharing only the regional shocks
(`generate(..., replicate=r)` / `simulate_cohort(..., replicate=r)`):

| replicate | role | policies simulated |
|---|---|---|
| 0 | logged world, the only data estimators see | behaviour |
| 1 | annotator's source (DM⁺-IS only) | every target |
| 2 … R+1 | reference | every candidate, on the same population |

Within a reference replicate all candidates share the population and the
per-(loan, month) draws, so gaps between candidates are paired; the per-loan
covariance of their rewards gives the paired Monte-Carlo standard error.
Reference values never use replicate 0 or 1. Seeds of the estimation steps
(bootstrap, cross-fitting folds, annotator noise, gradient-boosting random
state) are derived from the world seed with fixed roles
(`collection_simulator.generator.derived_seed`, roles 16–19).

## Conditions

Two worlds × hidden coupling off/on, at confounding strength 1.0, noise 0.25,
ε = 0.08 (`configs/tmlr/`):

| condition | outcome mechanism | coupling | hazard |
|---|---|---|---|
| A_off | original | off | 0.001421 |
| A_on | original | on | 0.001421 |
| B_off | stage-dependent channel effects | off | 0.001426 |
| B_on | stage-dependent channel effects | on | 0.001426 |

*Within a world* only the behaviour policy changes. With the coupling on, the
incumbent's channel weights are tilted by
clip(DPD/180 + payment friction − 0.4 · contactability, −2, 2): they read two
hidden factors and the observed DPD. With it off they are the fixed configured
weights (the switch of the grid's negative control). The incumbent's
discount ramp by DPD is common to both. Hazard, hidden-factor distribution and
outcome mechanism are identical. The on − off contrast therefore removes the
hidden coupling and, with it, the DPD tilt of the channel mix; the DPD part is
observed — the tabular contexts hold it to within one 30-day step (a tilt of at
most 30/180 within a step) and the gradient-boosted models see the exact DPD.
(The grid's α ladder changed the hidden-factor variance and the outcome
distribution together with the assignment; these pairs change the assignment
alone.)

*Between worlds* only the channel-effect table changes. World A uses the
original table at every stage. World B (fixed a priori from collections
practice, before any world-B estimate): in early delinquency (DPD < 90) every
contact channel has log-odds effect +0.30 (a prompt works through any
channel); from 90 DPD (credit in liquidation) SMS −0.10, app message 0.00,
phone +0.45, field visit +0.65 (impersonal channels lose effect, personal
negotiation gains); "none" stays −0.85. World A's hazard is the
grid's cell-6 calibration (strength 1.0, coupling on, ε 0.08); world B's hazard was
set in development (seeds 9001–9004, coupling on) to match world A's 12-month
recovery rate on the same seeds, then frozen for both coupling settings.

At the same seed the four conditions share population, hidden factors and
regional shocks; condition contrasts are computed seed by seed.

## Candidates

| name | month-0 action on explorable loans |
|---|---|
| π_b (`pi_b`) | incumbent + ε (behaviour) |
| π_sms (`pi_near`) | SMS, discount 0.125 |
| π_visit (`pi_far`) | field visit, discount 0.275 |
| π_stage (`pi_stage`) | SMS with discount 0.025 below 90 DPD; field visit with 0.275 from 90 DPD |

π_stage was fixed in development from collections practice (remind early,
negotiate late) before any reference value was computed; it is a function of
the observed DPD step, so every estimator can evaluate it in the same 36
contexts. Targets act at the centres of their discount bins; the estimators
read every logged row of the bin. The pilot measures the value difference
between the centre dose and a dose spread uniformly over the bin
(`pi_near_binU`, `pi_far_binU`; development runs only), and every run reports
the mean logged dose of the matching rows of each target cell.

## Estimators

*Tabular regime* (36 contexts × 45 action cells):
DM, context-blind DM, IS, SNIPS, cross-fitted DR, DM⁺-IS, pilot-IS, pilot-DR.
Propensities are within-context frequencies on the full cohort; DR and DM⁺-IS
cross-fit the reward model on two folds. DM⁺-IS's annotator is the per-context
mean of the replicate-1 cohort under the target, degraded with bias
+0.25 × scale and noise sd 0.25 × scale (scale = maximum absolute cell value).
Intervals: 90% percentile bootstrap of per-row contributions with
the fitted nuisances held fixed (for DM, an interval conditional on the
fitted model).

*Gradient-boosted regime* (`ope_bench.nontabular`): reward model
`HistGradientBoostingRegressor` on observable month-0 covariates (DPD, days in
liquidation, start balance, principal, rate, term, loan age, remaining
maturity, age, income, dependents, product, region, gender, income band) plus
the action cell; one `HistGradientBoostingClassifier` per target for
P(A = target cell | x). Both are cross-fitted on the same two folds as the
tabular DR (preprocessing is a fixed category coding). Estimators: DM, IS,
SNIPS, DR, pilot-DR; pilot-IS needs no model and is shared with the tabular
regime. DM⁺-IS is not re-implemented in this regime. Propensities are clipped
at 0.001 (below the design floor ε/44 ≈ 0.0018 of the target cells); clipped
rows and the mean IS weight are reported. Hyper-parameters were fixed in
development by a reference-free rule written before the pilot outputs (mean IS weight on the
control logs; learning rate 0.05, 300 iterations, 15 leaves, at least 1,000 rows
per leaf, l2 1.0), without looking at errors against references.
Borrower-level latent factors and reference values are never features. The
region code is an observed covariate that identifies the region's macro shock
(one shock per region and world); that shock moves outcomes, not assignment, so
it is not a confounder. In the tabular regime DM, IS and SNIPS are the same
estimator whenever every context holds a row of the target cell (within-context
frequencies make the IS weights cancel the DM cell means); runs report the
largest difference among the three.

*Interval diagnostic*: `ope_bench.panel.dm_refit_bootstrap` refits the
tabular reward model in every bootstrap resample. Resampling unit: the cohort
row (one loan per borrower; rows independent given the fixed regional shocks).

## Metrics and analysis

Per condition and candidate: reference value with its Monte-Carlo SE. Per
condition, regime, estimator and target: mean error against the reference with
its SE over seeds, RMSE with a bootstrap-over-seeds SE, interval containment
counts and widths, support (matched rows, anchors). Containment of a simulated
reference is not coverage of the expected value; the reference SE is reported
next to every interval width.

Selection: each estimator picks the candidate with the highest estimate (the
incumbent is valued by its factual logged mean). Graded against the
reference: the top ranking is *resolved* when the reference gap between the
best and the runner-up exceeds 1.96 paired SEs, otherwise *ambiguous*; both
are counted with denominators. Regret = reference(best) − reference(picked)
with its paired SE; gain over the incumbent = reference(picked) −
reference(π_b); pairwise order agreement over resolved pairs.

Contrasts: coupling on − off within each world and world B − world A within
each coupling setting (seed-paired); gradient-boosted − tabular on the same
run. Seeds are the independent unit within a condition; the same seed in two
conditions is a block, never an extra replicate.

## Rules

* Development uses seeds 9001–9004; confirmation seeds are disjoint and fixed
  in the frozen protocol before any confirmatory output exists.
* No seed is discarded for estimator results or recovery rates. A technical
  failure (crash, out of memory) is rerun with identical inputs and recorded.
  Rarity (12-month recovery of all loans) and the exploration share are
  recorded for every run and not used as gates: the grid's per-run tripwire
  is not applied to these worlds.
* Every run records the effective config hash, the code fingerprint (content
  hash of `src/` and the driver, plus the git state when available), the seeds
  of every role, batch size, package versions, wall time, CPU time and peak
  memory.

## Sizing (from the development pilot)

The pilot ran the control (A_off), the chosen confounded condition (A_on),
world B (B_on) and the grid's stress cell (strength 1.8, coupling on) on
three development seeds with four reference replicates each. One replicate of
1,000,000 borrowers (about 744,600 cohort decisions) gives a Monte-Carlo SE of
2.2–3.3 US$ per decision for a candidate's value and 0.6–1.1 for a paired gap
between candidates (within-replicate correlation of the candidates' rewards
about 0.96). The spread of the replicate means agrees with these SEs (mean
variance ratio 0.94 for values and 1.22 for gaps over 12 runs; p = 0.85 and
0.33). The precision rule fixed before inspection (value SE ≤ 2.0, gap SE ≤
1.0 per run, worst pilot run, ceiling 150 CPU-hours) gives **R = 3 reference
replicates** (expected worst SEs 1.92 and 0.64). With 20 seeds per condition the
campaign is 80 runs, 400 simulation jobs, about 75 CPU-hours.

The pilot also measured the bin approximation: the centre dose minus a dose
spread uniformly over the bin is +0.03 US$ (π_sms) and +0.08 US$ (π_visit) per
decision on average (paired SE about 0.08 per run), far below the precision
targets; it is not repeated in the confirmation runs. A development check
with 100 independent logged populations of one world found pilot-IS within
1.2 SE of the reference for the three targets (SE 5.8–7.5 US$): no bias of
the suspected 30–80 US$ size in generator version 2; biases below about
15–20 US$ are not resolved.
