"""Simulator as counterfactual annotator → DM⁺-IS (CANDOR, T-29).

The logs only cover the actions the incumbent took.  A calibrated simulator can
*annotate* outcomes for untaken actions, filling the reward model's coverage.
CANDOR (Mandyam et al. 2024) proves the safe place for these annotations is the
**reward-model fit only** — the IS correction stays anchored on factual rewards.
Then (Prop. 1) the estimator is unbiased *even if the annotator is biased*: the
annotator's bias flows into variance, never into the estimate.

The opposite — splicing annotated rows into the estimator sum (``naive_dr``) —
is arbitrarily biased because it changes the context distribution (App. D).
Both are implemented here so the test suite can show the difference.
"""

from __future__ import annotations

import numpy as np

from ope_bench.estimators import (
    Policy,
    TabularRewardModel,
    cross_fitted_dr_value,
    doubly_robust_value,
)


class OracleAnnotator:
    """Annotates counterfactual outcomes from the true bandit reward.

    ``bias`` shifts every annotation by a constant (a deliberately mis-calibrated
    simulator); ``noise`` adds zero-mean Gaussian noise.  Either degrades the
    annotation without—per CANDOR Prop. 1—biasing the DM⁺-IS estimate.
    """

    def __init__(
        self,
        true_reward_matrix: np.ndarray,
        bias: float = 0.0,
        noise: float = 0.0,
    ) -> None:
        self._R = np.asarray(true_reward_matrix, dtype=np.float64)
        self.bias = float(bias)
        self.noise = float(noise)

    def annotate(
        self,
        context_ids: np.ndarray,
        action_ids: np.ndarray,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        x = np.asarray(context_ids, dtype=np.int64)
        a = np.asarray(action_ids, dtype=np.int64)
        g = self._R[x, a] + self.bias
        if self.noise > 0.0:
            rng = rng or np.random.default_rng()
            g = g + rng.normal(0.0, self.noise, size=g.shape)
        return g


def build_annotations(
    logs: dict,
    target: Policy,
    annotator: OracleAnnotator,
    rng: np.random.Generator | None = None,
) -> dict:
    """Annotate, for each logged context, the action(s) the target would take.

    These are exactly the cells the DM term of DR reads — so the annotations go
    where the reward model is most consulted (and least covered by a behavior
    policy that never takes the target action).
    """
    x = logs["context"]
    pi_e = target.propensity(x)
    # support actions of the target (deterministic → one; stochastic → several)
    rows, acts = np.nonzero(pi_e > 0)
    ctx = x[rows]
    g = annotator.annotate(ctx, acts, rng=rng)
    return {"context": ctx, "action": acts.astype(np.int64), "value": g}


def annotate_grid(
    n_contexts: int,
    n_actions: int,
    annotator: OracleAnnotator,
    rng: np.random.Generator | None = None,
) -> dict:
    """Annotate every ``(context, action)`` cell once (uniform over contexts).

    A simulator that "fills the whole grid" produces annotations whose context
    distribution is uniform — generally **≠ d0**.  Spliced into the estimator
    sum (``naive_dr``) this distorts d0 and biases the estimate; used only in
    the reward-model *fit* (``dm_plus_is``) it is harmless.
    """
    ctx = np.repeat(np.arange(n_contexts), n_actions)
    act = np.tile(np.arange(n_actions), n_contexts)
    g = annotator.annotate(ctx, act, rng=rng)
    return {"context": ctx, "action": act.astype(np.int64), "value": g}


class AugmentedRewardModel:
    """Reward model fit on factual logs ⊕ counterfactual annotations.

    Annotations may be down-weighted (``annotation_weight`` < 1) when they are
    known to be imperfect — CANDOR App. F shows down-weighting imperfect
    annotations lowers variance.  ``annotation_weight = 0`` recovers the
    factual-only model (so DM⁺-IS reduces to plain DR).
    """

    def __init__(
        self,
        n_contexts: int,
        n_actions: int,
        annotation_weight: float = 1.0,
        resolution: str = "full",
    ) -> None:
        self.annotation_weight = float(annotation_weight)
        self._model = TabularRewardModel(n_contexts, n_actions, resolution=resolution)

    def fit(self, logs: dict, annotations: dict) -> AugmentedRewardModel:
        fx = logs["context"]
        fa = logs["action"].astype(np.int64)
        fr = logs["reward"].astype(np.float64)
        fw = np.ones(fx.shape[0], dtype=np.float64)

        ax = annotations["context"]
        aa = annotations["action"].astype(np.int64)
        ar = annotations["value"].astype(np.float64)
        aw = np.full(ax.shape[0], self.annotation_weight, dtype=np.float64)

        ctx = np.concatenate([fx, ax])
        act = np.concatenate([fa, aa])
        rew = np.concatenate([fr, ar])
        wgt = np.concatenate([fw, aw])
        self._model.fit(ctx, act, rew, sample_weight=wgt)
        return self

    def predict_matrix(self, context_ids: np.ndarray) -> np.ndarray:
        return self._model.predict_matrix(context_ids)


def dm_plus_is_value(
    logs: dict,
    annotations: dict,
    target: Policy,
    n_contexts: int,
    n_actions: int,
    annotation_weight: float = 1.0,
    cross_fit: bool = True,
    seed: int = 0,
    resolution: str = "full",
    return_contributions: bool = False,
) -> float | tuple[float, "np.ndarray"]:
    """DM⁺-IS: DR whose reward model is fit on factual ⊕ annotations.

    The IS correction iterates over the **factual logs only** (``logs``); the
    annotations touch the reward-model fit and nothing else.  Cross-fitting
    (default) splits the fit data from the evaluation sample, which is what
    makes the estimate unbiased even under a biased annotator (CANDOR Prop. 1).
    """

    def fit_fn(train_logs: dict):
        return AugmentedRewardModel(
            n_contexts, n_actions, annotation_weight, resolution=resolution
        ).fit(train_logs, annotations)

    if cross_fit:
        return cross_fitted_dr_value(
            logs, target, fit_fn, seed=seed, return_contributions=return_contributions
        )
    if return_contributions:
        raise ValueError("return_contributions requires cross_fit=True")
    return doubly_robust_value(logs, target, fit_fn(logs))


def naive_dr_value(
    logs: dict,
    annotations: dict,
    target: Policy,
    behavior: Policy,
    n_contexts: int,
    n_actions: int,
) -> float:
    """The WRONG way (CANDOR App. D): annotated rows enter the estimator sum.

    Splices ``(x, ã, g)`` annotations into the factual logs and runs standard DR
    over the union.  This alters the context distribution ``d0`` and is
    arbitrarily biased — implemented only as a negative control for the tests.
    """
    ax = annotations["context"]
    aa = annotations["action"].astype(np.int64)
    ar = annotations["value"].astype(np.float64)
    # naive propensity for the spliced rows: the behavior prob of that action
    pb = behavior.propensity(ax)
    a_prop = pb[np.arange(ax.shape[0]), aa]
    a_prop = np.where(a_prop <= 0, 1.0, a_prop)  # avoid div-by-zero in the control

    spliced = {
        "context": np.concatenate([logs["context"], ax]),
        "action": np.concatenate([logs["action"].astype(np.int64), aa]),
        "propensity": np.concatenate([logs["propensity"].astype(np.float64), a_prop]),
        "reward": np.concatenate([logs["reward"].astype(np.float64), ar]),
    }
    # reward model also fit on the union (matches the paper's naive estimator)
    model = TabularRewardModel(n_contexts, n_actions, resolution="full").fit(
        spliced["context"], spliced["action"], spliced["reward"])
    return doubly_robust_value(spliced, target, model)
