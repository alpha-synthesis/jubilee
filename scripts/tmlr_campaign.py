"""Revision campaign driver: simulation jobs, estimation, provenance.

A run is one (condition, seed). Its simulations are independent jobs:

* ``logs``       replicate 0 under the behaviour policy (incumbent + ε): the
                 month-0 explorable cohort with observable covariates (and
                 ``hidden_*`` columns for diagnostics only), plus the 12-month
                 recovery rate of all loans.
* ``annotator``  replicate 1 under every target: per-loan rewards, used only
                 to build the degraded annotator of DM+-IS.
* ``reference``  replicate r >= 2 under every candidate (incumbent included)
                 on the same population: per-candidate cohort means and the
                 per-loan covariance matrix of the candidates' rewards.

Every replicate shares the world's regional shocks (seed) and nothing else, so
the reference replicates are independent of the logs and of the annotator's
source. ``estimate`` then runs, per (condition, seed) and per protocol reward
(``rewards``, default ``["score"]``): the tabular panel with its archived
interval construction, the refit-bootstrap DM, the gradient-boosted panel, the
reference summaries and the policy selection. The score's panel is
``panel.json`` (unchanged format); another reward's is ``panel_<reward>.json``,
built from the same logs, annotations and reference replicates with that
reward's column (``cash``: the cash collected in the window).

Usage::

    python scripts/tmlr_campaign.py plan     --protocol PROTOCOL.json
    python scripts/tmlr_campaign.py simulate --protocol PROTOCOL.json --workers 40
    python scripts/tmlr_campaign.py estimate --protocol PROTOCOL.json --workers 12
    python scripts/tmlr_campaign.py status   --protocol PROTOCOL.json

Outputs go to ``<out_dir>/<condition>/seed<S>/``; finished jobs are skipped,
so both stages are resume-safe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
import platform
import resource
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from collection_simulator.config import load_config  # noqa: E402
from collection_simulator.dictionaries import (  # noqa: E402
    GENDERS,
    INCOME_BANDS,
    LOCATIONS,
    PRODUCTS,
)
from collection_simulator.generator import (  # noqa: E402
    CASH_DEFINITION,
    GENERATOR_VERSION,
    RNG_SCHEME,
    SCORE_DEFINITION,
    derived_seed,
    simulate_cohort,
)
from ope_bench.panel import (  # noqa: E402
    EXPLORE_MAX_LIQ_DAYS,
    EXPLORE_STATES,
    N_ACTIONS,
    PI_FAR,
    PI_NEAR,
    PI_STAGE,
    balance_terciles,
    build_logs,
    dm_refit_bootstrap,
    estimate_panel,
    truth_matrix_from_twin,
)

# Seed roles outside the generator (generator roles are 0..4).
ROLE_BOOTSTRAP, ROLE_FOLDS, ROLE_ANNOTATOR, ROLE_GBM = 16, 17, 18, 19
INCUMBENT = "pi_b"
CATEGORIES = {
    "product_type": [p["product_type"] for p in PRODUCTS],
    "uf": [loc["uf"] for loc in LOCATIONS],
    "gender": list(GENDERS),
    "income_band": [b["band"] for b in INCOME_BANDS],
}
TABULAR = ("dm", "dm_blind", "is", "snips", "dr", "dm_plus_is", "pilot_is", "pilot_dr")
NONTABULAR = ("dm", "is", "snips", "dr", "pilot_dr")
# Rewards a run can be estimated for, with the cohort column that carries each
# one: the evaluation score (the ``reward`` column, the campaign's reward) and
# the cash collected inside the window, both from the same simulation.
REWARD_COLUMNS = {"score": "reward", "cash": "cash_within_h"}
REWARD_DEFINITIONS = {"score": SCORE_DEFINITION, "cash": CASH_DEFINITION}


@dataclass(frozen=True)
class BinUniformTarget:
    """Diagnostic twin of a fixed target whose month-0 dose is spread uniformly
    over the target's discount bin instead of sitting at the bin center. The
    dose is a deterministic, equidistributed function of the loan's start
    balance (Weyl sequence over cents), so the per-loan coupling with the
    center-dose target is preserved."""

    name: str
    channel: str
    lo: float
    hi: float

    def generator_policy(self):
        phi = (math.sqrt(5.0) - 1.0) / 2.0

        def _policy(*, month, state, days_in_credito_em_liquidacao, outstanding_balance, **_):
            if (month == 0 and state in EXPLORE_STATES
                    and days_in_credito_em_liquidacao <= EXPLORE_MAX_LIQ_DAYS):
                frac = (round(outstanding_balance * 100) * phi) % 1.0
                return self.channel, min(self.lo + (self.hi - self.lo) * frac, self.hi - 1e-4)
            return None

        return _policy


CANDIDATES = {
    INCUMBENT: None,
    "pi_near": PI_NEAR,
    "pi_far": PI_FAR,
    "pi_stage": PI_STAGE,
    "pi_near_binU": BinUniformTarget("pi_near_binU", "sms", 0.10, 0.15),
    "pi_far_binU": BinUniformTarget("pi_far_binU", "field_visit", 0.25, 0.30),
}


# ── provenance ─────────────────────────────────────────────────────────────
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_fingerprint() -> dict:
    """Content hash of the code that can affect a result (works without git)."""
    files = sorted(
        [p for p in (REPO / "src").rglob("*.py")]
        + [REPO / "scripts" / "tmlr_campaign.py", REPO / "pyproject.toml"]
    )
    h = hashlib.sha256()
    for p in files:
        if p.exists():
            h.update(str(p.relative_to(REPO)).encode() + b"\0" + _sha256(p).encode() + b"\0")
    info = {"tree_sha256": h.hexdigest(), "n_files": len(files)}
    try:
        head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"],
                               capture_output=True, text=True, check=True).stdout
        info.update({"git_head": head, "git_dirty": bool(dirty.strip())})
    except Exception:
        info.update({"git_head": "unavailable", "git_dirty": None})
    return info


def environment() -> dict:
    import duckdb

    env = {"python": platform.python_version(), "platform": platform.platform(),
           "numpy": np.__version__, "pandas": pd.__version__, "duckdb": duckdb.__version__}
    try:
        import sklearn

        env["scikit_learn"] = sklearn.__version__
    except ImportError:
        env["scikit_learn"] = None
    env["omp_num_threads"] = os.environ.get("OMP_NUM_THREADS")
    return env


# ── protocol / jobs ───────────────────────────────────────────────────────
def load_protocol(path: Path) -> dict:
    raw = Path(path).read_bytes()
    proto = json.loads(raw)
    proto["_path"] = str(path)
    proto["_sha256"] = hashlib.sha256(raw).hexdigest()
    validate_protocol(proto)
    return proto


def validate_protocol(proto: dict) -> None:
    """Refuse protocols that would silently corrupt a campaign."""
    def _ints(x, name):
        if not isinstance(x, list) or not all(isinstance(v, int) and not isinstance(v, bool)
                                              for v in x):
            raise ValueError(f"protocol.{name} must be a list of integers, got {x!r}")
        if len(set(x)) != len(x):
            raise ValueError(f"protocol.{name} has duplicates: {x}")

    _ints(proto["seeds"], "seeds")
    _ints(proto["reference_replicates"], "reference_replicates")
    reps = set(proto["reference_replicates"])
    ann = proto.get("annotator_replicate")
    if ann is not None and ann != 1:
        raise ValueError("protocol.annotator_replicate must be 1 (or null)")
    if not reps or min(reps) < 2:
        raise ValueError("reference replicates must be >= 2 (0 = logs, 1 = annotator source)")
    if len(reps) < 2:
        raise ValueError("at least two reference replicates are needed for the between-"
                         "replicate check")
    unknown = set(proto["candidates"]) | set(proto.get("extra_reference_candidates", []))
    unknown -= set(CANDIDATES)
    if unknown or INCUMBENT not in proto["candidates"]:
        raise ValueError(f"unknown candidates {sorted(unknown)} or incumbent missing")
    for c in proto["candidates"]:
        if c != INCUMBENT and not hasattr(CANDIDATES[c], "actions_per_context"):
            raise ValueError(f"candidate {c!r} cannot be estimated (diagnostic only)")
    if proto.get("nontabular"):
        g = proto.get("gbm")
        if not isinstance(g, dict) or int(g.get("n_folds", 2)) != 2:
            raise ValueError("protocol.gbm must be a dict with n_folds == 2 (the tabular "
                             "cross-fitting uses two folds; both regimes share the folds)")
    rewards = proto.get("rewards", ["score"])
    if (not isinstance(rewards, list) or not rewards
            or not all(isinstance(r, str) for r in rewards) or len(set(rewards)) != len(rewards)):
        raise ValueError(f"protocol.rewards must be a non-empty list of distinct reward names, "
                         f"got {rewards!r}")
    if set(rewards) - set(REWARD_COLUMNS):
        raise ValueError(f"unknown rewards {sorted(set(rewards) - set(REWARD_COLUMNS))}; "
                         f"known: {sorted(REWARD_COLUMNS)}")
    for k, v in proto.items():
        if isinstance(v, str) and v.startswith("TO_BE_SET"):
            raise ValueError(f"protocol.{k} is still a placeholder")


def condition_config(proto: dict, cond: str, seed: int) -> dict:
    cfg = load_config(REPO / proto["conditions"][cond])
    cfg["seed"] = int(seed)
    cfg["population"]["borrowers"] = int(proto["borrowers"])
    return cfg


def run_dir(proto: dict, cond: str, seed: int) -> Path:
    return REPO / proto["out_dir"] / cond / f"seed{seed}"


def targets_of(proto: dict) -> list[str]:
    return [c for c in proto["candidates"] if c != INCUMBENT]


def reference_candidates(proto: dict) -> list[str]:
    return list(proto["candidates"]) + list(proto.get("extra_reference_candidates", []))


def rewards_of(proto: dict) -> list[str]:
    return list(proto.get("rewards", ["score"]))


def panel_file(reward: str) -> str:
    """The score keeps the archived file name; other rewards get their own."""
    return "panel.json" if reward == "score" else f"panel_{reward}.json"


def reward_values(cohort: pd.DataFrame, reward: str) -> np.ndarray:
    return cohort[REWARD_COLUMNS[reward]].to_numpy(np.float64)


def annotator_column(reward: str, target: str) -> str:
    """Column of ``annotator.parquet`` holding the target's per-loan reward."""
    return f"reward_{target}" if reward == "score" else f"{reward}_{target}"


