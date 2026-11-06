"""Design-unbiasedness check of the pilot estimators in one world.

Holds a world (config + seed, hence its regional shocks) fixed and simulates
the behaviour policy on many independent population replicates. For each
replicate it computes pilot-IS (Horvitz–Thompson over the ε-explored rows of
the target's cell, known propensity ε/44) and the anchors' mean reward. Their
average over replicates must match the target's reference value (from the
run's reference replicates) if the generator's exploration is independent of
outcomes. A coupled control re-simulates the target on replicate 0 itself
and compares its mean reward over the anchor loans with its mean over all
cohort loans (they differ only by sampling if the anchors are a random subset).

Usage::

    python scripts/tmlr_evidence/pilot_unbiasedness_check.py --config CFG --seed S \
        --replicates 10 109 --reference-json RUN/reference_r2.json ... --out OUT.json --workers 40
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
from ope_bench.panel import PI_FAR, PI_NEAR, PI_STAGE, action_id, balance_terciles, context_ids  # noqa: E402
from ope_bench.value_export import U_CELL  # noqa: E402

TARGETS = (PI_FAR, PI_NEAR, PI_STAGE)


def _one(args):
    cfg, r, batch = args
    coh, _ = simulate_cohort(cfg, policy=None, replicate=r, batch_size=batch)
    ter = balance_terciles(coh)
    ctx = context_ids(coh, ter)
    act = action_id(coh["channel_logged"], coh["discount_logged"])
    reward = coh["reward"].to_numpy(np.float64)
    expl = coh["is_exploration"].to_numpy(bool)
    eps = coh["exploration_epsilon"].to_numpy(np.float64)
    out = {"replicate": r, "n": len(coh), "behaviour_mean": float(reward.mean())}
    for t in TARGETS:
        anc = expl & (act == t.actions_per_context()[ctx])
        w = np.where(anc, 1.0 / np.maximum(eps, 1e-12) / U_CELL, 0.0)
        out[t.name] = {"pilot_is": float((w * reward).mean()), "n_anchor": int(anc.sum()),
                       "anchor_mean": float(reward[anc].mean()) if anc.any() else None}
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--borrowers", type=int, default=1_000_000)
    ap.add_argument("--batch-size", type=int, default=50_000)
    ap.add_argument("--replicates", type=int, nargs=2, required=True, metavar=("FIRST", "LAST"))
    ap.add_argument("--reference-json", type=Path, nargs="+", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    cfg["seed"], cfg["population"]["borrowers"] = a.seed, a.borrowers
    reps = list(range(a.replicates[0], a.replicates[1] + 1))
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
        res = pool.map(_one, [(copy.deepcopy(cfg), r, a.batch_size) for r in reps])
    refs = [json.loads(p.read_text())["means"] for p in a.reference_json]
    summary = {}
    for t in TARGETS:
        x = np.array([r[t.name]["pilot_is"] for r in res])
        ref = float(np.mean([m[t.name] for m in refs]))
        summary[t.name] = {"reference": ref, "mean_pilot_is": float(x.mean()),
                           "se": float(x.std(ddof=1) / np.sqrt(len(x))),
                           "z_vs_reference": float((x.mean() - ref) / (x.std(ddof=1) / np.sqrt(len(x)))),
                           "sd_per_world": float(x.std(ddof=1))}
    b = np.array([r["behaviour_mean"] for r in res])
    refb = float(np.mean([m["pi_b"] for m in refs]))
    summary["pi_b_logged_mean"] = {"reference": refb, "mean": float(b.mean()),
                                   "se": float(b.std(ddof=1) / np.sqrt(len(b)))}
    # coupled control on replicate 0: target world vs the logged anchors (same population/draws)
    logs, _ = simulate_cohort(cfg, policy=None, replicate=0, batch_size=a.batch_size)
    ter = balance_terciles(logs)
    ctx = context_ids(logs, ter)
    act = action_id(logs["channel_logged"], logs["discount_logged"])
    expl = logs["is_exploration"].to_numpy(bool)
    coupled = {}
    for t in TARGETS:
        tw, _ = simulate_cohort(cfg, policy=t.generator_policy(), replicate=0, batch_size=a.batch_size)
        assert np.array_equal(tw["loan_id"].to_numpy(), logs["loan_id"].to_numpy())
        anc = expl & (act == t.actions_per_context()[ctx])
        rt = tw["reward"].to_numpy(np.float64)
        coupled[t.name] = {"target_world_mean_all": float(rt.mean()),
                           "target_world_mean_on_anchors": float(rt[anc].mean()),
                           "logged_mean_on_anchors": float(logs["reward"].to_numpy()[anc].mean()),
                           "n_anchor": int(anc.sum())}
    rec = {"config": str(a.config), "seed": a.seed, "replicates": [reps[0], reps[-1]],
           "summary": summary, "coupled_replicate0": coupled, "per_replicate": res}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2))
    print(json.dumps({"summary": summary, "coupled_replicate0": coupled}, indent=2))


if __name__ == "__main__":
    main()
