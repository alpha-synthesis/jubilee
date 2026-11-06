# Reproducing the JUBILEE paper

There are three levels of reproduction.

| level | what it does | needs | cost |
|---|---|---|---|
| rebuild | rebuilds every generated table printed in the paper from `results/` and compares it byte for byte | this repository | seconds |
| re-estimate | reruns the estimators on the deposited cohort extracts | this repository and the data deposit | minutes per run |
| regenerate | reruns the simulations and the estimation | this repository | up to about 100 CPU-hours per protocol |

## Environment

Python 3.12 (validated, `pyproject.toml` accepts 3.11 and later) with the
versions pinned in `requirements.lock`. Install from the lock file, because
the optional extras of `pyproject.toml` do not include scipy, which the tests
and several analysis scripts need. The complete list of installed packages of
the validated environment is in `environment/`.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.lock
pip install --no-deps -e .
pytest                         # expected: 122 passed, 3 deselected
```

`snapshots/model-2.0.0/` is a separate package with the same package names
and needs its own environment.

## Rebuild

```bash
python reproduce/check_arxiv_tables.py --work outputs/arxiv_tables
```

It runs `reproduce/paper/render_campaign_tables.py` on the paired-study
records and `reproduce/paper/render_rerun_tables.py` on the grid, cash and
DM⁺ records, then compares the 32 generated files with
`reproduce/expected/arxiv_v1_tables/`. Figure 2 is drawn by
`render_rerun_tables.py` and Figure 3 by `reproduce/paper/render_tmlr_figures.py`.

## Re-estimate from the data deposit

Unpack an archive into `outputs/`, so that
`outputs/rerun_20261106/<protocol>/runs/` holds its runs, move aside the
`panel.json` and `panel_cash.json` files to be recomputed, and run the
estimation of the protocol:

```bash
unzip -q jubilee-paired-rerun-extracts-A_on.zip -d outputs
python scripts/tmlr_campaign.py estimate --protocol scripts/rerun_20261106/paired_cash.json --workers 4
python scripts/rerun_20261106/compare_paired_score.py \
  --archived results/rerun_20261106/paired/runs --rerun outputs/rerun_20261106/paired/runs \
  --out outputs/reestimate_check
```

The driver checks each extract against the sha256 stored in its run record.
`scripts/tmlr_evidence/dm_plus_from_extracts.py` computes the annotated direct
method from the same extracts without simulating.

## Regenerate

| study | protocol or script | command | measured cost |
|---|---|---|---|
| paired study, score and cash | `scripts/rerun_20261106/paired_cash.json` | `launch_rerun.sh` with `PROTOCOLS="paired:paired_cash.json"` | 94.2 CPU-hours |
| parameter grid, 20-seed cells | `scripts/rerun_20261106/grid_v2_20seeds.json` | `launch_rerun.sh` with `PROTOCOLS="grid20:grid_v2_20seeds.json"` | 104.8 CPU-hours |
| parameter grid, 5-seed cells | `scripts/rerun_20261106/grid_v2_5seeds.json` | `launch_rerun.sh` with `PROTOCOLS="grid5:grid_v2_5seeds.json"` | 36.0 CPU-hours |
| exploration comparison | `results/exploration_effect_20261104/protocol/protocol_frozen.json` | `python scripts/exploration_effect.py run --protocol Q --workers N`, then `aggregate --protocol Q --dest <dir>` | 8.16 CPU-hours |
| score equivalence between models | `results/settlement_score_equivalence_20261104/protocol/equivalence_grid.json` | `python scripts/settlement_equivalence.py run --grid <grid> --old-root snapshots/model-2.0.0 --new-root . --out <dir> --workers N`, then `summarize --grid <grid> --out <dir>` | 1.90 CPU-hours |
| contextual bandit | none | `python scripts/ope_meta_validation.py` | about 1 minute |

The launcher expects `<workspace>/repo` (this repository) and
`<workspace>/venv`, runs plan, simulate, estimate (both objectives), aggregate
(both objectives) and DM⁺ for each protocol, records every exit code in
`<protocol>/exit_codes.txt` and never deletes. Several instances with smaller
worker counts can share a server:

```bash
PROTOCOLS="paired:paired_cash.json" SIM_WORKERS=16 EST_WORKERS=10 EST_THREADS=2 \
  bash scripts/rerun_20261106/launch_rerun.sh
```

A driver skips the jobs whose output files exist, so to regenerate into a
fresh location write a copy of the protocol with a new `out_dir`. The paired
study's score panels regenerated under model 2.1.0 equal, field by field,
those of `results/tmlr_revision_20261103/` produced under model 2.0.0
(`results/rerun_20261106/paired/score_equivalence/`). The equivalence holds
for month-0 policies and does not cover tools that read the complete panel
after a recovery or stateful policies.

## Data deposit

https://doi.org/10.5281/zenodo.24008544 holds the files that are too large for
the repository:

| archive | content |
|---|---|
| `jubilee-paired-rerun-extracts-{A_off,A_on,B_off,B_on}.zip` | paired study, per condition: the 20 runs' `logs.parquet` and `annotator.parquet` (score and cash columns), `panel.json` (score), `panel_cash.json` (cash), reference and metadata records, and the protocol |
| `jubilee-grid-v2-extracts-20seed.zip` | parameter grid, the seven 20-seed cells: 140 runs, same members |
| `jubilee-grid-v2-extracts-5seed.zip` | parameter grid, the ten 5-seed cells: 50 runs, same members |
| `jubilee-pilot-extracts.zip` | the development pilot's extracts and records |
| `jubilee-result-records.zip` | result records, including records of earlier development runs not kept in this repository |
| `jubilee-auxiliary-records.zip` | run logs and development records |

`SHA256SUMS` lists the archives and `inventory.csv` every member with its size
and sha256.
