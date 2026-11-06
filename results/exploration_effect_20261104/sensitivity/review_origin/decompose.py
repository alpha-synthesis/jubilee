"""Reviewer check (read-only on the testbed): decompose the eps effect under the
benchmark reward R = 1{rec<=h} B0 (1-d0) and two alternatives:
  Rtau = 1{rec<=h} B0 (1 - d_tau)   (discount of the first-recovery month)
  cash = sum of recovered_amount over months 0..h-1
Reimplements simulate_cohort's loop with the generator's own private functions,
keeping per-month arrays. Validated by reproducing the pilot pair values.
"""
import copy
import json
import sys
from multiprocessing import Pool

import numpy as np

REPO = "<repo>"
sys.path.insert(0, REPO + "/src")
from collection_simulator.config import load_config  # noqa: E402
from collection_simulator import generator as g  # noqa: E402

H = 9


def run_batch(args):
    cfg_path, seed, rep, bidx, start, n, borrowers_total = args
    base = load_config(cfg_path)
    base["seed"] = seed
    base["population"]["borrowers"] = borrowers_total
    out = {}
    regional = g.regional_shocks(base)
    borrowers, hidden, loans = g._generate_population(base, rep, bidx, n, start, start + 1, regional)
    state0 = loans["initial_status"].to_numpy(dtype=object)
    liq0 = loans["days_in_credito_em_liquidacao"].to_numpy(dtype=np.int64)
    in_c = np.isin(state0, ["delinquent", "credito_em_liquidacao"])
    in_c &= ~((state0 == "credito_em_liquidacao") & (liq0 > 180))
    sel = np.flatnonzero(in_c)
    B0 = loans["outstanding_balance"].to_numpy(np.float64)[sel]
    out["B0"] = B0
    out["dpd0"] = loans["days_past_due"].to_numpy(np.int64)[sel]
    for arm, eps in (("e", 0.08), ("n", 0.0)):
        cfg = copy.deepcopy(base)
        cfg["actions"]["exploration"]["epsilon"] = eps
        rec = g._simulate_batch(cfg, borrowers, hidden, loans, rep, bidx, None,
                                n_months=H, loan_mask=in_c)
        first = rec["first_recovery_month"][sel]
        paid = (first >= 0) & (first < H)
        disc = rec["discount"][sel]          # (m, H)
        tau = np.where(paid, first, 0)
        dtau = disc[np.arange(len(sel)), tau]
        out[f"paid_{arm}"] = paid
        out[f"tau_{arm}"] = np.where(paid, first, -1)
        out[f"d0_{arm}"] = rec["discount0"][sel].astype(np.float64)
        out[f"dtau_{arm}"] = np.where(paid, dtau, 0.0)
        out[f"cash_{arm}"] = rec["recovered_amount"][sel][:, :H].sum(axis=1)
        out[f"expl0_{arm}"] = rec["is_exploration0"][sel]
        out[f"chan0_{arm}"] = np.array([str(c) for c in rec["channel0"][sel]])
        out[f"expl_any_later_{arm}"] = rec["is_exploration"][sel][:, 1:H].any(axis=1)
        # discount at explored later months in the eps arm and the incumbent's discount
        # in the eps=0 arm at the same loan-month (both alive there)
        out[f"alive_{arm}"] = rec["alive"][sel][:, :H]
        out[f"expl_{arm}"] = rec["is_exploration"][sel][:, :H]
        out[f"disc_{arm}"] = disc[:, :H]
        out[f"chan_{arm}"] = rec["channel"][sel][:, :H]
    return out


def main(cfg_path, seed, rep, borrowers=1_000_000, batch=50_000, workers=6, tag="x"):
    jobs = [(cfg_path, seed, rep, b, s, nn, borrowers) for b, s, nn in g._batches(borrowers, batch)]
    with Pool(workers, maxtasksperchild=1) as p:
        parts = p.map(run_batch, jobs)
    cat = {k: np.concatenate([q[k] for q in parts]) for k in parts[0]}
    np.savez_compressed(f"<scratch>/expl_scopeaudit/{tag}.npz", **cat)
    print("saved", tag, len(cat["B0"]))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), workers=int(sys.argv[4]), tag=sys.argv[5])
