"""Per-loan equivalence of the evaluation score under simulator models 2.0.0 and 2.1.0.

Model 2.1.0 (full settlement) changes what happens at a loan's first recovery
and after it: the borrower pays the whole offer, the remainder is written off
and the loan ends. Hypothesis under test: the population, the decisions and
draws before the first recovery, and the month of the first recovery are the
same under both models; then every quantity the OPE pipeline reads for the
score ``1{first recovery in months 0..h-1} × B0 × (1 − d0)`` is the same too.
This script checks that, loan by loan, instead of assuming it.

Isolation: each (unit, model) is simulated in its own Python process that
imports the simulator (``collection_simulator``), the estimator package
(``ope_bench``) and the campaign driver (``scripts/tmlr_campaign.py``) from one
source tree only (``--root``): the pre-task snapshot for 2.0.0, the working
tree for 2.1.0. The process records the path and sha256 of every such module
it imported and stops if one lies outside its tree. The driver compares the two
dumps exactly (no tolerance) and deletes them, keeping the comparison and the
dumps' sha256.

Units (grid file):

* ``cohort`` — one world, seed and exploration rate ε, the roles as the
  campaign uses them: logs (replicate 0, all loans stepped 12 months, cohort
  with covariates, ``build_logs`` arrays, the gradient-boosted design matrix),
  annotator (replicate 1, the three targets, the annotator table and truth
  matrices built with the logs' terciles), references (replicates 2 and 3, the
  four candidates, 9-month window; replicate 2 also with a 12-month window),
  plus the population and every loan's month-by-month trajectory (replicate 0).
* ``database`` — :func:`generate` with or without a target policy, then
  ``ope_bench.panel.load_cohort``: the tables up to each loan's first recovery
  and the extracted cohort, and ``simulate_cohort`` on the same world.

Usage::

    python scripts/settlement_equivalence.py run --grid G.json --old-root R0 \
        --new-root R1 --out DIR --workers N [--scratch TMP]
    python scripts/settlement_equivalence.py summarize --grid G.json --out DIR
    python scripts/settlement_equivalence.py dump --root R --unit JSON --out DIR   # one side
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
# per-(loan, month) arrays of ``_simulate_batch`` compared up to the first recovery
SLOT_PRE = ("alive", "status", "channel", "discount", "settlement", "is_exploration",
            "explore_prob", "loan_age", "remaining", "contacts", "recovered", "charged_off",
            "p_recovery", "p_chargeoff")
# post-transition values of a slot: compared before the recovery month only
SLOT_POST = ("dpd_after", "liq_after", "balance_after", "next_status", "recovered_amount")
LOAN_ARRAYS = ("first_recovery_month", "channel0", "discount0", "is_exploration0", "eps0")
REF_FIELDS = ("loan_id", "start_balance", "state", "dpd", "liq_days", "channel_logged",
              "discount_logged", "is_exploration", "exploration_epsilon", "paid_within_h",
              "first_recovery_month", "reward")
META_VERSION_KEYS = ("generator_version", "settlement_rule", "reward_definition")
STATE_CODES = ("performing", "delinquent", "credito_em_liquidacao", "cured", "charged_off")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:
    a = np.asarray(a)
    if a.dtype == object:
        return hashlib.sha256("\x1f".join(map(str, a.ravel().tolist())).encode()).hexdigest()
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


# ══ one side: runs in its own process ══════════════════════════════════════
class Side:
    """The simulator, estimator package and campaign driver of one source tree."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        for sub in ("src", "scripts"):
            sys.path.insert(0, str(self.root / sub))
        import tmlr_campaign as tc  # inserts <root>/src first as well

        from collection_simulator import generator as gen
        from collection_simulator.config import load_config
        from ope_bench import nontabular, panel

        self.tc, self.gen, self.load_config, self.panel, self.nontabular = (
            tc, gen, load_config, panel, nontabular)
        self.provenance = self._provenance()

    def _provenance(self) -> dict:
        mods = {}
        for name, mod in sorted(sys.modules.items()):
            top = name.split(".")[0]
            if top not in ("collection_simulator", "ope_bench", "tmlr_campaign"):
                continue
            f = getattr(mod, "__file__", None)
            if not f:
                continue
            p = Path(f).resolve()
            if self.root not in p.parents:
                raise RuntimeError(f"{name} imported from {p}, outside {self.root}")
            mods[name] = {"path": str(p.relative_to(self.root)), "sha256": sha256_file(p)}
        return {"root": str(self.root), "generator_version": self.gen.GENERATOR_VERSION,
                "rng_scheme": self.gen.RNG_SCHEME,
                "settlement_rule": getattr(self.gen, "SETTLEMENT_RULE", None),
                "modules": mods, "python": platform.python_version(),
                "numpy": np.__version__, "pandas": pd.__version__, "pid": os.getpid()}

    def config(self, unit: dict) -> dict:
        cfg = self.load_config(self.root / unit["config"])
        cfg["seed"] = int(unit["seed"])
        cfg["population"]["borrowers"] = int(unit["borrowers"])
        cfg["actions"]["exploration"]["epsilon"] = float(unit["epsilon"])
        return cfg

    def policy(self, name: str):
        pol = self.tc.CANDIDATES[name]
        return None if pol is None else pol.generator_policy()


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    import duckdb

    con = duckdb.connect()
    try:
        con.register("df", df)
        con.execute(f"COPY df TO '{path}' (FORMAT parquet, COMPRESSION zstd)")
    finally:
        con.close()


