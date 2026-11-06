"""Run the frozen-grid estimator panel for one (cell config, seed).

Logged world → twin worlds (π_far, π_near, policy-injected, same seed) →
month-0 cohort logs → five-estimator panel graded against twin truth →
one provenance-stamped JSON.

Archived-campaign driver. The archived results were generated with generator
version 1 (one shared random stream). Generator version 2 (keyed streams) gives
a different world for the same config and seed, so this driver no longer
reproduces the archived numbers: regenerate them from the version-1 source
snapshot, or reanalyse the stored JSONs (README, "Archived campaign").
The twin run shares the logged population (fully with version 2, in the first
batch only with version 1); its cohort mean is one Monte-Carlo realisation of
the target's value, not an exact truth. ``scripts/tmlr_campaign.py`` grades
against independent population replicates with reported Monte-Carlo error.

Usage:
    python scripts/run_panel.py --config configs/eps_floor_1m.yaml \
        --seed 101 --out results/cell03 [--borrowers 50000] [--n-boot 200] \
        [--keep-dbs] [--no-enforce-gates]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from collection_simulator.config import load_config  # noqa: E402
from collection_simulator.generator import generate  # noqa: E402
from ope_bench.panel import (  # noqa: E402
    PI_FAR,
    PI_NEAR,
    balance_terciles,
    build_logs,
    estimate_panel,
    load_cohort,
    policy_explorable,
    truth_matrix_from_twin,
)

# Per-run recovery TRIPWIRE (gross-error only): per-seed realized
# rates carry the common regional macro shock, which grows with confounding
# strength and does not average out within a world — re-rolling seeds against a
# tight per-run gate would select calm macro worlds and bias exactly the
# high-confounding cells. The ±0.3pp comparability gate applies to the CELL
# MEAN across the 5 paired seeds, enforced at aggregation.
GATE_RECOVERY_RANGE = (0.030, 0.055)


def _annual_recovery(db_path: Path) -> float:
    import duckdb

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        return float(
            con.execute(
                "SELECT AVG(paid) FROM (SELECT loan_id, "
                "MAX(CASE WHEN recovered AND month < 12 THEN 1 ELSE 0 END) AS paid "
                "FROM monthly_panel GROUP BY loan_id)"
            ).fetchone()[0]
        )
    finally:
        con.close()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def run_cell(
    config_path: Path,
    seed: int,
    out_dir: Path,
    borrowers: int | None = None,
    n_boot: int = 200,
    keep_dbs: bool = False,
    enforce_gates: bool = True,
    batch_size: int | None = 100_000,
) -> dict:
    t0 = time.time()
    cfg = load_config(config_path)
    cfg["seed"] = int(seed)
    if borrowers is not None:
        cfg["population"]["borrowers"] = int(borrowers)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── logged world ────────────────────────────────────────────────
    logged_dir = out_dir / f"logged_seed{seed}"
    logged = generate(cfg, logged_dir, batch_size=batch_size)
    cohort = load_cohort(logged.db_path)
    # estimand = the month-0 EXPLORABLE sub-cohort: the one-shot
    # targets are deterministic there; elsewhere π_e ≡ incumbent by design
    cohort = cohort[policy_explorable(cohort["state"], cohort["liq_days"])].reset_index(drop=True)
    terciles = balance_terciles(cohort)
    logs = build_logs(cohort, terciles)
    eps_cfg = float((cfg["actions"].get("exploration") or {}).get("epsilon", 0.0))

    # ── sanity gates ────────────────────────────────────────────────
    recovery12 = _annual_recovery(logged.db_path)
    n_expl = len(cohort)
    eps_observed = float(cohort["is_exploration"].mean()) if n_expl else 0.0
    eps_tol = max(0.25 * eps_cfg, 3.0 * np.sqrt(max(eps_cfg * (1 - eps_cfg), 1e-12) / max(n_expl, 1)))
    gates = {
        "recovery_12m": recovery12,
        "recovery_gate_ok": bool(GATE_RECOVERY_RANGE[0] <= recovery12 <= GATE_RECOVERY_RANGE[1]),
        "epsilon_config": eps_cfg,
        "epsilon_observed_month0": eps_observed,
        "epsilon_gate_ok": bool(abs(eps_observed - eps_cfg) <= float(eps_tol)),
    }
    if enforce_gates and not (gates["recovery_gate_ok"] and gates["epsilon_gate_ok"]):
        raise SystemExit(f"sanity gate failed: {gates} — re-tune the cell, never the results")

    # ── targets: twin truth + estimator panel ──────────────────────
    pi_b_realized = float(np.mean(logs["reward"]))
    results: dict = {}
    truths: dict[str, float] = {}
    for target in (PI_FAR, PI_NEAR):
        twin_dir = out_dir / f"twin_{target.name}_seed{seed}"
        twin = generate(cfg, twin_dir, batch_size=batch_size, policy=target.generator_policy())
        twin_cohort = load_cohort(twin.db_path)
        twin_cohort = twin_cohort[
            policy_explorable(twin_cohort["state"], twin_cohort["liq_days"])
        ].reset_index(drop=True)
        truth = float(twin_cohort["reward"].to_numpy(np.float64).mean())
        tmat = truth_matrix_from_twin(twin_cohort, terciles, target)
        est = estimate_panel(logs, target, tmat, n_boot=n_boot, seed=seed)
        for name, e in est.items():
            if e["value"] is None:  # pilot estimators at eps = 0
                e["error"] = None
                e["ci_covers_truth"] = None
                continue
            e["error"] = e["value"] - truth
            e["ci_covers_truth"] = bool(e["ci_low"] <= truth <= e["ci_high"])
        truths[target.name] = truth
        results[target.name] = {"truth": truth, "estimators": est}
        if not keep_dbs:
            shutil.rmtree(twin_dir, ignore_errors=True)

    # ── policy selection (π_b realized vs the two challengers) ─────
    true_vals = {"pi_b": pi_b_realized, **truths}
    true_best = max(true_vals, key=true_vals.get)
    selection: dict = {"true_ranking": sorted(true_vals, key=true_vals.get, reverse=True)}
    for name in results[PI_FAR.name]["estimators"]:
        v_far = results[PI_FAR.name]["estimators"][name]["value"]
        v_near = results[PI_NEAR.name]["estimators"][name]["value"]
        if v_far is None or v_near is None:  # pilot estimators at eps = 0
            selection[name] = {"undefined": "no randomized support (eps = 0)"}
            continue
        est_vals = {"pi_b": pi_b_realized, PI_FAR.name: v_far, PI_NEAR.name: v_near}
        picked = max(est_vals, key=est_vals.get)
        selection[name] = {
            "picked": picked,
            "top1_correct": picked == true_best,
            "regret": true_vals[true_best] - true_vals[picked],
        }

    if not keep_dbs:
        shutil.rmtree(logged_dir, ignore_errors=True)

    report = {
        "provenance": {
            "config_path": str(config_path),
            "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest(),
            "seed": seed,
            "borrowers": int(cfg["population"]["borrowers"]),
            "repo_commit": _git_commit(),
            "n_boot": n_boot,
            "wall_seconds": round(time.time() - t0, 1),
        },
        "gates": gates,
        "pi_b_realized": pi_b_realized,
        "targets": results,
        "selection": selection,
    }
    out_path = out_dir / f"panel_seed{seed}.json"
    out_path.write_text(json.dumps(report, indent=2))
    return report


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--borrowers", type=int, default=None)
    ap.add_argument("--n-boot", type=int, default=200)
    ap.add_argument("--batch-size", type=int, default=100_000)
    ap.add_argument("--keep-dbs", action="store_true")
    ap.add_argument("--no-enforce-gates", action="store_true")
    a = ap.parse_args(argv)
    report = run_cell(
        a.config, a.seed, a.out,
        borrowers=a.borrowers, n_boot=a.n_boot,
        keep_dbs=a.keep_dbs, enforce_gates=not a.no_enforce_gates,
        batch_size=a.batch_size,
    )
    print(json.dumps({"gates": report["gates"], "pi_b_realized": report["pi_b_realized"],
                      "truths": {k: v["truth"] for k, v in report["targets"].items()},
                      "wall_seconds": report["provenance"]["wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
