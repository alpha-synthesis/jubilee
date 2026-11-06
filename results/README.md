# Result records

The records behind every table of the paper. Run records are JSON, tables are
CSV, and every aggregate is written by the scripts named in `REPRODUCING.md`.

| folder | study | tables of the paper |
|---|---|---|
| `rerun_20261106/` | parameter grid, paired study under simulated cash, annotated direct method, and the paired study's score panels regenerated under model 2.1.0 (see its `README.md`) | grid tables and Figure 2, cash tables, DM⁺ table, score-equivalence counts |
| `tmlr_revision_20261103/` | paired study under the score: `campaign/` (protocol, per-run records, tables), `pilot/` (reference sizing), `diagnostics/` and `rng_validation/` (reference and stream checks) | paired-study score tables, Figure 3, Appendix B |
| `exploration_effect_20261104/` | fixed-hazard exploration comparison | exploration table |
| `settlement_score_equivalence_20261104/` | score equivalence between simulator models 2.0.0 and 2.1.0 | score-equivalence table |
| `ope_meta_validation/` | contextual bandit with closed-form truth | bandit table |

The paired-study records carry `git_head: "unavailable"` because the server
copy that produced them had no version-control metadata. Their code
fingerprint (`de3cb466…`, computed by `scripts/tmlr_campaign.py`) is
reproduced by `snapshots/model-2.0.0`. The reruns in `rerun_20261106/` carry
`bd3b682b…`, and the released repository root gives `de8eabc2…`, which
differs from it only in removed comments
(`rerun_20261106/comment_cleanup.json`). Server workspace paths in logs and
manifests were replaced by `<workspace>`, and no number was changed.
