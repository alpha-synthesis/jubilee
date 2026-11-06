# Reruns of 2026-11-06

The results reported in the paper for the parameter grid, for the paired
study under simulated cash and for the annotated direct method (DM⁺) come
from these runs. The plan was fixed before execution (`PLAN.md`); the three
protocols are `paired_cash.json`, `grid_v2_20seeds.json` and
`grid_v2_5seeds.json`, executed with `launch_rerun.sh` on a 48-core server
(simulator model 2.1.0, keyed random streams).

| folder | content |
|---|---|
| `paired/`, `grid20/`, `grid5/` | per protocol: `protocol.json`, `plan.json`, `exit_codes.txt`, `status.json`, logs, `aggregate_score/` and `aggregate_cash/` (every table the paper uses), `dm_plus/` (annotated direct method), and `runs/<condition>/seed<S>/` with the small run records (`panel.json` for the score, `panel_cash.json` for cash, `reference_r*.json`, `logs_meta.json`, `annotator_meta.json`) |
| `paired/score_equivalence/` | field-by-field comparison of the 80 regenerated score panels with the 2026-11-03 panels (model 2.0.0): 63,040 of 63,040 result fields equal; the 240 remaining differences are run time and memory |
| `paired/selection_tests_score.csv`, `paired/selection_tests_cash.csv` | post hoc seed-block selection tests with Holm adjustment, per objective |
| `DONE_*` | per-protocol exit codes of every step |
| `comment_cleanup.json` | the released code differs from the code that produced these runs only in removed comments: every edited file is identical as Python AST without docstrings, as parsed YAML or as shell without comment lines, and one run re-estimated with the released code reproduces its score and cash panels exactly (792 of 792 fields each); code fingerprints of both trees |

The cohort extracts (`logs.parquet`, `annotator.parquet`) of every run are in
the data deposit, one archive per paired-study condition and one per grid
protocol. Server workspace paths in the logs and manifests were replaced by
`<workspace>` (and the repository root by `.`); nothing else was edited.

Rebuild the paper's rerun tables and Figure 2 from these files:

```bash
python reproduce/paper/render_rerun_tables.py --rerun results/rerun_20261106 --source outputs/paper_tables
```
