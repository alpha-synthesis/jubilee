"""Annotated direct method (DM+) from the campaign's run extracts — no simulation.

For every run directory under a runs root (``<cond>/seed<S>/`` holding
``logs.parquet``, ``annotator.parquet``, ``panel.json`` and, when the run was
also estimated for the cash, ``panel_cash.json``), rebuild the tabular logs
exactly as the panel does (``tmlr_campaign.tabular_logs``: tercile cut points
from the logged cohort, 36 contexts, 45 action cells, within-context
propensities), rebuild each target's annotation truth matrix from the
annotator source (``truth_matrix_from_twin``) and compute, per target and per
available reward, the annotated direct method: the tabular reward model fit on
the factual logs plus one annotation per logged context at the target's cell
(annotation weight 1), read at the target's cells. Unlike DM+-IS there is no
importance-sampling correction, so a biased annotator biases the estimate.

Two annotators per target: ``protocol`` — the campaign's degraded one (bias
and noise fractions of the protocol times the largest absolute cell value,
Gaussian draws from the panel's ``annotator_noise`` seed, so the annotations
are the campaign's own) — and ``exact`` (bias 0, noise 0). Estimators:
``dm_plus_xfit`` (two folds, the panel's fold seed), ``dm_plus_insample`` (one
model fit on everything), ``dm_plus_is_xfit`` (the campaign's DM+-IS, recomputed
as a reproduction check) and, with annotator ``none``, the plain tabular ``dm``
of the panel. Errors are against the reward's reference mean (the panel's
reference block, or the run's reference files when the panel is missing).

Outputs in ``--dest``: ``dm_plus_by_run.csv`` (cond, seed, target, reward,
annotator, estimator, value, reference_mean, error), ``dm_plus_summary.csv``
(per condition, target, reward, annotator, estimator: mean error ± SE over
seeds, RMSE), ``panel_reproduction.csv`` (recomputed ``dm`` and ``dm_plus_is``
against the panel's values), ``skipped_runs.csv`` and ``manifest.json``.

Usage::

    python scripts/tmlr_evidence/dm_plus_from_extracts.py --protocol P.json --dest DIR \
        [--runs ROOT] [--workers N]
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

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import tmlr_campaign as tc  # noqa: E402  (also puts src/ on the path)

from ope_bench.annotator import (  # noqa: E402
    AugmentedRewardModel,
    OracleAnnotator,
    build_annotations,
    dm_plus_is_value,
)
from ope_bench.estimators import (  # noqa: E402
    DeterministicPolicy,
    TabularRewardModel,
    cross_fitted_dm_value,
    direct_method_value,
)
from ope_bench.panel import N_ACTIONS, N_CONTEXTS, truth_matrix_from_twin  # noqa: E402

ANNOTATION_WEIGHT = 1.0
N_FOLDS = 2


def discover_runs(root: Path) -> list[tuple[str, int, Path]]:
    out = []
    for d in sorted(root.glob("*/seed*")):
        if d.is_dir() and d.name[4:].isdigit():
            out.append((d.parent.name, int(d.name[4:]), d))
    return out


def _reference_mean(proto: dict, cond: str, seed: int, d: Path, reward: str) -> dict:
    """The reward's reference means: from its panel when estimated, else from
    the run's reference files (same summary as the panel's)."""
    p = d / tc.panel_file(reward)
    if p.exists():
        return json.loads(p.read_text())["reference"]["mean"]
    local = {**proto, "out_dir": str(d.parents[1])}
    return tc.reference_summary(local, cond, seed, reward)["mean"]


def available_rewards(cohort: pd.DataFrame, ann: pd.DataFrame, targets: list[str]) -> list[str]:
    out = []
    for reward, col in tc.REWARD_COLUMNS.items():
        if col in cohort and all(tc.annotator_column(reward, t) in ann for t in targets):
            out.append(reward)
    return out


def dm_plus_run(proto: dict, cond: str, seed: int, d: Path) -> dict:
    t0 = time.time()
    panel = json.loads((d / "panel.json").read_text())
    seeds = panel["seeds"]
    cohort = tc._read_parquet(d / "logs.parquet")
    ann = tc._read_parquet(d / "annotator.parquet")
    targets = tc.targets_of(proto)
    bias_frac = float(proto["annotator"]["bias_frac"])
    noise_frac = float(proto["annotator"]["noise_frac"])
    rows, checks = [], []
    for reward in available_rewards(cohort, ann, targets):
        terciles, logs = tc.tabular_logs(cohort, reward)
        ref = _reference_mean(proto, cond, seed, d, reward)
        rp = d / tc.panel_file(reward)
        reward_panel = json.loads(rp.read_text()) if rp.exists() else None
        for name in targets:
            target = tc.CANDIDATES[name]
            pol = DeterministicPolicy(target.actions_per_context(), N_ACTIONS)
            a_coh = pd.DataFrame({"start_balance": ann["start_balance"], "dpd": ann["dpd"],
                                  "reward": ann[tc.annotator_column(reward, name)]})
            tmat = truth_matrix_from_twin(a_coh, terciles, target)
            scale = float(np.abs(tmat).max())
            base = {"cond": cond, "seed": seed, "target": name, "reward": reward}

            def add(annotator, estimator, value):
                rows.append({**base, "annotator": annotator, "estimator": estimator,
                             "value": value, "reference_mean": ref[name],
                             "error": value - ref[name]})

            plain = TabularRewardModel(N_CONTEXTS, N_ACTIONS, resolution="full").fit(
                logs["context"], logs["action"], logs["reward"])
            dm = direct_method_value(logs, pol, plain)
            add("none", "dm", dm)
            if reward_panel is not None:
                pv = reward_panel["targets"][name]["tabular"]["dm"]["value"]
                checks.append({**base, "estimator": "dm", "panel_value": pv, "recomputed": dm,
                               "abs_diff": abs(dm - pv)})
            for label, (bias, noise) in (("protocol", (bias_frac * scale, noise_frac * scale)),
                                         ("exact", (0.0, 0.0))):
                annotator = OracleAnnotator(tmat, bias=bias, noise=noise)
                annotations = build_annotations(
                    logs, pol, annotator, rng=np.random.default_rng(seeds["annotator_noise"]))

                def fit_fn(train_logs, annotations=annotations):
                    return AugmentedRewardModel(N_CONTEXTS, N_ACTIONS, ANNOTATION_WEIGHT).fit(
                        train_logs, annotations)

                add(label, "dm_plus_xfit",
                    cross_fitted_dm_value(logs, pol, fit_fn, n_folds=N_FOLDS, seed=seeds["folds"]))
                add(label, "dm_plus_insample", direct_method_value(logs, pol, fit_fn(logs)))
                if label == "protocol":
                    v = dm_plus_is_value(logs, annotations, pol, N_CONTEXTS, N_ACTIONS,
                                         annotation_weight=ANNOTATION_WEIGHT, cross_fit=True,
                                         seed=seeds["folds"])
                    add(label, "dm_plus_is_xfit", v)
                    if reward_panel is not None:
                        pv = reward_panel["targets"][name]["tabular"]["dm_plus_is"]["value"]
                        checks.append({**base, "estimator": "dm_plus_is", "panel_value": pv,
                                       "recomputed": v, "abs_diff": abs(v - pv)})
    return {"cond": cond, "seed": seed, "rows": rows, "checks": checks,
            "wall_seconds": round(time.time() - t0, 1)}


def _worker(args):
    proto, cond, seed, d = args
    try:
        return dm_plus_run(proto, cond, seed, d)
    except Exception as exc:  # recorded, never swallowed
        return {"cond": cond, "seed": seed, "error": repr(exc), "trace": traceback.format_exc()}


def _se(x: np.ndarray) -> float:
    return float(x.std(ddof=1) / math.sqrt(len(x))) if len(x) > 1 else float("nan")


def summarize(by_run: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["cond", "target", "reward", "annotator", "estimator"]
    for key, g in by_run.groupby(keys, sort=True):
        e = g["error"].to_numpy(np.float64)
        rows.append({**dict(zip(keys, key, strict=True)), "n_seeds": len(g),
                     "mean_value": float(g["value"].mean()),
                     "mean_reference": float(g["reference_mean"].mean()),
                     "mean_error": float(e.mean()), "se_mean_error": _se(e),
                     "rmse": float(np.sqrt((e ** 2).mean()))})
    return pd.DataFrame(rows)


def _write(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    df = df if not df.empty else pd.DataFrame(columns=columns)
    df.to_csv(path, index=False, float_format="%.10g", lineterminator="\n")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--dest", required=True, type=Path)
    ap.add_argument("--runs", type=Path, default=None,
                    help="runs root (default: the protocol's out_dir)")
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args(argv)
    proto = tc.load_protocol(a.protocol)
    root = a.runs if a.runs is not None else REPO / proto["out_dir"]
    runs = discover_runs(root)
    required = ("logs.parquet", "annotator.parquet", "panel.json")
    todo, skipped = [], []
    for cond, seed, d in runs:
        missing = [f for f in required if not (d / f).exists()]
        if missing:
            skipped.append({"cond": cond, "seed": seed, "missing": " ".join(missing)})
        else:
            todo.append((proto, cond, seed, d))
    t0 = time.time()
    results = []
    if a.workers > 1 and len(todo) > 1:
        with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
            for res in pool.imap_unordered(_worker, todo):
                results.append(res)
                print(json.dumps({k: res[k] for k in res if k not in ("rows", "checks", "trace")}),
                      flush=True)
    else:
        for job in todo:
            res = _worker(job)
            results.append(res)
            print(json.dumps({k: res[k] for k in res if k not in ("rows", "checks", "trace")}),
                  flush=True)
    failed = [r for r in results if "error" in r]
    rows = [row for r in results if "rows" in r for row in r["rows"]]
    checks = [c for r in results if "checks" in r for c in r["checks"]]
    a.dest.mkdir(parents=True, exist_ok=True)
    by_run = pd.DataFrame(rows)
    cols = ["cond", "seed", "target", "reward", "annotator", "estimator", "value",
            "reference_mean", "error"]
    if not by_run.empty:
        by_run = by_run[cols].sort_values(["cond", "seed", "target", "reward", "annotator",
                                           "estimator"], kind="mergesort")
    _write(by_run, a.dest / "dm_plus_by_run.csv", cols)
    _write(summarize(by_run) if not by_run.empty else pd.DataFrame(),
           a.dest / "dm_plus_summary.csv",
           ["cond", "target", "reward", "annotator", "estimator", "n_seeds", "mean_value",
            "mean_reference", "mean_error", "se_mean_error", "rmse"])
    ck = pd.DataFrame(checks)
    ck_cols = ["cond", "seed", "target", "reward", "estimator", "panel_value", "recomputed",
               "abs_diff"]
    if not ck.empty:
        ck = ck[ck_cols].sort_values(["cond", "seed", "target", "reward", "estimator"],
                                     kind="mergesort")
    _write(ck, a.dest / "panel_reproduction.csv", ck_cols)
    _write(pd.DataFrame(skipped + [{"cond": r["cond"], "seed": r["seed"], "missing": r["error"]}
                                   for r in failed]),
           a.dest / "skipped_runs.csv", ["cond", "seed", "missing"])
    manifest = {"protocol": str(a.protocol), "protocol_sha256": proto["_sha256"],
                "protocol_name": proto["name"], "runs_root": str(root),
                "annotator": proto["annotator"], "annotation_weight": ANNOTATION_WEIGHT,
                "n_folds": N_FOLDS, "runs_found": len(runs),
                "runs_done": len(results) - len(failed),
                "runs_failed": [{"cond": r["cond"], "seed": r["seed"], "error": r["error"]}
                                for r in failed],
                "runs_skipped": skipped, "code": tc.code_fingerprint(),
                "max_abs_panel_reproduction_diff": (float(ck["abs_diff"].max())
                                                    if not ck.empty else None),
                "wall_seconds": round(time.time() - t0, 1),
                "outputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sorted(a.dest.glob("*.csv"))}}
    (a.dest / "manifest.json").write_text(json.dumps(manifest, indent=2, default=tc._json_default))
    print(json.dumps({"runs_done": manifest["runs_done"], "runs_failed": len(failed),
                      "runs_skipped": len(skipped), "dest": str(a.dest),
                      "max_abs_panel_reproduction_diff":
                          manifest["max_abs_panel_reproduction_diff"]}))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
