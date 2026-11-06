"""T-27 — synthetic logging bandit: honest propensities, known true value."""

from __future__ import annotations

import numpy as np

from ope_bench.bandit import collections_bandit, default_action_menu
from ope_bench.estimators import DeterministicPolicy
from ope_bench.logging_policy import (
    LoggingPolicy,
    generate_logs,
    suboptimal_incumbent,
)


def test_menu_matches_controller_grid():
    """The OPE action menu is the same discretization the controller uses."""
    menu = default_action_menu(contacts=("sms", "call"), discounts=(0.0, 0.2, 0.4))
    # no_action + 2 contacts × 3 discounts
    assert len(menu) == 1 + 2 * 3
    assert menu[0].contact == "no_action"
    labels = {m.label() for m in menu}
    assert "sms@0.20" in labels and "call@0.40" in labels


def test_true_value_is_closed_form():
    bandit = collections_bandit()
    opt = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    v_opt = bandit.policy_value(opt)
    # the argmax policy attains the optimal value, by construction
    assert np.isclose(v_opt, bandit.optimal_value())
    # and it is the ceiling over all deterministic policies
    for a in range(bandit.n_actions):
        const = DeterministicPolicy(
            np.full(bandit.n_contexts, a), bandit.n_actions)
        assert bandit.policy_value(const) <= v_opt + 1e-9


def test_logged_propensity_matches_empirical_frequency():
    """The declared propensity converges to the action frequency in the logs."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    policy = LoggingPolicy(inc, bandit.n_actions, epsilon=0.3)
    logs = generate_logs(bandit, policy, n=60_000, seed=1)

    # within a single context, compare empirical action freq to π_b(a|x)
    x0 = 0
    mask = logs["context"] == x0
    acts = logs["action"][mask]
    emp = np.bincount(acts, minlength=bandit.n_actions) / mask.sum()
    declared = policy.propensity(np.array([x0]))[0]
    assert np.allclose(emp, declared, atol=0.02)


def test_epsilon_floor_respected_and_zero_recovers_determinism():
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)

    floored = LoggingPolicy(inc, bandit.n_actions, epsilon=0.2)
    pi = floored.propensity(np.arange(bandit.n_contexts))
    # every action in the explore set has prob ≥ ε/K > 0 (common support)
    assert (pi >= 0.2 / bandit.n_actions - 1e-12).all()

    deterministic = LoggingPolicy(inc, bandit.n_actions, epsilon=0.0)
    logs = generate_logs(bandit, deterministic, n=2000, seed=2)
    # ε=0 → the incumbent rule is reproduced exactly
    assert np.array_equal(logs["action"], inc[logs["context"]])


def test_individual_reward_is_noisy_but_mean_is_value():
    """One draw is a coin flip; the mean over draws is the policy value."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    policy = LoggingPolicy(inc, bandit.n_actions, epsilon=0.1)
    logs = generate_logs(bandit, policy, n=40_000, seed=3)
    # empirical mean reward ≈ value of the behavior policy
    assert np.isclose(logs["reward"].mean(), bandit.policy_value(policy), atol=0.01)
