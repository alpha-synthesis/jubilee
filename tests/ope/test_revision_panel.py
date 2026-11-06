"""Revision-campaign additions to the panel: refit bootstrap for DM, the stage-rule
candidate, per-role seeds and the cross-fitted non-tabular regime."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ope_bench.estimators import DeterministicPolicy, TabularRewardModel, direct_method_value
from ope_bench.panel import (
    N_ACTIONS,
    N_CONTEXTS,
    PI_FAR,
    PI_NEAR,
    PI_STAGE,
    action_id,
    dm_refit_bootstrap,
    estimate_panel,
)


def _logs(n=6000, seed=0):
    rng = np.random.default_rng(seed)
    ctx = rng.integers(0, N_CONTEXTS, size=n)
    act = rng.integers(0, N_ACTIONS, size=n)
    # make sure every target cell is populated
    for pol in (PI_FAR, PI_NEAR, PI_STAGE):
        a = pol.actions_per_context()
        idx = rng.choice(n, size=N_CONTEXTS * 4, replace=False)
        act[idx] = a[ctx[idx]]
    reward = rng.binomial(1, 0.05, size=n) * rng.uniform(500, 20000, size=n)
    explored = rng.random(n) < 0.08
    table = np.zeros((N_CONTEXTS, N_ACTIONS))
    np.add.at(table, (ctx, act), 1.0)
    table /= table.sum(axis=1, keepdims=True)
    return {"context": ctx, "action": act, "reward": reward,
            "propensity": table[ctx, act], "explored": explored,
            "eps": np.where(explored, 0.08, 0.0)}


@pytest.mark.parametrize("target", [PI_FAR, PI_NEAR, PI_STAGE])
def test_dm_refit_bootstrap_point_equals_tabular_dm(target):
    logs = _logs()
    pol = DeterministicPolicy(target.actions_per_context(), N_ACTIONS)
    model = TabularRewardModel(N_CONTEXTS, N_ACTIONS, resolution="full").fit(
        logs["context"], logs["action"], logs["reward"])
    out = dm_refit_bootstrap(logs, target, n_boot=50, seed=1)
    assert out["value"] == pytest.approx(direct_method_value(logs, pol, model), rel=1e-12)
    assert out["ci_low"] < out["value"] < out["ci_high"]


def test_refit_interval_is_wider_than_fixed_model_interval():
    logs = _logs(seed=3)
    fixed = estimate_panel(logs, PI_NEAR, np.zeros((N_CONTEXTS, N_ACTIONS)), n_boot=60, seed=2)
    refit = dm_refit_bootstrap(logs, PI_NEAR, n_boot=60, seed=2)
    fixed_width = fixed["dm"]["ci_high"] - fixed["dm"]["ci_low"]
    assert (refit["ci_high"] - refit["ci_low"]) > 3 * fixed_width


def test_stage_rule_matches_its_generator_policy_in_every_context():
    pol = PI_STAGE.generator_policy()
    acts = PI_STAGE.actions_per_context()
    for c in range(N_CONTEXTS):
        dpd = (c // 3) * 30 + 15  # a DPD inside the context's 30-day step
        state = "credito_em_liquidacao" if dpd >= 90 else "delinquent"
        ch, d = pol(month=0, state=state, days_past_due=dpd,
                    days_in_credito_em_liquidacao=max(0, min(dpd - 90, 180)))
        assert int(action_id([ch], [d])[0]) == acts[c]
    assert pol(month=1, state="delinquent", days_past_due=40,
               days_in_credito_em_liquidacao=0) is None


def test_default_seed_roles_reproduce_the_archived_setting():
    logs = _logs(seed=5)
    tmat = np.zeros((N_CONTEXTS, N_ACTIONS))
    tmat[np.arange(N_CONTEXTS), PI_NEAR.actions_per_context()] = 900.0
    a = estimate_panel(logs, PI_NEAR, tmat, n_boot=20, seed=11)
    b = estimate_panel(logs, PI_NEAR, tmat, n_boot=20, seed=11, fold_seed=11, annotator_seed=11)
    c = estimate_panel(logs, PI_NEAR, tmat, n_boot=20, seed=11, fold_seed=12)
    assert a == b
    assert a["dr"]["value"] != c["dr"]["value"]


# ── non-tabular regime ─────────────────────────────────────────────────────
sklearn = pytest.importorskip("sklearn")

from ope_bench.nontabular import (  # noqa: E402
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    GBMConfig,
    design_matrix,
    estimate_nontabular,
    fit_cross_fitted_nuisances,
)

CATS = {"product_type": ["p0", "p1"], "uf": ["u0", "u1", "u2"],
        "gender": ["f", "m"], "income_band": ["b0", "b1"]}


def _cohort(n=8000, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c: rng.uniform(0, 1, size=n) for c in NUMERIC_FEATURES})
    df["dpd"] = rng.integers(30, 270, size=n)
    for c in CATEGORICAL_FEATURES:
        df[c] = rng.choice(CATS[c], size=n)
    return df


def test_cross_fitting_never_uses_a_rows_own_reward():
    """Perturbing the rewards of fold-0 rows leaves their reward predictions and
    propensities unchanged: fold-0 rows are scored by models fit on fold 1."""
    cfg = GBMConfig(max_iter=20, min_samples_leaf=20)
    df = _cohort()
    x = design_matrix(df, CATS)
    rng = np.random.default_rng(1)
    actions = rng.integers(0, N_ACTIONS, size=len(df))
    target = {"t": np.full(len(df), 1 + 2)}
    actions[: len(df) // 10] = 3
    rewards = rng.binomial(1, 0.1, size=len(df)) * 1000.0
    folds = rng.integers(0, 2, size=len(df))
    a = fit_cross_fitted_nuisances(x, actions, rewards, target, folds, cfg)
    r2 = rewards.copy()
    r2[folds == 0] = rng.permutation(r2[folds == 0]) + 7.0
    b = fit_cross_fitted_nuisances(x, actions, r2, target, folds, cfg)
    f0 = folds == 0
    np.testing.assert_array_equal(a["m_logged"][f0], b["m_logged"][f0])
    np.testing.assert_array_equal(a["m_target"]["t"][f0], b["m_target"]["t"][f0])
    assert not np.array_equal(a["m_logged"][~f0], b["m_logged"][~f0])
    # propensities never read rewards: perturb fold-0 ACTIONS instead. Fold-0 rows
    # are scored by the classifier fit on fold 1, so their propensities must not
    # move, while fold-1 propensities (fit on the perturbed fold 0) must.
    act2 = actions.copy()
    act2[f0] = np.where(rng.random(int(f0.sum())) < 0.5, 3, act2[f0])
    c = fit_cross_fitted_nuisances(x, act2, rewards, target, folds, cfg)
    np.testing.assert_array_equal(a["e_target"]["t"][f0], c["e_target"]["t"][f0])
    assert not np.array_equal(a["e_target"]["t"][~f0], c["e_target"]["t"][~f0])


def test_nontabular_estimators_unbiased_without_hidden_confounding():
    """Assignment depends on an observed covariate only: the four estimators
    recover the target value (known in closed form) within a few percent, and
    the estimated propensities are calibrated (mean IS weight close to 1).

    With an over-flexible propensity model (e.g. ``min_samples_leaf=50`` here)
    IS drifts upward although its weights are unbiased in expectation: noisy
    propensity estimates inflate ``E[1/e]`` (Jensen). ``sum_w_over_n`` is the
    reference-free diagnostic for that."""
    cfg = GBMConfig(max_iter=60, min_samples_leaf=500, max_leaf_nodes=8)
    n = 40000
    df = _cohort(n=n, seed=4)
    x = design_matrix(df, CATS)
    rng = np.random.default_rng(5)
    t_cell = 1 + 2  # sms, bin 2
    p_t = 0.05 + 0.25 * df["income_band"].eq("b1").to_numpy()  # observed confounder
    take = rng.random(n) < p_t
    actions = np.where(take, t_cell, rng.integers(4, N_ACTIONS, size=n))
    mu_t = 200 + 600 * df["income_band"].eq("b1").to_numpy()
    rewards = np.where(take, mu_t, 100.0) + rng.normal(0, 50, size=n)
    truth = float(mu_t.mean())
    folds = rng.integers(0, 2, size=n)
    tgt = np.full(n, t_cell)
    nuis = fit_cross_fitted_nuisances(x, actions, rewards, {"t": tgt}, folds, cfg)
    est = estimate_nontabular(nuis, "t", actions, rewards, tgt, np.zeros(n, bool),
                              np.zeros(n), cfg, n_boot=30, seed=0)
    for key in ("is", "snips", "dr", "dm"):
        assert est[key]["value"] == pytest.approx(truth, rel=0.04), key
    assert est["diagnostics"]["sum_w_over_n"] == pytest.approx(1.0, abs=0.03)
    assert est["diagnostics"]["n_match"] == int(take.sum())
