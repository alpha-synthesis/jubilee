# Exploration-effect add-on — precision and sizing rule

Written 2026-11-04, before any simulation of this add-on was run. It fixes how
the number of reference replicates is chosen from the development pilot and
how the result is reported. The confirmatory campaign
(`outputs/tmlr_revision_20261103/`) and its frozen protocol are not changed.

## Question and estimand

In worlds A_on and B_on of the revision campaign (generator version 2, hazards
as configured), what is the effect on the benchmark's recovery reward of
keeping the incumbent's random exploration at ε = 0.08 instead of ε = 0?

* Population: the month-0 explorable cohort (delinquent, or in liquidation for
  at most 180 days at month 0), the same cohort the campaign evaluates.
* Policy: the incumbent with its ε-exploration floor acts in every month of
  the window 0–8 in which the loan is explorable; only
  `actions.exploration.epsilon` differs (0.08 vs 0).
* Reward (the benchmark's convention, unchanged): 1{some recovery in months
  0–8} × start balance × (1 − month-0 discount). It is not the sum of amounts
  collected, does not apply the discount of the recovery month, and has no
  channel costs; it is not net profit.
* Signed cost per pair: Δ = V(ε = 0) − V(ε = 0.08), US$ per decision on the
  cohort. Positive = loss of reward from exploring; negative = gain.

## Pairing

Within a pair (world, seed, replicate), the two arms share config (except ε),
seed, replicate, batch size, population, hidden factors, regional shocks and
every per-(loan, month) draw. Checks per pair: identical loan ids in the same
order and identical month-0 state, DPD, days in liquidation and start balance;
explored share 0 under ε = 0. Trajectories may diverge.

## Uncertainty and target

* Per pair: Monte-Carlo SE of Δ from the per-loan paired differences
  (sd / √n; loans independent given the shocks).
* Per world: mean of the 20 per-seed Δ (a per-seed Δ averages its R
  replicates); 95% interval mean ± t(0.975, 19) · SD(per-seed Δ) / √20. Seeds
  are the independent unit; loans are not, and the two worlds share seeds, so
  they are not two independent replications.
* Target: 95% half-width ≤ 1.0 US$ per decision in each world, and per-pair
  Monte-Carlo SE ≤ 1.0. Justification: the incumbent's value is about 270–290
  US$ per decision, so 1 US$ is about 0.35% of it; the campaign's
  candidate gaps are 13–52 US$ and its selection regrets 4–16, and its
  reference rule asked for paired-gap SE ≤ 1.0. A half-width of 1 US$ places
  the exploration effect on the scale of those quantities.

## Sizing from the pilot

Pilot: worlds A_on and B_on, development seeds 9301–9305 (disjoint from the
campaign's 7001–7020 and from its development seeds 9001–9004), replicates 2
and 3, 1,000,000 borrowers, batch 50,000. From it:

* σ²_mc = median over pilot pairs of the per-pair Monte-Carlo variance of Δ
  (one replicate);
* σ²_seed = max(0, variance across the pilot's per-seed Δ (replicate 2),
  pooled over the two worlds, − mean σ²_mc);
* projected half-width(R) = t(0.975, 19) · √((σ²_seed + σ²_mc / R) / 20).

Choose the smallest R ∈ {1, 2, 3} whose projected half-width ≤ 1.0 and whose
projected cost fits the ceiling. If none does: R = 1 when √(σ²_seed/20)·t
alone exceeds 1.0 (replicates cannot help), else the largest affordable R;
then report the achieved half-width. Seeds, replicates and analysis are
frozen before the main simulations; they are not increased after the main
results are seen.

## Budget

Ceiling for the add-on (pilot, validation and main): 15 CPU-hours on the
existing compute server. The preliminary estimate (about 4.1 CPU-hours for 80
simulations at one replicate) is replaced by the cost measured in the pilot.

## Validation before the main run

For confirmation seeds, replicate r ≤ 4, the ε = 0.08 arm is the same
simulation as the campaign's reference of the incumbent π_b. Before the main
run, the ε = 0.08 arm of (A_on, 7001, r = 2) and (B_on, 7001, r = 2) must
reproduce the archived `reference_r2.json` π_b mean and cohort size (|Δmean|
≤ 1e-6 US$); the main run repeats the check for every pair with r ≤ 4. A
mismatch stops the dependent analysis and is reported.

## Reporting

Per world: mean Δ, 95% interval, Δ relative to V(ε = 0), the between-seed SD
and the Monte-Carlo component separately, recovery rates under both arms and
their difference. Both worlds are reported whatever the sign or width; an
interval that includes zero is reported as inconclusive, not as "no cost".
Secondary and descriptive: world B − world A per seed (shared seeds),
month-0 exploration shares, share of loans whose reward differs.
