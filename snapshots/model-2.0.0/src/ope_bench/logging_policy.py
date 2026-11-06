"""Behavior (logging) policy with a known propensity (T-27).

Every IS/DR estimator needs ``P(a|x)`` of the policy that generated the logs.
The real collections rule is deterministic (degenerate propensities) — which is
why the briefing asks for a **micro-randomized pilot**.  Here we reproduce that
pilot synthetically: a deterministic incumbent rule plus an ε exploration floor
over the action menu, giving propensities that are *known by construction*.

    π_b(a|x) = (1 − ε) · 1[a = incumbent(x)]  +  ε · uniform(a ∈ explore set)

With ``explore_actions`` covering the whole menu, every action has propensity
≥ ε/K > 0 (common support holds).  Restricting it carves a coverage gap — the
regime where the simulator-annotator (T-29) earns its keep.
"""

from __future__ import annotations

import numpy as np

from ope_bench.bandit import SyntheticBandit


class LoggingPolicy:
    """Incumbent rule + ε-floor exploration with known propensities."""

    def __init__(
        self,
        incumbent_actions: np.ndarray,
        n_actions: int,
        epsilon: float = 0.1,
        explore_actions: np.ndarray | None = None,
    ) -> None:
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be in [0, 1]")
        self.incumbent_actions = np.asarray(incumbent_actions, dtype=np.int64)
        self.n_actions = int(n_actions)
        self.epsilon = float(epsilon)
        if explore_actions is None:
            explore_actions = np.arange(self.n_actions)
        self.explore_actions = np.asarray(explore_actions, dtype=np.int64)

    def propensity(self, context_ids: np.ndarray) -> np.ndarray:
        x = np.asarray(context_ids, dtype=np.int64)
        n = x.shape[0]
        out = np.zeros((n, self.n_actions), dtype=np.float64)
        # ε spread uniformly over the explore set
        if self.explore_actions.size:
            out[:, self.explore_actions] = self.epsilon / self.explore_actions.size
        # (1-ε) mass on the incumbent action
        inc = self.incumbent_actions[x]
        out[np.arange(n), inc] += 1.0 - self.epsilon
        return out

    def sample(self, context_ids: np.ndarray, rng: np.random.Generator):
        """Draw an action per context and return (actions, taken_propensity)."""
        pi = self.propensity(context_ids)
        # guard against tiny numerical drift before sampling
        pi = pi / pi.sum(axis=1, keepdims=True)
        n = pi.shape[0]
        actions = np.array(
            [rng.choice(self.n_actions, p=pi[i]) for i in range(n)],
            dtype=np.int64,
        )
        taken_prop = pi[np.arange(n), actions]
        return actions, taken_prop


def suboptimal_incumbent(bandit: SyntheticBandit) -> np.ndarray:
    """A *reasonable but not optimal* incumbent: the 2nd-best action per context.

    Deliberately off the oracle so that the target (often the oracle policy)
    differs from the behavior policy — the setting where OPE is interesting.
    """
    order = np.argsort(-bandit.true_reward_matrix, axis=1)  # best→worst per row
    second = order[:, 1]
    return second.astype(np.int64)


def generate_logs(
    bandit: SyntheticBandit,
    policy: LoggingPolicy,
    n: int,
    seed: int = 0,
) -> dict:
    """Roll out the behavior policy on the bandit → a log of transitions.

    Returns a dict of arrays: ``context``, ``action``, ``propensity``,
    ``reward`` (each length ``n``) — the contract consumed by T-28..T-31.
    """
    rng = np.random.default_rng(seed)
    contexts = bandit.sample_contexts(n, rng)
    actions, propensity = policy.sample(contexts, rng)
    rewards = bandit.sample_reward(contexts, actions, rng)
    return {
        "context": contexts,
        "action": actions,
        "propensity": propensity,
        "reward": rewards,
    }
