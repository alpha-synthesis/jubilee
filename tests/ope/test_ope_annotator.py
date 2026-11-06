"""T-29 — simulator as annotator: DM⁺-IS robustness, coverage gain, guards."""

from __future__ import annotations

import numpy as np

from ope_bench.annotator import (
    OracleAnnotator,
    annotate_grid,
    build_annotations,
    dm_plus_is_value,
    naive_dr_value,
)
from ope_bench.bandit import collections_bandit
from ope_bench.estimators import (
    DeterministicPolicy,
    TabularRewardModel,
    cross_fitted_dr_value,
    direct_method_value,
    doubly_robust_value,
)
from ope_bench.logging_policy import (
    LoggingPolicy,
    generate_logs,
    suboptimal_incumbent,
)


def _setup(epsilon=0.3, n=40_000, seed=0, explore=None, context_probs=None):
    bandit = collections_bandit(context_probs=context_probs)
    inc = suboptimal_incumbent(bandit)
    behavior = LoggingPolicy(
        inc, bandit.n_actions, epsilon=epsilon, explore_actions=explore)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    logs = generate_logs(bandit, behavior, n=n, seed=seed)
    truth = bandit.policy_value(target)
    return bandit, behavior, target, logs, truth


def test_dm_plus_is_unbiased_under_biased_annotator():
    """CANDOR Prop. 1: a biased annotator does NOT bias DM⁺-IS — only DM⁺.

    Measured the way the paper does it (Fig. 3): the *bias* over many seeds.
    A single point estimate hides the result because the IS correction that
    cancels the annotation bias has high variance; averaging reveals that
    DM⁺-IS is unbiased while DM⁺ (pure direct method) inherits the full bias.
    """
    from ope_bench.annotator import AugmentedRewardModel

    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    behavior = LoggingPolicy(inc, bandit.n_actions, epsilon=0.3)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    truth = bandit.policy_value(target)
    annot = OracleAnnotator(bandit.true_reward_matrix, bias=0.5)

    err_dmis, err_dmplus = [], []
    for seed in range(100):
        logs = generate_logs(bandit, behavior, n=3000, seed=seed)
        annotations = build_annotations(
            logs, target, annot, rng=np.random.default_rng(seed))
        aug = AugmentedRewardModel(
            bandit.n_contexts, bandit.n_actions, 1.0).fit(logs, annotations)
        err_dmplus.append(direct_method_value(logs, target, aug) - truth)
        err_dmis.append(dm_plus_is_value(
            logs, annotations, target, bandit.n_contexts, bandit.n_actions,
            seed=seed) - truth)

    bias_dmis = abs(float(np.mean(err_dmis)))
    bias_dmplus = abs(float(np.mean(err_dmplus)))
    assert bias_dmplus > 0.1                 # DM⁺ inherits the annotation bias
    assert bias_dmis < 0.02                  # DM⁺-IS bias ≈ 0 (it → variance)
    assert bias_dmis < bias_dmplus / 5


def test_annotation_weight_zero_reduces_to_dr():
    """Backward-compat: no annotation weight → DM⁺-IS == cross-fitted plain DR."""
    bandit, _, target, logs, _ = _setup(n=10_000, seed=2)
    rng = np.random.default_rng(0)
    annot = OracleAnnotator(bandit.true_reward_matrix, bias=0.3)
    annotations = build_annotations(logs, target, annot, rng=rng)

    v_dm_plus_is = dm_plus_is_value(
        logs, annotations, target, bandit.n_contexts, bandit.n_actions,
        annotation_weight=0.0, seed=0)

    def plain_fit(train_logs):
        return TabularRewardModel(
            bandit.n_contexts, bandit.n_actions, "full"
        ).fit(train_logs["context"], train_logs["action"], train_logs["reward"])

    v_dr = cross_fitted_dr_value(logs, target, plain_fit, seed=0)
    assert np.isclose(v_dm_plus_is, v_dr)


