Re-estimation of run A_on / seed 7001 from its two cohort extracts (logs.parquet, annotator.parquet) and its reference summaries, 2026-11-03T23:58:55-03:00.
Environment: compute server venv (Python 3.12.3, requirements.lock), fresh copy of the final repository content, OMP/MKL threads 4, code fingerprint de3cb466a5e57aaad0acb35bc67f928dd9f6d0740da2a775e45336d2c0b6cdf0.
Call: tmlr_campaign.load_protocol(protocol_frozen.json); estimate_run(proto, 'A_on', 7001).
Result: panel_A_on_seed7001_reestimated.json equals campaign/runs/A_on/seed7001/panel.json in every field except wall_seconds, usage, gbm_fit_seconds and environment (0 differences). Wall 1:34, peak RSS 1,399,684 KB (time output in reestimate_A_on_7001.time.txt).
