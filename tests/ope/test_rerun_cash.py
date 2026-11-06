"""Rerun additions: the cash collected in the window next to the
score from one simulation, per-reward estimation, DM+ from run extracts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tc = _load("tmlr_campaign", REPO / "scripts" / "tmlr_campaign.py")
prd = _load("policy_reward_diagnostic", REPO / "scripts" / "policy_reward_diagnostic.py")

PROTO = {"worlds": {"A_on": "configs/tmlr/world_a_on.yaml"}, "borrowers": 3000,
         "epsilon": 0.08}


def test_cash_within_h_equals_the_diagnostic_cash_for_every_candidate():
    """``simulate_cohort`` now returns, per cohort loan, the cash collected in
    months 0..h-1 exactly as ``cohort_accounting`` computes it from the
    per-(loan, month) records; the score column and the row order are those of
    the diagnostic's benchmark."""
    cfg = prd.world_config(PROTO, "A_on", 11)
    for name in prd.CANDIDATES:
        pol = prd.policy_of(name)
        a = prd.cohort_accounting(cfg, 2, 1000, 9, pol)
        coh, meta = tc.simulate_cohort(cfg, policy=pol, replicate=2, batch_size=1000, horizon=9)
        assert np.array_equal(a["loan_id"], coh["loan_id"].to_numpy())
        assert np.array_equal(a["benchmark"], coh["reward"].to_numpy(np.float64))
        cash = coh["cash_within_h"].to_numpy(np.float64)
        assert np.array_equal(a["cash"], cash)
        paid = coh["paid_within_h"].to_numpy().astype(bool)
        assert (cash[~paid] == 0).all() and (cash[paid] > 0).all()
        # full settlement: the cash is one offer, never above the balance accrued
        assert (cash <= coh["start_balance"].to_numpy(np.float64) * 1.5).all()
        assert meta["reward_definition"] == tc.SCORE_DEFINITION
        assert meta["cash_definition"] == tc.CASH_DEFINITION
    # the logs-style call (every loan stepped for 12 months, covariates attached)
    # still sums the cash over the 9-month window only
    a0 = prd.cohort_accounting(cfg, 0, 1000, 9, None)
    logs, _ = tc.simulate_cohort(cfg, policy=None, replicate=0, months=12,
                                 simulate_all_loans=True, with_covariates=True,
                                 batch_size=1000, horizon=9)
    assert np.array_equal(a0["loan_id"], logs["loan_id"].to_numpy())
    assert np.array_equal(a0["cash"], logs["cash_within_h"].to_numpy(np.float64))
    assert np.array_equal(a0["benchmark"], logs["reward"].to_numpy(np.float64))


# ── a tiny campaign with two rewards ───────────────────────────────────────
import json  # noqa: E402
import shutil  # noqa: E402

import pytest  # noqa: E402

agg = _load("tmlr_aggregate", REPO / "scripts" / "tmlr_aggregate.py")

TINY = {
    "name": "tiny_two_rewards", "borrowers": 3000, "batch_size": 1000, "horizon": 9,
    "logs_months": 12, "n_boot": 30,
    "conditions": {"A_on": "configs/tmlr/world_a_on.yaml",
                   "A_off": "configs/tmlr/world_a_off.yaml"},
    "seeds": [11, 12], "annotator_replicate": 1, "reference_replicates": [2, 3, 4],
    "candidates": ["pi_b", "pi_near", "pi_far", "pi_stage"], "extra_reference_candidates": [],
    "annotator": {"bias_frac": 0.25, "noise_frac": 0.25},
    "nontabular": importlib.util.find_spec("sklearn") is not None,
    "gbm": {"max_iter": 20, "learning_rate": 0.1, "max_leaf_nodes": 7, "min_samples_leaf": 20,
            "l2_regularization": 1.0, "max_bins": 64, "propensity_clip": 0.001, "n_folds": 2},
    "selection_z": 1.96,
}
VOLATILE = ("protocol", "protocol_sha256", "wall_seconds", "usage", "environment", "code",
            "gbm_fit_seconds")


