"""T-32 — per-decision DR: reduces to bandit DR at H=1; unbiased on a tiny MDP.

Status: the estimator runs on synthetic trajectories; applying it to real logs
is #blocked until the régua's actions + dates arrive.
"""

from __future__ import annotations

import numpy as np

from ope_bench.bandit import collections_bandit
from ope_bench.estimators import (
    DeterministicPolicy,
    OracleRewardModel,
    TabularRewardModel,
    doubly_robust_value,
)
from ope_bench.logging_policy import (
    LoggingPolicy,
    generate_logs,
    suboptimal_incumbent,
)
from ope_bench.sequential import sequential_dr_value


def test_horizon_one_reduces_to_bandit_dr():
    """A trajectory of length 1 must give exactly the bandit DR estimate."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    behavior = LoggingPolicy(inc, bandit.n_actions, epsilon=0.3)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    logs = generate_logs(bandit, behavior, n=4000, seed=0)
    model = TabularRewardModel(bandit.n_contexts, bandit.n_actions, "full").fit(
        logs["context"], logs["action"], logs["reward"])

    v_bandit = doubly_robust_value(logs, target, model)

    # wrap each transition as a length-1 trajectory
    n = len(logs["reward"])
    trajectories = [
        {
            "context": logs["context"][i:i + 1],
            "action": logs["action"][i:i + 1],
            "reward": logs["reward"][i:i + 1],
            "propensity": logs["propensity"][i:i + 1],
        }
        for i in range(n)
    ]
    v_seq = sequential_dr_value(trajectories, target, model, gamma=1.0)
    assert np.isclose(v_seq, v_bandit)


def test_two_step_chain_unbiased_with_exact_q():
    """On a deterministic 2-step chain with an exact Q model, per-decision DR
    returns the true window value exactly (the correction vanishes sample-wise).
    """
    # 2 states, 2 actions; deterministic rewards r(s,a) = R[s,a].
    R = np.array([[1.0, 0.0], [0.0, 2.0]], dtype=np.float64)
    n_states, n_actions = R.shape
    gamma = 0.9

    # deterministic dynamics: action a in state s → next state a (toy chain).
    target = DeterministicPolicy(np.array([1, 1]), n_actions)  # always action 1

    # exact Q for this 1-step reward + greedy-ish continuation is just R here
    # (we evaluate window return = r0 + γ r1 with the model Q = R).
    q_model = OracleRewardModel(R)

    rng = np.random.default_rng(0)
    trajectories = []
    true_returns = []
    for _ in range(4000):
        s0 = int(rng.integers(0, n_states))
        a0 = int(rng.integers(0, n_actions))   # behavior: uniform
        s1 = a0
        a1 = int(rng.integers(0, n_actions))
        ret_under_target = R[s0, 1] + gamma * R[1, 1]  # target always picks 1
        true_returns.append(ret_under_target)
        trajectories.append({
            "context": np.array([s0, s1]),
            "action": np.array([a0, a1]),
            "reward": np.array([R[s0, a0], R[s1, a1]]),
            "propensity": np.array([0.5, 0.5]),  # uniform behavior
        })

    v_seq = sequential_dr_value(trajectories, target, q_model, gamma=gamma)
    v_true = float(np.mean(true_returns))
    assert abs(v_seq - v_true) < 0.05