def _read_parquet(path: Path) -> pd.DataFrame:
    import duckdb

    con = duckdb.connect()
    try:
        return con.execute(f"SELECT * FROM read_parquet('{path}')").df()
    finally:
        con.close()


def _cohort_arrays(coh: pd.DataFrame, prefix: str, arrays: dict) -> None:
    for f in REF_FIELDS:
        v = coh[f].to_numpy()
        arrays[f"{prefix}.{f}"] = v.astype(str) if v.dtype == object else v


def dump_cohort_unit(side: Side, unit: dict, out: Path) -> dict:
    gen, panel, tc = side.gen, side.panel, side.tc
    cfg = side.config(unit)
    bs = int(unit["batch_size"])
    arrays: dict[str, np.ndarray] = {}
    summary: dict = {"config_effective_sha256": hashlib.sha256(
        json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest(), "timing": {}}

    # population, draws and the month-by-month trajectory of every loan (replicate 0)
    t0 = time.time()
    lg = unit["logs"]
    regional = gen.regional_shocks(cfg)
    summary["regional_shocks"] = regional
    pops, recs, draws_sha, loan_next = [], [], {}, 1
    for b, start, n in gen._batches(int(cfg["population"]["borrowers"]), bs):
        borrowers, hidden, loans = gen._generate_population(
            cfg, lg["replicate"], b, n, start, loan_next, regional)
        loan_next += len(loans)
        d = gen._panel_draws(int(cfg["seed"]), lg["replicate"], b, len(loans),
                             int(cfg["panel"]["months"]))
        draws_sha[str(b)] = {k: sha256_array(v) for k, v in d.items()}
        rec = gen._simulate_batch(cfg, borrowers, hidden, loans, lg["replicate"], b, None,
                                  n_months=lg["months"])
        pops.append((borrowers, hidden, loans))
        recs.append(rec)
    summary["draws_sha256"] = draws_sha
    for k, name in enumerate(("borrowers", "hidden", "loans")):
        _write_parquet(pd.concat([p[k] for p in pops], ignore_index=True), out / f"{name}.parquet")
    for f in SLOT_PRE + SLOT_POST + LOAN_ARRAYS:
        v = np.concatenate([r[f] for r in recs])
        arrays[f"traj.{f}"] = v.astype(str) if v.dtype == object else v
    summary["timing"]["trajectory"] = round(time.time() - t0, 1)

    # role 0: logs, as tmlr_campaign.run_job builds them, then build_logs / design matrix
    t0 = time.time()
    coh, meta = gen.simulate_cohort(cfg, policy=None, replicate=lg["replicate"],
                                    months=lg["months"], simulate_all_loans=True,
                                    with_covariates=True, batch_size=bs, horizon=lg["horizon"])
    _write_parquet(coh, out / "logs_cohort.parquet")
    terc = panel.balance_terciles(coh)
    logs = panel.build_logs(coh, terc)
    arrays["logs.terciles"] = terc
    for k, v in logs.items():
        arrays[f"logs.{k}"] = v
    arrays["logs.design_matrix"] = side.nontabular.design_matrix(coh, tc.CATEGORIES)
    summary["logs_meta"] = meta
    summary["logs_stats"] = {"n_cohort": int(len(coh)),
                             "explore_share": float(coh["is_exploration"].mean()),
                             "logged_mean_reward": float(coh["reward"].mean()),
                             "paid_rate_h": float(coh["paid_within_h"].mean())}
    summary["timing"]["logs"] = round(time.time() - t0, 1)

    # role 1: annotator source under every target; truth matrices with the logs' terciles
    t0 = time.time()
    an = unit["annotator"]
    cols, loan_ids = {}, None
    summary["truth_matrix_sha256"] = {}
    for name in an["targets"]:
        c, m = gen.simulate_cohort(cfg, policy=side.policy(name), replicate=an["replicate"],
                                   batch_size=bs, horizon=an["horizon"])
        if loan_ids is None:
            loan_ids = c["loan_id"].to_numpy()
            cols.update({"loan_id": loan_ids, "start_balance": c["start_balance"],
                         "dpd": c["dpd"]})
        elif not np.array_equal(loan_ids, c["loan_id"].to_numpy()):
            raise AssertionError("annotator cohorts differ across targets")
        cols[f"reward_{name}"] = c["reward"].to_numpy()
        _cohort_arrays(c, f"annotator.{name}", arrays)
        a_coh = pd.DataFrame({"start_balance": c["start_balance"], "dpd": c["dpd"],
                              "reward": c["reward"]})
        tm = panel.truth_matrix_from_twin(a_coh, terc, tc.CANDIDATES[name])
        arrays[f"annotator.{name}.truth_matrix"] = tm
        summary["annotator_meta"] = m
    _write_parquet(pd.DataFrame(cols), out / "annotator.parquet")
    summary["timing"]["annotator"] = round(time.time() - t0, 1)

    # role 2+: references (per-loan rewards, means, covariance, paid rates)
    t0 = time.time()
    summary["reference"] = {}
    for ref in unit["reference"]:
        for r in ref["replicates"]:
            key = f"r{r}_h{ref['horizon']}"
            mats, ids, per = [], None, {}
            for name in ref["candidates"]:
                c, m = gen.simulate_cohort(cfg, policy=side.policy(name), replicate=r,
                                           batch_size=bs, horizon=ref["horizon"])
                if ids is None:
                    ids = c["loan_id"].to_numpy()
                elif not np.array_equal(ids, c["loan_id"].to_numpy()):
                    raise AssertionError("reference cohorts differ across candidates")
                mats.append(c["reward"].to_numpy(np.float64))
                per[name] = {"paid_rate_h": float(c["paid_within_h"].mean())}
                _cohort_arrays(c, f"reference.{key}.{name}", arrays)
            mat = np.vstack(mats)
            summary["reference"][key] = {
                "candidates": list(ref["candidates"]), "n_cohort": int(mat.shape[1]),
                "means": dict(zip(ref["candidates"], mat.mean(axis=1).tolist(), strict=True)),
                "cov": np.cov(mat, ddof=1).tolist(), "per_candidate": per, "meta": m}
    summary["timing"]["reference"] = round(time.time() - t0, 1)
    np.savez(out / "arrays.npz", **arrays)
    return summary


def dump_database_unit(side: Side, unit: dict, out: Path) -> dict:
    import duckdb

    gen, panel = side.gen, side.panel
    cfg = side.config(unit)
    t0 = time.time()
    pol = side.policy(unit["policy"])
    res = gen.generate(cfg, out / "db", batch_size=int(unit["batch_size"]), policy=pol,
                       replicate=int(unit["replicate"]))
    from collection_simulator.validation import validate_database

    rep = validate_database(res.db_path)
    con = duckdb.connect(str(res.db_path), read_only=True)
    try:
        for t in ("borrowers", "loans", "actions", "monthly_panel", "oracle_truth"):
            con.execute(f"COPY (SELECT * FROM {t} ORDER BY ALL) TO '{out / (t + '.parquet')}' "
                        "(FORMAT parquet, COMPRESSION zstd)")
    finally:
        con.close()
    db_coh = panel.load_cohort(res.db_path)
    _write_parquet(db_coh, out / "db_cohort.parquet")
    sim_coh, meta = gen.simulate_cohort(cfg, policy=pol, replicate=int(unit["replicate"]),
                                        batch_size=int(unit["batch_size"]), horizon=9,
                                        cohort_states=None)
    _write_parquet(sim_coh, out / "sim_cohort.parquet")
    shutil.rmtree(out / "db")
    return {"validate_database": {"ok": rep.ok, "errors": rep.errors, "counts": rep.counts},
            "generate_meta": res.meta, "simulate_cohort_meta": meta,
            "timing": {"total": round(time.time() - t0, 1)}}


def dump(root: Path, unit: dict, out: Path) -> None:
    t0 = time.time()
    side = Side(root)
    out.mkdir(parents=True, exist_ok=True)
    fn = dump_cohort_unit if unit["kind"] == "cohort" else dump_database_unit
    summary = fn(side, unit, out)
    side.provenance = side._provenance()  # every module imported by now
    ru = resource.getrusage(resource.RUSAGE_SELF)
    summary.update({"unit": unit, "provenance": side.provenance,
                    "cpu_seconds": round(ru.ru_utime + ru.ru_stime, 1),
                    "peak_rss_mb": ru.ru_maxrss // 1024,
                    "wall_seconds": round(time.time() - t0, 1)})
    summary["files_sha256"] = {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=_json_default))


