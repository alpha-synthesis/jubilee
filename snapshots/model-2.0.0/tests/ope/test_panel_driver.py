"""Panel driver: policy injection, twin-world alignment, end-to-end determinism."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import yaml

from ope_bench.panel import (
    PI_FAR,
    action_id,
    build_logs,
    load_cohort,
    policy_explorable,
)

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location("run_panel", REPO / "scripts" / "run_panel.py")
run_panel = importlib.util.module_from_spec(_spec)
sys.modules["run_panel"] = run_panel
_spec.loader.exec_module(run_panel)


def _tiny_config(**overrides):
    from collection_simulator.config import load_config

    cfg = load_config(REPO / "configs" / "tiny_ci.yaml")
    cfg["population"]["borrowers"] = 60
    cfg["actions"]["exploration"] = {
        "epsilon": 0.2,
        "explore_states": ["delinquent", "credito_em_liquidacao"],
        "explore_max_liquidacao_days": 180,
    }
    cfg.update(overrides)
    return cfg


def test_twin_world_population_identical_and_actions_follow_policy(tmp_path):
    from collection_simulator.config import load_config
    from collection_simulator.generator import generate

    base = load_config(REPO / "configs" / "tiny_ci.yaml")
    base["population"]["borrowers"] = 60
    logged = generate(base, tmp_path / "logged")
    twin = generate(base, tmp_path / "twin", policy=PI_FAR.generator_policy())

    # population + hidden-world draws are identical (same seed, sampled pre-panel)
    for name in ("borrowers", "loans"):
        assert logged.tables[name].equals(twin.tables[name])

    # twin month-0 actions obey the one-shot policy on explorable rows;
    # everywhere else (and months > 0) the incumbent law applies
    acts = twin.tables["actions"]
    m0 = acts[acts["month"] == 0].set_index("loan_id")
    loans = twin.tables["loans"].set_index("loan_id")
    expl = policy_explorable(
        loans.loc[m0.index, "initial_status"],
        loans.loc[m0.index, "days_in_credito_em_liquidacao"],
    )
    assert (m0.loc[expl, "channel"] == "field_visit").all()
    assert np.allclose(m0.loc[expl, "discount_offer"], 0.275)
    assert not m0.loc[expl, "is_exploration"].any()


def test_action_encoding_and_propensity_formula(tmp_path):
    assert action_id(["none"], [0.0])[0] == 0
    assert action_id(["sms"], [0.10])[0] == 1 + 0 * 11 + 2
    assert action_id(["field_visit"], [0.25])[0] == 1 + 3 * 11 + 5

    from collection_simulator.generator import generate

    cfg = _tiny_config()
    res = generate(cfg, tmp_path / "world")
    cohort = load_cohort(res.db_path)
    from ope_bench.panel import balance_terciles, behavior_propensity_table, context_ids

    ter = balance_terciles(cohort)
    logs = build_logs(cohort, ter)
    ctx = context_ids(cohort, ter)
    table = behavior_propensity_table(ctx, logs["action"])
    row_sums = table.sum(axis=1)
    assert np.allclose(row_sums[row_sums > 0], 1.0)
    # each row's propensity is its empirical (context, action) frequency
    assert np.allclose(logs["propensity"], table[ctx, logs["action"]])
    assert (logs["propensity"] > 0).all()


def test_run_cell_end_to_end_deterministic(tmp_path):
    cfg_path = tmp_path / "cell.yaml"
    cfg_path.write_text(yaml.safe_dump(_tiny_config()))

    r1 = run_panel.run_cell(cfg_path, seed=11, out_dir=tmp_path / "a",
                            n_boot=50, enforce_gates=False)
    r2 = run_panel.run_cell(cfg_path, seed=11, out_dir=tmp_path / "b",
                            n_boot=50, enforce_gates=False)
    for r in (r1, r2):
        r["provenance"].pop("wall_seconds")
        r["provenance"].pop("config_path")
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)

    for target in ("pi_far", "pi_near"):
        block = r1["targets"][target]
        assert set(block["estimators"]) == {"dm", "dm_blind", "is", "snips", "dr",
                                            "dm_plus_is", "pilot_is", "pilot_dr"}
        for name, est in block["estimators"].items():
            if est["value"] is None:  # pilot estimators when eps = 0
                assert name in ("pilot_is", "pilot_dr")
                continue
            assert isinstance(est["ci_covers_truth"], bool)
            assert est["ci_low"] <= est["ci_high"]
        # tiny config has eps = 0.2 -> pilots must be DEFINED here
        assert block["estimators"]["pilot_is"]["value"] is not None


def test_run_cell_eps_zero_pilots_undefined(tmp_path):
    cfg = _tiny_config()
    cfg["actions"]["exploration"]["epsilon"] = 0.0
    cfg_path = tmp_path / "cell0.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    r = run_panel.run_cell(cfg_path, seed=11, out_dir=tmp_path / "o",
                           n_boot=30, enforce_gates=False)
    for target in ("pi_far", "pi_near"):
        est = r["targets"][target]["estimators"]
        assert est["pilot_is"]["value"] is None
        assert est["pilot_is"]["error"] is None
    # selection must skip undefined estimators instead of crashing
    assert "undefined" in r["selection"]["pilot_is"]
    assert r["selection"]["dr"]["picked"] in ("pi_b", "pi_far", "pi_near")
    assert set(r["selection"]["true_ranking"]) == {"pi_b", "pi_far", "pi_near"}
