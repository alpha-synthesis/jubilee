"""Post hoc sensitivity of the exploration effect to the reward's accounting.

Companion to ``scripts/exploration_effect.py`` (whose primary result uses the
benchmark reward). For the same pairs, it re-simulates both arms and keeps the
per-(loan, month) records that ``simulate_cohort`` discards, to value each
cohort loan three ways:

* ``benchmark``: 1{recovery in months 0..h-1} × B0 × (1 − month-0 discount),
  the benchmark's convention (must reproduce the main run exactly);
* ``recovery_month_discount``: 1{recovery in months 0..h-1} × B0 ×
  (1 − discount offered in the month of the first recovery);
* ``cash``: the amounts actually collected in months 0..h-1 (settlement ×
  paid share, after balance growth; several recoveries add up).

The cohort loop mirrors ``simulate_cohort`` (same population, streams, cohort
gate and loan numbering) and calls the generator's own internal functions; the
simulator is not changed. Signed effect per pair: Δ = V(ε = 0) − V(ε).

Usage::

    P=<sensitivity protocol json>
    python scripts/exploration_effect_accounting.py run       --protocol $P --workers 40
    python scripts/exploration_effect_accounting.py aggregate --protocol $P --dest <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import exploration_effect as ee  # noqa: E402
import tmlr_campaign as tc  # noqa: E402

from collection_simulator import generator as gen  # noqa: E402

ACCOUNTINGS = ("benchmark", "recovery_month_discount", "cash")
COHORT_STATES = ("delinquent", "credito_em_liquidacao")
COHORT_MAX_LIQ_DAYS = 180


def cohort_accounting(config: dict, replicate: int, batch_size: int, horizon: int) -> dict:
    """Per cohort loan: month-0 action, recovery, discounts and cash in the window."""
    gen._validate_assignment(config)
    gen._validate_channel_effects(config)
    h = int(horizon)
    total = int(config["population"]["borrowers"])
    regional = gen.regional_shocks(config)
    parts: list[dict] = []
    loan_next = 1
    for batch_idx, start, n in gen._batches(total, int(batch_size)):
        borrowers, hidden, loans = gen._generate_population(
            config, replicate, batch_idx, n, start, loan_next, regional)
        loan_next += len(loans)
        state0 = loans["initial_status"].to_numpy(dtype=object)
        liq0 = loans["days_in_credito_em_liquidacao"].to_numpy(dtype=np.int64)
        in_c = np.isin(state0, list(COHORT_STATES))
        in_c &= ~((state0 == "credito_em_liquidacao") & (liq0 > COHORT_MAX_LIQ_DAYS))
        rec = gen._simulate_batch(config, borrowers, hidden, loans, replicate, batch_idx, None,
                                  n_months=h, loan_mask=in_c)
        sel = np.flatnonzero(in_c)
        first = rec["first_recovery_month"][sel]
        paid = (first >= 0) & (first < h)
        disc = rec["discount"][sel][:, :h]
        idx = np.where(paid, first, 0)
        parts.append({
            "loan_id": loans["loan_id"].to_numpy()[sel],
            "start_balance": loans["outstanding_balance"].to_numpy(np.float64)[sel],
            "paid": paid, "first": np.where(paid, first, -1),
            "d0": rec["discount0"][sel].astype(np.float64),
            "d_first": np.where(paid, disc[np.arange(len(sel)), idx], np.nan),
            "cash": rec["recovered_amount"][sel][:, :h].sum(axis=1),
            "channel0": np.array([str(c) for c in rec["channel0"][sel]], dtype=object),
            "explored0": rec["is_exploration0"][sel].astype(bool),
            "explored": rec["is_exploration"][sel][:, :h],
            "alive": rec["alive"][sel][:, :h],
            "disc": disc,
        })
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    b0 = out["start_balance"]
    out["value_benchmark"] = out["paid"] * b0 * (1.0 - out["d0"])
    out["value_recovery_month_discount"] = np.where(out["paid"],
                                                    b0 * (1.0 - out["d_first"]), 0.0)
    out["value_cash"] = out["cash"]
    return out


def _paired(v0: np.ndarray, ve: np.ndarray, explored0: np.ndarray) -> dict:
    d = v0 - ve
    n = len(d)
    return {"value_eps0": float(v0.mean()), "value_eps": float(ve.mean()),
            "delta": float(d.mean()), "se_delta": float(d.std(ddof=1) / math.sqrt(n)),
            "relative_delta": float(d.mean() / v0.mean()),
            "delta_from_month0_explored": float((d * explored0).sum() / n),
            "delta_from_other_loans": float((d * ~explored0).sum() / n)}


def run_pair(proto: dict, world: str, seed: int, replicate: int) -> dict:
    t0, c0 = time.time(), time.process_time()
    cfg_e = ee.world_config(proto, world, seed)
    cfg_0 = ee.world_config(proto, world, seed, epsilon=0.0)
    if ee.config_difference(cfg_e, cfg_0) != ["actions.exploration.epsilon"]:
        raise AssertionError("arms differ beyond ε")
    a_e = cohort_accounting(cfg_e, replicate, proto["batch_size"], proto["horizon"])
    a_0 = cohort_accounting(cfg_0, replicate, proto["batch_size"], proto["horizon"])
    for key in ("loan_id", "start_balance"):
        if not np.array_equal(a_e[key], a_0[key]):
            raise AssertionError(f"arms differ in {key}")
    if a_0["explored"].any():
        raise AssertionError("the ε = 0 arm explored")
    differs0 = (a_e["channel0"] != a_0["channel0"]) | (a_e["d0"] != a_0["d0"])
    if bool((differs0 & ~a_e["explored0"]).any()):
        raise AssertionError("a month-0 action differs on a loan the ε arm did not explore")
    explored0 = a_e["explored0"]
    acc = {k: _paired(a_0[f"value_{k}"], a_e[f"value_{k}"], explored0) for k in ACCOUNTINGS}
    # consistency with the main run (benchmark accounting, same pair)
    main = json.loads(ee.pair_path(proto["main_protocol"], world, seed, replicate)
                      .read_text())["summary"]
    consistency = {"abs_diff_value_eps0": abs(acc["benchmark"]["value_eps0"] - main["value_eps0"]),
                   "abs_diff_value_eps": abs(acc["benchmark"]["value_eps"] - main["value_eps"])}
    consistency["ok"] = bool(max(consistency.values()) <= 1e-9)
    later = a_e["explored"][:, 1:] & a_0["alive"][:, 1:]
    contact0 = later & (a_0["disc"][:, 1:] > 0)
    paid_e, paid_0 = a_e["paid"], a_0["paid"]
    desc = {
        "recoveries_at_month0_share_eps0": float((a_0["first"] == 0).sum() / max(paid_0.sum(), 1)),
        "recoveries_at_month0_share_eps": float((a_e["first"] == 0).sum() / max(paid_e.sum(), 1)),
        "mean_d0_recovered_eps0": float(a_0["d0"][paid_0].mean()),
        "mean_d0_recovered_eps": float(a_e["d0"][paid_e].mean()),
        "mean_d_first_recovered_eps0": float(np.nanmean(a_0["d_first"][paid_0])),
        "mean_d_first_recovered_eps": float(np.nanmean(a_e["d_first"][paid_e])),
        "mean_d0_explored_loans_eps": float(a_e["d0"][explored0].mean()),
        "mean_d0_explored_loans_eps0": float(a_0["d0"][explored0].mean()),
        "later_explored_slots_share": float(a_e["explored"][:, 1:].sum()
                                            / max(a_e["alive"][:, 1:].sum(), 1)),
        "later_explored_discount_mean": float(a_e["disc"][:, 1:][later].mean()),
        "incumbent_discount_same_slots_mean": float(a_0["disc"][:, 1:][later].mean()),
        "incumbent_discount_same_slots_contacted_mean": float(a_0["disc"][:, 1:][contact0].mean()),
        "cash_mean_eps0": float(a_0["cash"].mean()), "cash_mean_eps": float(a_e["cash"].mean()),
    }
    out = {"protocol": proto["name"], "protocol_sha256": proto["_sha256"], "world": world,
           "seed": seed, "replicate": replicate, "code": proto["_code"],
           "driver_sha256": tc._sha256(Path(__file__)),
           "main_driver_sha256": tc._sha256(REPO / "scripts" / "exploration_effect.py"),
           "environment": tc.environment(), "n_cohort": int(len(explored0)),
           "accountings": acc, "consistency_with_main": consistency, "descriptive": desc,
           "timing": {"wall_seconds": round(time.time() - t0, 2),
                      "cpu_seconds": round(time.process_time() - c0, 2), **tc._usage()}}
    p = REPO / proto["out_dir"] / world / f"seed{seed}_r{replicate}_accounting.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tc._write_json(out, p)
    return out


def _worker(args):
    proto, job = args
    t0 = time.time()
    try:
        out = run_pair(proto, *job)
        return {"job": job, "ok": True, "wall_seconds": round(time.time() - t0, 1),
                "consistency_ok": out["consistency_with_main"]["ok"], **tc._usage()}
    except Exception as exc:  # recorded, never swallowed
        return {"job": job, "ok": False, "error": repr(exc), "trace": traceback.format_exc()}


def load_protocol(path: Path) -> dict:
    raw = Path(path).read_bytes()
    proto = json.loads(raw)
    proto["_path"], proto["_sha256"] = str(path), hashlib.sha256(raw).hexdigest()
    proto["main_protocol"] = ee.load_protocol(REPO / proto["main_protocol_path"])
    for k in ("worlds", "seeds", "replicates", "borrowers", "batch_size", "horizon", "epsilon",
              "config_sha256"):
        proto[k] = proto["main_protocol"][k]
    return proto


def aggregate(proto: dict, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for world, seed, r in ee.pairs(proto):
        p = REPO / proto["out_dir"] / world / f"seed{seed}_r{r}_accounting.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        for k, a in rec["accountings"].items():
            rows.append({"world": world, "seed": seed, "replicate": r, "accounting": k, **a,
                         "consistency_ok": rec["consistency_with_main"]["ok"],
                         **rec["descriptive"], "cpu_seconds": rec["timing"]["cpu_seconds"]})
    pr = pd.DataFrame(rows)
    pr.to_csv(dest / "accounting_pairs.csv", index=False)
    out = []
    for (world, k), g in pr.groupby(["world", "accounting"], sort=True):
        row = {"world": world, "accounting": k, "n_seeds": len(g),
               "mean_value_eps0": float(g["value_eps0"].mean()),
               "mean_value_eps": float(g["value_eps"].mean()),
               "mc_se_per_seed_rms": float(np.sqrt((g["se_delta"] ** 2).mean())),
               "seeds_with_positive_delta": int((g["delta"] > 0).sum())}
        for col in ("delta", "relative_delta", "delta_from_month0_explored",
                    "delta_from_other_loans"):
            c = ee._ci(g[col].to_numpy())
            row.update({f"{col}_mean": c["mean"], f"{col}_ci95_low": c["ci95_low"],
                        f"{col}_ci95_high": c["ci95_high"]})
        out.append(row)
    bw = pd.DataFrame(out)
    bw.to_csv(dest / "accounting_by_world.csv", index=False)
    desc_cols = [c for c in pr.columns if c.startswith(("recoveries_", "mean_d", "later_",
                                                         "incumbent_", "cash_mean"))]
    dsc = pr[pr.accounting == "benchmark"].groupby("world")[desc_cols].agg(["min", "max"])
    dsc.to_csv(dest / "accounting_descriptive.csv")
    f2 = "{:+.2f}"
    md = ["# Exploration effect under three reward accountings (post hoc sensitivity)", "",
          "Δ = V(ε = 0) − V(ε = 0.08), US$ per decision on the month-0 explorable cohort; "
          "positive = exploring loses value. 95% t intervals over seeds. The benchmark "
          "accounting is the primary definition; the other two are post hoc.", "",
          ee._md_table(bw, ["world", "accounting", "mean_value_eps0", "mean_value_eps",
                            "delta_mean", "delta_ci95_low", "delta_ci95_high",
                            "relative_delta_mean", "delta_from_month0_explored_mean",
                            "delta_from_other_loans_mean", "seeds_with_positive_delta"],
                       {"mean_value_eps0": "{:.2f}", "mean_value_eps": "{:.2f}",
                        "delta_mean": f2, "delta_ci95_low": f2, "delta_ci95_high": f2,
                        "relative_delta_mean": "{:+.3%}",
                        "delta_from_month0_explored_mean": f2,
                        "delta_from_other_loans_mean": f2})]
    (dest / "accounting_tables.md").write_text("\n".join(md) + "\n")
    manifest = {"protocol": proto["_path"], "protocol_sha256": proto["_sha256"],
                "pairs_found": int(pr[["world", "seed"]].drop_duplicates().shape[0]),
                "consistency_failures": int((~pr["consistency_ok"]).sum()),
                "outputs": sorted(p.name for p in dest.glob("accounting*"))}
    tc._write_json(manifest, dest / "accounting_manifest.json")
    return manifest


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("run", "aggregate"))
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--dest", type=Path, default=None)
    a = ap.parse_args(argv)
    proto = load_protocol(a.protocol)
    proto["_code"] = tc.code_fingerprint()
    proto["main_protocol"]["_code"] = proto["_code"]
    if a.command == "run":
        todo = [p for p in ee.pairs(proto)
                if not (REPO / proto["out_dir"] / p[0]
                        / f"seed{p[1]}_r{p[2]}_accounting.json").exists()]
        ee._log(proto, {"event": "accounting_start", "todo": len(todo), "workers": a.workers})
        failures = 0
        with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
            for res in pool.imap_unordered(_worker, [(proto, j) for j in todo]):
                ee._log(proto, res)
                failures += 0 if res["ok"] else 1
                print(json.dumps({k: v for k, v in res.items() if k != "trace"}), flush=True)
        ee._log(proto, {"event": "accounting_end", "failures": failures})
        sys.exit(1 if failures else 0)
    print(json.dumps(aggregate(proto, a.dest), indent=2, default=tc._json_default))


if __name__ == "__main__":
    main()
