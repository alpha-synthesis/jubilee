"""Non-tabular nuisance regime: gradient-boosted reward and propensity models.

Runs on the same month-0 logs, targets and action cells as the tabular panel
(:mod:`ope_bench.panel`), with two deliberate differences, both reported as
part of the contrast between regimes:

* **covariates** — the tabular panel sees 36 contexts (30-day DPD step ×
  start-balance tercile); here the nuisances read the observable month-0 loan
  and borrower attributes listed in :data:`NUMERIC_FEATURES` and
  :data:`CATEGORICAL_FEATURES` (never a borrower-level latent factor; the
  region code identifies the region's macro shock, which moves outcomes but
  not assignment);
* **model class and fitting** — gradient boosting
  (``HistGradientBoostingRegressor`` for the reward, one binary
  ``HistGradientBoostingClassifier`` per target for ``P(A = target cell | x)``),
  both **cross-fitted on the same folds**: every row's reward prediction and
  propensity come from models fit on the other fold(s) only. The categorical
  coding is fixed in advance by the caller, so no preprocessing step is fit
  outside a training fold. (The tabular panel instead estimates its
  propensities on the full cohort and cross-fits only the reward model.)

Estimators: DM (mean out-of-fold prediction at the target cell), IS and SNIPS
(estimated propensities), DR (both nuisances cross-fitted) and pilot-DR (the
gradient-boosted reward model with the design-known ε weights of the
randomised rows). Pilot-IS needs no nuisance model and is the same in both
regimes. Intervals are 90% percentile bootstraps of the per-row contributions
with the fitted nuisances held fixed (for DM: conditional on the model).

scikit-learn is an optional dependency, imported only when a model is fit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from ope_bench.value_export import N_DISCOUNT_BINS, U_CELL

NUMERIC_FEATURES = (
    "dpd", "liq_days", "start_balance", "original_principal", "interest_rate_monthly",
    "term_months", "loan_age_months", "remaining_maturity_months", "age",
    "monthly_income", "dependents",
)
CATEGORICAL_FEATURES = ("product_type", "uf", "gender", "income_band")


@dataclass(frozen=True)
class GBMConfig:
    """Hyper-parameters, fixed in development (no search)."""

    max_iter: int = 200
    learning_rate: float = 0.1
    max_leaf_nodes: int = 31
    min_samples_leaf: int = 200
    l2_regularization: float = 1.0
    max_bins: int = 255
    propensity_clip: float = 1e-3
    n_folds: int = 2
    random_state: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def design_matrix(cohort: pd.DataFrame, categories: dict[str, list]) -> np.ndarray:
    """Observable covariates as a float matrix; categories coded by the caller's
    fixed lists. A value outside the list is an error (the coding is fixed in
    advance, never learned from the data)."""
    cols = [cohort[c].to_numpy(np.float64) for c in NUMERIC_FEATURES]
    for c in CATEGORICAL_FEATURES:
        codes = {v: i for i, v in enumerate(categories[c])}
        values = cohort[c].to_numpy()
        unknown = set(values) - set(codes)
        if unknown:
            raise ValueError(f"{c}: values outside the fixed category list: {sorted(unknown)[:5]}")
        cols.append(np.array([codes[v] for v in values], dtype=np.float64))
    return np.column_stack(cols)


def _cat_mask(n_extra: int = 0) -> np.ndarray:
    return np.array([False] * len(NUMERIC_FEATURES) + [True] * len(CATEGORICAL_FEATURES)
                    + [False] * n_extra)


def action_features(action_ids: np.ndarray) -> np.ndarray:
    """(channel code, discount bin) of action cells: channel 0 = none, 1..4 = the
    active channels; the bin is 0 for ``none``."""
    a = np.asarray(action_ids, dtype=np.int64)
    ch = np.where(a == 0, 0, 1 + (a - 1) // N_DISCOUNT_BINS)
    b = np.where(a == 0, 0, (a - 1) % N_DISCOUNT_BINS)
    return np.column_stack([ch, b]).astype(np.float64)


def _reward_model(cfg: GBMConfig, n_features: int):
    from sklearn.ensemble import HistGradientBoostingRegressor

    cat = np.concatenate([_cat_mask(), [True, False]])  # + channel (cat), bin (ordinal)
    assert cat.shape[0] == n_features
    return HistGradientBoostingRegressor(
        loss="squared_error", learning_rate=cfg.learning_rate, max_iter=cfg.max_iter,
        max_leaf_nodes=cfg.max_leaf_nodes, min_samples_leaf=cfg.min_samples_leaf,
        l2_regularization=cfg.l2_regularization, max_bins=cfg.max_bins,
        categorical_features=cat, early_stopping=False, random_state=cfg.random_state,
    )


def _propensity_model(cfg: GBMConfig):
    from sklearn.ensemble import HistGradientBoostingClassifier

    return HistGradientBoostingClassifier(
        learning_rate=cfg.learning_rate, max_iter=cfg.max_iter,
        max_leaf_nodes=cfg.max_leaf_nodes, min_samples_leaf=cfg.min_samples_leaf,
        l2_regularization=cfg.l2_regularization, max_bins=cfg.max_bins,
        categorical_features=_cat_mask(), early_stopping=False,
        random_state=cfg.random_state,
    )


def _percentile_ci(contrib: np.ndarray, stat, n_boot: int, seed: int, alpha: float = 0.10):
    rng = np.random.default_rng(seed)
    n = contrib.shape[0]
    draws = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        draws[b] = stat(rng.integers(0, n, size=n))
    lo, hi = np.quantile(draws, [alpha / 2, 1 - alpha / 2])
    return float(lo), float(hi), float(draws.std(ddof=1))


def fit_cross_fitted_nuisances(
    x: np.ndarray,
    actions: np.ndarray,
    rewards: np.ndarray,
    target_actions: dict[str, np.ndarray],
    folds: np.ndarray,
    cfg: GBMConfig,
) -> dict:
    """Out-of-fold reward predictions (at the logged and at each target's cell)
    and out-of-fold propensities ``P(A = target cell | x)`` for every target.

    ``target_actions[name]`` is the target's action cell for every row.
    """
    n = x.shape[0]
    xa_logged = np.column_stack([x, action_features(actions)])
    out = {
        "m_logged": np.empty(n),
        "m_target": {k: np.empty(n) for k in target_actions},
        "e_target": {k: np.empty(n) for k in target_actions},
        "fit_info": [],
    }
    for k in range(cfg.n_folds):
        test = folds == k
        train = ~test
        if not test.any():
            continue
        reg = _reward_model(cfg, xa_logged.shape[1]).fit(xa_logged[train], rewards[train])
        out["m_logged"][test] = reg.predict(xa_logged[test])
        info = {"fold": k, "n_train": int(train.sum()), "n_test": int(test.sum())}
        for name, ta in target_actions.items():
            xt = np.column_stack([x[test], action_features(ta[test])])
            out["m_target"][name][test] = reg.predict(xt)
            y = (actions == ta).astype(np.int64)
            if y[train].sum() == 0:
                raise ValueError(f"target {name!r}: no logged row of its cell in fold {k}")
            clf = _propensity_model(cfg).fit(x[train], y[train])
            out["e_target"][name][test] = clf.predict_proba(x[test])[:, 1]
            info[f"pos_train_{name}"] = int(y[train].sum())
        out["fit_info"].append(info)
    return out


def estimate_nontabular(
    nuis: dict,
    name: str,
    actions: np.ndarray,
    rewards: np.ndarray,
    target_action: np.ndarray,
    explored: np.ndarray,
    eps: np.ndarray,
    cfg: GBMConfig,
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """DM, IS, SNIPS, DR and pilot-DR for one target from cross-fitted nuisances."""
    m_t = nuis["m_target"][name]
    m_a = nuis["m_logged"]
    e_raw = nuis["e_target"][name]
    e = np.clip(e_raw, cfg.propensity_clip, 1.0)
    match = actions == target_action
    w = np.where(match, 1.0 / e, 0.0)
    w_pilot = np.where(explored & match, 1.0 / np.maximum(eps, 1e-12) / U_CELL, 0.0)
    r = rewards

    contrib = {
        "dm": m_t,
        "is": w * r,
        "dr": m_t + w * (r - m_a),
        "pilot_dr": m_t + w_pilot * (r - m_a),
    }
    res: dict = {}
    for key, c in contrib.items():
        lo, hi, sd = _percentile_ci(c, lambda idx, c=c: c[idx].mean(), n_boot, seed)
        res[key] = {"value": float(c.mean()), "ci_low": lo, "ci_high": hi, "boot_sd": sd}
    wr = w * r
    den = float(w.sum())
    lo, hi, sd = _percentile_ci(
        wr, lambda idx: (wr[idx].sum() / w[idx].sum()) if w[idx].sum() > 0 else 0.0,
        n_boot, seed)
    res["snips"] = {"value": float(wr.sum() / den) if den > 0 else None,
                    "ci_low": lo, "ci_high": hi, "boot_sd": sd}
    n_match = int(match.sum())
    res["diagnostics"] = {
        "n_match": n_match,
        "n_anchor": int((explored & match).sum()),
        "propensity_mean_vs_match_rate": [float(e_raw.mean()), float(match.mean())],
        "propensity_min_on_match": float(e_raw[match].min()) if n_match else None,
        "n_clipped_on_match": int((e_raw[match] < cfg.propensity_clip).sum()),
        "ess_is": float(w.sum() ** 2 / np.square(w).sum()) if n_match else 0.0,
        "sum_w_over_n": float(w.mean()),
        "oof_r2_logged": float(1 - np.mean((r - m_a) ** 2) / np.var(r)),
    }
    return res