def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


# ══ comparison (driver process; imports neither simulator) ════════════════
class Checks:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, name: str, equal: bool, n: int, scope: str, divergence=None, note=None):
        self.items.append({"check": name, "equal": bool(equal), "n_compared": int(n),
                           "scope": scope, "first_divergence": divergence, "note": note})

    def arrays(self, name: str, a, b, ids=None, scope: str = "per loan"):
        a, b = np.asarray(a), np.asarray(b)
        if a.shape != b.shape:
            self.add(name, False, max(a.size, b.size), scope,
                     {"shape_old": list(a.shape), "shape_new": list(b.shape)})
            return
        if a.dtype.kind == "f":
            eq = (a == b) | (np.isnan(a) & np.isnan(b))
        else:
            eq = a == b
        eq = np.asarray(eq)
        ok = bool(eq.all())
        div = None
        if not ok:
            idx = tuple(int(x) for x in np.argwhere(~eq)[0])
            div = {"index": list(idx), "old": _py(a[idx]), "new": _py(b[idx]),
                   "n_different": int((~eq).sum())}
            if ids is not None:
                div["loan_id"] = str(ids[idx[0]])
        self.add(name, ok, a.shape[0] if a.ndim else 1, scope, div)

    def frames(self, name: str, a: pd.DataFrame, b: pd.DataFrame, key: str | None = None):
        if list(a.columns) != list(b.columns) or len(a) != len(b):
            self.add(name, False, max(len(a), len(b)), "per row, every column",
                     {"columns_old": list(a.columns), "columns_new": list(b.columns),
                      "rows_old": len(a), "rows_new": len(b)})
            return
        for c in a.columns:
            av, bv = a[c].to_numpy(), b[c].to_numpy()
            if av.dtype == object or bv.dtype == object:
                eq = np.array([x == y for x, y in zip(av, bv, strict=True)], dtype=bool)
            elif av.dtype.kind == "f":
                eq = (av == bv) | (np.isnan(av) & np.isnan(bv))
            else:
                eq = av == bv
            if not eq.all():
                i = int(np.flatnonzero(~eq)[0])
                self.add(name, False, len(a), "per row, every column",
                         {"column": c, "row": i,
                          "key": None if key is None else str(a[key].iloc[i]),
                          "old": _py(av[i]), "new": _py(bv[i]), "n_different": int((~eq).sum())})
                return
        self.add(name, True, len(a), f"per row, {len(a.columns)} columns")

    def values(self, name: str, a, b, scope: str):
        self.add(name, _canon(a) == _canon(b), 1, scope,
                 None if _canon(a) == _canon(b) else {"old": a, "new": b})


