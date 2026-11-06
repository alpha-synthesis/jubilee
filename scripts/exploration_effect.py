"""Effect of the incumbent's ε-exploration on the benchmark's recovery reward.

Add-on to the revision campaign (``docs/revision_campaign.md``). For a world
config, seed and replicate, the month-0 explorable cohort is simulated twice
with generator version 2: the incumbent with the configured exploration rate
(ε = 0.08 in the campaign worlds) and the same incumbent with ε = 0. Only
``actions.exploration.epsilon`` differs; population, hidden factors, regional
shocks and every per-(loan, month) draw are shared, so a decision differs
between the two arms only where the exploration coin fires. The reward is the
benchmark's: 1{some recovery in months 0..horizon-1} × start balance ×
(1 − month-0 discount). It is not the amount collected (the discount of the
recovery month is not applied) and carries no channel costs.

Signed cost per pair: Δ = V(ε = 0) − V(ε), US$ per decision on the cohort;
positive means exploring loses reward. Per-pair Monte-Carlo SE from the
per-loan paired differences; per world, a t interval over seeds.

Usage::

    P=<protocol json>
    python scripts/exploration_effect.py plan      --protocol $P
    python scripts/exploration_effect.py validate  --protocol $P --workers 2
    python scripts/exploration_effect.py run       --protocol $P --workers 40
    python scripts/exploration_effect.py size      --protocol $P --dest <dir>   # pilot only
    python scripts/exploration_effect.py aggregate --protocol $P --dest <dir>
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
import tmlr_campaign as tc  # noqa: E402  (also puts src/ on the path)

from collection_simulator.config import load_config  # noqa: E402
from collection_simulator.generator import (  # noqa: E402
    GENERATOR_VERSION,
    RNG_SCHEME,
    simulate_cohort,
)

COHORT_KEYS = ("loan_id", "state", "dpd", "liq_days", "start_balance")


# ── protocol ───────────────────────────────────────────────────────────────
def load_protocol(path: Path) -> dict:
    raw = Path(path).read_bytes()
    proto = json.loads(raw)
    proto["_path"] = str(path)
    proto["_sha256"] = hashlib.sha256(raw).hexdigest()
    for key in ("name", "out_dir", "worlds", "seeds", "replicates", "borrowers",
                "batch_size", "horizon", "epsilon"):
        if key not in proto:
            raise ValueError(f"protocol lacks {key!r}")
    if len(set(proto["seeds"])) != len(proto["seeds"]) or len(proto["seeds"]) < 2:
        raise ValueError("seeds must be at least two distinct integers")
    if len(set(proto["replicates"])) != len(proto["replicates"]):
        raise ValueError("replicates must be distinct")
    for world, cfg_path in proto["worlds"].items():
        want = proto.get("config_sha256", {}).get(world)
        if want is not None and tc._sha256(REPO / cfg_path) != want:
            raise ValueError(f"{cfg_path} differs from the recorded config hash")
    return proto


def world_config(proto: dict, world: str, seed: int, epsilon: float | None = None) -> dict:
    cfg = load_config(REPO / proto["worlds"][world])
    cfg["seed"] = int(seed)
    cfg["population"]["borrowers"] = int(proto["borrowers"])
    configured = float(cfg["actions"]["exploration"]["epsilon"])
    if abs(configured - float(proto["epsilon"])) > 1e-12:
        raise ValueError(f"{world}: configured ε {configured} != protocol ε {proto['epsilon']}")
    if epsilon is not None:
        cfg["actions"]["exploration"]["epsilon"] = float(epsilon)
    return cfg


def _flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        out.update(_flat(v, key + ".") if isinstance(v, dict) else {key: v})
    return out


def config_difference(a: dict, b: dict) -> list[str]:
    fa, fb = _flat(a), _flat(b)
    return sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))


def _config_sha(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()


def pair_path(proto: dict, world: str, seed: int, replicate: int, kind: str = "pair") -> Path:
    return REPO / proto["out_dir"] / world / f"seed{seed}_r{replicate}_{kind}.json"


def pairs(proto: dict) -> list[tuple[str, int, int]]:
    return [(w, int(s), int(r)) for w in proto["worlds"] for s in proto["seeds"]
            for r in proto["replicates"]]


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def archived_reference(proto: dict, world: str, seed: int, replicate: int) -> dict | None:
    """Archived campaign reference of the incumbent for this pair, if any."""
    arch = proto.get("archived_reference")
    if not arch:
        return None
    p = REPO / arch["dir"] / world / f"seed{seed}" / f"reference_r{replicate}.json"
    if not p.exists():
        return None
    rec = json.loads(p.read_text())
    return {"path": _rel(p), "sha256": tc._sha256(p),
            "mean": float(rec["means"][arch["candidate"]]), "n_cohort": int(rec["n_cohort"])}


# ── simulation ─────────────────────────────────────────────────────────────
def _simulate(proto: dict, cfg: dict, replicate: int) -> tuple[pd.DataFrame, dict, dict]:
    t0, c0 = time.time(), time.process_time()
    cohort, meta = simulate_cohort(cfg, policy=None, replicate=int(replicate),
                                   batch_size=int(proto["batch_size"]),
                                   horizon=int(proto["horizon"]))
    timing = {"wall_seconds": round(time.time() - t0, 2),
              "cpu_seconds": round(time.process_time() - c0, 2)}
    return cohort, meta, timing


def _validation(proto: dict, world: str, seed: int, replicate: int, mean_eps: float,
                n: int) -> dict:
    arch = archived_reference(proto, world, seed, replicate)
    if arch is None:
        return {"checked": False}
    tol = float(proto["archived_reference"].get("tolerance", 1e-6))
    return {"checked": True, **arch, "new_mean": mean_eps, "new_n_cohort": n,
            "abs_difference": abs(mean_eps - arch["mean"]),
            "ok": bool(abs(mean_eps - arch["mean"]) <= tol and n == arch["n_cohort"])}


def _base_record(proto: dict, world: str, seed: int, replicate: int) -> dict:
    return {"protocol": proto["name"], "protocol_sha256": proto["_sha256"],
            "world": world, "seed": seed, "replicate": replicate,
            "generator_version": GENERATOR_VERSION, "rng_scheme": RNG_SCHEME,
            "code": proto["_code"], "driver_sha256": tc._sha256(Path(__file__)),
            "environment": tc.environment(), "config_path": proto["worlds"][world],
            "config_file_sha256": tc._sha256(REPO / proto["worlds"][world])}


def summarize_pair(c_eps: pd.DataFrame, c_none: pd.DataFrame) -> dict:
    """Paired comparison of the two arms on the same cohort (raises if misaligned)."""
    for key in COHORT_KEYS:
        if not np.array_equal(c_eps[key].to_numpy(), c_none[key].to_numpy()):
            raise AssertionError(f"arms differ in cohort column {key!r}")
    if bool(c_none["is_exploration"].any()):
        raise AssertionError("the ε = 0 arm explored")
    r0 = c_none["reward"].to_numpy(np.float64)
    re = c_eps["reward"].to_numpy(np.float64)
    d = r0 - re
    n = len(d)
    p0 = c_none["paid_within_h"].to_numpy(np.float64)
    pe = c_eps["paid_within_h"].to_numpy(np.float64)
    explored0 = c_eps["is_exploration"].to_numpy(bool)
    action_diff0 = ((c_eps["channel_logged"].to_numpy() != c_none["channel_logged"].to_numpy())
                    | (c_eps["discount_logged"].to_numpy() != c_none["discount_logged"].to_numpy()))
    sd = float(d.std(ddof=1))
    v0 = float(r0.mean())
    return {
        "n_cohort": n,
        "value_eps0": v0, "value_eps": float(re.mean()),
        "se_value_eps0": float(r0.std(ddof=1) / math.sqrt(n)),
        "se_value_eps": float(re.std(ddof=1) / math.sqrt(n)),
        "delta": float(d.mean()), "sd_loan_delta": sd, "se_delta": sd / math.sqrt(n),
        "corr_arms": float(np.corrcoef(r0, re)[0, 1]),
        "relative_delta": float(d.mean() / v0),
        "delta_from_month0_explored": float((d * explored0).sum() / n),
        "delta_from_other_loans": float((d * ~explored0).sum() / n),
        "recovery_rate_eps0": float(p0.mean()), "recovery_rate_eps": float(pe.mean()),
        "recovery_rate_delta": float((p0 - pe).mean()),
        "se_recovery_rate_delta": float((p0 - pe).std(ddof=1) / math.sqrt(n)),
        "month0_explored_share": float(explored0.mean()),
        "month0_action_differs_share": float(action_diff0.mean()),
        "reward_differs_share": float((d != 0).mean()),
        "recovery_differs_share": float((p0 != pe).mean()),
        "month0_mean_discount_eps0": float(c_none["discount_logged"].mean()),
        "month0_mean_discount_eps": float(c_eps["discount_logged"].mean()),
    }


def run_pair(proto: dict, world: str, seed: int, replicate: int) -> dict:
    cfg_eps = world_config(proto, world, seed)
    cfg_none = world_config(proto, world, seed, epsilon=0.0)
    diff = config_difference(cfg_eps, cfg_none)
    if diff != ["actions.exploration.epsilon"]:
        raise AssertionError(f"arms differ beyond ε: {diff}")
    c_eps, meta_eps, t_eps = _simulate(proto, cfg_eps, replicate)
    c_none, meta_none, t_none = _simulate(proto, cfg_none, replicate)
    out = {**_base_record(proto, world, seed, replicate),
           "config_effective_sha256": {"eps": _config_sha(cfg_eps), "eps0": _config_sha(cfg_none)},
           "configs_differ_in": diff, "epsilon": float(proto["epsilon"]),
           "meta": {"eps": meta_eps, "eps0": meta_none},
           "summary": summarize_pair(c_eps, c_none)}
    out["validation"] = _validation(proto, world, seed, replicate,
                                    out["summary"]["value_eps"], out["summary"]["n_cohort"])
    out["timing"] = {"eps": t_eps, "eps0": t_none, **tc._usage()}
    p = pair_path(proto, world, seed, replicate)
    p.parent.mkdir(parents=True, exist_ok=True)
    tc._write_json(out, p)
    return out


def validate_job(proto: dict, world: str, seed: int, replicate: int) -> dict:
    """ε arm only: reproduce the archived reference of the incumbent."""
    cfg = world_config(proto, world, seed)
    coh, meta, timing = _simulate(proto, cfg, replicate)
    out = {**_base_record(proto, world, seed, replicate), "meta": meta,
           "validation": _validation(proto, world, seed, replicate,
                                     float(coh["reward"].mean()), int(len(coh))),
           "timing": {**timing, **tc._usage()}}
    p = pair_path(proto, world, seed, replicate, kind="validation")
    p.parent.mkdir(parents=True, exist_ok=True)
    tc._write_json(out, p)
    return out


def _worker(args):
    kind, proto, job = args
    t0 = time.time()
    try:
        fn = run_pair if kind == "run" else validate_job
        out = fn(proto, *job)
        return {"kind": kind, "job": job, "ok": True, "wall_seconds": round(time.time() - t0, 1),
                "validation_ok": out["validation"].get("ok"), **tc._usage()}
    except Exception as exc:  # recorded, never swallowed
        return {"kind": kind, "job": job, "ok": False, "error": repr(exc),
                "trace": traceback.format_exc()}


def _log(proto: dict, record: dict) -> None:
    path = REPO / proto["out_dir"] / "jobs.log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record},
                            default=tc._json_default) + "\n")


# ── analysis ───────────────────────────────────────────────────────────────
def _t95(df: int) -> float:
    from scipy import stats

    return float(stats.t.ppf(0.975, df))


def load_pairs(proto: dict) -> pd.DataFrame:
    rows = []
    for world, seed, r in pairs(proto):
        p = pair_path(proto, world, seed, r)
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        s = rec["summary"]
        rows.append({"world": world, "seed": seed, "replicate": r, **s,
                     "validation_checked": rec["validation"].get("checked", False),
                     "validation_ok": rec["validation"].get("ok"),
                     "validation_abs_difference": rec["validation"].get("abs_difference"),
                     "cpu_seconds_pair": rec["timing"]["eps"]["cpu_seconds"]
                     + rec["timing"]["eps0"]["cpu_seconds"],
                     "wall_seconds_pair": rec["timing"]["eps"]["wall_seconds"]
                     + rec["timing"]["eps0"]["wall_seconds"],
                     "peak_rss_mb": rec["timing"]["peak_rss_mb"]})
    return pd.DataFrame(rows)


def per_seed(pr: pd.DataFrame) -> pd.DataFrame:
    """Average the replicates of a seed; Monte-Carlo SE of that average."""
    g = pr.groupby(["world", "seed"], sort=True)
    out = g.agg(R=("replicate", "size"), n_cohort=("n_cohort", "mean"),
                value_eps0=("value_eps0", "mean"), value_eps=("value_eps", "mean"),
                delta=("delta", "mean"), relative_delta=("relative_delta", "mean"),
                delta_from_month0_explored=("delta_from_month0_explored", "mean"),
                delta_from_other_loans=("delta_from_other_loans", "mean"),
                recovery_rate_eps0=("recovery_rate_eps0", "mean"),
                recovery_rate_eps=("recovery_rate_eps", "mean"),
                recovery_rate_delta=("recovery_rate_delta", "mean"),
                month0_explored_share=("month0_explored_share", "mean"))
    out["se_delta_mc"] = g["se_delta"].apply(lambda s: math.sqrt((s ** 2).sum()) / len(s))
    out["se_recovery_rate_delta_mc"] = g["se_recovery_rate_delta"].apply(
        lambda s: math.sqrt((s ** 2).sum()) / len(s))
    return out.reset_index()


def _ci(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=np.float64)
    k = len(x)
    se = float(x.std(ddof=1) / math.sqrt(k))
    t = _t95(k - 1)
    return {"mean": float(x.mean()), "sd_between_seeds": float(x.std(ddof=1)), "se": se,
            "ci95_low": float(x.mean() - t * se), "ci95_high": float(x.mean() + t * se),
            "half_width": t * se}


def by_world(ps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for world, g in ps.groupby("world", sort=True):
        d = _ci(g["delta"].to_numpy())
        rel = _ci(g["relative_delta"].to_numpy())
        rec = _ci(g["recovery_rate_delta"].to_numpy())
        m0 = _ci(g["delta_from_month0_explored"].to_numpy())
        oth = _ci(g["delta_from_other_loans"].to_numpy())
        mc_var = float((g["se_delta_mc"] ** 2).mean())
        rows.append({
            "world": world, "n_seeds": len(g), "replicates_per_seed": int(g["R"].min()),
            "mean_n_cohort": float(g["n_cohort"].mean()),
            "mean_value_eps0": float(g["value_eps0"].mean()),
            "mean_value_eps": float(g["value_eps"].mean()),
            "delta_mean": d["mean"], "delta_se": d["se"], "delta_ci95_low": d["ci95_low"],
            "delta_ci95_high": d["ci95_high"], "delta_half_width": d["half_width"],
            "delta_sd_between_seeds": d["sd_between_seeds"],
            "mc_se_per_seed_rms": math.sqrt(mc_var),
            "sd_seed_component": math.sqrt(max(0.0, d["sd_between_seeds"] ** 2 - mc_var)),
            "relative_delta_mean": rel["mean"], "relative_delta_ci95_low": rel["ci95_low"],
            "relative_delta_ci95_high": rel["ci95_high"],
            "recovery_rate_eps0": float(g["recovery_rate_eps0"].mean()),
            "recovery_rate_eps": float(g["recovery_rate_eps"].mean()),
            "recovery_rate_delta_mean": rec["mean"],
            "recovery_rate_delta_ci95_low": rec["ci95_low"],
            "recovery_rate_delta_ci95_high": rec["ci95_high"],
            "delta_from_month0_explored_mean": m0["mean"],
            "delta_from_month0_explored_ci95_low": m0["ci95_low"],
            "delta_from_month0_explored_ci95_high": m0["ci95_high"],
            "delta_from_other_loans_mean": oth["mean"],
            "delta_from_other_loans_ci95_low": oth["ci95_low"],
            "delta_from_other_loans_ci95_high": oth["ci95_high"],
            "month0_explored_share": float(g["month0_explored_share"].mean()),
            "seeds_with_positive_delta": int((g["delta"] > 0).sum()),
        })
    return pd.DataFrame(rows)


def world_contrast(ps: pd.DataFrame) -> pd.DataFrame:
    """Seed-paired difference of Δ between worlds (descriptive: worlds share seeds)."""
    worlds = sorted(ps["world"].unique())
    rows = []
    for i, a in enumerate(worlds):
        for b in worlds[i + 1:]:
            m = ps[ps.world == a].set_index("seed")["delta"].to_frame("a").join(
                ps[ps.world == b].set_index("seed")["delta"].to_frame("b"), how="inner")
            if len(m) < 2:
                continue
            c = _ci((m["b"] - m["a"]).to_numpy())
            rows.append({"contrast": f"{b} - {a}", "n_seeds": len(m),
                         "corr_seed_deltas": float(np.corrcoef(m["a"], m["b"])[0, 1]), **c})
    return pd.DataFrame(rows)


def replicate_consistency(pr: pd.DataFrame) -> pd.DataFrame:
    """Spread of replicate Δ within a seed against the per-loan Monte-Carlo SE."""
    rows = []
    for world, g in pr.groupby("world", sort=True):
        num, den, dof = 0.0, 0.0, 0
        for _, s in g.groupby("seed"):
            if len(s) < 2:
                continue
            num += float(((s["delta"] - s["delta"].mean()) ** 2).sum())
            den += float((s["se_delta"] ** 2).mean()) * (len(s) - 1)
            dof += len(s) - 1
        if dof:
            rows.append({"world": world, "dof": dof, "variance_ratio": num / den})
    return pd.DataFrame(rows)


def sizing(pr: pd.DataFrame, proto: dict) -> dict:
    """Apply protocol/precision_rule.md to pilot pairs (development seeds only)."""
    rule = proto["sizing_rule"]
    first = pr[pr.replicate == min(proto["replicates"])]
    sig2_mc = float(np.median(pr["se_delta"] ** 2))
    per_world_var = [float(g["delta"].var(ddof=1)) for _, g in first.groupby("world")]
    sig2_seed = max(0.0, float(np.mean(per_world_var)) - float((first["se_delta"] ** 2).mean()))
    n_seeds = int(rule["main_seeds"])
    t = _t95(n_seeds - 1)
    cpu_pair = float(pr["cpu_seconds_pair"].median())
    n_worlds = len(proto["worlds"])
    proj = {}
    for R in rule["R_options"]:
        hw = t * math.sqrt((sig2_seed + sig2_mc / R) / n_seeds)
        cpu_h = n_worlds * n_seeds * R * cpu_pair / 3600.0
        proj[R] = {"half_width": hw, "main_cpu_hours": cpu_h}
    spent = float(pr["cpu_seconds_pair"].sum()) / 3600.0
    budget_left = float(rule["cpu_hours_ceiling"]) - spent - float(rule.get("reserve_cpu_hours", 0))
    ok = [R for R in rule["R_options"]
          if proj[R]["half_width"] <= rule["target_half_width"]
          and proj[R]["main_cpu_hours"] <= budget_left]
    if ok:
        chosen, reason = min(ok), "smallest R meeting the half-width target within budget"
    elif t * math.sqrt(sig2_seed / n_seeds) > rule["target_half_width"]:
        chosen, reason = min(rule["R_options"]), "between-seed term alone exceeds the target"
    else:
        aff = [R for R in rule["R_options"] if proj[R]["main_cpu_hours"] <= budget_left]
        chosen, reason = (max(aff) if aff else min(rule["R_options"])), "largest affordable R"
    return {"sigma2_mc": sig2_mc, "sigma_mc": math.sqrt(sig2_mc),
            "per_world_variance_of_seed_deltas": per_world_var,
            "sigma2_seed": sig2_seed, "sigma_seed": math.sqrt(sig2_seed),
            "max_pair_se": float(pr["se_delta"].max()),
            "median_cpu_seconds_per_pair": cpu_pair, "pilot_cpu_hours": spent,
            "budget_left_cpu_hours": budget_left, "projection": proj,
            "chosen_R": chosen, "reason": reason, "t_quantile": t, "main_seeds": n_seeds}


def _md_table(df: pd.DataFrame, cols: list[str], fmt: dict) -> str:
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt.get(c, "{}").format(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def aggregate(proto: dict, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    pr = load_pairs(proto)
    expected = pairs(proto)
    missing = sorted(set(expected) - set(zip(pr.world, pr.seed, pr.replicate)))
    ps = per_seed(pr)
    bw = by_world(ps)
    wc = world_contrast(ps)
    rc = replicate_consistency(pr)
    pr.to_csv(dest / "pairs.csv", index=False)
    ps.to_csv(dest / "per_seed.csv", index=False)
    bw.to_csv(dest / "by_world.csv", index=False)
    wc.to_csv(dest / "world_contrast.csv", index=False)
    rc.to_csv(dest / "replicate_consistency.csv", index=False)
    f2 = "{:+.2f}"
    md = ["# Effect of ε-exploration on the benchmark's recovery reward",
          "",
          "Units: US$ per decision on the month-0 explorable cohort. Δ = V(ε = 0) − "
          f"V(ε = {proto['epsilon']}); positive = exploring loses reward. Intervals: 95%, "
          "t over seeds (seeds are the independent unit).", "",
          _md_table(bw, ["world", "n_seeds", "replicates_per_seed", "mean_value_eps0",
                         "mean_value_eps", "delta_mean", "delta_ci95_low", "delta_ci95_high",
                         "relative_delta_mean", "delta_sd_between_seeds",
                         "mc_se_per_seed_rms", "seeds_with_positive_delta"],
                    {"mean_value_eps0": "{:.2f}", "mean_value_eps": "{:.2f}",
                     "delta_mean": f2, "delta_ci95_low": f2, "delta_ci95_high": f2,
                     "relative_delta_mean": "{:+.3%}", "delta_sd_between_seeds": "{:.2f}",
                     "mc_se_per_seed_rms": "{:.2f}"}), "",
          "Recovery rate within the window (share of the cohort):", "",
          _md_table(bw, ["world", "recovery_rate_eps0", "recovery_rate_eps",
                         "recovery_rate_delta_mean", "recovery_rate_delta_ci95_low",
                         "recovery_rate_delta_ci95_high"],
                    {c: "{:.5f}" for c in ["recovery_rate_eps0", "recovery_rate_eps",
                                            "recovery_rate_delta_mean",
                                            "recovery_rate_delta_ci95_low",
                                            "recovery_rate_delta_ci95_high"]}), "",
          "Δ split by whether the loan was explored at month 0 (the two parts add to Δ):", "",
          _md_table(bw, ["world", "delta_from_month0_explored_mean",
                         "delta_from_month0_explored_ci95_low",
                         "delta_from_month0_explored_ci95_high",
                         "delta_from_other_loans_mean", "delta_from_other_loans_ci95_low",
                         "delta_from_other_loans_ci95_high", "month0_explored_share"],
                    {"delta_from_month0_explored_mean": f2,
                     "delta_from_month0_explored_ci95_low": f2,
                     "delta_from_month0_explored_ci95_high": f2,
                     "delta_from_other_loans_mean": f2,
                     "delta_from_other_loans_ci95_low": f2,
                     "delta_from_other_loans_ci95_high": f2,
                     "month0_explored_share": "{:.4f}"})]
    if len(wc):
        md += ["", "World contrast (descriptive; the worlds share seeds and month-0 actions):",
               "", _md_table(wc, ["contrast", "n_seeds", "mean", "ci95_low", "ci95_high",
                                  "corr_seed_deltas"],
                             {"mean": f2, "ci95_low": f2, "ci95_high": f2,
                              "corr_seed_deltas": "{:.3f}"})]
    (dest / "tables.md").write_text("\n".join(md) + "\n")
    manifest = {"protocol": proto["_path"], "protocol_sha256": proto["_sha256"],
                "pairs_expected": len(expected), "pairs_found": len(pr),
                "missing": missing,
                "validation_checked": int(pr["validation_checked"].sum()),
                "validation_failed": int((pr["validation_checked"]
                                          & (pr["validation_ok"] != True)).sum()),  # noqa: E712
                "inputs_sha256": {_rel(pair_path(proto, w, s, r)):
                                  tc._sha256(pair_path(proto, w, s, r))
                                  for w, s, r in expected if pair_path(proto, w, s, r).exists()},
                "outputs": sorted(p.name for p in dest.glob("*") if p.is_file())}
    tc._write_json(manifest, dest / "aggregate_manifest.json")
    return manifest


# ── CLI ────────────────────────────────────────────────────────────────────
def _pool_run(kind: str, proto: dict, jobs: list, workers: int) -> int:
    _log(proto, {"event": f"{kind}_start", "todo": len(jobs), "workers": workers,
                 "code": proto["_code"]})
    failures = 0
    with mp.get_context("fork").Pool(workers, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(_worker, [(kind, proto, j) for j in jobs]):
            _log(proto, res)
            failures += 0 if res["ok"] else 1
            print(json.dumps({k: v for k, v in res.items() if k != "trace"}), flush=True)
    _log(proto, {"event": f"{kind}_end", "failures": failures})
    return failures


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("plan", "validate", "run", "size", "aggregate"))
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--dest", type=Path, default=None)
    a = ap.parse_args(argv)
    proto = load_protocol(a.protocol)
    proto["_code"] = tc.code_fingerprint()
    if a.command == "plan":
        todo = [p for p in pairs(proto) if not pair_path(proto, *p).exists()]
        print(json.dumps({"pairs": len(pairs(proto)), "todo": len(todo),
                          "simulations": 2 * len(todo), "code": proto["_code"]}, indent=2))
    elif a.command == "validate":
        jobs = [tuple(v) for v in proto["validation_pairs"]]
        sys.exit(1 if _pool_run("validate", proto, jobs, a.workers) else 0)
    elif a.command == "run":
        todo = [p for p in pairs(proto) if not pair_path(proto, *p).exists()]
        sys.exit(1 if _pool_run("run", proto, todo, a.workers) else 0)
    elif a.command == "size":
        out = sizing(load_pairs(proto), proto)
        a.dest.mkdir(parents=True, exist_ok=True)
        tc._write_json(out, a.dest / "sizing.json")
        print(json.dumps(out, indent=2, default=tc._json_default))
    else:
        print(json.dumps(aggregate(proto, a.dest), indent=2, default=tc._json_default))


if __name__ == "__main__":
    main()