def _write_protocol(path: Path, **kw) -> Path:
    path.write_text(json.dumps({**TINY, **kw}, indent=1))
    return path


def _cli(cmd: str, protocol: Path) -> None:
    tc.main([cmd, "--protocol", str(protocol), "--workers", "1"])


@pytest.fixture(scope="module")
def tiny_campaign(tmp_path_factory):
    """Simulate and estimate the tiny protocol for both rewards (absolute
    out_dir: the driver's run paths then ignore the repository root)."""
    root = tmp_path_factory.mktemp("tiny_campaign")
    proto = _write_protocol(root / "both.json", out_dir=str(root / "runs"),
                            rewards=["score", "cash"])
    _cli("simulate", proto)
    _cli("estimate", proto)
    return {"root": root, "protocol": proto, "runs": root / "runs"}


def _strip(panel: dict) -> dict:
    return {k: v for k, v in panel.items() if k not in VOLATILE}


def test_both_panels_written_and_score_panel_unchanged_by_the_cash_reward(tiny_campaign):
    """(b) ``rewards: [score, cash]`` writes panel.json and panel_cash.json; the
    score panel equals, value for value, the one a ``rewards: [score]`` protocol
    produces from the same simulation files."""
    root, runs = tiny_campaign["root"], tiny_campaign["runs"]
    score_only = _write_protocol(root / "score_only.json", out_dir=str(root / "runs_score"),
                                 rewards=["score"])
    for run in sorted(runs.glob("*/seed*")):
        dst = root / "runs_score" / run.parent.name / run.name
        dst.mkdir(parents=True)
        for f in run.iterdir():
            if not f.name.startswith("panel"):
                shutil.copy(f, dst / f.name)
    _cli("estimate", score_only)
    n = 0
    for run in sorted(runs.glob("*/seed*")):
        both = json.loads((run / "panel.json").read_text())
        cash = json.loads((run / "panel_cash.json").read_text())
        alone = json.loads((root / "runs_score" / run.parent.name / run.name / "panel.json")
                           .read_text())
        assert not (root / "runs_score" / run.parent.name / run.name / "panel_cash.json").exists()
        assert _strip(both) == _strip(alone)
        assert both["reward"] == "score" and cash["reward"] == "cash"
        assert both["reward_definition"] == tc.SCORE_DEFINITION
        assert cash["reward_definition"] == tc.CASH_DEFINITION
        assert cash["simulation_provenance"]["reward"] == "cash"
        assert cash["seeds"] == both["seeds"]
        # the cash panel's reference is the cash block of the same reference files
        refs = [json.loads((run / f"reference_r{r}.json").read_text()) for r in (2, 3, 4)]
        for c in cash["reference"]["candidates"]:
            assert cash["reference"]["mean"][c] == pytest.approx(
                np.mean([r["cash"]["means"][c] for r in refs]))
            assert both["reference"]["mean"][c] == pytest.approx(
                np.mean([r["means"][c] for r in refs]))
        logs_meta = json.loads((run / "logs_meta.json").read_text())
        assert cash["logged_mean"] == pytest.approx(logs_meta["logged_mean_cash"])
        assert both["logged_mean"] == pytest.approx(logs_meta["logged_mean_reward"])
        # same logs, different reward: the estimates differ, the support does not
        for t in both["targets"]:
            assert both["targets"][t]["dose"] == cash["targets"][t]["dose"]
            assert (both["targets"][t]["tabular"]["dm"]["value"]
                    != cash["targets"][t]["tabular"]["dm"]["value"])
            if TINY["nontabular"]:
                assert "nontabular" in cash["targets"][t]
        n += 1
    assert n == 4


