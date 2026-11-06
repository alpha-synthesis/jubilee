# Exploring the simulator: how to vary noise and confounding

This is a guide for a person or an agent running a series of 1M-loan datasets to
see how an off-policy method behaves as the world gets harder. It treats noise
and confounding as **two separate axes**. Vary one axis per run and hold the
other at baseline. Do not take the cartesian product of every setting; that is
hundreds of multi-GB runs for little extra signal.

## The knobs

At the config level, these are the dials that matter (everything else can stay
at the package defaults):

| key | dial | effect |
|---|---|---|
| `oracle.hidden_confounding_strength` | confounding magnitude | scales the hidden drivers and their coupling to the action |
| `actions.intensity_confounds_with_friction` | confounding mechanism | toggles whether assignment uses the hidden driver at all |
| `oracle.noise_std` | variance | per-month idiosyncratic noise on the recovery log-odds |
| `oracle.target_monthly_recovery_rate` | event rarity | the baseline payment hazard |
| `actions.exploration.epsilon` | countermeasure | randomized exploration floor (0 disables) |

Everything finer (the hidden-factor weights, the delinquency ramp, the
assignment coefficients) lives in `generator.py` and is fixed; the agent works
the config dials above. One outcome mechanism is also exposed as optional
config: `oracle.channel_effects` replaces the default channel log-odds table
and `oracle.channel_effects_late` applies from 90 days past due (stage-dependent
effects, world B of `docs/revision_campaign.md`). Absent, the default table
applies at every stage. `ope-eval` and the CATE export mirror the default table
and refuse configs that change it.

**Baseline** is `configs/eps_floor_1m.yaml`: `hidden_confounding_strength = 0.6`,
`noise_std = 0.25`, exploration `epsilon = 0.08`, calibrated to roughly a 4%
annual realized recovery rate.

## Axis A — confounding (bias)

- **Turn:** `hidden_confounding_strength`. Add one control run with
  `actions.intensity_confounds_with_friction: false`.
- **Hold fixed:** `noise_std = 0.25`.
- **Ladder (coarse, then refine):** off (control) -> 0.6 -> 1.0 -> 1.4 -> 1.8.
  Refine between the two points where the signal first collapses.
- **Watch:** `offer_rho_marginal` from `ope-eval` (falls toward 0 as bias
  deepens) and `assignment_dependence` from `oracleless-report` (rises).
- **Stop when:** `offer_rho_marginal` reaches about 0. At that point the raw data
  alone is uninformative about the discount, which is the hard end of the range.

To isolate confounding from mere hidden heterogeneity, compare the mechanism
on versus off **at the same strength**: same hidden variance, only the coupling
to the action differs.

## Axis B — noise (variance)

- **Turn:** `noise_std`.
- **Hold fixed:** `hidden_confounding_strength = 0.6`.
- **Ladder:** 0.15 -> 0.25 -> 0.40 -> 0.60.
- **Watch:** how stable the "percent of ceiling" figure is across two seeds, and
  how wide the confidence interval gets.
- **Stop when:** the estimate starts jumping around from seed to seed.

## The one shared rule

Both dials drag the **realized recovery rate** with them: more noise raises it
(the sigmoid is convex at a low base rate), and large confounding shifts it too.
After changing either dial, do a quick small-population calibration and retune
`oracle.target_monthly_recovery_rate` back to roughly 4% annual before launching
the 1M run. This keeps an Axis-A run and an Axis-B run comparable. Apart from
this calibration step, the two axes are swept independently.

## Exploration is a countermeasure

`actions.exploration.epsilon` is the fix for confounding. Climb it only where
recoverability matters: at the few confounding levels you care about, run both
`epsilon = 0` and `epsilon = 0.08` so the pair shows how deep the trap is and
whether exploration climbs back out.

## Cross terms

A couple of deliberate high-confounding by high-noise corners are worth running
to confirm the two effects compound. Two or three such points are enough; the
full grid adds cost without much extra signal.

## Reading each run

- `oracleless-report` (public columns only): `assignment_dependence`, channel
  overlap, exploration coverage. This is what a client-side analyst would see.
- `ope-eval` (needs the policy CSV and the matching `oracle_truth`):
  `offer_rho_marginal`, `obs_r2`, calibration optimism, and policy value as a
  percent of the perfect-information ceiling. This is the graded answer.

## Budget

Each 1M run is minutes of compute and several GB of export. A full study is on
the order of a dozen runs: the confounding ladder at baseline noise, the noise
ladder at baseline confounding, two or three cross corners, each key point at
both exploration settings, and the one or two headline points replicated under a
second seed.
