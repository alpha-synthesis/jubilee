"""Does the per-loan variance predict the replicate-to-replicate variance of a
cohort mean? (Development check of the reference SE.)

For one world (config + seed, regional shocks fixed) simulate many independent
population replicates under two candidates (behaviour and one target) and
compare, for the candidate values and for their paired gap:

    observed  = variance of the replicate means across replicates
    predicted = average of (per-loan variance / cohort size) within replicates

Their ratio is 1 if the loans of a replicate are independent draws given the
shocks. Optionally the population is decomposed: the variance of the mean of
the start balance (a pure population quantity) is compared the same way.

Usage::

    python scripts/tmlr_evidence/replicate_variance_check.py --config CFG --seed S \
        --borrowers 50000 --batch-size 50000 --replicates 1000 1399 --out OUT.json --workers 40
"""

from __future__ import annotations

import argparse
import copy
import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from collection_simulator.config import load_config  # noqa: E402
from collection_simulator.generator import simulate_cohort  # noqa: E402
from ope_bench.panel import PI_NEAR  # noqa: E402


def _one(args):
    cfg, r, batch = args
    b, _ = simulate_cohort(cfg, policy=None, replicate=r, batch_size=batch)
    t, _ = simulate_cohort(cfg, policy=PI_NEAR.generator_policy(), replicate=r, batch_size=batch)
    rb, rt = b["reward"].to_numpy(np.float64), t["reward"].to_numpy(np.float64)
    bal = b["start_balance"].to_numpy(np.float64)
    paid = b["paid_within_h"].to_numpy(np.float64)
    n = len(rb)
    d = rt - rb
    return {"r": r, "n": n, "mean_b": rb.mean(), "var_b": rb.var(ddof=1),
            "mean_t": rt.mean(), "var_t": rt.var(ddof=1),
            "mean_d": d.mean(), "var_d": d.var(ddof=1),
            "mean_bal": bal.mean(), "var_bal": bal.var(ddof=1),
            "mean_paid": paid.mean(), "var_paid": paid.var(ddof=1)}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--borrowers", type=int, default=50_000)
    ap.add_argument("--batch-size", type=int, default=50_000)
    ap.add_argument("--replicates", type=int, nargs=2, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    cfg["seed"], cfg["population"]["borrowers"] = a.seed, a.borrowers
    reps = list(range(a.replicates[0], a.replicates[1] + 1))
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=20) as pool:
        res = pool.map(_one, [(copy.deepcopy(cfg), r, a.batch_size) for r in reps])
    out = {"config": str(a.config), "seed": a.seed, "borrowers": a.borrowers,
           "batch_size": a.batch_size, "n_replicates": len(res), "quantities": {}}
    for q in ("b", "t", "d", "bal", "paid"):
        means = np.array([x[f"mean_{q}"] for x in res])
        pred = float(np.mean([x[f"var_{q}"] / x["n"] for x in res]))
        obs = float(means.var(ddof=1))
        df = len(res) - 1
        out["quantities"][q] = {"observed_var_of_means": obs, "predicted_var": pred,
                                "ratio": obs / pred,
                                "ratio_se_approx": float(np.sqrt(2 / df))}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: round(v["ratio"], 3) for k, v in out["quantities"].items()}),
          "ratio SE ~", round(float(np.sqrt(2 / (len(res) - 1))), 3))


if __name__ == "__main__":
    main()
