"""Unit tests for the post-processing OPE value exporter (Split B)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ope_bench.value_export import (
    EPSILON,
    N_DISCOUNT_BINS,
    U_CELL,
    build_log_dict,
    compute_estimates,
    discretize_discount,
)


def test_discretize_discount_bins():
    d = np.array([0.0, 0.049, 0.05, 0.10, 0.50, 0.55])
    got = discretize_discount(d)
    # 0.55 clamps into the last bin (N-1)
    assert list(got) == [0, 0, 1, 2, 10, N_DISCOUNT_BINS - 1]


def test_discretize_discount_exact_edges_go_up():
    """Every multiple of 0.05 opens its own bin (floating point put 0.15, 0.30 and
    0.35 in the lower bin), and the generator's 4-decimal dose grid fills bins
    0-9 equally, so the explored mass per cell matches U_CELL."""
    edges = np.round(np.arange(11) * 0.05, 4)
    assert list(discretize_discount(edges)) == list(range(11))
    grid = np.round(np.arange(0, 5501) * 1e-4, 4)  # doses produced by round(u*0.55, 4)
    counts = np.bincount(discretize_discount(grid), minlength=N_DISCOUNT_BINS)
    assert list(counts[:10]) == [500] * 10 and counts[10] == 501


def _toy():
    """Two loans, target π_e = field_visit @ bin from discount column.

    Row A: explorable non-exploration row whose logged action == π_e → π_b = (1-e)+e*u.
    Row B: explorable exploration draw whose logged action == π_e → π_b = e*u.
    Row C: non-explorable, logged action != π_e → contributes 0 to IPS.
    """
    logs = pd.DataFrame(
        {
            "loan_id": ["A", "B", "C"],
            "month": [0, 0, 0],
            "channel_logged": ["field_visit", "field_visit", "sms"],
            "discount_logged": [0.10, 0.10, 0.10],
            "is_exploration": [False, True, False],
            "exploration_epsilon": [0.08, 0.08, 0.0],
            "start_balance": [1000.0, 1000.0, 1000.0],
            "paid_within_h": [1, 1, 1],
        }
    )
    policy = pd.DataFrame(
        {
            "loan_id": ["A", "B", "C"],
            "month": [0, 0, 0],
            "channel": ["field_visit", "field_visit", "field_visit"],
            "discount_offer": [0.10, 0.10, 0.10],  # bin 2 for all
            "expected_return": [100.0, 100.0, 100.0],
        }
    )
    return logs, policy


def test_propensity_and_matching():
    logs, policy = _toy()
    log = build_log_dict(logs, policy)
    # A and B match π_e (field_visit, bin 2); C is sms → no match
    assert list(log["matches_target"]) == [True, True, False]
    # propensities
    assert np.isclose(log["propensity"][0], (1 - EPSILON) + EPSILON * U_CELL)
    assert np.isclose(log["propensity"][1], EPSILON * U_CELL)
    assert np.isclose(log["propensity"][2], 1.0)  # non-explorable incumbent
    # reward = paid * balance * (1 - discount)
    assert np.allclose(log["reward"], [900.0, 900.0, 900.0])


def test_ips_matches_hand_computation():
    logs, policy = _toy()
    log = build_log_dict(logs, policy)
    res = compute_estimates(log, n_boot=50, seed=0)
    # IPS = mean_i 1[match]/pi_b * r ; only A,B contribute, C->0
    pb_a = (1 - EPSILON) + EPSILON * U_CELL
    pb_b = EPSILON * U_CELL
    ips_expected = ((1 / pb_a) * 900.0 + (1 / pb_b) * 900.0 + 0.0) / 3
    assert np.isclose(res["estimators"]["ips"]["value"], ips_expected, rtol=1e-9)
    # DM = mean expected_return = 100
    assert np.isclose(res["estimators"]["dm"]["value"], 100.0)
    # SNIPS = sum(rho*r)/sum(rho)
    snips_expected = ((1 / pb_a) * 900.0 + (1 / pb_b) * 900.0) / ((1 / pb_a) + (1 / pb_b))
    assert np.isclose(res["estimators"]["snips"]["value"], snips_expected, rtol=1e-9)


def test_dr_point_estimate_equals_contribution_mean():
    # DR point estimate (via ope_bench) must equal mean of the per-row DR
    # contributions the bootstrap resamples — else the CI won't bracket it.
    from ope_bench.value_export import _contributions, _fit_logged_qhat

    logs, policy = _toy()
    log = build_log_dict(logs, policy)
    qhat = _fit_logged_qhat(log)
    contrib = _contributions(log, qhat)
    res = compute_estimates(log, n_boot=10, seed=0)
    assert np.isclose(res["estimators"]["dr"]["value"], contrib["dr"].mean())


def test_ci_brackets_point_estimate_roughly():
    logs, policy = _toy()
    log = build_log_dict(logs, policy)
    res = compute_estimates(log, n_boot=200, seed=1)
    for name in ("dm", "ips", "snips", "dr"):
        e = res["estimators"][name]
        assert e["ci_low"] <= e["ci_high"]
        assert e["n"] == 3
