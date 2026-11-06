"""T-28 — DM / IS / DR estimators: double robustness + variance + positivity."""

from __future__ import annotations

import numpy as np
import pytest

from ope_bench.bandit import collections_bandit
from ope_bench.estimators import (
    DeterministicPolicy,
    OracleRewardModel,
    StochasticPolicy,
    TabularRewardModel,
    direct_method_value,
    doubly_robust_value,
    importance_sampling_value,
    positivity_violations,
)
from ope_bench.logging_policy import (
    LoggingPolicy,
    generate_logs,
    suboptimal_incumbent,
)


def _setup(epsilon=0.3, n=40_000, seed=0):
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    behavior = LoggingPolicy(inc, bandit.n_actions, epsilon=epsilon)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    logs = generate_logs(bandit, behavior, n=n, seed=seed)
    truth = bandit.policy_value(target)
    return bandit, behavior, target, logs, truth


def test_is_and_dr_unbiased_with_true_propensities():
    bandit, _, target, logs, truth = _setup(n=80_000, seed=1)
    full_model = TabularRewardModel(
        bandit.n_contexts, bandit.n_actions, "full"
    ).fit(logs["context"], logs["action"], logs["reward"])
    v_is = importance_sampling_value(logs, target)
    v_dr = doubly_robust_value(logs, target, full_model)
    assert abs(v_is - truth) < 0.01
    assert abs(v_dr - truth) < 0.01


def test_dr_robust_to_misspecified_model_leg_a():
    """Model wrong + propensities right → DR stays correct; DM is biased."""
    bandit, _, target, logs, truth = _setup(n=80_000, seed=2)
    bad_model = TabularRewardModel(
        bandit.n_contexts, bandit.n_actions, "action_only"  # ignores profile
    ).fit(logs["context"], logs["action"], logs["reward"])

    v_dm = direct_method_value(logs, target, bad_model)
    v_dr = doubly_robust_value(logs, target, bad_model)
    assert abs(v_dm - truth) > 0.03          # DM inherits the model bias
    assert abs(v_dr - truth) < 0.01          # DR corrects it via the IS term


def test_dr_robust_to_wrong_propensities_leg_b():
    """Model right + propensities wrong → DR stays correct; IS is biased."""
    bandit, behavior, target, logs, truth = _setup(n=40_000, seed=3)
    true_model = OracleRewardModel(bandit.true_reward_matrix)

    # corrupt the propensities (pretend a different behavior policy)
    wrong_logs = dict(logs)
    wrong_logs["propensity"] = np.full_like(logs["propensity"], 1.0 / bandit.n_actions)

    v_is_wrong = importance_sampling_value(wrong_logs, target)
    v_dr_wrong = doubly_robust_value(wrong_logs, target, true_model)
    # correct model → the IS correction has zero conditional mean, so DR is
    # unbiased for ANY propensities; only Monte-Carlo noise of the stochastic
    # reward remains (the policy value is the mean of a noisy draw).
    assert abs(v_is_wrong - truth) > 0.03            # IS broken by wrong ρ
    assert abs(v_dr_wrong - truth) < 0.005           # DR essentially immune
    assert abs(v_dr_wrong - truth) < abs(v_is_wrong - truth) / 5  # ≫ better


def test_dr_variance_no_worse_than_is():
    """With a decent model, DR variance ≤ IS variance across seeds."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    behavior = LoggingPolicy(inc, bandit.n_actions, epsilon=0.3)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)

    is_vals, dr_vals = [], []
    for seed in range(120):
        logs = generate_logs(bandit, behavior, n=1000, seed=seed)
        model = TabularRewardModel(
            bandit.n_contexts, bandit.n_actions, "full"
        ).fit(logs["context"], logs["action"], logs["reward"])
        is_vals.append(importance_sampling_value(logs, target))
        dr_vals.append(doubly_robust_value(logs, target, model))
    assert np.var(dr_vals) <= np.var(is_vals)


def test_positivity_violation_detected_and_raised():
    """Target action the behavior policy never takes → flagged, and DR raises."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    # explore only a subset → some actions get propensity 0 (coverage gap)
    explore = np.array([0, 1, 2])
    behavior = LoggingPolicy(
        inc, bandit.n_actions, epsilon=0.3, explore_actions=explore)
    # target deterministically takes an action OUTSIDE the explore set
    target = DeterministicPolicy(
        np.full(bandit.n_contexts, bandit.n_actions - 1), bandit.n_actions)

    viol = positivity_violations(target, behavior, np.arange(bandit.n_contexts))
    assert viol.any()

    logs = generate_logs(bandit, behavior, n=2000, seed=4)
    model = TabularRewardModel(bandit.n_contexts, bandit.n_actions, "full").fit(
        logs["context"], logs["action"], logs["reward"])
    with pytest.raises(ValueError, match="positivity"):
        doubly_robust_value(
            logs, target, model, strict_positivity=True, behavior=behavior)


def test_dr_handles_stochastic_target():
    bandit, _, _, logs, _ = _setup(n=20_000, seed=5)
    probs = np.full((bandit.n_contexts, bandit.n_actions), 1.0 / bandit.n_actions)
    target = StochasticPolicy(probs)
    model = TabularRewardModel(bandit.n_contexts, bandit.n_actions, "full").fit(
        logs["context"], logs["action"], logs["reward"])
    v_dr = doubly_robust_value(logs, target, model)
    truth = bandit.policy_value(target)
    assert abs(v_dr - truth) < 0.02
