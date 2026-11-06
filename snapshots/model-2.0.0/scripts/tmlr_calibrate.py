"""Development-only hazard calibration of one world against another.

Sets ``oracle.target_monthly_recovery_rate`` of the CANDIDATE config so that its
12-month recovery rate (all loans, months 0-11) matches the REFERENCE config's,
averaged over development seeds. Both worlds are simulated on the same seeds,
hence the same populations and regional shocks, so the comparison is paired.
Recovery is rare, so the rate is close to proportional to the hazard; each
iteration rescales the hazard by the ratio of the two mean rates.

Usage::

    python scripts/tmlr_calibrate.py --reference configs/tmlr/world_a_on.yaml \
        --candidate configs/tmlr/world_b_on.yaml --seeds 9001 9002 9003 9004 \
        --borrowers 250000 --out calibration.json [--workers 8]

Prints and records the hazards and rates; it never edits a config file.
"""

from __future__ import annotations

import argparse
import copy
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from collection_simulator.config import load_config  # noqa: E402
from collection_simulator.generator import GENERATOR_VERSION, simulate_cohort  # noqa: E402


def _rate(args) -> float:
    cfg, seed, borrowers, batch = args
    cfg = copy.deepcopy(cfg)
    cfg["seed"] = int(seed)
    cfg["population"]["borrowers"] = int(borrowers)
    _, meta = simulate_cohort(cfg, batch_size=batch, months=12, simulate_all_loans=True)
    return float(meta["recovery_12m"])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--seeds", required=True, type=int, nargs="+")
    ap.add_argument("--borrowers", type=int, default=250_000)
    ap.add_argument("--batch-size", type=int, default=50_000)
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    t0 = time.time()
    ref_cfg, cand_cfg = load_config(a.reference), load_config(a.candidate)
    with mp.get_context("fork").Pool(a.workers) as pool:
        ref_rates = pool.map(_rate, [(ref_cfg, s, a.borrowers, a.batch_size) for s in a.seeds])
        target = sum(ref_rates) / len(ref_rates)
        hazard = float(cand_cfg["oracle"]["target_monthly_recovery_rate"])
        history = []
        for it in range(a.iterations):
            cfg = copy.deepcopy(cand_cfg)
            cfg["oracle"]["target_monthly_recovery_rate"] = hazard
            rates = pool.map(_rate, [(cfg, s, a.borrowers, a.batch_size) for s in a.seeds])
            mean = sum(rates) / len(rates)
            history.append({"iteration": it, "hazard": hazard, "rates": rates, "mean_rate": mean})
            print(json.dumps(history[-1]), flush=True)
            hazard = hazard * target / mean
    record = {
        "generator_version": GENERATOR_VERSION,
        "reference_config": str(a.reference), "candidate_config": str(a.candidate),
        "seeds": a.seeds, "borrowers": a.borrowers, "batch_size": a.batch_size,
        "reference_rates": ref_rates, "target_mean_rate": target,
        "history": history,
        "selected_hazard": round(history[-1]["hazard"], 6),
        "selected_mean_rate": history[-1]["mean_rate"],
        "wall_seconds": round(time.time() - t0, 1),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(record, indent=2))
    print(json.dumps({k: record[k] for k in ("target_mean_rate", "selected_hazard",
                                             "selected_mean_rate", "wall_seconds")}))


if __name__ == "__main__":
    main()
