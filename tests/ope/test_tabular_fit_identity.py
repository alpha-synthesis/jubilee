"""The grouped tabular fit is bit-identical to the mask-per-cell loop it replaced."""

from __future__ import annotations

import numpy as np
import pytest

from ope_bench.estimators import (
    DeterministicPolicy,
    TabularRewardModel,
    cross_fitted_dm_value,
    cross_fitted_dr_value,
    direct_method_value,
)


def _loop_fit(n_contexts, n_actions, resolution, x, a, r, w):
    """The original implementation (one boolean mask per cell)."""
    global_mean = float(np.average(r, weights=w)) if r.size else 0.0
    if resolution == "action_only":
        cell = np.full(n_actions, global_mean)
        for ai in range(n_actions):
            m = a == ai
            if m.any():
                cell[ai] = np.average(r[m], weights=w[m])
        return np.tile(cell, (n_contexts, 1))
    R = np.full((n_contexts, n_actions), global_mean)
    for xi in range(n_contexts):
        for ai in range(n_actions):
            m = (x == xi) & (a == ai)
            if m.any():
                R[xi, ai] = np.average(r[m], weights=w[m])
    return R


@pytest.mark.parametrize("resolution", ["full", "action_only"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_grouped_fit_equals_mask_loop_bit_for_bit(resolution, seed):
    rng = np.random.default_rng(seed)
    n, nc, na = 20_000, 12, 9
    x = rng.integers(0, nc, size=n)
    a = rng.integers(0, na, size=n)
    x[: n // 3] = rng.integers(0, 3, size=n // 3)  # crowded cells, empty cells elsewhere
    r = rng.binomial(1, 0.05, size=n) * rng.uniform(100, 30_000, size=n) + rng.normal(size=n)
    w = np.where(rng.random(n) < 0.5, 1.0, 0.37)
    for weights in (None, w):
        got = TabularRewardModel(nc, na, resolution).fit(x, a, r, sample_weight=weights)._R
        want = _loop_fit(nc, na, resolution, x, a, r, np.ones(n) if weights is None else weights)
        np.testing.assert_array_equal(got, want)
    # ids outside the table are ignored by both, never indexed
    x2 = x.copy()
    x2[:5] = nc + 3
    a2 = a.copy()
    a2[5:10] = -1
    got = TabularRewardModel(nc, na, resolution).fit(x2, a2, r)._R
    np.testing.assert_array_equal(got, _loop_fit(nc, na, resolution, x2, a2, r, np.ones(n)))


def test_cross_fitted_dm_is_the_model_term_of_cross_fitted_dr():
    rng = np.random.default_rng(3)
    n, nc, na = 5000, 6, 4
    logs = {"context": rng.integers(0, nc, size=n), "action": rng.integers(0, na, size=n),
            "reward": rng.normal(size=n), "propensity": np.full(n, 1 / na)}
    pol = DeterministicPolicy(rng.integers(0, na, size=nc), na)

    def fit_fn(train):
        return TabularRewardModel(nc, na).fit(train["context"], train["action"], train["reward"])

    dm = cross_fitted_dm_value(logs, pol, fit_fn, n_folds=2, seed=7)
    _, contrib = cross_fitted_dr_value(logs, pol, fit_fn, n_folds=2, seed=7,
                                       weights=np.zeros(n), return_contributions=True)
    assert dm == pytest.approx(float(contrib.mean()), rel=1e-12)
    # with a model fit on everything it is NOT the in-sample DM (folds differ)
    assert dm != direct_method_value(logs, pol, fit_fn(logs))