def test_estimate_skips_only_the_rewards_whose_panel_exists(tiny_campaign):
    runs, proto = tiny_campaign["runs"], tiny_campaign["protocol"]
    run = runs / "A_on" / "seed11"
    p = tc.load_protocol(proto)
    p["_code"] = tc.code_fingerprint()
    assert tc.estimate_run(p, "A_on", 11) == {}
    before = (run / "panel.json").read_bytes()
    (run / "panel_cash.json").unlink()
    done = tc.estimate_run(p, "A_on", 11)
    assert list(done) == ["cash"] and (run / "panel_cash.json").exists()
    assert (run / "panel.json").read_bytes() == before


def test_aggregate_per_reward(tiny_campaign):
    """(d) ``--reward cash`` aggregates the cash panels; the default the score."""
    root, proto, runs = tiny_campaign["root"], tiny_campaign["protocol"], tiny_campaign["runs"]
    for reward in ("score", "cash"):
        dest = root / f"aggregate_{reward}"
        agg.main(["--protocol", str(proto), "--dest", str(dest), "--reward", reward])
        manifest = json.loads((dest / "aggregate_manifest.json").read_text())
        assert manifest["reward"] == reward and manifest["n_runs"] == 4
        assert not manifest["missing_runs"]
        est = agg.pd.read_csv(dest / "estimates_by_run.csv")
        panel = json.loads((runs / "A_on" / "seed11" / tc.panel_file(reward)).read_text())
        row = est[(est["cond"] == "A_on") & (est["seed"] == 11) & (est["target"] == "pi_near")
                  & (est["regime"] == "tabular") & (est["estimator"] == "dm")].iloc[0]
        # the tables are written with six significant digits
        assert row["reference"] == pytest.approx(panel["targets"]["pi_near"]["reference"],
                                                 rel=1e-5)
        assert row["value"] == pytest.approx(panel["targets"]["pi_near"]["tabular"]["dm"]["value"],
                                             rel=1e-5)
        for name in ("error_summary.csv", "selection_summary.csv", "reference_values_by_run.csv",
                     "interval_diagnostic.csv", "paired_condition_contrasts.csv"):
            assert (dest / name).exists()
    a = agg.pd.read_csv(root / "aggregate_score" / "reference_values_by_run.csv")
    b = agg.pd.read_csv(root / "aggregate_cash" / "reference_values_by_run.csv")
    assert not np.allclose(a["mean"], b["mean"])
    # the default is the score, and a panel of another reward is refused
    agg.main(["--protocol", str(proto), "--dest", str(root / "aggregate_default")])
    assert json.loads((root / "aggregate_default" / "aggregate_manifest.json").read_text())[
        "reward"] == "score"


@pytest.mark.parametrize("bad", [
    {"rewards": ["score", "profit"]},   # unknown reward
    {"rewards": ["score", "score"]},    # duplicates
    {"rewards": []},
    {"rewards": "cash"},
])
def test_protocol_rejects_bad_rewards(bad):
    with pytest.raises(ValueError):
        tc.validate_protocol({**TINY, "out_dir": "x", **bad})


def test_protocol_accepts_both_rewards_and_defaults_to_the_score():
    tc.validate_protocol({**TINY, "out_dir": "x", "rewards": ["score", "cash"]})
    tc.validate_protocol({**TINY, "out_dir": "x"})
    assert tc.rewards_of({**TINY}) == ["score"]
    assert tc.panel_file("score") == "panel.json" and tc.panel_file("cash") == "panel_cash.json"