def _py(x):
    return x.item() if hasattr(x, "item") else (str(x) if not isinstance(x, (int, float)) else x)


def _canon(x) -> str:
    return json.dumps(x, sort_keys=True, default=_json_default)


def _strip_versions(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if k not in META_VERSION_KEYS}


def compare_cohort_unit(old: Path, new: Path) -> dict:
    so, sn = (json.loads((d / "summary.json").read_text()) for d in (old, new))
    ao, an = np.load(old / "arrays.npz", allow_pickle=False), np.load(new / "arrays.npz",
                                                                      allow_pickle=False)
    ck = Checks()
    # population and draws
    for t in ("borrowers", "hidden", "loans"):
        ck.frames(f"population.{t}", _read_parquet(old / f"{t}.parquet"),
                  _read_parquet(new / f"{t}.parquet"))
    ck.values("population.regional_shocks", so["regional_shocks"], sn["regional_shocks"],
              "per region")
    ck.values("draws.sha256_per_batch_and_array", so["draws_sha256"], sn["draws_sha256"],
              "every (loan, month) draw of replicate 0, per batch")
    ck.values("config_effective_sha256", so["config_effective_sha256"],
              sn["config_effective_sha256"], "effective config")

    # trajectories up to the first recovery
    ids = _read_parquet(new / "loans.parquet")["loan_id"].to_numpy()
    for f in LOAN_ARRAYS:
        ck.arrays(f"trajectory.{f}", ao[f"traj.{f}"], an[f"traj.{f}"], ids)
    first = an["traj.first_recovery_month"]
    alive_new = an["traj.alive"]
    months = np.arange(alive_new.shape[1])[None, :]
    n_alive_new = alive_new.sum(axis=1)
    end = np.where(first >= 0, first, n_alive_new - 1)  # last month that must agree
    pre_mask = months <= end[:, None]
    post_mask = months < np.where(first >= 0, first, n_alive_new)[:, None]
    for f in SLOT_PRE:
        a, b = ao[f"traj.{f}"], an[f"traj.{f}"]
        ck.arrays(f"trajectory.{f} (months <= first recovery)", np.where(pre_mask, a, 0),
                  np.where(pre_mask, b, 0), ids, "per loan-month")
    for f in SLOT_POST:
        a, b = ao[f"traj.{f}"], an[f"traj.{f}"]
        ck.arrays(f"trajectory.{f} (months before the first recovery)",
                  np.where(post_mask, a, 0), np.where(post_mask, b, 0), ids, "per loan-month")
    no_rec = (first < 0)[:, None]
    ck.arrays("trajectory.alive (loans without a recovery: the whole window)",
              np.where(no_rec, ao["traj.alive"], False), np.where(no_rec, alive_new, False),
              ids, "per loan-month")
    # first charge-off before any recovery (terminal in both models)
    co_o, co_n = ao["traj.charged_off"], an["traj.charged_off"]
    first_co = lambda co: np.where(co.any(axis=1), co.argmax(axis=1), -1)  # noqa: E731
    fo, fn = first_co(co_o), first_co(co_n)
    relevant = (first < 0) | ((fo >= 0) & (fo < first))
    ck.arrays("trajectory.first_chargeoff_before_recovery", np.where(relevant, fo, -9),
              np.where(relevant, fn, -9), ids)
    rec_new = first >= 0
    # what the correction changes (expected differences, reported, not required equal)
    alive_old = ao["traj.alive"]
    idx = np.flatnonzero(rec_new)
    fr = first[idx]
    old_next = ao["traj.next_status"][idx, fr]
    old_bal = ao["traj.balance_after"][idx, fr]
    old_amt = ao["traj.recovered_amount"][idx, fr]
    offer = an["traj.settlement"][idx, fr]
    cured = STATE_CODES.index("cured")
    later = alive_old[idx][:, :].copy()
    later[months[0][None, :] <= fr[:, None]] = False
    expected = {
        "loans": int(len(first)), "loans_recovering_in_window": int(rec_new.sum()),
        "old_first_recovery_not_cured": int((old_next != cured).sum()),
        "old_balance_left_after_first_recovery": int((old_bal > 0).sum()),
        "old_paid_less_than_offer": int((old_amt < offer - 1e-9).sum()),
        "new_paid_equals_offer": bool(np.array_equal(an["traj.recovered_amount"][idx, fr], offer)),
        "new_balance_after_zero": bool((an["traj.balance_after"][idx, fr] == 0).all()),
        "new_cured": bool((an["traj.next_status"][idx, fr] == cured).all()),
        "new_rows_after_first_recovery": int((alive_new[idx] & (months > fr[:, None])).sum()),
        "old_rows_after_first_recovery": int(later.sum()),
        "old_loans_with_rows_after_first_recovery": int(later.any(axis=1).sum()),
        "old_recoveries_after_the_first": int((ao["traj.recovered"][idx] & later).sum()),
        "cash_months_0_8": {"old": float(ao["traj.recovered_amount"][:, :9].sum()),
                            "new": float(an["traj.recovered_amount"][:, :9].sum())},
        "cash_months_0_11": {"old": float(ao["traj.recovered_amount"].sum()),
                             "new": float(an["traj.recovered_amount"].sum())},
    }

    # role 0: logs as the estimators receive them
    lo, ln = _read_parquet(old / "logs_cohort.parquet"), _read_parquet(new / "logs_cohort.parquet")
    ck.frames("logs.cohort (every column, incl. covariates and hidden_*)", lo, ln, "loan_id")
    lid = ln["loan_id"].to_numpy()
    for k in ("terciles", "context", "action", "propensity", "reward", "explored", "eps",
              "design_matrix"):
        ck.arrays(f"logs.build_logs.{k}" if k != "design_matrix" else "logs.design_matrix",
                  ao[f"logs.{k}"], an[f"logs.{k}"], None if k == "terciles" else lid)
    ck.values("logs.meta (version keys excluded)", _strip_versions(so["logs_meta"]),
              _strip_versions(sn["logs_meta"]), "recovery_12m, n_cohort, batches")
    ck.values("logs.stats", so["logs_stats"], sn["logs_stats"],
              "n_cohort, explore_share, logged_mean_reward, paid_rate_h")
    eps_ok = bool((ln["exploration_epsilon"].to_numpy() == float(sn["unit"]["epsilon"])).all())
    ck.add("logs.exploration_epsilon equals the unit's epsilon on every cohort row", eps_ok,
           len(ln), "per loan (new model)")

    # role 1: annotator
    ck.frames("annotator.table", _read_parquet(old / "annotator.parquet"),
              _read_parquet(new / "annotator.parquet"), "loan_id")
    for name in sn["unit"]["annotator"]["targets"]:
        ids_a = an[f"annotator.{name}.loan_id"]
        for f in REF_FIELDS:
            ck.arrays(f"annotator.{name}.{f}", ao[f"annotator.{name}.{f}"],
                      an[f"annotator.{name}.{f}"], ids_a)
        ck.arrays(f"annotator.{name}.truth_matrix", ao[f"annotator.{name}.truth_matrix"],
                  an[f"annotator.{name}.truth_matrix"], None, "per context x action cell")

    # role 2+: references
    for key, rn in sn["reference"].items():
        ro = so["reference"][key]
        for name in rn["candidates"]:
            ids_r = an[f"reference.{key}.{name}.loan_id"]
            for f in REF_FIELDS:
                ck.arrays(f"reference.{key}.{name}.{f}", ao[f"reference.{key}.{name}.{f}"],
                          an[f"reference.{key}.{name}.{f}"], ids_r)
        ck.values(f"reference.{key}.means", ro["means"], rn["means"], "per candidate")
        ck.values(f"reference.{key}.cov", ro["cov"], rn["cov"], "per candidate pair")
        ck.values(f"reference.{key}.paid_rates", ro["per_candidate"], rn["per_candidate"],
                  "per candidate")
        ck.values(f"reference.{key}.meta (version keys excluded)", _strip_versions(ro["meta"]),
                  _strip_versions(rn["meta"]), "simulate_cohort meta")

    # pairing and role independence (same in both models; reported for the new one)
    pairing = {}
    for key, rn in sn["reference"].items():
        base = an[f"reference.{key}.{rn['candidates'][0]}.loan_id"]
        pairing[f"reference.{key}"] = all(
            np.array_equal(base, an[f"reference.{key}.{c}.loan_id"])
            and np.array_equal(an[f"reference.{key}.{rn['candidates'][0]}.start_balance"],
                               an[f"reference.{key}.{c}.start_balance"])
            for c in rn["candidates"])
    t0 = sn["unit"]["annotator"]["targets"][0]
    pairing["annotator"] = all(
        np.array_equal(an[f"annotator.{t0}.loan_id"], an[f"annotator.{t}.loan_id"])
        for t in sn["unit"]["annotator"]["targets"])
    ck.add("pairing: one population per role and replicate (loan ids and start balances)",
           all(pairing.values()), len(pairing), "per role-replicate (new model)",
           None if all(pairing.values()) else pairing)
    bal = {"logs_r0": ln.sort_values("loan_id")["start_balance"].to_numpy(),
           "annotator_r1": an[f"annotator.{t0}.start_balance"]}
    for key in sn["reference"]:
        if key.endswith("_h9"):
            first_c = sn["reference"][key]["candidates"][0]
            bal[f"reference_{key.split('_')[0]}"] = an[f"reference.{key}.{first_c}.start_balance"]
    indep = {}
    names = list(bal)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            m = min(len(bal[a]), len(bal[b]))
            indep[f"{a}~{b}"] = {
                "position_correlation": float(np.corrcoef(bal[a][:m], bal[b][:m])[0, 1]),
                "share_equal_start_balance": float((bal[a][:m] == bal[b][:m]).mean())}
    cohort_sha = {k.split(".")[0] + "." + k.split(".")[1]: sha256_array(an[k])
                  for k in an.files if k.endswith(".loan_id")}
    cohort_sha["logs"] = sha256_array(lid)
    cohort_state_sha = {"logs": sha256_array(ln["state"].to_numpy().astype(str))}
    return {"checks": ck.items, "all_equal": all(c["equal"] for c in ck.items),
            "expected_differences": expected, "role_independence": indep,
            "cohort_loan_id_sha256": cohort_sha, "cohort_state_sha256": cohort_state_sha}


