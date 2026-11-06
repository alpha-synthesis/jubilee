"""Policy-reward diagnostic: extraction under each candidate, gaps and winners."""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "policy_reward_diagnostic", REPO / "scripts" / "policy_reward_diagnostic.py")
prd = importlib.util.module_from_spec(_spec)
sys.modules["policy_reward_diagnostic"] = prd
_spec.loader.exec_module(prd)

PROTO = {"worlds": {"A_on": "configs/tmlr/world_a_on.yaml"}, "borrowers": 3000,
         "epsilon": 0.08}


def test_extraction_matches_simulate_cohort_for_every_candidate():
    cfg = prd.world_config(PROTO, "A_on", 11)
    base = None
    for name in prd.CANDIDATES:
        pol = prd.policy_of(name)
        a = prd.cohort_accounting(cfg, 2, 1000, 9, pol)
        coh, _ = prd.gen.simulate_cohort(cfg, policy=prd.policy_of(name), replicate=2,
                                          batch_size=1000, horizon=9)
        assert np.array_equal(a["loan_id"], coh["loan_id"].to_numpy())
        assert np.array_equal(a["benchmark"], coh["reward"].to_numpy())
        assert np.array_equal(a["channel0"], coh["channel_logged"].astype(str).to_numpy())
        assert np.array_equal(a["d0"], coh["discount_logged"].to_numpy(np.float64))
        assert np.array_equal(a["paid"].astype(np.int64), coh["paid_within_h"].to_numpy())
        paid = a["paid"]
        assert np.array_equal(a["first"][paid], coh["first_recovery_month"].to_numpy()[paid])
        assert (a["cash"] >= 0).all() and (a["cash"][~paid] == 0).all()
        at0 = a["first"] == 0
        assert np.array_equal(a["first_recovery_discount"][at0], a["benchmark"][at0])
        if base is None:
            base = a
        else:
            for k in prd.ALIGN_KEYS:
                assert np.array_equal(base[k], a[k])
    # the month-0 challengers act on every cohort loan (all explorable)
    near = prd.cohort_accounting(cfg, 2, 1000, 9, prd.policy_of("pi_near"))
    assert set(near["channel0"]) == {"sms"} and np.allclose(near["d0"], 0.125)


def test_gap_se_equals_se_of_paired_differences():
    rng = np.random.default_rng(1)
    n = 5000
    common = rng.normal(size=n)
    vals = np.vstack([common + rng.normal(scale=s, size=n) + m
                      for s, m in ((0.3, 1.0), (0.5, 1.2), (0.4, 0.0), (0.2, 3.0))])
    names = ["pi_b", "pi_near", "pi_far", "pi_stage"]
    s = prd.summarize_objective(vals, names)
    for i, j in [(0, 1), (0, 2), (1, 3)]:
        d = vals[i] - vals[j]
        g = s["gaps"][f"{names[i]}-{names[j]}"]
        assert math.isclose(g["gap"], d.mean())
        assert math.isclose(g["se"], d.std(ddof=1) / math.sqrt(n), rel_tol=1e-9)
    assert s["ranking"] == ["pi_stage", "pi_near", "pi_b", "pi_far"]
    assert s["best"] == "pi_stage" and s["top_resolved"]


def _summary(values, ses):
    names = list(values)
    gaps = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            gaps[f"{a}-{b}"] = {"gap": values[a] - values[b], "se": ses}
    best = max(values, key=values.get)
    return {"best": best, "gaps": gaps}


def test_winner_change_rule():
    bench = _summary({"pi_b": 1.0, "pi_near": 5.0, "pi_stage": 3.0}, 0.5)
    same = _summary({"pi_b": 1.0, "pi_near": 6.0, "pi_stage": 2.0}, 0.5)
    clear = _summary({"pi_b": 1.0, "pi_near": 2.0, "pi_stage": 6.0}, 0.5)
    noisy = _summary({"pi_b": 1.0, "pi_near": 5.0, "pi_stage": 5.3}, 0.5)
    assert prd.winner_change(bench, same) == "same"
    assert prd.winner_change(bench, clear) == "clear"
    assert prd.winner_change(bench, noisy) == "unresolved"