def tabular_logs(cohort: pd.DataFrame, reward: str = "score") -> tuple[np.ndarray, dict]:
    """The panel's bandit view of the logged cohort for one reward: tercile cut
    points from the logged cohort, contexts, actions, within-context
    propensities and ε metadata as :func:`ope_bench.panel.build_logs`, with the
    reward column selected by ``reward`` (the score is ``build_logs``'s own)."""
    terciles = balance_terciles(cohort)
    logs = build_logs(cohort, terciles)
    logs["reward"] = reward_values(cohort, reward)
    return terciles, logs


def jobs(proto: dict) -> list[dict]:
    out = []
    for cond in proto["conditions"]:
        for seed in proto["seeds"]:
            out.append({"kind": "logs", "cond": cond, "seed": seed})
            if proto.get("annotator_replicate") is not None:
                out.append({"kind": "annotator", "cond": cond, "seed": seed})
            for r in proto["reference_replicates"]:
                out.append({"kind": "reference", "cond": cond, "seed": seed, "replicate": r})
    return out


def job_path(proto: dict, job: dict) -> Path:
    d = run_dir(proto, job["cond"], job["seed"])
    if job["kind"] == "logs":
        return d / "logs_meta.json"
    if job["kind"] == "annotator":
        return d / "annotator_meta.json"
    return d / f"reference_r{job['replicate']}.json"


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    import duckdb

    tmp = path.with_suffix(".tmp.parquet")
    con = duckdb.connect()
    try:
        con.register("df", df)
        con.execute(f"COPY df TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)")
    finally:
        con.close()
    tmp.replace(path)