def compare_database_unit(old: Path, new: Path) -> dict:
    so, sn = (json.loads((d / "summary.json").read_text()) for d in (old, new))
    ck = Checks()
    tab = {s: {t: _read_parquet(d / f"{t}.parquet") for t in
               ("borrowers", "loans", "actions", "monthly_panel", "oracle_truth")}
           for s, d in (("old", old), ("new", new))}
    for t in ("borrowers", "loans"):
        ck.frames(f"db.{t}", tab["old"][t], tab["new"][t], "loan_id" if t == "loans" else None)
    pn = tab["new"]["monthly_panel"]
    first = (pn[pn["recovered"]].groupby("loan_id")["month"].min())
    last_new = pn.groupby("loan_id")["month"].max()
    keys = ["loan_id", "month"]

    def window(df: pd.DataFrame) -> pd.DataFrame:
        lim = df["loan_id"].map(last_new)
        return df[df["month"] <= lim].sort_values(keys).reset_index(drop=True)

    po, pn_w = window(tab["old"]["monthly_panel"]), window(pn)
    rec_row = pn_w["recovered"].to_numpy()
    changed = ["next_status", "outstanding_balance", "recovered_amount"]
    same_cols = [c for c in pn_w.columns if c not in changed + ["action_id"]]
    ck.frames("db.monthly_panel up to each loan's last 2.1.0 row (action_id and the "
              "recovery row's next_status, balance, amount excluded)",
              po[same_cols], pn_w[same_cols], "loan_id")
    ck.frames("db.monthly_panel next_status, balance and amount before the first recovery",
              po.loc[~rec_row, changed].reset_index(drop=True),
              pn_w.loc[~rec_row, changed].reset_index(drop=True))
    for t in ("actions", "oracle_truth"):
        a, b = window(tab["old"][t]), window(tab["new"][t])
        cols = [c for c in b.columns if c != "action_id"]
        ck.frames(f"db.{t} up to each loan's last 2.1.0 row" + (
            " (action_id excluded)" if t == "actions" else ""), a[cols], b[cols], "loan_id")
    old_p = tab["old"]["monthly_panel"]
    after = old_p[old_p["month"] > old_p["loan_id"].map(last_new)]
    a0 = {s: tab[s]["actions"].query("month == 0").set_index("loan_id")["action_id"]
          for s in ("old", "new")}
    expected = {
        "loans": int(len(tab["new"]["loans"])),
        "loans_recovering": int(len(first)),
        "old_rows_after_the_new_last_row": int(len(after)),
        "old_loans_with_such_rows": int(after["loan_id"].nunique()),
        "rows": {"old": int(len(old_p)), "new": int(len(pn))},
        "month0_action_ids_renumbered": int(
            (a0["old"] != a0["new"].reindex(a0["old"].index)).sum()),
        "cash_months_0_8": {s: float(tab[s]["monthly_panel"].query("month < 9")["recovered_amount"]
                                     .sum()) for s in ("old", "new")},
        "validate_database": {"old (2.0.0 validator)": so["validate_database"]["ok"],
                              "new (2.1.0 validator)": sn["validate_database"]["ok"]},
    }
    ck.add("db.validate_database (2.1.0 validator on the 2.1.0 database)",
           sn["validate_database"]["ok"], 1, "database", sn["validate_database"]["errors"] or None)
    dco, dcn = (_read_parquet(d / "db_cohort.parquet") for d in (old, new))
    ck.frames("db.load_cohort (score extraction from the database)", dco, dcn, "loan_id")
    sco, scn = (_read_parquet(d / "sim_cohort.parquet") for d in (old, new))
    ck.frames("simulate_cohort (all loans, 9-month window)", sco, scn, "loan_id")
    cols = ["loan_id", "start_balance", "state", "dpd", "liq_days", "channel_logged",
            "discount_logged", "is_exploration", "exploration_epsilon", "paid_within_h", "reward"]
    for s, d_c, s_c in (("old", dco, sco), ("new", dcn, scn)):
        x = d_c[cols].sort_values("loan_id").reset_index(drop=True)
        y = s_c[cols].sort_values("loan_id").reset_index(drop=True)
        for c in ("dpd", "liq_days", "paid_within_h"):
            x[c], y[c] = x[c].astype(np.int64), y[c].astype(np.int64)
        ck.frames(f"{s} model: load_cohort equals simulate_cohort per loan", x, y, "loan_id")
    return {"checks": ck.items, "all_equal": all(c["equal"] for c in ck.items),
            "expected_differences": expected}


