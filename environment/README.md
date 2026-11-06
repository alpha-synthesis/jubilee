# Validated environments

`requirements.lock` (repository root and snapshot) pins the direct
dependencies used by the experiments. The file below lists every package,
including unpinned transitive dependencies, installed in the fresh virtual
environment used to validate the release (CPython 3.12.3 on Linux x86-64,
`pip install -r requirements.lock` then `pip install --no-deps .`).

| file | environment |
|---|---|
| `pip-freeze-validated-root-and-model-2.0.0.txt` | repository root (model 2.1.0) and `snapshots/model-2.0.0` (identical lists) |

To recreate the validated environment exactly:
`pip install -r environment/pip-freeze-validated-root-and-model-2.0.0.txt`,
then `pip install --no-deps .`.

The paired-study runs themselves recorded Python 3.12.3, numpy 2.2.6,
pandas 2.2.3, duckdb 1.5.4 and scikit-learn 1.7.2 in each `*_meta.json` and
`panel.json`.
