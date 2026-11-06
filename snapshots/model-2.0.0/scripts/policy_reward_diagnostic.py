"""Do the campaign candidates' ranking and gaps depend on the reward?

Exploratory diagnostic (no estimator is evaluated). For each world and seed,
the four campaign candidates (``scripts/tmlr_campaign.py`` CANDIDATES: the
incumbent with ε-exploration, and three month-0 challengers that hand over to
the incumbent) are simulated on the same population and draws, and every
cohort loan is valued three ways on the same trajectory:

* ``benchmark``: 1{first recovery in months 0..h-1} × B0 × (1 − month-0 discount);
* ``first_recovery_discount``: 1{first recovery in months 0..h-1} × B0 ×
  (1 − discount offered in the month of the first recovery);
* ``cash``: the ``recovered_amount`` recorded by the simulator in months
  0..h-1 (partial payments and the simulator's balance rules included).

Per world, seed and objective it reports each candidate's value and
Monte-Carlo SE, the six paired gaps with SE from the per-loan covariance, the
ranking with its resolved pairs, and whether the winner changes between
objectives. The cohort loop generalises
``scripts/exploration_effect_accounting.py`` to take a policy; it calls the
generator's own internal functions and changes neither the simulator nor the
candidates.

Usage::

    P=<protocol json>
    python scripts/policy_reward_diagnostic.py run       --protocol $P --workers 10
    python scripts/policy_reward_diagnostic.py aggregate --protocol $P --dest <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
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
import tmlr_campaign as tc  # noqa: E402  (also puts src/ on the path)

from collection_simulator import generator as gen  # noqa: E402
from collection_simulator.config import load_config  # noqa: E402

OBJECTIVES = ("benchmark", "first_recovery_discount", "cash")
CANDIDATES = ("pi_b", "pi_near", "pi_far", "pi_stage")
COHORT_STATES = ("delinquent", "credito_em_liquidacao")
COHORT_MAX_LIQ_DAYS = 180
Z = 1.96


# ── simulation ─────────────────────────────────────────────────────────────
def policy_of(name: str):
    pol = tc.CANDIDATES[name]
    return None if pol is None else pol.generator_policy()


def world_config(proto: dict, world: str, seed: int) -> dict:
    cfg = load_config(REPO / proto["worlds"][world])
    cfg["seed"] = int(seed)
    cfg["population"]["borrowers"] = int(proto["borrowers"])
    eps = float(cfg["actions"]["exploration"]["epsilon"])
    if abs(eps - float(proto["epsilon"])) > 1e-12:
        raise ValueError(f"{world}: configured ε {eps} != protocol ε {proto['epsilon']}")
    return cfg


def cohort_accounting(config: dict, replicate: int, batch_size: int, horizon: int,
                      policy=None) -> dict:
    """Per cohort loan, under ``policy``: month-0 state and action, first
    recovery, and the three valuations (mirrors ``simulate_cohort``)."""
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
        rec = gen._simulate_batch(config, borrowers, hidden, loans, replicate, batch_idx,
                                  policy, n_months=h, loan_mask=in_c)
        sel = np.flatnonzero(in_c)
        first = rec["first_recovery_month"][sel]
        paid = (first >= 0) & (first < h)
        disc = rec["discount"][sel][:, :h]
        idx = np.where(paid, first, 0)
        parts.append({
            "loan_id": loans["loan_id"].to_numpy()[sel],
            "state0": state0[sel], "liq0": liq0[sel],
            "dpd0": loans["days_past_due"].to_numpy(np.int64)[sel],
            "start_balance": loans["outstanding_balance"].to_numpy(np.float64)[sel],
            "paid": paid, "first": np.where(paid, first, -1),
            "d0": rec["discount0"][sel].astype(np.float64),
            "channel0": np.array([str(c) for c in rec["channel0"][sel]], dtype=object),
            "d_first": np.where(paid, disc[np.arange(len(sel)), idx], np.nan),
            "cash": rec["recovered_amount"][sel][:, :h].sum(axis=1),
        })
    out = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    b0 = out["start_balance"]
    out["benchmark"] = out["paid"] * b0 * (1.0 - out["d0"])
    out["first_recovery_discount"] = np.where(out["paid"], b0 * (1.0 - out["d_first"]), 0.0)
    out["cash"] = out["cash"].astype(np.float64)
    return out


ALIGN_KEYS = ("loan_id", "state0", "liq0", "dpd0", "start_balance")


def summarize_objective(values: np.ndarray, names: list[str], z: float = Z) -> dict:
    """``values``: K × n per-loan values of K candidates on the same loans."""
    n = values.shape[1]
    means = values.mean(axis=1)
    cov = np.cov(values, ddof=1) / n  # covariance of the K means
    se = np.sqrt(np.diag(cov))
    gaps = {}
    for i, j in itertools.combinations(range(len(names)), 2):
        g = float(means[i] - means[j])
        s = math.sqrt(max(cov[i, i] + cov[j, j] - 2 * cov[i, j], 0.0))
        gaps[f"{names[i]}-{names[j]}"] = {
            "gap": g, "se": s, "resolved": bool(abs(g) > z * s),
            "se_if_independent": math.sqrt(cov[i, i] + cov[j, j])}
    order = [names[k] for k in np.argsort(-means, kind="stable")]

    def gap(a, b):
        key = f"{a}-{b}" if f"{a}-{b}" in gaps else f"{b}-{a}"
        sign = 1.0 if key == f"{a}-{b}" else -1.0
        return sign * gaps[key]["gap"], gaps[key]["se"]

    top_gap, top_se = gap(order[0], order[1])
    adjacent = [bool(abs(gap(order[k], order[k + 1])[0]) > z * gap(order[k], order[k + 1])[1])
                for k in range(len(order) - 1)]
    return {"values": dict(zip(names, means.tolist(), strict=True)),
            "se": dict(zip(names, se.tolist(), strict=True)),
            "ranking": order, "best": order[0], "runner_up": order[1],
            "top_gap": top_gap, "top_gap_se": top_se, "top_resolved": bool(top_gap > z * top_se),
            "adjacent_resolved": adjacent, "ranking_fully_resolved": all(adjacent),
            "gaps": gaps}


def winner_change(a: dict, b: dict, z: float = Z) -> str:
    """Compare winners of objective a (reference) and b on the same candidates:
    'same', 'clear' (each winner resolved better under its own objective), or
    'unresolved'."""
    wa, wb = a["best"], b["best"]
    if wa == wb:
        return "same"

    def better(summary, x, y):
        key = f"{x}-{y}" if f"{x}-{y}" in summary["gaps"] else f"{y}-{x}"
        g = summary["gaps"][key]
        d = g["gap"] if key == f"{x}-{y}" else -g["gap"]
        return d > z * g["se"]

    return "clear" if better(a, wa, wb) and better(b, wb, wa) else "unresolved"


def validation_reference(proto: dict, world: str, seed: int) -> dict:
    ref = proto.get("validation_reference")
    if not ref:
        return {"checked": False}
    p = REPO / ref["dir"] / world / f"seed{seed}_r{proto['replicate']}_pair.json"
    if not p.exists():
        return {"checked": False}
    rec = json.loads(p.read_text())["summary"]
    return {"checked": True, "path": str(p.relative_to(REPO)), "sha256": tc._sha256(p),
            "value": float(rec["value_eps"]), "n_cohort": int(rec["n_cohort"])}


def run_world_seed(proto: dict, world: str, seed: int) -> dict:
    cfg = world_config(proto, world, seed)
    base = None
    per_obj = {o: [] for o in OBJECTIVES}
    desc, timing = {}, {}
    for name in CANDIDATES:
        t0, c0 = time.time(), time.process_time()
        a = cohort_accounting(cfg, proto["replicate"], proto["batch_size"], proto["horizon"],
                              policy_of(name))
        timing[name] = {"wall_seconds": round(time.time() - t0, 2),
                        "cpu_seconds": round(time.process_time() - c0, 2)}
        if base is None:
            base = {k: a[k] for k in ALIGN_KEYS}
        else:
            for k in ALIGN_KEYS:
                if not np.array_equal(base[k], a[k]):
                    raise AssertionError(f"{name}: cohort column {k!r} differs from pi_b")
        if (a["cash"] < 0).any() or (a["cash"][~a["paid"]] != 0).any():
            raise AssertionError(f"{name}: cash negative or nonzero without recovery")
        for o in OBJECTIVES:
            per_obj[o].append(a[o])
        paid = a["paid"]
        desc[name] = {"recovery_rate": float(paid.mean()),
                      "recoveries_at_month0_share": float((a["first"] == 0).sum()
                                                          / max(paid.sum(), 1)),
                      "mean_d0_recovered": float(a["d0"][paid].mean()),
                      "mean_d_first_recovered": float(np.nanmean(a["d_first"][paid])),
                      "month0_contact_share": float((a["channel0"] != "none").mean())}
        del a
    names = list(CANDIDATES)
    summaries = {o: summarize_objective(np.vstack(per_obj[o]), names) for o in OBJECTIVES}
    val = validation_reference(proto, world, seed)
    if val["checked"]:
        got = summaries["benchmark"]["values"]["pi_b"]
        val.update({"new_value": got, "new_n_cohort": int(len(base["loan_id"])),
                    "abs_difference": abs(got - val["value"]),
                    "ok": bool(abs(got - val["value"]) <= 1e-9
                               and len(base["loan_id"]) == val["n_cohort"])})
    out = {"protocol": proto["name"], "protocol_sha256": proto["_sha256"], "world": world,
           "seed": seed, "replicate": proto["replicate"], "code": proto["_code"],
           "driver_sha256": tc._sha256(Path(__file__)),
           "generator_version": gen.GENERATOR_VERSION, "rng_scheme": gen.RNG_SCHEME,
           "config_path": proto["worlds"][world],
           "config_file_sha256": tc._sha256(REPO / proto["worlds"][world]),
           "config_effective_sha256": hashlib.sha256(
               json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest(),
           "environment": tc.environment(), "n_cohort": int(len(base["loan_id"])),
           "objectives": summaries,
           "winner_change_vs_benchmark": {o: winner_change(summaries["benchmark"], summaries[o])
                                          for o in OBJECTIVES if o != "benchmark"},
           "descriptive": desc, "validation": val,
           "timing": {"per_candidate": timing, **tc._usage()}}
    p = REPO / proto["out_dir"] / world / f"seed{seed}_r{proto['replicate']}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tc._write_json(out, p)
    return out


def _worker(args):
    proto, job = args
    t0 = time.time()
    try:
        out = run_world_seed(proto, *job)
        return {"job": job, "ok": True, "wall_seconds": round(time.time() - t0, 1),
                "validation_ok": out["validation"].get("ok"), **tc._usage()}
    except Exception as exc:  # recorded, never swallowed
        return {"job": job, "ok": False, "error": repr(exc), "trace": traceback.format_exc()}


def _log(proto: dict, record: dict) -> None:
    path = REPO / proto["out_dir"] / "jobs.log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record},
                            default=tc._json_default) + "\n")


# ── analysis ───────────────────────────────────────────────────────────────
def _t_ci(x: np.ndarray) -> dict:
    from scipy import stats

    x = np.asarray(x, dtype=np.float64)
    k = len(x)
    se = float(x.std(ddof=1) / math.sqrt(k)) if k > 1 else float("nan")
    t = float(stats.t.ppf(0.975, k - 1)) if k > 1 else float("nan")
    return {"mean": float(x.mean()), "sd_between_seeds": float(x.std(ddof=1)) if k > 1 else None,
            "ci95_low": float(x.mean() - t * se), "ci95_high": float(x.mean() + t * se)}


def load_records(proto: dict) -> list[dict]:
    recs = []
    for world in proto["worlds"]:
        for seed in proto["seeds"]:
            p = REPO / proto["out_dir"] / world / f"seed{seed}_r{proto['replicate']}.json"
            if p.exists():
                recs.append(json.loads(p.read_text()))
    return recs


def _md_table(df: pd.DataFrame, cols: list[str], fmt: dict) -> str:
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt.get(c, "{}").format(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def aggregate(proto: dict, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    recs = load_records(proto)
    vals, gaps, ranks, chg = [], [], [], []
    for r in recs:
        for o, s in r["objectives"].items():
            for c in CANDIDATES:
                vals.append({"world": r["world"], "seed": r["seed"], "objective": o,
                             "candidate": c, "value": s["values"][c], "mc_se": s["se"][c],
                             "rank": s["ranking"].index(c) + 1})
            for pair, g in s["gaps"].items():
                gaps.append({"world": r["world"], "seed": r["seed"], "objective": o,
                             "pair": pair, **g})
            ranks.append({"world": r["world"], "seed": r["seed"], "objective": o,
                          "ranking": " > ".join(s["ranking"]), "best": s["best"],
                          "runner_up": s["runner_up"], "top_gap": s["top_gap"],
                          "top_gap_se": s["top_gap_se"], "top_resolved": s["top_resolved"],
                          "ranking_fully_resolved": s["ranking_fully_resolved"],
                          "adjacent_resolved": "/".join("y" if x else "n"
                                                        for x in s["adjacent_resolved"])})
        for o, v in r["winner_change_vs_benchmark"].items():
            chg.append({"world": r["world"], "seed": r["seed"], "objective": o,
                        "benchmark_best": r["objectives"]["benchmark"]["best"],
                        "objective_best": r["objectives"][o]["best"], "winner_change": v})
    vals, gaps, ranks, chg = (pd.DataFrame(x) for x in (vals, gaps, ranks, chg))
    vals.to_csv(dest / "values_by_seed.csv", index=False)
    gaps.to_csv(dest / "gaps_by_seed.csv", index=False)
    ranks.to_csv(dest / "rankings_by_seed.csv", index=False)
    chg.to_csv(dest / "winner_change_by_seed.csv", index=False)
    agg_v, agg_g = [], []
    for (w, o, c), g in vals.groupby(["world", "objective", "candidate"], sort=True):
        ci = _t_ci(g["value"].to_numpy())
        agg_v.append({"world": w, "objective": o, "candidate": c, "n_seeds": len(g), **ci,
                      "mc_se_rms": float(np.sqrt((g["mc_se"] ** 2).mean())),
                      "rank_counts": json.dumps({str(k): int(v) for k, v in
                                                 g["rank"].value_counts().sort_index().items()})})
    for (w, o, pair), g in gaps.groupby(["world", "objective", "pair"], sort=True):
        ci = _t_ci(g["gap"].to_numpy())
        agg_g.append({"world": w, "objective": o, "pair": pair, "n_seeds": len(g), **ci,
                      "mc_se_rms": float(np.sqrt((g["se"] ** 2).mean())),
                      "seeds_resolved": int(g["resolved"].sum()),
                      "seeds_positive": int((g["gap"] > 0).sum())})
    agg_v, agg_g = pd.DataFrame(agg_v), pd.DataFrame(agg_g)
    agg_v.to_csv(dest / "values_by_world.csv", index=False)
    agg_g.to_csv(dest / "gaps_by_world.csv", index=False)
    best = (ranks.groupby(["world", "objective", "best"]).size().rename("seeds").reset_index())
    best.to_csv(dest / "best_counts.csv", index=False)
    f2 = "{:+.2f}"
    md = ["# Candidate values, gaps and rankings under three rewards (exploratory diagnostic)",
          "", "US$ per decision on the month-0 explorable cohort. Per world: mean over the 5 "
          "development seeds, 95% t interval over seeds (4 df), root-mean-square Monte-Carlo SE "
          "per seed. A pair is resolved in a seed if |gap| > 1.96 SE. Worlds share seeds.", "",
          "## Values", "",
          _md_table(agg_v, ["world", "objective", "candidate", "mean", "ci95_low", "ci95_high",
                            "sd_between_seeds", "mc_se_rms", "rank_counts"],
                    {"mean": "{:.2f}", "ci95_low": "{:.2f}", "ci95_high": "{:.2f}",
                     "sd_between_seeds": "{:.2f}", "mc_se_rms": "{:.2f}"}),
          "", "## Gaps (first minus second candidate)", "",
          _md_table(agg_g, ["world", "objective", "pair", "mean", "ci95_low", "ci95_high",
                            "sd_between_seeds", "mc_se_rms", "seeds_resolved",
                            "seeds_positive"],
                    {"mean": f2, "ci95_low": f2, "ci95_high": f2, "sd_between_seeds": "{:.2f}",
                     "mc_se_rms": "{:.2f}"}),
          "", "## Rankings per seed", "",
          _md_table(ranks, ["world", "seed", "objective", "ranking", "top_gap", "top_gap_se",
                            "top_resolved", "adjacent_resolved"],
                    {"top_gap": "{:.2f}", "top_gap_se": "{:.2f}"}),
          "", "## Winner change against the benchmark reward", "",
          _md_table(chg, ["world", "seed", "objective", "benchmark_best", "objective_best",
                          "winner_change"], {})]
    (dest / "tables.md").write_text("\n".join(md) + "\n")
    manifest = {"protocol": proto["_path"], "protocol_sha256": proto["_sha256"],
                "records": len(recs),
                "validation_failed": int(sum(1 for r in recs if r["validation"].get("checked")
                                             and not r["validation"].get("ok"))),
                "inputs_sha256": {f"{r['world']}/seed{r['seed']}": tc._sha256(
                    REPO / proto["out_dir"] / r["world"]
                    / f"seed{r['seed']}_r{proto['replicate']}.json") for r in recs},
                "outputs": sorted(p.name for p in dest.glob("*") if p.is_file())}
    tc._write_json(manifest, dest / "aggregate_manifest.json")
    return manifest


def load_protocol(path: Path) -> dict:
    raw = Path(path).read_bytes()
    proto = json.loads(raw)
    proto["_path"], proto["_sha256"] = str(path), hashlib.sha256(raw).hexdigest()
    for world, cfg_path in proto["worlds"].items():
        if tc._sha256(REPO / cfg_path) != proto["config_sha256"][world]:
            raise ValueError(f"{cfg_path} differs from the recorded config hash")
    return proto


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
    if a.command == "aggregate":
        print(json.dumps(aggregate(proto, a.dest), indent=2, default=tc._json_default))
        return
    jobs = [(w, s) for w in proto["worlds"] for s in proto["seeds"]
            if not (REPO / proto["out_dir"] / w / f"seed{s}_r{proto['replicate']}.json").exists()]
    _log(proto, {"event": "run_start", "todo": len(jobs), "workers": a.workers,
                 "code": proto["_code"]})
    failures = 0
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(_worker, [(proto, j) for j in jobs]):
            _log(proto, res)
            failures += 0 if res["ok"] else 1
            print(json.dumps({k: v for k, v in res.items() if k != "trace"}), flush=True)
    _log(proto, {"event": "run_end", "failures": failures})
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