# ══ driver ════════════════════════════════════════════════════════════════
def units(grid: dict) -> list[dict]:
    out = []
    base = {"borrowers": grid["borrowers"], "batch_size": grid["batch_size"]}
    for world, cfg in grid["worlds"].items():
        for seed in grid["seeds"]:
            for eps in grid["epsilons"]:
                out.append({"kind": "cohort", "id": f"cohort_{world}_s{seed}_eps{eps}",
                            "world": world, "config": cfg, "seed": seed, "epsilon": eps,
                            **base, "logs": grid["logs"], "annotator": grid["annotator"],
                            "reference": grid["reference"]})
        db = grid["database"]
        for seed in db["seeds"]:
            for pol in db["policies"]:
                out.append({"kind": "database", "id": f"database_{world}_s{seed}_{pol}",
                            "world": world, "config": cfg, "seed": seed,
                            "epsilon": db["epsilon"], "policy": pol,
                            "replicate": db["replicate"], **base})
    return out


def _run_unit(args) -> dict:
    grid_path, unit, old_root, new_root, out_dir, scratch = args
    t0 = time.time()
    res_path = Path(out_dir) / "units" / f"{unit['id']}.json"
    if res_path.exists():
        return {"id": unit["id"], "skipped": True}
    tmp = Path(tempfile.mkdtemp(prefix=unit["id"] + "_", dir=scratch))
    try:
        sides = {}
        for side, root in (("old", old_root), ("new", new_root)):
            d = tmp / side
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
            cmd = [sys.executable, "-I", "-B", str(HERE), "dump", "--root", str(root),
                   "--unit", json.dumps(unit), "--out", str(d)]
            p = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if p.returncode:
                raise RuntimeError(f"{side} dump failed:\n{p.stderr[-4000:]}")
            sides[side] = d
        cmp = (compare_cohort_unit if unit["kind"] == "cohort" else compare_database_unit)(
            sides["old"], sides["new"])
        summ = {s: json.loads((d / "summary.json").read_text()) for s, d in sides.items()}
        out = {"unit": unit, "grid": str(grid_path), **cmp,
               "sides": {s: {"provenance": v["provenance"], "files_sha256": v["files_sha256"],
                             "cpu_seconds": v["cpu_seconds"], "peak_rss_mb": v["peak_rss_mb"],
                             "wall_seconds": v["wall_seconds"], "timing": v.get("timing")}
                         for s, v in summ.items()},
               "compare_wall_seconds": round(time.time() - t0, 1)}
        res_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_json = res_path.with_suffix(".tmp")
        tmp_json.write_text(json.dumps(out, indent=1, default=_json_default))
        tmp_json.replace(res_path)
        return {"id": unit["id"], "all_equal": out["all_equal"],
                "wall_seconds": round(time.time() - t0, 1)}
    except Exception as exc:
        return {"id": unit["id"], "error": repr(exc), "trace": traceback.format_exc()}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(grid_path: Path, old_root: Path, new_root: Path, out_dir: Path, workers: int,
        scratch: Path | None) -> None:
    grid = json.loads(grid_path.read_text())
    us = units(grid)
    out_dir.mkdir(parents=True, exist_ok=True)
    log = out_dir / "jobs.log.jsonl"
    scratch = scratch or Path(tempfile.gettempdir())
    jobs = [(str(grid_path), u, str(old_root), str(new_root), str(out_dir), str(scratch))
            for u in us]
    with mp.get_context("spawn").Pool(workers, maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(_run_unit, jobs):
            with log.open("a") as fh:
                fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **r}) + "\n")
            print(json.dumps({k: v for k, v in r.items() if k != "trace"}), flush=True)


