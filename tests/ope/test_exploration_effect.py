"""Exploration-effect add-on: pairing of the ε arms, summaries and sizing."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "exploration_effect", REPO / "scripts" / "exploration_effect.py")
ee = importlib.util.module_from_spec(_spec)
sys.modules["exploration_effect"] = ee
_spec.loader.exec_module(ee)


def _proto(tmp_path, **kw):
    proto = {"name": "test", "out_dir": str(tmp_path),
             "worlds": {"A_on": "configs/tmlr/world_a_on.yaml"},
             "seeds": [11, 12], "replicates": [2], "borrowers": 3000,
             "batch_size": 1000, "horizon": 9, "epsilon": 0.08,
             "_sha256": "test", "_code": {"tree_sha256": "test"}}
    proto.update(kw)
    return proto


def test_pair_differs_only_by_exploration(tmp_path):
    proto = _proto(tmp_path)
    out = ee.run_pair(proto, "A_on", 11, 2)
    s = out["summary"]
    assert out["configs_differ_in"] == ["actions.exploration.epsilon"]
    assert ee.pair_path(proto, "A_on", 11, 2).exists()
    assert 0.0 < s["month0_explored_share"] < 0.25
    # month-0 actions differ exactly where the ε arm explored or ... nowhere else
    assert s["month0_action_differs_share"] <= s["month0_explored_share"] + 1e-12
    assert math.isclose(s["delta"], s["delta_from_month0_explored"]
                        + s["delta_from_other_loans"], abs_tol=1e-9)
    assert math.isclose(s["delta"], s["value_eps0"] - s["value_eps"], abs_tol=1e-9)
    assert out["validation"] == {"checked": False}


def test_eps_arm_is_the_campaign_reference_construction(tmp_path):
    proto = _proto(tmp_path)
    out = ee.run_pair(proto, "A_on", 12, 2)
    cfg = ee.world_config(proto, "A_on", 12)
    ref, _ = ee.simulate_cohort(cfg, policy=None, replicate=2, batch_size=1000, horizon=9)
    assert out["summary"]["value_eps"] == float(ref["reward"].mean())
    assert out["summary"]["n_cohort"] == len(ref)


def test_validation_against_an_archived_reference(tmp_path):
    proto = _proto(tmp_path)
    out = ee.run_pair(proto, "A_on", 11, 2)
    arch_dir = tmp_path / "arch" / "A_on" / "seed11"
    arch_dir.mkdir(parents=True)
    rec = {"means": {"pi_b": out["summary"]["value_eps"]}, "n_cohort": out["summary"]["n_cohort"]}
    (arch_dir / "reference_r2.json").write_text(json.dumps(rec))
    proto["archived_reference"] = {"dir": str(tmp_path / "arch"), "candidate": "pi_b",
                                   "tolerance": 1e-6}
    v = ee._validation(proto, "A_on", 11, 2, out["summary"]["value_eps"],
                       out["summary"]["n_cohort"])
    assert v["checked"] and v["ok"]
    bad = ee._validation(proto, "A_on", 11, 2, out["summary"]["value_eps"] + 0.01,
                         out["summary"]["n_cohort"])
    assert not bad["ok"]


def test_misaligned_arms_are_rejected():
    base = pd.DataFrame({"loan_id": ["a", "b"], "state": ["delinquent"] * 2, "dpd": [30, 60],
                         "liq_days": [0, 0], "start_balance": [100.0, 200.0],
                         "is_exploration": [False, False], "reward": [0.0, 200.0],
                         "paid_within_h": [0, 1], "channel_logged": ["sms", "sms"],
                         "discount_logged": [0.0, 0.0]})
    other = base.copy()
    other["loan_id"] = ["a", "c"]
    with pytest.raises(AssertionError):
        ee.summarize_pair(base, other)
    explored = base.copy()
    explored["is_exploration"] = [True, False]
    with pytest.raises(AssertionError):
        ee.summarize_pair(base, explored)  # the ε = 0 arm must not explore


def _pairs_frame():
    rows = []
    rng = np.random.default_rng(0)
    for seed in (1, 2, 3):
        for r in (2, 3):
            rows.append({"world": "A_on", "seed": seed, "replicate": r, "n_cohort": 1000,
                         "value_eps0": 300.0, "value_eps": 298.0,
                         "delta": 2.0 + seed + 0.1 * r, "se_delta": 0.5 + 0.1 * r,
                         "relative_delta": (2.0 + seed) / 300.0,
                         "delta_from_month0_explored": 1.0, "delta_from_other_loans": 1.0,
                         "recovery_rate_eps0": 0.04, "recovery_rate_eps": 0.041,
                         "recovery_rate_delta": -0.001, "se_recovery_rate_delta": 1e-4,
                         "month0_explored_share": 0.08,
                         "cpu_seconds_pair": 100.0 + rng.random()})
    return pd.DataFrame(rows)


def test_per_seed_average_and_world_interval():
    ps = ee.per_seed(_pairs_frame())
    s1 = ps[ps.seed == 1].iloc[0]
    assert s1["R"] == 2 and math.isclose(s1["delta"], 3.25)
    assert math.isclose(s1["se_delta_mc"], math.sqrt(0.7 ** 2 + 0.8 ** 2) / 2)
    bw = ee.by_world(ps).iloc[0]
    d = ps["delta"].to_numpy()
    half = stats.t.ppf(0.975, 2) * d.std(ddof=1) / math.sqrt(3)
    assert math.isclose(bw["delta_mean"], d.mean())
    assert math.isclose(bw["delta_ci95_high"] - bw["delta_mean"], half)
    assert bw["seeds_with_positive_delta"] == 3


def test_sizing_rule_picks_the_smallest_sufficient_R():
    pr = _pairs_frame()
    proto = {"replicates": [2, 3], "worlds": {"A_on": "x"},
             "sizing_rule": {"R_options": [1, 2, 3], "target_half_width": 1.0,
                             "main_seeds": 20, "cpu_hours_ceiling": 15.0}}
    out = ee.sizing(pr, proto)
    first = pr[pr.replicate == 2]
    sig2_seed = max(0.0, first["delta"].var(ddof=1) - (first["se_delta"] ** 2).mean())
    assert math.isclose(out["sigma2_seed"], sig2_seed)
    t = stats.t.ppf(0.975, 19)
    for R in (1, 2, 3):
        hw = t * math.sqrt((sig2_seed + out["sigma2_mc"] / R) / 20)
        assert math.isclose(out["projection"][R]["half_width"], hw)
    ok = [R for R in (1, 2, 3) if out["projection"][R]["half_width"] <= 1.0]
    assert out["chosen_R"] == (min(ok) if ok else 1)


def test_accounting_mirrors_simulate_cohort(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "exploration_effect_accounting", REPO / "scripts" / "exploration_effect_accounting.py")
    ea = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ea)
    proto = _proto(tmp_path)
    for eps in (None, 0.0):
        cfg = ee.world_config(proto, "A_on", 11, epsilon=eps)
        acc = ea.cohort_accounting(cfg, 2, 1000, 9)
        coh, _ = ee.simulate_cohort(cfg, policy=None, replicate=2, batch_size=1000, horizon=9)
        assert np.array_equal(acc["loan_id"], coh["loan_id"].to_numpy())
        assert np.array_equal(acc["value_benchmark"], coh["reward"].to_numpy())
        at0 = acc["first"] == 0
        assert np.array_equal(acc["value_recovery_month_discount"][at0],
                              acc["value_benchmark"][at0])
        assert (acc["cash"][~acc["paid"]] == 0).all() and (acc["cash"] >= 0).all()
        assert acc["paid"].sum() > 0
