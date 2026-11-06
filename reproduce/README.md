# Table rebuild

Run from the repository root.

| file | purpose |
|---|---|
| `check_arxiv_tables.py` | rebuilds every generated table printed in the paper from `results/` and compares it byte for byte with `expected/arxiv_v1_tables/` |
| `paper/render_campaign_tables.py` | the paper's generator of the paired-study tables and appendix |
| `paper/render_rerun_tables.py` | the paper's generator of the grid, cash and DM⁺ tables and of Figure 2 |
| `paper/render_tmlr_figures.py` | the paper's generator of Figure 3 |
| `expected/arxiv_v1_tables/` | the generated tables as printed in the paper |
