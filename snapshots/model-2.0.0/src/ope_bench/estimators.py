"""OPE estimators: Direct Method, Importance Sampling, Doubly Robust (T-28).

Doubly robust (Dudík et al. 2011) is unbiased if *either* the reward model or
the propensities are correct — two chances to be right, with lower variance
than IS.  These estimators consume logs produced by ``generate_logs`` (T-27);
no synthetic/annotated samples ever enter the estimator sum (that guard lives
in :mod:`ope_bench.annotator`).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


# ── Policies ─────────────────────────────────────────────────────────
class Policy(Protocol):
    n_actions: int

    def propensity(self, context_ids: np.ndarray) -> np.ndarray:
        """Return an ``(n, n_actions)`` row-stochastic propensity matrix."""
        ...


class DeterministicPolicy:
    """Maps each context to a single action (one-hot propensity)."""

    def __init__(self, actions_per_context: np.ndarray, n_actions: int) -> None:
        self.actions_per_context = np.asarray(actions_per_context, dtype=np.int64)
        self.n_actions = int(n_actions)

    def propensity(self, context_ids: np.ndarray) -> np.ndarray:
        x = np.asarray(context_ids, dtype=np.int64)
        out = np.zeros((x.shape[0], self.n_actions), dtype=np.float64)
        out[np.arange(x.shape[0]), self.actions_per_context[x]] = 1.0
        return out


class StochasticPolicy:
    """Arbitrary per-context action distribution."""

    def __init__(self, prob_matrix: np.ndarray) -> None:
        self.prob = np.asarray(prob_matrix, dtype=np.float64)
        if not np.allclose(self.prob.sum(axis=1), 1.0):
            raise ValueError("each context row of prob_matrix must sum to 1")
        self.n_actions = self.prob.shape[1]

    def propensity(self, context_ids: np.ndarray) -> np.ndarray:
        return self.prob[np.asarray(context_ids, dtype=np.int64)]


# ── Reward models (the DM part) ──────────────────────────────────────
class RewardModel(Protocol):
    def predict_matrix(self, context_ids: np.ndarray) -> np.ndarray: ...


class OracleRewardModel:
    """Returns the bandit's true ``R̄(x, a)`` — a *correctly specified* model.

    Used to exercise the second leg of double robustness (correct model →
    DR unbiased under *any* propensities).
    """

    def __init__(self, true_reward_matrix: np.ndarray) -> None:
        self._R = np.asarray(true_reward_matrix, dtype=np.float64)

    def predict_matrix(self, context_ids: np.ndarray) -> np.ndarray:
        return self._R[np.asarray(context_ids, dtype=np.int64)]


class TabularRewardModel:
    """Empirical mean reward per cell, fit on logs.

    ``resolution="full"``  → one mean per ``(context, action)`` (consistent).
    ``resolution="action_only"`` → one mean per ``action``, ignoring context
    (deliberately *misspecified*; mirrors the partial-observability trick in
    CANDOR's experiments).  Unseen cells fall back to the global mean.
    """

    def __init__(
        self,
        n_contexts: int,
        n_actions: int,
        resolution: str = "full",
    ) -> None:
        if resolution not in {"full", "action_only"}:
            raise ValueError("resolution must be 'full' or 'action_only'")
        self.n_contexts = int(n_contexts)
        self.n_actions = int(n_actions)
        self.resolution = resolution
        self._R = np.zeros((self.n_contexts, self.n_actions), dtype=np.float64)
        self._fitted = False

    def fit(
        self,
        context_ids: np.ndarray,
        action_ids: np.ndarray,
        rewards: np.ndarray,
        sample_weight: np.ndarray | None = None,
    ) -> TabularRewardModel:
        x = np.asarray(context_ids, dtype=np.int64)
        a = np.asarray(action_ids, dtype=np.int64)
        r = np.asarray(rewards, dtype=np.float64)
        w = (np.ones_like(r) if sample_weight is None
             else np.asarray(sample_weight, dtype=np.float64))
        global_mean = float(np.average(r, weights=w)) if r.size else 0.0

        if self.resolution == "action_only":
            cell = np.full(self.n_actions, global_mean)
            for ai in range(self.n_actions):
                m = a == ai
                if m.any():
                    cell[ai] = np.average(r[m], weights=w[m])
            self._R = np.tile(cell, (self.n_contexts, 1))
        else:
            self._R = np.full((self.n_contexts, self.n_actions), global_mean)
            for xi in range(self.n_contexts):
                for ai in range(self.n_actions):
                    m = (x == xi) & (a == ai)
                    if m.any():
                        self._R[xi, ai] = np.average(r[m], weights=w[m])
        self._fitted = True
        return self

    def predict_matrix(self, context_ids: np.ndarray) -> np.ndarray:
        return self._R[np.asarray(context_ids, dtype=np.int64)]


# ── helpers ──────────────────────────────────────────────────────────
def _importance_ratios(
    logs: dict, target: Policy,
) -> np.ndarray:
    x = logs["context"]
    a = logs["action"].astype(np.int64)
    pb = logs["propensity"].astype(np.float64)
    pi_e = target.propensity(x)
    pe_taken = pi_e[np.arange(x.shape[0]), a]
    return pe_taken / pb


def _reward_model_matrix(logs: dict, reward_model: RewardModel) -> np.ndarray:
    return reward_model.predict_matrix(logs["context"])


# ── estimators ───────────────────────────────────────────────────────
def direct_method_value(
    logs: dict, target: Policy, reward_model: RewardModel,
) -> float:
    """``V̂_DM = mean_i Σ_a π_e(a|x_i) R̂(x_i, a)``."""
    pi_e = target.propensity(logs["context"])
    rhat = _reward_model_matrix(logs, reward_model)
    return float(np.mean(np.einsum("ia,ia->i", pi_e, rhat)))


def importance_sampling_value(logs: dict, target: Policy) -> float:
    """``V̂_IS = mean_i ρ_i r_i``."""
    rho = _importance_ratios(logs, target)
    return float(np.mean(rho * logs["reward"].astype(np.float64)))


def doubly_robust_value(
    logs: dict,
    target: Policy,
    reward_model: RewardModel,
    weights: np.ndarray | None = None,
    strict_positivity: bool = False,
    behavior=None,
) -> float:
    """``V̂_DR = mean_i [ R̂(x_i,π_e) + ρ_i (r_i − R̂(x_i,a_i)) ]``.

    ``weights`` optionally overrides the importance ratios ρ (used by the
    shrinkage estimator, T-30).  With ``strict_positivity`` and a ``behavior``
    policy, raises if the target puts mass on an action the behavior policy
    can never take in some logged context (positivity violation, T-21).
    """
    x = logs["context"]
    a = logs["action"].astype(np.int64)
    r = logs["reward"].astype(np.float64)

    if strict_positivity:
        if behavior is None:
            raise ValueError("strict_positivity requires a behavior policy")
        viol = positivity_violations(target, behavior, x)
        if viol.any():
            raise ValueError(
                f"positivity violation: target places mass on {int(viol.sum())} "
                "(context, action) cells the behavior policy never reaches"
            )

    pi_e = target.propensity(x)
    rhat = _reward_model_matrix(logs, reward_model)
    dm_term = np.einsum("ia,ia->i", pi_e, rhat)
    rhat_taken = rhat[np.arange(x.shape[0]), a]

    rho = _importance_ratios(logs, target) if weights is None else np.asarray(
        weights, dtype=np.float64)
    correction = rho * (r - rhat_taken)
    return float(np.mean(dm_term + correction))


def cross_fitted_dr_value(
    logs: dict,
    target: Policy,
    fit_fn,
    n_folds: int = 2,
    weights: np.ndarray | None = None,
    seed: int = 0,
    return_contributions: bool = False,
) -> float | tuple[float, np.ndarray]:
    """Cross-fitted DR: each sample is scored by a model NOT trained on it.

    Splitting the fit dataset from the evaluation sample removes the in-sample
    correlation between ``R̂`` and the rewards it is scored against — the
    correlation that otherwise lets a biased reward model (e.g. one fit on
    biased annotations, T-29) leak into the estimate.  This is the modern DR
    standard (Kallus & Uehara 2020); CANDOR's unbiasedness assumes exactly this
    fit/estimate split.

    ``fit_fn(train_logs)`` returns a reward model with ``predict_matrix``.
    """
    x = logs["context"]
    a = logs["action"].astype(np.int64)
    r = logs["reward"].astype(np.float64)
    n = x.shape[0]

    pi_e = target.propensity(x)
    rho = (pi_e[np.arange(n), a] / logs["propensity"].astype(np.float64)
           if weights is None else np.asarray(weights, dtype=np.float64))

    fold = np.random.default_rng(seed).integers(0, n_folds, size=n)
    contrib = np.empty(n, dtype=np.float64)
    for k in range(n_folds):
        test = fold == k
        if not test.any():
            continue
        train_logs = {key: np.asarray(v)[~test] for key, v in logs.items()}
        model = fit_fn(train_logs)
        rhat = model.predict_matrix(x[test])
        dm = np.einsum("ia,ia->i", pi_e[test], rhat)
        rhat_taken = rhat[np.arange(int(test.sum())), a[test]]
        contrib[test] = dm + rho[test] * (r[test] - rhat_taken)
    if return_contributions:
        return float(contrib.mean()), contrib
    return float(contrib.mean())


def positivity_violations(
    target: Policy, behavior, context_ids: np.ndarray,
) -> np.ndarray:
    """Boolean ``(n_unique_contexts, n_actions)`` where overlap fails.

    A cell is a violation where the target assigns positive probability but the
    behavior policy assigns zero — the action is unreachable in the logs, so
    its value is unidentified (Assumption 4 of Dudík et al. 2011; the discrete
    analogue of the KDE positivity check in ``benchmark/support.py``, T-21).
    """
    uniq = np.unique(np.asarray(context_ids, dtype=np.int64))
    pe = target.propensity(uniq)
    pb = behavior.propensity(uniq)
    return (pe > 0) & (pb <= 0)