def test_provenance_requires_the_cash_reward_to_be_recorded(tmp_path):
    proto = {**TINY, "out_dir": str(tmp_path)}
    run = tmp_path / "C" / "seed1"
    run.mkdir(parents=True)
    legacy = {"code": {"tree_sha256": "a"}, "generator_version": "2.0.0",
              "rng_scheme": "keyed-streams-v2", "config_effective_sha256": "c",
              "meta": {"batch_size": 50000, "reward_definition": tc.SCORE_DEFINITION}}
    for name in ("logs_meta.json", "annotator_meta.json", "reference_r2.json",
                 "reference_r3.json", "reference_r4.json"):
        (run / name).write_text(json.dumps(legacy))
    assert tc.check_run_provenance(proto, "C", 1)["reward_definition"] == tc.SCORE_DEFINITION
    with pytest.raises(RuntimeError):
        tc.check_run_provenance(proto, "C", 1, "cash")


# ── DM+ from the extracts ──────────────────────────────────────────────────
dmp = _load("dm_plus_from_extracts",
            REPO / "scripts" / "tmlr_evidence" / "dm_plus_from_extracts.py")


def _dm_plus_se(cohort, ann, target, reward, terciles) -> float:
    """Monte-Carlo SE of the exact-annotator DM+ on a tiny world: per context,
    the cell mean mixes the factual rows of the target cell with one
    annotation (the replicate-1 context mean) per logged row; the contexts
    are weighted by the logged cohort."""
    from ope_bench.panel import context_ids

    _, logs = tc.tabular_logs(cohort, reward)
    ctx, act, r = logs["context"], logs["action"], logs["reward"]
    a_ctx = context_ids(ann, terciles)
    a_r = ann[tc.annotator_column(reward, target.name)].to_numpy(np.float64)
    acts = target.actions_per_context()
    var = 0.0
    n = len(ctx)
    for c in range(len(acts)):
        in_c = ctx == c
        if not in_c.any():
            continue
        w = in_c.sum() / n
        f = in_c & (act == acts[c])
        n_f, n_a = int(f.sum()), int(in_c.sum())
        var_f = (r[f].var(ddof=1) / n_f) if n_f > 1 else (r.var(ddof=1) if n_f == 1 else 0.0)
        m = a_ctx == c
        var_a = (a_r[m].var(ddof=1) / m.sum()) if m.sum() > 1 else a_r.var(ddof=1)
        var += w ** 2 * ((n_f / (n_f + n_a)) ** 2 * var_f + (n_a / (n_f + n_a)) ** 2 * var_a)
    return float(np.sqrt(var))


def test_dm_plus_from_extracts_on_the_tiny_run(tiny_campaign):
    """(c) The script runs on the tiny campaign without simulating, reproduces
    the panel's DM and DM+-IS exactly, and with the uncorrupted annotator DM+
    sits within Monte-Carlo noise of the reference (3 SE: reference replicates
    and the annotated model's own sampling noise) on every well-supported
    target (at most a tenth of the cohort in contexts without logged support;
    an exact annotation fills those anyway), for both rewards; the protocol's
    biased annotator pushes DM+ away from it (no IS correction cancels the
    annotation bias)."""
    root, proto, runs = tiny_campaign["root"], tiny_campaign["protocol"], tiny_campaign["runs"]
    dest = root / "dm_plus"
    dmp.main(["--protocol", str(proto), "--dest", str(dest), "--runs", str(runs)])
    manifest = json.loads((dest / "manifest.json").read_text())
    assert manifest["runs_done"] == 4 and not manifest["runs_failed"]
    assert manifest["max_abs_panel_reproduction_diff"] == 0.0
    by_run = agg.pd.read_csv(dest / "dm_plus_by_run.csv")
    assert set(by_run["reward"]) == {"score", "cash"}
    assert set(by_run["annotator"]) == {"none", "protocol", "exact"}
    summary = agg.pd.read_csv(dest / "dm_plus_summary.csv")
    assert (summary["n_seeds"] == 2).all()
    checked = 0
    for cond, seed in (("A_on", 11), ("A_on", 12), ("A_off", 11), ("A_off", 12)):
        run = runs / cond / f"seed{seed}"
        panel = json.loads((run / "panel.json").read_text())
        cohort = tc._read_parquet(run / "logs.parquet")
        ann = tc._read_parquet(run / "annotator.parquet")
        terciles = tc.balance_terciles(cohort)
        sub = by_run[(by_run["cond"] == cond) & (by_run["seed"] == seed)]
        for name, t in panel["targets"].items():
            if t["dose"]["cohort_share_without_support"] > 0.10:
                continue
            target = tc.CANDIDATES[name]
            for reward in ("score", "cash"):
                rows = sub[(sub["target"] == name) & (sub["reward"] == reward)].set_index(
                    ["annotator", "estimator"])
                ref_se = json.loads((run / tc.panel_file(reward)).read_text())["targets"][name][
                    "reference_se"]
                se = np.hypot(ref_se, _dm_plus_se(cohort, ann, target, reward, terciles))
                exact = rows.loc[("exact", "dm_plus_xfit"), "error"]
                assert abs(exact) < 3.0 * se, (cond, seed, name, reward, exact, se)
                assert abs(rows.loc[("exact", "dm_plus_insample"), "error"]) < 3.0 * se
                # the biased annotator (+0.25 x scale) moves DM+ up, by more than the noise
                biased = rows.loc[("protocol", "dm_plus_xfit"), "value"]
                assert biased - rows.loc[("exact", "dm_plus_xfit"), "value"] > 2.0 * se
                checked += 1
    assert checked >= 4