def summarize(grid_path: Path, out_dir: Path) -> dict:
    """One table over units, plus the cross-unit check that the cohort (who is
    eligible) does not depend on ε."""
    grid = json.loads(grid_path.read_text())
    recs = {u["id"]: json.loads((out_dir / "units" / f"{u['id']}.json").read_text())
            for u in units(grid)}
    rows, failures = [], []
    for uid, r in recs.items():
        n_eq = sum(c["equal"] for c in r["checks"])
        rows.append({"unit": uid, "kind": r["unit"]["kind"], "world": r["unit"]["world"],
                     "seed": r["unit"]["seed"], "epsilon": r["unit"]["epsilon"],
                     "checks": len(r["checks"]), "equal": n_eq,
                     "all_equal": r["all_equal"],
                     "loans_compared": r["expected_differences"]["loans"],
                     "old_generator": r["sides"]["old"]["provenance"]["generator_version"],
                     "new_generator": r["sides"]["new"]["provenance"]["generator_version"],
                     "cpu_seconds_old": r["sides"]["old"]["cpu_seconds"],
                     "cpu_seconds_new": r["sides"]["new"]["cpu_seconds"]})
        failures += [{"unit": uid, **c} for c in r["checks"] if not c["equal"]]
    # eligibility does not depend on ε (new model; the comparison above covers the old one)
    eps_checks = []
    for world in grid["worlds"]:
        for seed in grid["seeds"]:
            shas = [recs[f"cohort_{world}_s{seed}_eps{e}"]["cohort_loan_id_sha256"]
                    for e in grid["epsilons"]]
            states = [recs[f"cohort_{world}_s{seed}_eps{e}"]["cohort_state_sha256"]
                      for e in grid["epsilons"]]
            eps_checks.append({"world": world, "seed": seed,
                               "cohort_ids_equal_across_eps": all(s == shas[0] for s in shas),
                               "cohort_states_equal_across_eps": all(
                                   s == states[0] for s in states),
                               "n_cohorts": len(shas[0])})
    prov = {}
    for side in ("old", "new"):
        mods = {}
        for r in recs.values():
            for name, m in r["sides"][side]["provenance"]["modules"].items():
                mods.setdefault(name, set()).add((m["path"], m["sha256"]))
        pv = [r["sides"][side]["provenance"] for r in recs.values()]
        prov[side] = {"roots": sorted({v["root"] for v in pv}),
                      "generator_versions": sorted({v["generator_version"] for v in pv}),
                      "modules": {k: [list(x) for x in sorted(v)] for k, v in sorted(mods.items())}}
    out = {"grid": grid, "units": rows, "n_units": len(rows),
           "n_checks": sum(r["checks"] for r in rows),
           "n_checks_equal": sum(r["equal"] for r in rows),
           "all_units_equal": all(r["all_equal"] for r in rows), "failures": failures,
           "eligibility_independent_of_epsilon": eps_checks, "provenance": prov,
           "cpu_seconds_total": round(sum(r["cpu_seconds_old"] + r["cpu_seconds_new"]
                                          for r in rows), 1)}
    (out_dir / "summary.json").write_text(json.dumps(out, indent=1, default=_json_default))
    pd.DataFrame(rows).to_csv(out_dir / "units.csv", index=False)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--root", type=Path, required=True)
    d.add_argument("--unit", required=True)
    d.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--grid", type=Path, required=True)
    r.add_argument("--old-root", type=Path, required=True)
    r.add_argument("--new-root", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--scratch", type=Path, default=None)
    s = sub.add_parser("summarize")
    s.add_argument("--grid", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "dump":
        dump(a.root, json.loads(a.unit), a.out)
    elif a.cmd == "run":
        run(a.grid, a.old_root, a.new_root, a.out, a.workers, a.scratch)
    else:
        out = summarize(a.grid, a.out)
        print(json.dumps({k: out[k] for k in ("n_units", "n_checks", "n_checks_equal",
                                               "all_units_equal")}, indent=1))


if __name__ == "__main__":
    main()
