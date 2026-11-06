# JUBILEE: a benchmark environment for off-policy evaluation in debt collections

A synthetic debt-collections simulator with a known generating process, and
the estimator panel used to grade off-policy evaluation (OPE) methods against
simulated policy values.

Real collections logs cannot be released, and on real logs the true value of
a policy is unknowable, so OPE estimators cannot be graded there. This
repository provides a relational loan-month world whose generating process is
known. The `oracle_truth` table exposes the hidden factors, the true monthly
probabilities and the random draws of every loan-month. Hidden factors drive
both outcomes and action assignment, and the experimental parameters include
confounding strength, outcome noise, a randomized exploration share and
annotator quality. A policy's value is computed by simulating the policy on
the same world, as a Monte Carlo estimate with a reported standard error.

## Paper, code and data

This repository accompanies the paper *JUBILEE: A Benchmark Environment for
Off-Policy Evaluation in Debt Collections*. The cohort extracts of every run
are in the data deposit, https://doi.org/10.5281/zenodo.24008544. Every
generated table printed in the paper rebuilds byte for byte with

```bash
python reproduce/check_arxiv_tables.py --work outputs/arxiv_tables
```

`REPRODUCING.md` explains how to rebuild the tables, re-estimate any run from
the deposited extracts and regenerate each study from the simulation.

## Scope of claims

This is an instrument, not a digital twin. The data-generating process has
known causal structure and the shape of a collections portfolio (monthly
panel, rare recovery events, competing charge-off risk, confounded action
assignment), but its parameters are synthetic and are not calibrated to any
real portfolio. Findings produced with it are claims about estimator behavior
under known conditions, not about any real collections operation.

## Random streams

Every source of randomness has its own stream keyed by `(seed, role,
replicate, batch)`: regional shocks, population and contracts, hidden
factors, behaviour-policy actions and outcomes. For a fixed configuration,
seed, replicate and batch size, the population and regional shocks are the
same under every policy, and two policies use the same draws at every (loan,
month) they both reach. Their trajectories still diverge once their actions
differ. A different `replicate` gives an independent population of the same
world, with the same regional shocks. The batch size is part of the
reproduction configuration. Details and tests:
`src/collection_simulator/generator.py`, `tests/simulator/test_rng_streams.py`.

## Simulator model

Model 2.1.0 applies full settlement: when a loan recovers, the borrower pays
the whole settlement offer, the discounted remainder is written off and the
loan ends `cured`. Two objectives are recorded for every decision, the
synthetic score `1{first recovery in months 0–8} × B0 × (1 − d0)` and the cash
paid in months 0–8, and neither includes channel costs. The earlier model
2.0.0 collected a random share of the offer and kept the loan open. Both
models step every loan identically until its first recovery, so the score
and every input its estimators read are the same under both for month-0
policies, which `scripts/settlement_equivalence.py` checks loan by loan. The
2.0.0 generator is kept in `src/collection_simulator/legacy/` and as a full
source tree in `snapshots/model-2.0.0/`.

## Layout

| Path | What it is |
|---|---|
| `src/collection_simulator/` | The world: generation, export (public tables and `oracle_truth`), validation, oracleless audit, `ope-eval` grading harness |
| `src/ope_bench/` | The estimator panel: DM, IS, SNIPS, DR (cross-fitted), annotated estimators, pilot estimators, gradient-boosted nuisances, bootstrap intervals, synthetic bandit |
| `configs/` | Simulation configurations: `tmlr/` the paired-study worlds, `grid/` the 17 parameter-grid cells, `tiny_ci.yaml` a seconds-long smoke world |
| `scripts/` | Drivers: `tmlr_campaign.py` (simulate and estimate a protocol), `tmlr_aggregate.py` (tables), `rerun_20261106/` (the protocols behind the paper), `exploration_effect.py`, `settlement_equivalence.py`, `ope_meta_validation.py` (bandit), `tmlr_evidence/` (selection tests, DM⁺ from extracts, diagnostics) |
| `results/` | Result records behind every table of the paper (see `results/README.md`) |
| `reproduce/` | Table rebuild and byte comparison with the printed tables |
| `snapshots/model-2.0.0/` | Source tree of model 2.0.0, used by the score-equivalence check |
| `docs/` | Paired-study design, estimators, experiment design, data dictionary |
| `environment/` | Complete package list of the validated environment |
| `tests/` | Test suite (`pytest`, slow statistical tier: `pytest -m behavioral`) |

## Quickstart

```bash
pip install -r requirements.lock   # pinned versions, including scipy for the tests
pip install -e .

# seconds-long smoke run
collection-simulator generate --config configs/tiny_ci.yaml --out data/generated/tiny
collection-simulator validate --db data/generated/tiny/sim.duckdb

# test suite
pytest

# a new policy or world in a few lines, under a minute on one core
python scripts/tmlr_evidence/example_new_policy.py --borrowers 50000
```

## License

MIT, see [LICENSE](LICENSE).