# ── ε = 0 cells (pilot estimators undefined) through every stage ──────────
def test_eps0_cells_run_through_simulate_estimate_aggregate_and_dm_plus(tmp_path):
    """The 5-seed grid rerun has five ε = 0 cells: no randomized rows, so the
    pilot estimators and their selections are undefined; every stage must
    still complete for both rewards."""
    import yaml

    cfg = yaml.safe_load((REPO / "configs" / "grid" / "cell_01_control_eps0.yaml").read_text())
    assert cfg["actions"]["exploration"]["epsilon"] == 0.0
    (tmp_path / "eps0.yaml").write_text(yaml.safe_dump(cfg))
    proto = _write_protocol(tmp_path / "p.json", name="tiny_eps0", out_dir=str(tmp_path / "runs"),
                            conditions={"cell_eps0": str(tmp_path / "eps0.yaml")}, seeds=[101, 102],
                            candidates=["pi_b", "pi_near", "pi_far"], nontabular=False,
                            rewards=["score", "cash"])
    _cli("simulate", proto)
    _cli("estimate", proto)
    for reward in ("score", "cash"):
        panel = json.loads((tmp_path / "runs" / "cell_eps0" / "seed101" / tc.panel_file(reward))
                           .read_text())
        assert panel["explore_share"] == 0.0
        for t in panel["targets"].values():
            assert t["tabular"]["pilot_is"]["value"] is None
            assert t["tabular"]["pilot_dr"]["error"] is None
            assert t["tabular"]["dm"]["value"] is not None and t["dose"]["n_anchor"] == 0
        assert panel["selection"]["tabular:pilot_is"] == {"undefined": "no randomized support"}
        assert "picked" in panel["selection"]["tabular:dm"]
        dest = tmp_path / f"aggregate_{reward}"
        agg.main(["--protocol", str(proto), "--dest", str(dest), "--reward", reward])
        summ = agg.pd.read_csv(dest / "error_summary.csv")
        pilot = summ[summ["estimator"] == "pilot_is"]
        assert (pilot["n_defined"] == 0).all() and len(pilot) == 2
        assert (summ[summ["estimator"] == "dm"]["n_defined"] == 2).all()
    dmp.main(["--protocol", str(proto), "--dest", str(tmp_path / "dm_plus")])
    manifest = json.loads((tmp_path / "dm_plus" / "manifest.json").read_text())
    assert manifest["runs_done"] == 2 and manifest["max_abs_panel_reproduction_diff"] == 0.0
