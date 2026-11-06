"""Deterministic aggregation of the revision campaign (or pilot) run files.

Reads every ``<out_dir>/<condition>/seed<S>/panel.json`` of a protocol and the
simulation job records, and writes CSV/JSON tables (and figures with
``--figures``) to ``--dest``. Same inputs → byte-identical tables.

Units: every value, error, gap and regret is in US$ per decision on the month-0
explorable cohort. Seeds within a condition are independent replicates
(different populations and regional shocks); the same seed in two conditions
shares population and shocks, so contrasts between conditions are computed
seed by seed (paired). Fractions are counts over stated denominators; no
binomial SE is attached to pooled fractions across conditions.

Usage::

    python scripts/tmlr_aggregate.py --protocol PROTOCOL.json --dest DIR [--figures]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
INCUMBENT = "pi_b"
DISPLAY = {"pi_b": "π_b (incumbent)", "pi_near": "π_sms (pi_near)",
           "pi_far": "π_visit (pi_far)", "pi_stage": "π_stage (pi_stage)"}


def _run_path(proto: dict, cond: str, seed: int) -> Path:
    return REPO / proto["out_dir"] / cond / f"seed{seed}" / "panel.json"


def _load(proto: dict) -> tuple[list[dict], list[dict]]:
    """Every expected run of the protocol; missing ones are listed, never skipped
    silently."""
    runs, missing = [], []
    for cond in proto["conditions"]:
        for seed in proto["seeds"]:
            p = _run_path(proto, cond, seed)
            if p.exists():
                runs.append(json.loads(p.read_text()))
            else:
                missing.append({"cond": cond, "seed": seed})
    return runs, missing


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


def _se(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")


def _mean_or_none(s: pd.Series) -> float | None:
    return float(s.dropna().mean()) if s.notna().any() else None


def _rmse_se(err: np.ndarray, n_boot: int = 2000, seed: int = 0) -> float:
    """Bootstrap-over-seeds SE of the RMSE (seeds are the independent unit)."""
    err = np.asarray(err, dtype=np.float64)
    if len(err) < 3:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(err), size=(n_boot, len(err)))
    return float(np.sqrt((err[idx] ** 2).mean(axis=1)).std(ddof=1))


def estimator_rows(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for run in runs:
        for tname, t in run["targets"].items():
            for regime in ("tabular", "nontabular"):
                block = t.get(regime)
                if not block:
                    continue
                for key, e in block.items():
                    if not isinstance(e, dict) or "value" not in e:
                        continue
                    rows.append({
                        "cond": run["cond"], "seed": run["seed"], "target": tname,
                        "regime": regime, "estimator": key, "value": e["value"],
                        "error": e.get("error"), "ci_low": e.get("ci_low"),
                        "ci_high": e.get("ci_high"),
                        "ci_width": ((e["ci_high"] - e["ci_low"])
                                     if e.get("ci_low") is not None else None),
                        "contains_reference": e.get("contains_reference"),
                        "boot_sd": e.get("boot_sd"),
                        "reference": t["reference"], "reference_se": t["reference_se"],
                        "n_anchor": e.get("n_anchor"),  # pilot estimators only
                    })
        rows.append({"cond": run["cond"], "seed": run["seed"], "target": INCUMBENT,
                     "regime": "factual", "estimator": "logged_mean", "value": run["logged_mean"],
                     "error": run["incumbent_factual_error"],
                     "reference": run["reference"]["mean"][INCUMBENT],
                     "reference_se": run["reference"]["se_within"][INCUMBENT]})
    return pd.DataFrame(rows).sort_values(["cond", "regime", "estimator", "target", "seed"],
                                          kind="mergesort").reset_index(drop=True)


def error_summary(est: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cond, regime, key, target), g in est.groupby(
            ["cond", "regime", "estimator", "target"], sort=True):
        e = g["error"].dropna().to_numpy(np.float64)
        if len(e) == 0:
            rows.append({"cond": cond, "regime": regime, "estimator": key, "target": target,
                         "n_runs": len(g), "n_defined": 0})
            continue
        cont = g["contains_reference"].dropna()
        rows.append({
            "cond": cond, "regime": regime, "estimator": key, "target": target,
            "n_runs": len(g), "n_defined": len(e),
            "mean_error": float(e.mean()), "se_mean_error": _se(e),
            "t_stat": float(e.mean() / _se(e)) if len(e) > 1 and _se(e) > 0 else None,
            "sd_error": float(e.std(ddof=1)) if len(e) > 1 else None,
            "rmse": float(np.sqrt((e ** 2).mean())), "se_rmse": _rmse_se(e),
            "mean_abs_error": float(np.abs(e).mean()),
            "mean_reference": float(g["reference"].mean()),
            "mean_reference_se": float(g["reference_se"].mean()),
            "contains_count": int(cont.sum()) if len(cont) else None,
            "contains_denominator": int(len(cont)) if len(cont) else None,
            "mean_ci_width": _mean_or_none(g["ci_width"]),
            "mean_boot_sd": _mean_or_none(g["boot_sd"]),
            "mean_n_anchor": _mean_or_none(g["n_anchor"]),
        })
    return pd.DataFrame(rows)


def reference_rows(runs: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    vals, gaps = [], []
    for run in runs:
        ref = run["reference"]
        for c in ref["candidates"]:
            vals.append({"cond": run["cond"], "seed": run["seed"], "candidate": c,
                         "R": ref["R"], "mean": ref["mean"][c],
                         "se_within": ref["se_within"][c], "se_between": ref["se_between"][c],
                         "se_one_replicate": ref.get("se_one_replicate",
                                                     ref.get("per_replicate_sd_within"))[c],
                         "n_per_replicate_mean": float(np.mean(ref["n_per_replicate"]))})
        for pair, g in ref["gaps"].items():
            gaps.append({"cond": run["cond"], "seed": run["seed"], "pair": pair, "R": ref["R"],
                         **g})
    return (pd.DataFrame(vals).sort_values(["cond", "candidate", "seed"]).reset_index(drop=True),
            pd.DataFrame(gaps).sort_values(["cond", "pair", "seed"]).reset_index(drop=True))


def selection_rows(runs: list[dict]) -> pd.DataFrame:
    rows = []
    for run in runs:
        for label, s in run["selection"].items():
            regime, key = label.split(":")
            base = {"cond": run["cond"], "seed": run["seed"], "regime": regime, "estimator": key}
            if "picked" not in s:
                rows.append({**base, "defined": False})
                continue
            pw = s["pairwise"]
            rows.append({**base, "defined": True, "picked": s["picked"], "ref_best": s["ref_best"],
                         "ref_runner_up": s["ref_runner_up"], "top_gap": s["top_gap"],
                         "top_gap_se": s["top_gap_se"], "top_resolved": s["top_resolved"],
                         "correct": s["correct"], "regret": s["regret"],
                         "regret_se": s["regret_se"], "gain_vs_incumbent": s["gain_vs_incumbent"],
                         "gain_vs_incumbent_se": s["gain_vs_incumbent_se"],
                         "pairs_resolved": sum(v["resolved"] for v in pw.values()),
                         "pairs_resolved_agree": sum(
                             v["resolved"] and v["est_sign"] == v["ref_sign"]
                             for v in pw.values()),
                         "pairs_total": len(pw)})
    return (pd.DataFrame(rows).sort_values(["cond", "regime", "estimator", "seed"])
            .reset_index(drop=True))


def selection_summary(sel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cond, regime, key), g in sel.groupby(["cond", "regime", "estimator"], sort=True):
        d = g[g["defined"]]
        if d.empty:
            rows.append({"cond": cond, "regime": regime, "estimator": key, "n_runs": len(g),
                         "n_defined": 0})
            continue
        res = d[d["top_resolved"].astype(bool)]
        picks = d["picked"].value_counts().to_dict()
        z = 1.96
        worse = (d["gain_vs_incumbent"] < -z * d["gain_vs_incumbent_se"]).sum()
        better = (d["gain_vs_incumbent"] > z * d["gain_vs_incumbent_se"]).sum()
        rows.append({
            "cond": cond, "regime": regime, "estimator": key, "n_runs": len(g),
            "n_defined": len(d),
            "n_top_resolved": len(res), "n_top_ambiguous": len(d) - len(res),
            "correct_among_resolved": int(res["correct"].sum()),
            "correct_all": int(d["correct"].sum()),
            "mean_regret": float(d["regret"].mean()), "se_mean_regret": _se(d["regret"]),
            "mean_regret_resolved_runs": float(res["regret"].mean()) if len(res) else None,
            "se_mean_regret_resolved_runs": _se(res["regret"]) if len(res) > 1 else None,
            "max_regret": float(d["regret"].max()),
            "mean_gain_vs_incumbent": float(d["gain_vs_incumbent"].mean()),
            "se_mean_gain_vs_incumbent": _se(d["gain_vs_incumbent"]),
            "n_picks_resolved_worse_than_incumbent": int(worse),
            "n_picks_resolved_better_than_incumbent": int(better),
            "pairs_resolved": int(d["pairs_resolved"].sum()),
            "pairs_resolved_agree": int(d["pairs_resolved_agree"].sum()),
            "picks": json.dumps(dict(sorted(picks.items()))),
            "ref_best": json.dumps(dict(sorted(d["ref_best"].value_counts().to_dict().items()))),
        })
    return pd.DataFrame(rows)


def selection_sensitivity(runs: list[dict], cands: list[str]) -> pd.DataFrame:
    """Selection graded against references built from the first R' replicates
    (R' = 1..R): share of runs whose reference best candidate equals the
    full-R one, and each estimator's correct picks and mean regret at R'."""
    rows = []
    for run in runs:
        ref = run["reference"]
        names = ref["candidates"]
        rm = np.asarray(ref["replicate_means"], dtype=np.float64)  # R × K
        idx = [names.index(c) for c in cands]
        full = rm[:, idx].mean(axis=0)
        best_full = cands[int(np.argmax(full))]
        for rp in range(1, rm.shape[0] + 1):
            m = rm[:rp, idx].mean(axis=0)
            best = cands[int(np.argmax(m))]
            for label, sel in run["selection"].items():
                if "picked" not in sel:
                    continue
                regime, key = label.split(":")
                picked = sel["picked"]
                rows.append({"cond": run["cond"], "seed": run["seed"], "R_used": rp,
                             "regime": regime, "estimator": key,
                             "ref_best": best, "ref_best_equals_full": best == best_full,
                             "correct": picked == best,
                             "regret": float(m.max() - m[cands.index(picked)])})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return (df.groupby(["cond", "regime", "estimator", "R_used"], sort=True)
            .agg(n_runs=("seed", "size"), ref_best_equals_full=("ref_best_equals_full", "sum"),
                 correct=("correct", "sum"), mean_regret=("regret", "mean"))
            .reset_index())


def replicate_consistency(runs: list[dict]) -> pd.DataFrame:
    """Between-replicate variance of the reference means against the per-loan
    prediction, per condition: ratio = mean over seeds of (se_between /
    se_within)^2; under independent loans sum((R-1) * ratio) ~ chi2((R-1) * S)
    over the S seeds of a condition (seeds are the independent unit)."""
    from scipy import stats

    rows = []
    by: dict[tuple, list[float]] = {}
    for run in runs:
        ref = run["reference"]
        R = ref["R"]
        for c in ref["candidates"]:
            if ref["se_within"][c] > 0 and ref["se_between"][c] is not None:
                by.setdefault((run["cond"], "value", c, R), []).append(
                    (ref["se_between"][c] / ref["se_within"][c]) ** 2)
        for pair, g in ref["gaps"].items():
            if g["se_within"] > 0 and g.get("se_between") is not None:
                by.setdefault((run["cond"], "gap", pair, R), []).append(
                    (g["se_between"] / g["se_within"]) ** 2)
    for (cond, kind, name, R), ratios in sorted(by.items()):
        r = np.asarray(ratios)
        df = (R - 1) * len(r)
        chi = float(((R - 1) * r).sum())
        p = 2 * min(stats.chi2.cdf(chi, df), stats.chi2.sf(chi, df))
        rows.append({"cond": cond, "kind": kind, "name": name, "n_seeds": len(r),
                     "replicates": R, "mean_variance_ratio": float(r.mean()),
                     "chi2": chi, "df": df, "p_two_sided": float(min(p, 1.0))})
    return pd.DataFrame(rows)


LOG_FAMILY = {"tabular": ("dm", "is", "snips", "dr", "dm_plus_is"),
              "nontabular": ("dm", "is", "snips", "dr")}


def family_agreement(est: pd.DataFrame) -> pd.DataFrame:
    """Per run, the spread (max − min) of the log-based estimators' errors within
    a regime, and the spread excluding IS (whose estimated-propensity weights
    are the most fragile); summarised per condition, regime and target."""
    rows = []
    for regime, members in LOG_FAMILY.items():
        sub = est[(est["regime"] == regime) & est["estimator"].isin(members)]
        piv = sub.pivot_table(index=["cond", "target", "seed"], columns="estimator",
                              values="error")
        if piv.empty:
            continue
        spread = piv.max(axis=1) - piv.min(axis=1)
        no_is = piv.drop(columns=[c for c in ("is",) if c in piv]).pipe(
            lambda d: d.max(axis=1) - d.min(axis=1))
        df = pd.DataFrame({"spread": spread, "spread_without_is": no_is}).reset_index()
        for (cond, target), g in df.groupby(["cond", "target"], sort=True):
            rows.append({"cond": cond, "regime": regime, "target": target,
                         "members": "/".join(members), "n_runs": len(g),
                         "mean_spread": float(g["spread"].mean()),
                         "max_spread": float(g["spread"].max()),
                         "mean_spread_without_is": float(g["spread_without_is"].mean()),
                         "max_spread_without_is": float(g["spread_without_is"].max())})
    return pd.DataFrame(rows)


def paired_contrasts(est: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Seed-by-seed error differences between two conditions (cond_a − cond_b)."""
    rows = []
    key = ["regime", "estimator", "target", "seed"]
    for a, b in pairs:
        ea = est[est["cond"] == a].set_index(key)["error"]
        eb = est[est["cond"] == b].set_index(key)["error"]
        d = (ea - eb).dropna()
        for (regime, estimator, target), g in d.groupby(level=[0, 1, 2], sort=True):
            x = g.to_numpy(np.float64)
            rows.append({"contrast": f"{a} - {b}", "regime": regime, "estimator": estimator,
                         "target": target, "n_seeds": len(x), "mean_diff": float(x.mean()),
                         "se": _se(x)})
    return pd.DataFrame(rows)


def regime_contrast(est: pd.DataFrame) -> pd.DataFrame:
    """Same run, same logs: non-tabular minus tabular error, per estimator."""
    rows = []
    k = ["cond", "target", "seed"]
    for estimator in ("dm", "is", "snips", "dr", "pilot_dr"):
        same = est["estimator"] == estimator
        a = est[(est["regime"] == "nontabular") & same].set_index(k)["error"]
        b = est[(est["regime"] == "tabular") & same].set_index(k)["error"]
        d = (a - b).dropna()
        for (cond, target), g in d.groupby(level=[0, 1], sort=True):
            x = g.to_numpy(np.float64)
            rows.append({"cond": cond, "target": target, "estimator": estimator,
                         "n_seeds": len(x), "mean_diff_nontab_minus_tab": float(x.mean()),
                         "se": _se(x)})
    return pd.DataFrame(rows)


def interval_diagnostic(est: pd.DataFrame) -> pd.DataFrame:
    """Fixed-model vs refit DM intervals (and the other tabular intervals) per
    condition and target: containment of the reference, width, bootstrap SD vs
    the across-seed SD of the error, and the reference SE relative to width."""
    rows = []
    sel = est[(est["regime"] == "tabular") & est["estimator"].isin(
        ["dm", "dm_refit", "is", "snips", "dr", "dm_plus_is", "pilot_is", "pilot_dr"])]
    for (cond, target, key), g in sel.groupby(["cond", "target", "estimator"], sort=True):
        g = g.dropna(subset=["error"])
        if g.empty:
            continue
        rows.append({
            "cond": cond, "target": target, "interval": key, "n_seeds": len(g),
            "contains": int(g["contains_reference"].sum()),
            "mean_width": float(g["ci_width"].mean()),
            "sd_error_across_seeds": float(g["error"].std(ddof=1)) if len(g) > 1 else None,
            "mean_error": float(g["error"].mean()),
            "mean_boot_sd": float(g["boot_sd"].mean()) if g["boot_sd"].notna().any() else None,
            "width_implied_sd": float(g["ci_width"].mean() / (2 * 1.6449)),
            "mean_reference_se": float(g["reference_se"].mean()),
        })
    return pd.DataFrame(rows)


def _jobs_table(proto: dict) -> pd.DataFrame:
    p = REPO / proto["out_dir"] / "jobs.log.jsonl"
    if not p.exists():
        return pd.DataFrame()
    rows = []
    for line in p.read_text().splitlines():
        r = json.loads(line)
        if r.get("event") == "job" and r.get("ok"):
            j = r["job"]
            rows.append({"kind": j["kind"], "cond": j["cond"], "seed": j["seed"],
                         "replicate": j.get("replicate"), "wall_seconds": r["wall_seconds"],
                         "cpu_seconds": r.get("cpu_seconds"), "peak_rss_mb": r.get("peak_rss_mb")})
        elif r.get("event") == "estimate" and r.get("ok"):
            rows.append({"kind": "estimate", "cond": r["cond"], "seed": r["seed"],
                         "replicate": None, "wall_seconds": r["wall_seconds"],
                         "cpu_seconds": r.get("cpu_seconds"), "peak_rss_mb": r.get("peak_rss_mb")})
    return pd.DataFrame(rows)


def _write(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, float_format="%.6g", lineterminator="\n")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--figures", action="store_true")
    ap.add_argument("--allow-missing", action="store_true",
                    help="aggregate the runs present and list the missing ones")
    a = ap.parse_args(argv)
    proto = json.loads(a.protocol.read_text())
    runs, missing = _load(proto)
    a.dest.mkdir(parents=True, exist_ok=True)
    _write(pd.DataFrame(missing, columns=["cond", "seed"]), a.dest / "missing_runs.csv")
    if missing and not a.allow_missing:
        raise SystemExit(f"{len(missing)} expected runs have no panel.json (see "
                         f"{a.dest / 'missing_runs.csv'}); rerun them or pass --allow-missing")

    est = estimator_rows(runs)  # includes the refit-bootstrap DM as 'dm_refit'
    _write(est, a.dest / "estimates_by_run.csv")
    _write(error_summary(est), a.dest / "error_summary.csv")
    vals, gaps = reference_rows(runs)
    _write(vals, a.dest / "reference_values_by_run.csv")
    _write(gaps, a.dest / "reference_gaps_by_run.csv")
    sel = selection_rows(runs)
    _write(sel, a.dest / "selection_by_run.csv")
    _write(selection_summary(sel), a.dest / "selection_summary.csv")
    _write(selection_sensitivity(runs, list(proto["candidates"])),
           a.dest / "selection_sensitivity_to_reference_replicates.csv")
    conds = list(proto["conditions"])
    pairs = [(f"{w}_on", f"{w}_off") for w in ("A", "B")
             if f"{w}_on" in conds and f"{w}_off" in conds]
    pairs += [(f"B_{s}", f"A_{s}") for s in ("on", "off")
              if f"A_{s}" in conds and f"B_{s}" in conds]
    _write(paired_contrasts(est, pairs), a.dest / "paired_condition_contrasts.csv")
    _write(regime_contrast(est), a.dest / "regime_contrast_nontabular_minus_tabular.csv")
    _write(family_agreement(est), a.dest / "log_family_agreement.csv")
    _write(replicate_consistency(runs), a.dest / "reference_replicate_consistency.csv")
    _write(interval_diagnostic(est), a.dest / "interval_diagnostic.csv")
    dose = []
    for run in runs:
        for tname, t in run["targets"].items():
            dose.append({"cond": run["cond"], "seed": run["seed"], "target": tname, **t["dose"]})
    _write(pd.DataFrame(dose), a.dest / "support_and_dose_by_run.csv")
    ident = []
    for run in runs:
        for tname, t in run["targets"].items():
            tab = t["tabular"]
            ident.append({"cond": run["cond"], "seed": run["seed"], "target": tname,
                          "abs_dm_minus_is": abs(tab["dm"]["value"] - tab["is"]["value"]),
                          "abs_dm_minus_snips": abs(tab["dm"]["value"] - tab["snips"]["value"])})
    _write(pd.DataFrame(ident), a.dest / "tabular_identity_dm_is_snips.csv")
    rarity = pd.DataFrame([{"cond": r["cond"], "seed": r["seed"], "recovery_12m": r["recovery_12m"],
                            "explore_share": r["explore_share"], "n_cohort": r["n_cohort"],
                            "logged_mean": r["logged_mean"]} for r in runs])
    _write(rarity, a.dest / "rarity_and_cohort_by_run.csv")
    gbm = []
    for run in runs:
        for tname, t in run["targets"].items():
            if "nontabular" in t:
                gbm.append({"cond": run["cond"], "seed": run["seed"], "target": tname,
                            **t["nontabular"]["diagnostics"]})
    if gbm:
        g = pd.DataFrame(gbm)
        g["propensity_mean_vs_match_rate"] = g["propensity_mean_vs_match_rate"].map(json.dumps)
        _write(g, a.dest / "nontabular_diagnostics_by_run.csv")
    jobs = _jobs_table(proto)
    if not jobs.empty:
        _write(jobs.sort_values(["kind", "cond", "seed", "replicate"], na_position="first"),
               a.dest / "job_costs.csv")
    manifest = {"protocol": proto["name"], "n_runs": len(runs),
                "runs_expected": len(proto["conditions"]) * len(proto["seeds"]),
                "inputs": {}, "outputs": {}}
    manifest["missing_runs"] = missing
    for run in runs:
        p = _run_path(proto, run["cond"], run["seed"])
        manifest["inputs"][_rel(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(a.dest.glob("*.csv")):
        manifest["outputs"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (a.dest / "aggregate_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    if a.figures:
        _figures(est, sel, a.dest)
    print(json.dumps({"runs": len(runs), "dest": str(a.dest)}))


def _figures(est: pd.DataFrame, sel: pd.DataFrame, dest: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams["pdf.fonttype"] = 42
    summ = error_summary(est)
    keep = [("tabular", "dm"), ("tabular", "dr"), ("tabular", "dm_plus_is"),
            ("tabular", "pilot_is"), ("tabular", "pilot_dr"), ("nontabular", "dm"),
            ("nontabular", "snips"), ("nontabular", "dr"), ("nontabular", "pilot_dr")]
    targets = sorted(t for t in summ["target"].unique() if t != INCUMBENT)
    conds = sorted(summ["cond"].unique())
    fig, axes = plt.subplots(1, len(targets), figsize=(4.2 * len(targets), 4.2), sharey=False)
    axes = np.atleast_1d(axes)
    for ax, target in zip(axes, targets, strict=True):
        for i, cond in enumerate(conds):
            for j, (regime, key) in enumerate(keep):
                r = summ[(summ["cond"] == cond) & (summ["target"] == target)
                         & (summ["regime"] == regime) & (summ["estimator"] == key)]
                if r.empty or not r["n_defined"].iloc[0]:
                    continue
                x = j + (i - (len(conds) - 1) / 2) * 0.18
                ax.errorbar(x, r["mean_error"].iloc[0], yerr=1.96 * r["se_mean_error"].iloc[0],
                            fmt="o", ms=4, capsize=2, color=f"C{i}",
                            label=cond if j == 0 else None)
        ax.axhline(0, color="0.5", lw=0.8)
        ax.set_xticks(range(len(keep)))
        ax.set_xticklabels([f"{k}\n({'T' if r == 'tabular' else 'G'})" for r, k in keep],
                           fontsize=7, rotation=60)
        ax.set_title(DISPLAY.get(target, target))
        ax.set_ylabel("mean error vs reference (US$/decision), ±1.96 SE")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(dest / "fig_errors_by_condition.pdf")
    fig.savefig(dest / "fig_errors_by_condition.png", dpi=150)
    plt.close(fig)

    ss = selection_summary(sel)
    ss = ss[ss["n_defined"] > 0]
    labels = sorted({(r, k) for r, k in zip(ss["regime"], ss["estimator"], strict=True)})
    fig, ax = plt.subplots(figsize=(max(6, 0.55 * len(labels)), 3.8))
    for i, cond in enumerate(conds):
        for j, (regime, key) in enumerate(labels):
            r = ss[(ss["cond"] == cond) & (ss["regime"] == regime) & (ss["estimator"] == key)]
            if r.empty:
                continue
            x = j + (i - (len(conds) - 1) / 2) * 0.18
            ax.errorbar(x, r["mean_regret"].iloc[0], yerr=1.96 * r["se_mean_regret"].iloc[0],
                        fmt="o", ms=4, capsize=2, color=f"C{i}", label=cond if j == 0 else None)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([f"{k}\n({'T' if r == 'tabular' else 'G'})" for r, k in labels],
                       fontsize=7, rotation=60)
    ax.axhline(0, color="0.5", lw=0.8)
    ax.set_ylabel("mean recovery regret (US$/decision), ±1.96 SE")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(dest / "fig_selection_regret.pdf")
    fig.savefig(dest / "fig_selection_regret.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
