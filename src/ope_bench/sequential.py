"""Per-decision doubly robust OPE for window value (Jiang & Li 2016, T-32).

The value we sell is *cumulative over the collection window* — sequential, not
one-shot.  Bandit DR (T-28) estimates only the next decision's value; this
extends it to trajectories with per-decision importance weighting.

    V̂_DR^{t}   = V̂(s_t) + ρ_t · ( r_t + γ·V̂_DR^{t+1} − Q̂(s_t, a_t) )
    V̂_DR^{T}   = 0

For horizon 1 this collapses exactly to the bandit DR estimator — the test that
ties this module back to T-28.

**Status: #blocked.**  The estimator and its tests run on synthetic MDPs, but
applying it to *real* logs needs the incumbent régua's actions **plus dates**
(the sequence) — the data ask in the executive briefing.  Until those logs
arrive this is validated synthetically only.
"""

from __future__ import annotations

import numpy as np

from ope_bench.estimators import Policy, RewardModel


def sequential_dr_value(
    trajectories: list[dict],
    target: Policy,
    q_model: RewardModel,
    gamma: float = 1.0,
) -> float:
    """Per-decision DR value over a list of trajectories.

    Each trajectory is a dict of equal-length arrays: ``context`` (state ids),
    ``action``, ``reward``, ``propensity`` (behavior prob of the taken action).
    ``q_model.predict_matrix(states)`` returns ``Q̂(s, ·)``; the state value is
    ``V̂(s) = Σ_a π_e(a|s) Q̂(s, a)``.
    """
    values = np.empty(len(trajectories), dtype=np.float64)
    for i, traj in enumerate(trajectories):
        states = np.asarray(traj["context"], dtype=np.int64)
        actions = np.asarray(traj["action"], dtype=np.int64)
        rewards = np.asarray(traj["reward"], dtype=np.float64)
        pb = np.asarray(traj["propensity"], dtype=np.float64)

        q = q_model.predict_matrix(states)              # (T, K)
        pi = target.propensity(states)                  # (T, K)
        v = np.einsum("ta,ta->t", pi, q)                # (T,)
        q_taken = q[np.arange(states.shape[0]), actions]
        rho = pi[np.arange(states.shape[0]), actions] / pb

        acc = 0.0
        for t in range(states.shape[0] - 1, -1, -1):
            acc = v[t] + rho[t] * (rewards[t] + gamma * acc - q_taken[t])
        values[i] = acc
    return float(values.mean())
