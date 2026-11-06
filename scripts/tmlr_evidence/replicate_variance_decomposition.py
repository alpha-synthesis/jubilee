"""High-powered check of the replicate-to-replicate variance of cohort means
(behaviour policy only), separating population quantities from outcomes.

For each replicate of one world (shocks fixed) it records cohort means and
per-loan variances of: the reward, the paid indicator, the start balance, the
first region's share, the cohort share of all loans and the latent
resilience. For each quantity the ratio (variance of replicate means) /
(average per-loan variance / cohort size) is 1 under independent loans.

Usage::

    python scripts/tmlr_evidence/replicate_variance_decomposition.py --config CFG \
        --seed S --borrowers 20000 --replicates 2000 3999 --out OUT.json --workers 40
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


def _one(args):
    cfg, r, batch = args
    c, meta = simulate_cohort(cfg, policy=None, replicate=r, batch_size=batch,
                              with_covariates=True)
    total = int(cfg["population"]["borrowers"])
    x = {
        "reward": c["reward"].to_numpy(np.float64),
        "paid": c["paid_within_h"].to_numpy(np.float64),
        "balance": c["start_balance"].to_numpy(np.float64),
        "region1": (c["uf"].to_numpy() == "R01").astype(np.float64),
        "resilience": c["hidden_borrower_resilience"].to_numpy(np.float64),
    }
    out = {"r": r, "n": len(c), "cohort_share": len(c) / total}
    for k, v in x.items():
        out[f"mean_{k}"] = float(v.mean())
        out[f"var_{k}"] = float(v.var(ddof=1))
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--borrowers", type=int, required=True)
    ap.add_argument("--batch-size", type=int, default=50_000)
    ap.add_argument("--replicates", type=int, nargs=2, required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    cfg["seed"], cfg["population"]["borrowers"] = a.seed, a.borrowers
    reps = list(range(a.replicates[0], a.replicates[1] + 1))
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=50) as pool:
        res = pool.map(_one, [(copy.deepcopy(cfg), r, a.batch_size) for r in reps],
                       chunksize=4)
    df = len(res) - 1
    out = {"config": str(a.config), "seed": a.seed, "borrowers": a.borrowers,
           "batch_size": a.batch_size, "n_replicates": len(res),
           "ratio_se_approx": float(np.sqrt(2 / df)), "quantities": {}}
    for k in ("reward", "paid", "balance", "region1", "resilience"):
        means = np.array([x[f"mean_{k}"] for x in res])
        pred = float(np.mean([x[f"var_{k}"] / x["n"] for x in res]))
        out["quantities"][k] = {"ratio": float(means.var(ddof=1) / pred)}
    share = np.array([x["cohort_share"] for x in res])
    p = share.mean()
    out["quantities"]["cohort_share"] = {
        "ratio": float(share.var(ddof=1) / (p * (1 - p) / a.borrowers))}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: round(v["ratio"], 3) for k, v in out["quantities"].items()}),
          "| ratio SE ~", round(out["ratio_se_approx"], 3), "| n_rep", len(res))


if __name__ == "__main__":
    main()
