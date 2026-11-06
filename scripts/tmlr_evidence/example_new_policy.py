"""Minimal example: value a new policy, in the original world and in a new one.

A policy is any callable of the observable loan-month state that returns
``(channel, discount)`` or ``None`` (``None`` keeps the incumbent + ε action).
A world is a config: here world A of the revision campaign, and a variant
that sets ``oracle.channel_effects`` (all contact channels equally effective).

The policy and the incumbent are simulated on the same independent population
replicates (same regional shocks as the world's seed, a population disjoint
from the logs). Within a replicate the two share population and per-(loan,
month) draws, so their per-loan difference gives a precise paired gap.

Usage::

    python scripts/tmlr_evidence/example_new_policy.py --borrowers 50000
"""

from __future__ import annotations

import argparse
import copy
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from collection_simulator.config import load_config  # noqa: E402
from collection_simulator.generator import simulate_cohort  # noqa: E402


def phone_for_large_balances(*, month, state, days_in_credito_em_liquidacao,
                             outstanding_balance, **_):
    """Month 0, explorable loans: phone + 7.5% above 20,000; SMS + 12.5% below."""
    if month != 0 or state not in ("delinquent", "credito_em_liquidacao"):
        return None
    if days_in_credito_em_liquidacao > 180:
        return None
    return ("phone", 0.075) if outstanding_balance > 20_000 else ("sms", 0.125)


def value(cfg: dict, policy, replicates: list[int], batch: int) -> dict:
    gaps, pol_means, inc_means, ses = [], [], [], []
    for r in replicates:
        inc, _ = simulate_cohort(cfg, policy=None, replicate=r, batch_size=batch)
        new, _ = simulate_cohort(cfg, policy=policy, replicate=r, batch_size=batch)
        assert np.array_equal(inc["loan_id"].to_numpy(), new["loan_id"].to_numpy())
        d = new["reward"].to_numpy() - inc["reward"].to_numpy()
        gaps.append(d.mean())
        ses.append(d.std(ddof=1) / math.sqrt(len(d)))
        pol_means.append(new["reward"].mean())
        inc_means.append(inc["reward"].mean())
    R = len(replicates)
    return {"policy": float(np.mean(pol_means)), "incumbent": float(np.mean(inc_means)),
            "gap": float(np.mean(gaps)), "gap_se": float(math.sqrt(np.sum(np.square(ses))) / R)}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--borrowers", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=9501)
    ap.add_argument("--replicates", type=int, nargs="+", default=[2, 3])
    a = ap.parse_args(argv)
    world_a = load_config(REPO / "configs" / "tmlr" / "world_a_on.yaml")
    world_a["seed"], world_a["population"]["borrowers"] = a.seed, a.borrowers
    flat = copy.deepcopy(world_a)
    flat["oracle"]["channel_effects"] = {
        "none": -0.85, "sms": 0.30, "app_message": 0.30, "phone": 0.30, "field_visit": 0.30}
    for name, cfg in (("world A", world_a), ("equal-channel variant", flat)):
        v = value(cfg, phone_for_large_balances, a.replicates, batch=min(50_000, a.borrowers))
        print(f"{name:22s} policy {v['policy']:8.2f}  incumbent {v['incumbent']:8.2f}  "
              f"gap {v['gap']:+7.2f} ± {v['gap_se']:.2f} US$/decision (paired MC SE)")


if __name__ == "__main__":
    main()
