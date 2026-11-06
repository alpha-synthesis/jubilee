"""Synthetic contextual bandit with a closed-form true policy value (T-27).

This is the *oracle* for the Oracle Program: a contextual bandit whose true
mean reward ``R̄(x, a)`` is known, so we can compute the exact value of any
policy and use it to grade the OPE estimators (T-31).

The reward structure mirrors the collections simulator used by
``scripts/collections/compare_policies.py`` (the same ``compare_policies`` that
caught the CIF-propensity collapse in experiment 012):

    p(profile, contact, discount) = b + u · (1 − e^{−s·discount})
    R̄(profile, action)           = p · (1 − discount) · debt(profile)

A single drawn reward is a Bernoulli recovery times the net value — i.e. an
individual outcome is a noisy coin flip, while the *policy value* is its mean.
That gap (one sample never reveals the expected profit) is exactly why OPE is
needed on real data.

The canonical effect parameters below are copied from ``compare_policies.py``;
that script remains the source of truth.  They are duplicated (not imported)
to keep this subpackage self-contained and importable without the scripts tree.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Canonical recovery-curve parameters (profile, contact) -> (b, u, s).
# Mirror of compare_policies.EFFECT_PARAMS.
_EFFECT_PARAMS: dict[tuple[str, str], tuple[float, float, float]] = {
    ("young_professional", "call"): (0.01, 0.05, 1.5),
    ("young_professional", "sms"): (0.40, 0.08, 12.0),
    ("young_parent", "call"): (0.04, 0.80, 2.2),
    ("young_parent", "sms"): (0.08, 0.10, 2.5),
    ("deal_seeker", "call"): (0.03, 0.55, 6.0),
    ("deal_seeker", "sms"): (0.22, 0.50, 10.0),
    ("negotiator", "call"): (0.20, 0.42, 6.0),
    ("negotiator", "sms"): (0.02, 0.06, 2.0),
    ("hardship", "call"): (0.03, 0.85, 2.0),
    ("hardship", "sms"): (0.02, 0.05, 2.0),
    ("loyal_payer", "call"): (0.01, 0.04, 1.5),
    ("loyal_payer", "sms"): (0.05, 0.04, 8.0),
}

_PROFILE_ORDER = [
    "young_professional", "young_parent", "deal_seeker",
    "negotiator", "hardship", "loyal_payer",
]


def _recovery_prob(profile: str, contact: str, discount: float) -> float:
    if contact == "no_action":
        return 0.0
    key = (profile, contact)
    if key not in _EFFECT_PARAMS:
        return 0.0
    b, u, s = _EFFECT_PARAMS[key]
    return float(b + u * (1.0 - np.exp(-s * discount)))


@dataclass(frozen=True)
class ActionMeta:
    """One discrete action in the menu: a contact method and a discount."""

    contact: str
    discount: float

    def label(self) -> str:
        if self.contact == "no_action":
            return "no_action"
        return f"{self.contact}@{self.discount:.2f}"


class SyntheticBandit:
    """Closed-form contextual bandit over collections profiles.

    Parameters
    ----------
    profiles : ordered list of context (profile) names.
    actions : ordered menu of :class:`ActionMeta` — the discrete action space,
        aligned with the controller's grid (the OPE menu == the optimizer menu).
    context_probs : prior over contexts ``d0`` (defaults to uniform).
    debt : per-profile reward scale (defaults to 1.0 → reward is "per dollar").
    """

    def __init__(
        self,
        profiles: list[str],
        actions: list[ActionMeta],
        context_probs: np.ndarray | None = None,
        debt: np.ndarray | None = None,
    ) -> None:
        self.profiles = list(profiles)
        self.actions = list(actions)
        self.n_contexts = len(self.profiles)
        self.n_actions = len(self.actions)

        if context_probs is None:
            context_probs = np.full(self.n_contexts, 1.0 / self.n_contexts)
        self.context_probs = np.asarray(context_probs, dtype=np.float64)
        if not np.isclose(self.context_probs.sum(), 1.0):
            raise ValueError("context_probs must sum to 1")

        if debt is None:
            debt = np.ones(self.n_contexts, dtype=np.float64)
        self.debt = np.asarray(debt, dtype=np.float64)

        # Pre-compute p(x,a), net-scale (1-disc)*debt, and R̄(x,a) = p*scale.
        self._p = np.zeros((self.n_contexts, self.n_actions), dtype=np.float64)
        self._scale = np.zeros_like(self._p)
        for xi, prof in enumerate(self.profiles):
            for ai, meta in enumerate(self.actions):
                self._p[xi, ai] = _recovery_prob(prof, meta.contact, meta.discount)
                self._scale[xi, ai] = (1.0 - meta.discount) * self.debt[xi]
        self._R_bar = self._p * self._scale

    # ── ground truth ────────────────────────────────────────────────
    @property
    def true_reward_matrix(self) -> np.ndarray:
        """``R̄(x, a)`` — the (n_contexts, n_actions) true mean reward."""
        return self._R_bar.copy()

    def policy_value(self, policy) -> float:
        """Exact value ``v(π) = Σ_x d0(x) Σ_a π(a|x) R̄(x,a)``."""
        pi = policy.propensity(np.arange(self.n_contexts))  # (n_contexts, K)
        per_context = np.einsum("xa,xa->x", pi, self._R_bar)
        return float(self.context_probs @ per_context)

    def optimal_value(self) -> float:
        """Value of the per-context argmax policy (the achievable ceiling)."""
        return float(self.context_probs @ self._R_bar.max(axis=1))

    def optimal_actions(self) -> np.ndarray:
        """argmax action per context."""
        return self._R_bar.argmax(axis=1)

    # ── sampling ────────────────────────────────────────────────────
    def sample_contexts(self, n: int, rng: np.random.Generator) -> np.ndarray:
        return rng.choice(self.n_contexts, size=n, p=self.context_probs)

    def sample_reward(
        self,
        context_ids: np.ndarray,
        action_ids: np.ndarray,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """Draw rewards: Bernoulli(p) recovery × net value (per (x,a))."""
        x = np.asarray(context_ids, dtype=np.int64)
        a = np.asarray(action_ids, dtype=np.int64)
        p = self._p[x, a]
        scale = self._scale[x, a]
        recovered = rng.random(x.shape[0]) < p
        return recovered.astype(np.float64) * scale

    def reward_variance(self, context_ids: np.ndarray, action_ids: np.ndarray):
        """Var of the drawn reward at (x,a): scale² · p · (1−p)."""
        x = np.asarray(context_ids, dtype=np.int64)
        a = np.asarray(action_ids, dtype=np.int64)
        p = self._p[x, a]
        return (self._scale[x, a] ** 2) * p * (1.0 - p)


def default_action_menu(
    contacts: tuple[str, ...] = ("sms", "call"),
    discounts: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4),
    include_no_action: bool = True,
) -> list[ActionMeta]:
    """Discrete action menu = no_action ⊕ (contacts × discounts)."""
    menu: list[ActionMeta] = []
    if include_no_action:
        menu.append(ActionMeta("no_action", 0.0))
    for contact in contacts:
        for disc in discounts:
            menu.append(ActionMeta(contact, float(disc)))
    return menu


def collections_bandit(
    contacts: tuple[str, ...] = ("sms", "call"),
    discounts: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4),
    context_probs: np.ndarray | None = None,
    debt: np.ndarray | None = None,
) -> SyntheticBandit:
    """Factory for the canonical collections bandit (the H8 ground truth)."""
    menu = default_action_menu(contacts, discounts)
    return SyntheticBandit(
        profiles=list(_PROFILE_ORDER),
        actions=menu,
        context_probs=context_probs,
        debt=debt,
    )