def _read_parquet(path: Path) -> pd.DataFrame:
    import duckdb

    con = duckdb.connect()
    try:
        return con.execute(f"SELECT * FROM read_parquet('{path}')").df()
    finally:
        con.close()


def _write_json(obj: dict, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=_json_default))
    tmp.replace(path)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def _usage() -> dict:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return {"cpu_seconds": round(ru.ru_utime + ru.ru_stime, 1), "peak_rss_mb": ru.ru_maxrss // 1024}


def _cohort_kw(proto: dict) -> dict:
    return {"batch_size": int(proto["batch_size"]), "horizon": int(proto["horizon"])}


def run_job(proto: dict, job: dict) -> dict:
    t0 = time.time()
    cfg = condition_config(proto, job["cond"], job["seed"])
    d = run_dir(proto, job["cond"], job["seed"])
    d.mkdir(parents=True, exist_ok=True)
    base = {"job": job, "protocol": proto["name"], "generator_version": GENERATOR_VERSION,
            "rng_scheme": RNG_SCHEME, "reward_definition": SCORE_DEFINITION,
            "reward_definitions": dict(REWARD_DEFINITIONS),
            "code": proto["_code"], "environment": environment(),
            "config_path": proto["conditions"][job["cond"]],
            "config_file_sha256": _sha256(REPO / proto["conditions"][job["cond"]]),
            "config_effective_sha256": hashlib.sha256(
                json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()}
    if job["kind"] == "logs":
        cohort, meta = simulate_cohort(
            cfg, policy=None, replicate=0, months=int(proto.get("logs_months", 12)),
            simulate_all_loans=True, with_covariates=True, **_cohort_kw(proto))
        _write_parquet(cohort, d / "logs.parquet")
        out = {**base, "meta": meta,
               "n_cohort": int(len(cohort)),
               "explore_share": float(cohort["is_exploration"].mean()),
               "logged_mean_reward": float(cohort["reward"].mean()),
               "logged_mean_cash": float(cohort["cash_within_h"].mean()),
               "paid_rate_h": float(cohort["paid_within_h"].mean()),
               "logs_sha256": _sha256(d / "logs.parquet")}
    elif job["kind"] == "annotator":
        r = int(proto["annotator_replicate"])
        cols, loan_ids = {}, None
        for name in targets_of(proto):
            coh, meta = simulate_cohort(cfg, policy=CANDIDATES[name].generator_policy(),
                                        replicate=r, **_cohort_kw(proto))
            if loan_ids is None:
                loan_ids = coh["loan_id"].to_numpy()
                cols.update({"loan_id": loan_ids, "start_balance": coh["start_balance"],
                             "dpd": coh["dpd"]})
            elif not np.array_equal(loan_ids, coh["loan_id"].to_numpy()):
                raise AssertionError("annotator cohorts differ across targets")
            cols[f"reward_{name}"] = coh["reward"].to_numpy()
            cols[f"cash_{name}"] = coh["cash_within_h"].to_numpy()
        df = pd.DataFrame(cols)
        _write_parquet(df, d / "annotator.parquet")
        out = {**base, "meta": meta, "n_cohort": int(len(df)),
               "means": {k[7:]: float(df[k].mean()) for k in df if k.startswith("reward_")},
               "means_cash": {k[5:]: float(df[k].mean()) for k in df if k.startswith("cash_")},
               "annotator_sha256": _sha256(d / "annotator.parquet")}
    else:
        r = int(job["replicate"])
        names = reference_candidates(proto)
        rewards, cash, loan_ids, metas = [], [], None, {}
        for name in names:
            pol = CANDIDATES[name]
            coh, meta = simulate_cohort(
                cfg, policy=None if pol is None else pol.generator_policy(),
                replicate=r, **_cohort_kw(proto))
            if loan_ids is None:
                loan_ids = coh["loan_id"].to_numpy()
            elif not np.array_equal(loan_ids, coh["loan_id"].to_numpy()):
                raise AssertionError("reference cohorts differ across candidates")
            rewards.append(coh["reward"].to_numpy(np.float64))
            cash.append(coh["cash_within_h"].to_numpy(np.float64))
            metas[name] = {"paid_rate_h": float(coh["paid_within_h"].mean())}
        mat = np.vstack(rewards)
        cmat = np.vstack(cash)
        # ``means``/``cov`` are the score (unchanged layout); the cash collected in
        # the window, from the same cohorts and draws, sits in its own block.
        out = {**base, "meta": meta, "candidates": names, "n_cohort": int(mat.shape[1]),
               "means": dict(zip(names, mat.mean(axis=1).tolist(), strict=True)),
               "cov": np.cov(mat, ddof=1).tolist(), "per_candidate": metas,
               "cash": {"definition": CASH_DEFINITION,
                        "means": dict(zip(names, cmat.mean(axis=1).tolist(), strict=True)),
                        "cov": np.cov(cmat, ddof=1).tolist()}}
    out["wall_seconds"] = round(time.time() - t0, 1)
    out["usage"] = _usage()
    _write_json(out, job_path(proto, job))
    return {"job": job, "ok": True, "wall_seconds": out["wall_seconds"], **out["usage"]}


def _job_worker(args):
    proto, job = args
    try:
        return run_job(proto, job)
    except Exception as exc:  # recorded, never swallowed silently
        return {"job": job, "ok": False, "error": repr(exc), "trace": traceback.format_exc()}


# ── estimation ─────────────────────────────────────────────────────────────
def _reference_block(rep: dict, reward: str, path: Path) -> dict:
    """The ``means``/``cov`` pair of one reference record for ``reward``: the
    record itself for the score, its ``<reward>`` block otherwise."""
    if reward == "score":
        return rep
    block = rep.get(reward)
    if not isinstance(block, dict) or "means" not in block or "cov" not in block:
        raise RuntimeError(f"{path}: no {reward!r} block (simulated before the reward was "
                           "recorded?)")
    return block


def reference_summary(proto: dict, cond: str, seed: int, reward: str = "score") -> dict:
    """Mean over replicates, its Monte-Carlo SE two ways (between replicates;
    pooled within-replicate per-loan variance), and paired gaps with their SE
    and correlation, for one reward."""
    reps, blocks = [], []
    for r in proto["reference_replicates"]:
        path = run_dir(proto, cond, seed) / f"reference_r{r}.json"
        rep = json.loads(path.read_text())
        reps.append(rep)
        blocks.append(_reference_block(rep, reward, path))
    names = reps[0]["candidates"]
    R = len(reps)
    means = np.array([[b["means"][c] for c in names] for b in blocks])  # R × K
    covs = np.array([b["cov"] for b in blocks])  # R × K × K
    ns = np.array([rep["n_cohort"] for rep in reps], dtype=np.float64)
    m = means.mean(axis=0)
    # variance of the mean of R replicate means, from within-replicate per-loan covariances
    within = (covs / ns[:, None, None]).sum(axis=0) / R**2  # K × K
    between = np.cov(means.T, ddof=1) / R if R > 1 else np.full((len(names),) * 2, np.nan)
    out = {"candidates": names, "R": R, "reward": reward, "n_per_replicate": ns.tolist(),
           "replicate_means": means.tolist(),
           "mean": dict(zip(names, m.tolist(), strict=True)),
           "se_within": dict(zip(names, np.sqrt(np.diag(within)).tolist(), strict=True)),
           "se_between": dict(zip(names, np.sqrt(np.diag(between)).tolist(), strict=True)),
           "se_one_replicate": dict(zip(
               names, np.sqrt(np.mean([np.diag(c) / n for c, n in zip(covs, ns)], axis=0)).tolist(),
               strict=True)),
           "gaps": {}}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if j <= i:
                continue
            g = means[:, i] - means[:, j]
            var_w = within[i, i] + within[j, j] - 2 * within[i, j]
            corr = within[i, j] / math.sqrt(within[i, i] * within[j, j])
            out["gaps"][f"{a}-{b}"] = {
                "mean": float(g.mean()), "se_within": math.sqrt(max(var_w, 0.0)),
                "se_between": float(g.std(ddof=1) / math.sqrt(R)) if R > 1 else None,
                "corr_within": float(corr),
                "se_if_independent": math.sqrt(within[i, i] + within[j, j]),
            }
    return out


def _gap(ref: dict, a: str, b: str) -> tuple[float, float]:
    if a == b:
        return 0.0, 0.0
    key = f"{a}-{b}" if f"{a}-{b}" in ref["gaps"] else f"{b}-{a}"
    g = ref["gaps"][key]
    sign = 1.0 if key == f"{a}-{b}" else -1.0
    return sign * g["mean"], g["se_within"]


def selection(est_values: dict[str, float], ref: dict, cands: list[str], z: float) -> dict:
    """Pick argmax of the estimates; grade against the reference with its
    Monte-Carlo uncertainty. ``resolved`` means the reference separates the
    best candidate from the runner-up by more than ``z`` paired SEs."""
    ref_mean = {c: ref["mean"][c] for c in cands}
    order = sorted(cands, key=ref_mean.get, reverse=True)
    best, second = order[0], order[1]
    g12, se12 = _gap(ref, best, second)
    picked = max(cands, key=lambda c: est_values[c])
    regret, regret_se = _gap(ref, best, picked)
    gain, gain_se = _gap(ref, picked, INCUMBENT)
    pairwise = {}
    for i, a in enumerate(cands):
        for b in cands[i + 1:]:
            g, se = _gap(ref, a, b)
            pairwise[f"{a}-{b}"] = {
                "ref_sign": int(np.sign(g)), "resolved": bool(abs(g) > z * se),
                "est_sign": int(np.sign(est_values[a] - est_values[b])),
            }
    return {"picked": picked, "ref_best": best, "ref_runner_up": second,
            "top_gap": g12, "top_gap_se": se12, "top_resolved": bool(g12 > z * se12),
            "correct": picked == best, "regret": regret, "regret_se": regret_se,
            "gain_vs_incumbent": gain, "gain_vs_incumbent_se": gain_se, "pairwise": pairwise}


def _dose_diagnostics(cohort: pd.DataFrame, logs: dict, target) -> dict:
    a_t = target.actions_per_context()[logs["context"]]
    match = logs["action"] == a_t
    d = cohort["discount_logged"].to_numpy(np.float64)
    expl = logs["explored"]
    out = {"n_match": int(match.sum()), "n_anchor": int((match & expl).sum()), "cells": {}}
    # one entry per target action cell (the stage rule has two)
    for cell in sorted(set(target.actions_per_context().tolist())):
        mc = match & (logs["action"] == cell)
        entry = {"n_match": int(mc.sum()), "n_anchor": int((mc & expl).sum())}
        for lab, m in (("incumbent", mc & ~expl), ("explored", mc & expl)):
            entry[f"mean_dose_{lab}"] = float(d[m].mean()) if m.any() else None
        out["cells"][str(cell)] = entry
    n_ctx = len(target.actions_per_context())
    in_cohort = np.bincount(logs["context"], minlength=n_ctx)
    per_ctx = np.bincount(logs["context"][match], minlength=n_ctx)
    present = in_cohort > 0
    unsupported = present & (per_ctx == 0)
    out["contexts_in_cohort"] = int(present.sum())
    out["contexts_without_support"] = int(unsupported.sum())
    out["cohort_share_without_support"] = float(in_cohort[unsupported].sum() / in_cohort.sum())
    out["min_rows_per_present_context"] = int(per_ctx[present].min())
    out["anchors_per_present_context_min"] = int(np.bincount(
        logs["context"][match & expl], minlength=n_ctx)[present].min())
    return out


def _recorded_definition(m: dict, reward: str) -> str | None:
    """The definition a simulation record gives for ``reward``; records written
    before the definitions were listed carry the score in ``meta`` (or, for the
    earliest ones, nowhere: the score was the only reward then)."""
    defs = m.get("reward_definitions")
    if isinstance(defs, dict) and reward in defs:
        return defs[reward]
    if reward == "score":
        return m.get("reward_definition") or m.get("meta", {}).get("reward_definition") \
            or SCORE_DEFINITION
    return None


def check_run_provenance(proto: dict, cond: str, seed: int, reward: str = "score") -> dict:
    """All simulation files of a run must come from the same code, generator
    version and effective config, and record the same definition of the
    estimated reward; otherwise the run mixes worlds (or lacks the reward)."""
    d = run_dir(proto, cond, seed)
    files = [d / "logs_meta.json"] + [d / f"reference_r{r}.json"
                                      for r in proto["reference_replicates"]]
    if proto.get("annotator_replicate") is not None:
        files.append(d / "annotator_meta.json")
    keys = set()
    for f in files:
        m = json.loads(f.read_text())
        definition = _recorded_definition(m, reward)
        if definition is None:
            raise RuntimeError(f"{f}: does not record the {reward!r} reward")
        keys.add((m["code"]["tree_sha256"], m["generator_version"], m["rng_scheme"],
                  m["config_effective_sha256"], m["meta"]["batch_size"], reward, definition))
    if len(keys) != 1:
        raise RuntimeError(f"{cond}/seed{seed}: simulation files disagree on code/config: {keys}")
    tree, gen, rng, cfg, batch, _, definition = keys.pop()
    return {"code_tree_sha256": tree, "generator_version": gen, "rng_scheme": rng,
            "config_effective_sha256": cfg, "batch_size": batch, "reward": reward,
            "reward_definition": definition, "files_checked": len(files)}


def estimate_run(proto: dict, cond: str, seed: int) -> dict:
    """One panel per protocol reward from the run's simulation files; a reward
    whose panel file already exists is skipped. Returns ``{reward: panel}`` for
    the panels written."""
    d = run_dir(proto, cond, seed)
    todo = [r for r in rewards_of(proto) if not (d / panel_file(r)).exists()]
    if not todo:
        return {}
    cohort = _read_parquet(d / "logs.parquet")
    logs_meta = json.loads((d / "logs_meta.json").read_text())
    ann = None
    if proto.get("annotator_replicate") is not None:
        ann = _read_parquet(d / "annotator.parquet")
    return {r: estimate_run_reward(proto, cond, seed, r, cohort, logs_meta, ann) for r in todo}


def estimate_run_reward(proto: dict, cond: str, seed: int, reward: str, cohort: pd.DataFrame,
                        logs_meta: dict, ann: pd.DataFrame | None) -> dict:
    t0 = time.time()
    d = run_dir(proto, cond, seed)
    provenance = check_run_provenance(proto, cond, seed, reward)
    terciles, logs = tabular_logs(cohort, reward)
    seeds = {"bootstrap": derived_seed(seed, ROLE_BOOTSTRAP),
             "folds": derived_seed(seed, ROLE_FOLDS),
             "annotator_noise": derived_seed(seed, ROLE_ANNOTATOR),
             "gbm_random_state": derived_seed(seed, ROLE_GBM) % (2**31 - 1)}
    n_boot = int(proto["n_boot"])
    ref = reference_summary(proto, cond, seed, reward)
    tgts = targets_of(proto)

    out = {"protocol": proto["name"], "protocol_sha256": proto.get("_sha256"),
           "cond": cond, "seed": seed, "seeds": seeds,
           "reward": reward, "reward_definition": REWARD_DEFINITIONS[reward],
           "reward_column": REWARD_COLUMNS[reward],
           "simulation_provenance": provenance,
           "code": proto["_code"], "environment": environment(),
           "n_cohort": int(len(cohort)), "recovery_12m": logs_meta["meta"]["recovery_12m"],
           "explore_share": logs_meta["explore_share"],
           "logged_mean": float(np.mean(logs["reward"])), "reference": ref,
           "targets": {}, "selection": {}}
    out["incumbent_factual_error"] = out["logged_mean"] - ref["mean"][INCUMBENT]

    # tabular panel (archived construction) + refit-bootstrap DM
    for name in tgts:
        target = CANDIDATES[name]
        tmat = np.zeros((len(target.actions_per_context()), N_ACTIONS))
        if ann is not None:
            a_coh = pd.DataFrame({"start_balance": ann["start_balance"], "dpd": ann["dpd"],
                                  "reward": ann[annotator_column(reward, name)]})
            tmat = truth_matrix_from_twin(a_coh, terciles, target)
        est = estimate_panel(
            logs, target, tmat, n_boot=n_boot, seed=seeds["bootstrap"],
            fold_seed=seeds["folds"], annotator_seed=seeds["annotator_noise"],
            annotator_bias_frac=float(proto["annotator"]["bias_frac"]),
            annotator_noise_frac=float(proto["annotator"]["noise_frac"]))
        est["dm_refit"] = dm_refit_bootstrap(logs, target, n_boot=n_boot, seed=seeds["bootstrap"])
        identity = {"abs_dm_minus_is": abs(est["dm"]["value"] - est["is"]["value"]),
                    "abs_dm_minus_snips": abs(est["dm"]["value"] - est["snips"]["value"])}
        out["targets"][name] = {"tabular": est, "dose": _dose_diagnostics(cohort, logs, target),
                                "tabular_identity": identity}

    # gradient-boosted panel on the same logs and folds
    if proto.get("nontabular"):
        from ope_bench.nontabular import (
            GBMConfig,
            design_matrix,
            estimate_nontabular,
            fit_cross_fitted_nuisances,
        )

        gcfg = GBMConfig(**{**proto["gbm"], "random_state": seeds["gbm_random_state"]})
        x = design_matrix(cohort, CATEGORIES)
        folds = np.random.default_rng(seeds["folds"]).integers(0, gcfg.n_folds, size=len(cohort))
        t_act = {n: CANDIDATES[n].actions_per_context()[logs["context"]] for n in tgts}
        tg = time.time()
        nuis = fit_cross_fitted_nuisances(x, logs["action"], logs["reward"], t_act, folds, gcfg)
        out["gbm_fit_seconds"] = round(time.time() - tg, 1)
        out["gbm_fit_info"] = nuis["fit_info"]
        out["gbm_config"] = gcfg.as_dict()
        for name in tgts:
            out["targets"][name]["nontabular"] = estimate_nontabular(
                nuis, name, logs["action"], logs["reward"], t_act[name], logs["explored"],
                logs["eps"], gcfg, n_boot=n_boot, seed=seeds["bootstrap"])

    # errors and interval containment against the independent reference
    for name in tgts:
        refv = ref["mean"][name]
        blocks = [("tabular", out["targets"][name]["tabular"])]
        if "nontabular" in out["targets"][name]:
            blocks.append(("nontabular", out["targets"][name]["nontabular"]))
        for _, block in blocks:
            for key, e in block.items():
                if not isinstance(e, dict) or "value" not in e:
                    continue
                if e["value"] is None:
                    e["error"], e["contains_reference"] = None, None
                    continue
                e["error"] = e["value"] - refv
                e["contains_reference"] = bool(e["ci_low"] <= refv <= e["ci_high"])
        out["targets"][name]["reference"] = refv
        out["targets"][name]["reference_se"] = ref["se_within"][name]

    # selection over the candidates (incumbent valued by its factual logged mean)
    cands = list(proto["candidates"])
    z = float(proto.get("selection_z", 1.96))
    regimes = [("tabular", TABULAR)]
    if proto.get("nontabular"):
        regimes.append(("nontabular", NONTABULAR))
    for regime, keys in regimes:
        for key in keys:
            vals = {INCUMBENT: out["logged_mean"]}
            ok = True
            for name in tgts:
                v = out["targets"][name][regime][key]["value"]
                if v is None:
                    ok = False
                    break
                vals[name] = v
            label = f"{regime}:{key}"
            out["selection"][label] = selection(vals, ref, cands, z) if ok else {
                "undefined": "no randomized support"}
    out["wall_seconds"] = round(time.time() - t0, 1)
    out["usage"] = _usage()
    _write_json(out, d / panel_file(reward))
    return out


def _estimate_worker(args):
    proto, cond, seed = args
    try:
        t0 = time.time()
        done = estimate_run(proto, cond, seed)
        return {"cond": cond, "seed": seed, "ok": True, "rewards": sorted(done),
                "wall_seconds": round(time.time() - t0, 1), **_usage()}
    except Exception as exc:
        return {"cond": cond, "seed": seed, "ok": False, "error": repr(exc),
                "trace": traceback.format_exc()}


# ── CLI ────────────────────────────────────────────────────────────────────
def _log(proto: dict, record: dict) -> None:
    path = REPO / proto["out_dir"] / "jobs.log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record},
                            default=_json_default) + "\n")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("plan", "simulate", "estimate", "status"))
    ap.add_argument("--protocol", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--only-cond", default=None)
    a = ap.parse_args(argv)
    proto = load_protocol(a.protocol)
    proto["_code"] = code_fingerprint()
    all_jobs = [j for j in jobs(proto) if a.only_cond in (None, j["cond"])]
    if a.command == "plan":
        print(json.dumps({"jobs": len(all_jobs), "code": proto["_code"]}, indent=2))
        return
    rewards = rewards_of(proto)

    def _estimated(c, s):
        return all((run_dir(proto, c, s) / panel_file(r)).exists() for r in rewards)

    if a.command == "status":
        done = sum(job_path(proto, j).exists() for j in all_jobs)
        runs = [(c, s) for c in proto["conditions"] for s in proto["seeds"]
                if a.only_cond in (None, c)]
        est = sum(_estimated(c, s) for c, s in runs)
        per_reward = {r: sum((run_dir(proto, c, s) / panel_file(r)).exists() for c, s in runs)
                      for r in rewards}
        print(json.dumps({"simulation_jobs_done": done, "simulation_jobs": len(all_jobs),
                          "runs_estimated": est, "runs": len(runs),
                          "panels_by_reward": per_reward}))
        return
    if a.command == "simulate":
        todo = [j for j in all_jobs if not job_path(proto, j).exists()]
        _log(proto, {"event": "simulate_start", "todo": len(todo), "workers": a.workers,
                     "code": proto["_code"]})
        with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
            for res in pool.imap_unordered(_job_worker, [(proto, j) for j in todo]):
                _log(proto, {"event": "job", **res})
                print(json.dumps({k: res[k] for k in res if k != "trace"}, default=_json_default),
                      flush=True)
        return
    runs = [(c, s) for c in proto["conditions"] for s in proto["seeds"]
            if a.only_cond in (None, c) and not _estimated(c, s)]
    _log(proto, {"event": "estimate_start", "todo": len(runs), "workers": a.workers,
                 "rewards": rewards, "code": proto["_code"]})
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
        for res in pool.imap_unordered(_estimate_worker, [(proto, c, s) for c, s in runs]):
            _log(proto, {"event": "estimate", **res})
            print(json.dumps({k: res[k] for k in res if k != "trace"}, default=_json_default),
                  flush=True)


if __name__ == "__main__":
    main()
