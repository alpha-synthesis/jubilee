"""First-order size of the bin approximation's dose offset, per campaign run.

The targets act at the centre dose of a discount bin; the tabular estimators
read the logged rows of the bin in each context, whose doses differ from the
centre. Holding the recovery probability fixed within the bin (the reward is
1{recovered} * B0 * (1 - d)), the estimators' value in context c exceeds the
target's by m_c * [1 - (1 - d_centre) / (1 - mean logged dose in c)], where m_c
is the mean logged reward of the target cell in c. Weighted by the cohort's
context shares, this gives the offset per run (US$ per decision). It ignores
the recovery response to the dose, which offsets part of it.

Run from the code repository root:
    python outputs/tmlr_revision_20261103/diagnostics/dose_offset_first_order.py
"""

import glob
import sys

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from ope_bench.panel import (  # noqa: E402
    PI_FAR, PI_NEAR, PI_STAGE, action_id, balance_terciles, context_ids)

OUT = "outputs/tmlr_revision_20261103/diagnostics/dose_offset_first_order_by_run.csv"
CENTRES = [(PI_FAR, lambda c: 0.275), (PI_NEAR, lambda c: 0.125),
           (PI_STAGE, lambda c: 0.275 if (c // 3) * 30 >= PI_STAGE.late_dpd else 0.025)]

rows = []
for f in sorted(glob.glob("outputs/tmlr_revision_20261103/campaign/runs/*/seed*/logs.parquet")):
    cond, seed = f.split("/")[-3], int(f.split("/")[-2][4:])
    con = duckdb.connect()
    logs = con.execute(f"SELECT * FROM read_parquet('{f}')").df()
    con.close()
    ctx = context_ids(logs, balance_terciles(logs))
    act = action_id(logs["channel_logged"], logs["discount_logged"])
    r = logs["reward"].to_numpy(np.float64)
    d = logs["discount_logged"].to_numpy(np.float64)
    pc = np.bincount(ctx, minlength=36) / len(logs)
    for pol, centre in CENTRES:
        cells = pol.actions_per_context()
        offset = value = 0.0
        for c in range(36):
            m = (ctx == c) & (act == cells[c])
            if pc[c] == 0 or not m.any():
                continue
            mc, dbar = r[m].mean(), d[m].mean()
            value += pc[c] * mc
            offset += pc[c] * mc * (1 - (1 - centre(c)) / (1 - dbar))
        rows.append({"cond": cond, "seed": seed, "target": pol.name,
                     "dm_value": value, "first_order_offset": offset})
out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print(out.groupby("target")["first_order_offset"].agg(["mean", "min", "max"]).round(2))