def test_annotations_recover_value_under_hard_coverage_gap():
    """When the régua NEVER takes the target action, DR is biased (empty cells);
    the simulator's annotations fill them, so DM⁺-IS recovers the true value."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    truth = bandit.policy_value(target)

    # explore set EXCLUDES every context's optimal action → those cells are
    # never sampled (a hard positivity gap for the target).
    optimal = set(int(a) for a in bandit.optimal_actions())
    explore = np.array([a for a in range(bandit.n_actions) if a not in optimal])
    behavior = LoggingPolicy(
        inc, bandit.n_actions, epsilon=0.3, explore_actions=explore)
    logs = generate_logs(bandit, behavior, n=20_000, seed=7)
    rng = np.random.default_rng(0)
    annot = OracleAnnotator(bandit.true_reward_matrix)  # perfect simulator
    annotations = build_annotations(logs, target, annot, rng=rng)

    plain_model = TabularRewardModel(
        bandit.n_contexts, bandit.n_actions, "full"
    ).fit(logs["context"], logs["action"], logs["reward"])
    v_dr = doubly_robust_value(logs, target, plain_model)
    v_dmis = dm_plus_is_value(
        logs, annotations, target, bandit.n_contexts, bandit.n_actions)

    assert abs(v_dr - truth) > 0.05            # DR leans on empty optimal cells
    assert abs(v_dmis - truth) < 0.01          # annotations recover the value


def test_naive_dr_biased_under_nonuniform_d0():
    """CANDOR App. D: splicing grid annotations distorts d0 → naive DR biased.

    DM⁺-IS averages over the FACTUAL logs (which follow d0); the annotations only
    enter the reward-model fit, so it stays correct.
    """
    probs = np.array([0.50, 0.30, 0.10, 0.05, 0.03, 0.02])  # non-uniform d0
    bandit, behavior, target, logs, truth = _setup(
        n=20_000, seed=3, context_probs=probs)
    rng = np.random.default_rng(0)
    annot = OracleAnnotator(bandit.true_reward_matrix)  # perfect (bias=0)
    grid = annotate_grid(bandit.n_contexts, bandit.n_actions, annot, rng=rng)
    # replicate the (uniform-over-contexts) grid so M ≈ 4N — the spliced naive
    # sum then visibly distorts the non-uniform d0.
    reps = (4 * len(logs["reward"])) // grid["context"].shape[0]
    grid_big = {k: np.tile(v, reps) for k, v in grid.items()}

    v_dmis = dm_plus_is_value(
        logs, grid_big, target, bandit.n_contexts, bandit.n_actions)
    v_naive = naive_dr_value(
        logs, grid_big, target, behavior, bandit.n_contexts, bandit.n_actions)

    assert abs(v_dmis - truth) < 0.015                      # correct estimator
    assert abs(v_naive - truth) > 0.02                      # naive distorts d0
    assert abs(v_naive - truth) > abs(v_dmis - truth) * 4


def test_dm_plus_is_sum_is_over_factual_logs_only():
    """Contract lock: DM⁺-IS is exactly DR over the FACTUAL logs with an
    annotation-augmented reward model — the estimator's sample sum never
    extends over annotations (that is what naive DR does, and it differs)."""
    from ope_bench.annotator import AugmentedRewardModel

    bandit, behavior, target, logs, _ = _setup(n=10_000, seed=4)
    rng = np.random.default_rng(0)
    annot = OracleAnnotator(bandit.true_reward_matrix)
    annotations = build_annotations(logs, target, annot, rng=rng)

    aug = AugmentedRewardModel(
        bandit.n_contexts, bandit.n_actions, 1.0).fit(logs, annotations)
    # DR averaged over the n factual transitions only
    v_factual_sum = doubly_robust_value(logs, target, aug)
    # DM⁺-IS with cross-fitting OFF must equal exactly that
    v_dmis = dm_plus_is_value(
        logs, annotations, target, bandit.n_contexts, bandit.n_actions,
        cross_fit=False)
    assert np.isclose(v_factual_sum, v_dmis)

    # naive DR sums over factual ⊕ annotations → a different estimator entirely
    v_naive = naive_dr_value(
        logs, annotations, target, behavior, bandit.n_contexts, bandit.n_actions)
    assert not np.isclose(v_factual_sum, v_naive)
