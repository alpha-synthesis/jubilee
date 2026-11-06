"""Behavioral: grade the grader — OPE recovers the true policy value vs the oracle.

This is the distributional ("over many seeds, at pilot N") version of
experiment-013, complementing the single-run point-bias unit tests in
`tests/test_ope_estimators.py`. The oracle is the closed-form `SyntheticBandit`,
so the *true* value of the target policy is known and each estimator can be graded.

The claim (exp-013): when the reward model is **right**, self-evaluated DM is fine;
when it is **wrong** (the realistic, unverifiable case), DM is badly biased (~44% of
the true value) while DR and DM⁺-IS zero that bias. The misspecified model
(`action_only`, ignoring the profile) is the honest analogue of a world model with a
structural blind spot self-evaluating.

Fast (no training) but lives in the validation tier — it validates the *method*
against ground truth, not data flow.
"""

from __future__ import annotations

import numpy as np
import pytest

from ope_bench.annotator import OracleAnnotator, build_annotations, dm_plus_is_value
from ope_bench.bandit import collections_bandit
from ope_bench.estimators import (
    DeterministicPolicy,
    TabularRewardModel,
    cross_fitted_dr_value,
    direct_method_value,
)
from ope_bench.logging_policy import LoggingPolicy, generate_logs, suboptimal_incumbent

pytestmark = pytest.mark.behavioral

N = 2000          # pilot-scale logs
SEEDS = 60
EPS = 0.2         # behavior-policy exploration floor


def _fit(logs, resolution, bandit):
    return TabularRewardModel(bandit.n_contexts, bandit.n_actions, resolution).fit(
        logs["context"], logs["action"], logs["reward"]
    )


@pytest.fixture(scope="module")
def errors():
    """Per-seed estimator errors (estimate − truth) in both model regimes."""
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    behavior = LoggingPolicy(inc, bandit.n_actions, epsilon=EPS)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    truth = bandit.policy_value(target)
    annot = OracleAnnotator(bandit.true_reward_matrix, bias=0.0)

    e = {k: [] for k in ("dm_well", "dm_miss", "dr_miss", "dmis_miss")}
    for seed in range(SEEDS):
        logs = generate_logs(bandit, behavior, n=N, seed=seed)
        good = _fit(logs, "full", bandit)
        bad = _fit(logs, "action_only", bandit)  # structural blind spot
        ann = build_annotations(logs, target, annot, rng=np.random.default_rng(seed))

        e["dm_well"].append(direct_method_value(logs, target, good) - truth)
        e["dm_miss"].append(direct_method_value(logs, target, bad) - truth)
        e["dr_miss"].append(
            cross_fitted_dr_value(
                logs, target, lambda lg: _fit(lg, "action_only", bandit), seed=seed
            )
            - truth
        )
        e["dmis_miss"].append(
            dm_plus_is_value(logs, ann, target, bandit.n_contexts, bandit.n_actions, seed=seed)
            - truth
        )
    return {k: np.asarray(v) for k, v in e.items()}, truth


def _bias(a):
    return abs(float(np.mean(a)))


def _rmse(a):
    return float(np.sqrt(np.mean(a ** 2)))


def test_self_evaluated_dm_is_fine_when_model_is_right(errors, record_metric):
    e, _ = errors
    record_metric(dm_well_bias=_bias(e["dm_well"]))
    assert _bias(e["dm_well"]) < 0.02, (
        f"DM biased even when well-specified ({_bias(e['dm_well']):.3f})"
    )


def test_misspecified_dm_is_badly_biased(errors, record_metric):
    """The unverifiable failure mode: a blind-spot model self-grades far from truth."""
    e, truth = errors
    bias = float(np.mean(e["dm_miss"]))
    record_metric(dm_miss_bias=bias, dm_miss_rmse=_rmse(e["dm_miss"]))
    assert bias < -0.04, f"misspecified DM not biased as expected (bias={bias:.3f})"
    assert _rmse(e["dm_miss"]) > 0.04


def test_dr_and_dmis_zero_the_misspecification_bias(errors, record_metric):
    """DR and DM⁺-IS recover the truth despite the blind-spot reward model."""
    e, _ = errors
    record_metric(
        dr_bias=_bias(e["dr_miss"]), dmis_bias=_bias(e["dmis_miss"]),
        dr_rmse=_rmse(e["dr_miss"]), dmis_rmse=_rmse(e["dmis_miss"]),
    )
    assert _bias(e["dr_miss"]) < 0.02, f"DR did not correct the bias ({_bias(e['dr_miss']):.3f})"
    assert _bias(e["dmis_miss"]) < 0.02, (
        f"DM⁺-IS did not correct the bias ({_bias(e['dmis_miss']):.3f})"
    )
    # and they are more accurate than the self-evaluated DM under misspecification
    assert _rmse(e["dr_miss"]) < _rmse(e["dm_miss"])
    assert _rmse(e["dmis_miss"]) < _rmse(e["dm_miss"])
