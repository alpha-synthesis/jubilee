"""Panel-world OPE meta-validation: cohort view, target policies, reference values.

Turns the simulator's loan-month world into a finite contextual-bandit view —
the **month-0 decision cohort** (the explorable loans at month 0) — so the
ope_bench estimators run on it exactly as on the synthetic bandit:

* CONTEXT — 30-day entering-DPD step (12, capped) × start-balance tercile (3)
  = 36 ids. Tercile cut points come from the LOGGED cohort and are reused for
  every other cohort of the same run.
* ACTION — 0 = ``none``; 1..44 = (active channel × 11 width-0.05 discount
  bins), the same grid as ``value_export`` (``U_CELL = 1/44``).
* REWARD — ``paid within the H-month window × start_balance × (1 − month-0
  discount)``: recovery value, not cash flow net of costs.
* REFERENCE VALUE — the estimand is the target's per-decision value on the
  month-0 explorable cohort of the generating population: the one-shot
  month-0 action, then the incumbent+ε continuation, conditional on the
  world's regional shocks. Any simulated cohort mean is a Monte-Carlo estimate
  of it. The archived campaign graded against one twin run per target (same
  seed, target injected; ``scripts/run_panel.py``); with generator version 1
  that twin shared the logged population only in its first batch, and its
  Monte-Carlo error was not separately estimated. The revision campaign
  (``scripts/tmlr_campaign.py``) grades against independent population
  replicates and reports their Monte-Carlo standard errors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ope_bench.annotator import OracleAnnotator, build_annotations, dm_plus_is_value
from ope_bench.estimators import (
    DeterministicPolicy,
    TabularRewardModel,
    cross_fitted_dr_value,
    direct_method_value,
    importance_sampling_value,
)
from ope_bench.value_export import (
    ACTIVE_CHANNELS,
    HORIZON_MONTHS,
    N_DISCOUNT_BINS,
    U_CELL,
    discretize_discount,
)

N_ACTIONS = 1 + len(ACTIVE_CHANNELS) * N_DISCOUNT_BINS  # none ⊕ 4×11 = 45
# Explorable-only context space (the estimand is the explorable month-0 cohort,
# Amendment A3): 30-day DPD steps (12, capped) × start-balance tercile (3).
_N_DPD_STEPS = 12
N_CONTEXTS = _N_DPD_STEPS * 3

# Frozen-protocol explorable gate (policy-side; independent of the cell's ε)
EXPLORE_STATES = ("delinquent", "credito_em_liquidacao")
EXPLORE_MAX_LIQ_DAYS = 180


def policy_explorable(state, liq_days) -> np.ndarray:
    state = np.asarray(state, dtype=object)
    liq = np.asarray(liq_days, dtype=np.int64)
    return np.isin(state, EXPLORE_STATES) & (liq <= EXPLORE_MAX_LIQ_DAYS)


def action_id(channel, discount) -> np.ndarray:
    """0 for ``none``; else 1 + channel_idx*11 + discount bin."""
    ch = np.asarray(channel, dtype=object)
    ids = np.zeros(ch.shape, dtype=np.int64)
    bins = discretize_discount(np.asarray(discount, dtype=np.float64))
    for i, name in enumerate(ACTIVE_CHANNELS):
        m = ch == name
        ids[m] = 1 + i * N_DISCOUNT_BINS + bins[m]
    return ids


@dataclass(frozen=True)
class TargetPolicy:
    """Fixed challenger: one (channel, discount) on explorable rows, none elsewhere."""

    name: str
    channel: str
    discount: float

    def generator_policy(self):
        """Callable for ``collection_simulator.generate(policy=...)``.

        ONE-SHOT deviation (Amendment A3): the target acts only at month 0 on
        explorable rows and returns ``None`` everywhere else, falling through
        to the incumbent+ε assignment. Logged rows matching the month-0 action
        then share the target's continuation law, so the single-step panel is
        correctly specified for the 9-month-window estimand.
        """

        def _policy(*, month, state, days_in_credito_em_liquidacao, **_):
            if (
                month == 0
                and state in EXPLORE_STATES
                and days_in_credito_em_liquidacao <= EXPLORE_MAX_LIQ_DAYS
            ):
                return self.channel, self.discount
            return None

        return _policy

    def actions_per_context(self) -> np.ndarray:
        """Deterministic action per context id (all contexts are explorable)."""
        aid = int(action_id([self.channel], [self.discount])[0])
        return np.full(N_CONTEXTS, aid, dtype=np.int64)


@dataclass(frozen=True)
class StageRulePolicy:
    """Context-dependent one-shot deviation: one (channel, discount) below
    ``late_dpd`` days past due, another from it on (explorable rows, month 0).

    ``late_dpd`` must be a multiple of 30 so the rule is exactly a function of
    the 30-day DPD step in the context id.
    """

    name: str
    early_channel: str
    early_discount: float
    late_channel: str
    late_discount: float
    late_dpd: int = 90

    def __post_init__(self):
        if self.late_dpd % 30:
            raise ValueError("late_dpd must be a multiple of 30")

    def generator_policy(self):
        def _policy(*, month, state, days_past_due, days_in_credito_em_liquidacao, **_):
            if (
                month == 0
                and state in EXPLORE_STATES
                and days_in_credito_em_liquidacao <= EXPLORE_MAX_LIQ_DAYS
            ):
                if days_past_due >= self.late_dpd:
                    return self.late_channel, self.late_discount
                return self.early_channel, self.early_discount
            return None

        return _policy

    def actions_per_context(self) -> np.ndarray:
        early = int(action_id([self.early_channel], [self.early_discount])[0])
        late = int(action_id([self.late_channel], [self.late_discount])[0])
        dpd_step = np.arange(N_CONTEXTS) // 3
        return np.where(dpd_step * 30 >= self.late_dpd, late, early).astype(np.int64)


# Discounts sit at BIN CENTERS (bins are width-0.05, left edges 0.25 / 0.10). The
# estimators read every logged row of the matching bin, whose doses are spread
# over the bin, so the bin-level value they estimate and the value of the exact
# center dose can differ; the revision campaign quantifies that gap.
PI_FAR = TargetPolicy("pi_far", "field_visit", 0.275)
PI_NEAR = TargetPolicy("pi_near", "sms", 0.125)
# Revision-campaign contextual candidate (fixed in development, 2026-11-03): an
# SMS reminder with a near-zero discount in early delinquency, a field visit
# with the π_far discount once the loan is 90+ days past due.
PI_STAGE = StageRulePolicy("pi_stage", "sms", 0.025, "field_visit", 0.275, late_dpd=90)

_COHORT_SQL = f"""
SELECT
    l.loan_id,
    l.outstanding_balance                  AS start_balance,
    l.initial_status                       AS state,
    l.days_past_due                        AS dpd,
    l.days_in_credito_em_liquidacao        AS liq_days,
    a.channel                              AS channel_logged,
    a.discount_offer                       AS discount_logged,
    a.is_exploration,
    a.exploration_epsilon,
    COALESCE(w.paid, 0)                    AS paid_within_h
FROM loans l
JOIN actions a ON a.loan_id = l.loan_id AND a.month = 0
LEFT JOIN (
    SELECT loan_id, MAX(CASE WHEN recovered THEN 1 ELSE 0 END) AS paid
    FROM monthly_panel WHERE month < {HORIZON_MONTHS} GROUP BY loan_id
) w ON w.loan_id = l.loan_id
ORDER BY l.loan_id
"""


def load_cohort(db_path) -> pd.DataFrame:
    """Month-0 decision cohort with window reward pieces."""
    import duckdb

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(_COHORT_SQL).fetchdf()
    finally:
        con.close()
    df["reward"] = (
        df["paid_within_h"].astype(np.float64)
        * df["start_balance"].astype(np.float64)
        * (1.0 - df["discount_logged"].astype(np.float64))
    )
    return df


def balance_terciles(cohort: pd.DataFrame) -> np.ndarray:
    return np.quantile(cohort["start_balance"].to_numpy(np.float64), [1 / 3, 2 / 3])


def context_ids(cohort: pd.DataFrame, terciles: np.ndarray) -> np.ndarray:
    dpd_step = np.minimum(cohort["dpd"].to_numpy(np.int64) // 30, _N_DPD_STEPS - 1)
    ter = np.searchsorted(terciles, cohort["start_balance"].to_numpy(np.float64), side="right")
    return dpd_step * 3 + ter


def propensities(cohort: pd.DataFrame, ctx: np.ndarray, actions: np.ndarray) -> np.ndarray:
    """Estimated within-context behavior propensity: P̂(a | context).

    The incumbent is STOCHASTIC (weighted channel mix + beta discount), so a
    point-mass "ε-collapse" propensity is wrong even without hidden
    confounding and would fail the mechanism-off negative control. Empirical
    (context, action) frequencies are consistent whenever assignment depends
    on the context only; under hidden confounding the within-cell selection
    they cannot see is exactly the bias under study (frozen grid, Amendment
    A2). The ε floor guarantees support at the target cells.
    """
    table = np.zeros((N_CONTEXTS, N_ACTIONS), dtype=np.float64)
    np.add.at(table, (ctx, actions), 1.0)
    totals = table.sum(axis=1, keepdims=True)
    table = table / np.maximum(totals, 1.0)
    p = table[ctx, actions]
    return np.maximum(p, 1e-12)


def behavior_propensity_table(ctx: np.ndarray, actions: np.ndarray) -> np.ndarray:
    """The full P̂(a|c) table (used for diagnostics / positivity reporting)."""
    table = np.zeros((N_CONTEXTS, N_ACTIONS), dtype=np.float64)
    np.add.at(table, (ctx, actions), 1.0)
    return table / np.maximum(table.sum(axis=1, keepdims=True), 1.0)


def build_logs(cohort: pd.DataFrame, terciles: np.ndarray) -> dict:
    ctx = context_ids(cohort, terciles)
    actions = action_id(cohort["channel_logged"], cohort["discount_logged"])
    return {
        "context": ctx,
        "action": actions,
        "propensity": propensities(cohort, ctx, actions),
        "reward": cohort["reward"].to_numpy(np.float64),
        # ε-explore metadata for the pilot estimators (Amendment A5): on
        # explore rows the behavior propensity of the logged action cell is
        # KNOWN by construction (ε · U_CELL), regardless of confounding.
        "explored": cohort["is_exploration"].to_numpy(bool),
        "eps": cohort["exploration_epsilon"].to_numpy(np.float64),
    }


def _percentile_ci(draws_fn, n: int, n_boot: int, seed: int, alpha: float = 0.10):
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        stats[b] = draws_fn(idx)
    lo, hi = np.quantile(stats, [alpha / 2, 1.0 - alpha / 2])
    return float(lo), float(hi)


def estimate_panel(
    logs: dict,
    target: TargetPolicy,
    truth_matrix: np.ndarray,
    annotator_bias_frac: float = 0.25,
    annotator_noise_frac: float = 0.25,
    n_boot: int = 200,
    seed: int = 0,
    fold_seed: int | None = None,
    annotator_seed: int | None = None,
) -> dict:
    """The eight-estimator panel + 90% bootstrap CIs for one target policy.

    ``truth_matrix`` is the (N_CONTEXTS × N_ACTIONS) per-context mean reward
    at the target's cells (zeros elsewhere) from the annotator's source
    simulation; it feeds the (degraded) annotator ONLY — never the estimator
    sums. ``seed`` drives the bootstrap resamples; ``fold_seed`` (cross-fitting
    folds) and ``annotator_seed`` (annotation noise) default to ``seed``, which
    is the archived campaign's setting.

    Intervals: percentile bootstrap of per-row contributions with the fitted
    nuisances held fixed. For DM that is an interval conditional on the fitted
    reward model (its sampling variability is not included); see
    :func:`dm_refit_bootstrap` for the version that refits the model.
    """
    fold_seed = seed if fold_seed is None else fold_seed
    annotator_seed = seed if annotator_seed is None else annotator_seed
    pol = DeterministicPolicy(target.actions_per_context(), N_ACTIONS)
    n = len(logs["reward"])
    rho = pol.propensity(logs["context"])[np.arange(n), logs["action"]] / logs["propensity"]
    r = logs["reward"]

    def fit_fn(train_logs):
        return TabularRewardModel(N_CONTEXTS, N_ACTIONS, resolution="full").fit(
            train_logs["context"], train_logs["action"], train_logs["reward"]
        )

    def fit_fn_blind(train_logs):
        return TabularRewardModel(N_CONTEXTS, N_ACTIONS, resolution="action_only").fit(
            train_logs["context"], train_logs["action"], train_logs["reward"]
        )

    out: dict = {}

    # DM, well-specified and context-blind (H1 regimes) — model held fixed in the CI
    for key, fn in (("dm", fit_fn), ("dm_blind", fit_fn_blind)):
        model = fn(logs)
        value = direct_method_value(logs, pol, model)
        dm_contrib = np.einsum(
            "ia,ia->i", pol.propensity(logs["context"]), model.predict_matrix(logs["context"])
        )
        ci = _percentile_ci(lambda idx: dm_contrib[idx].mean(), n, n_boot, seed)
        out[key] = {"value": value, "ci_low": ci[0], "ci_high": ci[1]}

    # IS
    is_contrib = rho * r
    value = importance_sampling_value(logs, pol)
    ci = _percentile_ci(lambda idx: is_contrib[idx].mean(), n, n_boot, seed)
    out["is"] = {"value": value, "ci_low": ci[0], "ci_high": ci[1]}

    # SNIPS (self-normalized ratio)
    den = rho.sum()
    value = float(is_contrib.sum() / den) if den > 0 else 0.0
    ci = _percentile_ci(
        lambda idx: (is_contrib[idx].sum() / rho[idx].sum()) if rho[idx].sum() > 0 else 0.0,
        n, n_boot, seed,
    )
    out["snips"] = {"value": value, "ci_low": ci[0], "ci_high": ci[1]}

    # DR (cross-fitted, 2 folds) — contribution bootstrap, nuisance fixed
    value, contrib = cross_fitted_dr_value(
        logs, pol, fit_fn, n_folds=2, seed=fold_seed, return_contributions=True
    )
    ci = _percentile_ci(lambda idx: contrib[idx].mean(), n, n_boot, seed)
    out["dr"] = {"value": value, "ci_low": ci[0], "ci_high": ci[1]}

    # DM⁺-IS — annotator = per-context twin truth, deliberately degraded
    scale = float(np.abs(truth_matrix).max())
    annotator = OracleAnnotator(
        truth_matrix,
        bias=annotator_bias_frac * scale,
        noise=annotator_noise_frac * scale,
    )
    annotations = build_annotations(
        logs, pol, annotator, rng=np.random.default_rng(annotator_seed)
    )
    value, contrib = dm_plus_is_value(
        logs, annotations, pol, N_CONTEXTS, N_ACTIONS,
        cross_fit=True, seed=fold_seed, return_contributions=True,
    )
    ci = _percentile_ci(lambda idx: contrib[idx].mean(), n, n_boot, seed)
    out["dm_plus_is"] = {"value": value, "ci_low": ci[0], "ci_high": ci[1]}

    # Pilot estimators (Amendment A5): anchor exclusively on the ε-explore
    # rows, whose propensity is known BY CONSTRUCTION — unbiased under any
    # hidden confounding; undefined at ε = 0 (the identifiability cliff).
    explored = logs.get("explored")
    eps_rows = logs.get("eps")
    aid_per_row = pol.propensity(logs["context"]).argmax(axis=1)
    match = logs["action"] == aid_per_row
    if explored is not None and bool(explored.any()):
        rho_pilot = np.where(
            explored & match, 1.0 / np.maximum(eps_rows, 1e-12) / U_CELL, 0.0
        )
        pilot_contrib = rho_pilot * r
        value = float(pilot_contrib.mean())
        ci = _percentile_ci(lambda idx: pilot_contrib[idx].mean(), n, n_boot, seed)
        out["pilot_is"] = {"value": value, "ci_low": ci[0], "ci_high": ci[1],
                           "n_anchor": int((explored & match).sum())}
        value, contrib = cross_fitted_dr_value(
            logs, pol, fit_fn, n_folds=2, seed=fold_seed,
            weights=rho_pilot, return_contributions=True,
        )
        ci = _percentile_ci(lambda idx: contrib[idx].mean(), n, n_boot, seed)
        out["pilot_dr"] = {"value": value, "ci_low": ci[0], "ci_high": ci[1],
                           "n_anchor": int((explored & match).sum())}
    else:
        for key in ("pilot_is", "pilot_dr"):
            out[key] = {"value": None, "ci_low": None, "ci_high": None,
                        "undefined": "no randomized support (eps = 0)"}
    return out


def dm_refit_bootstrap(
    logs: dict,
    target,
    n_boot: int = 200,
    seed: int = 0,
    alpha: float = 0.10,
) -> dict:
    """Tabular DM with the reward model REFIT on every bootstrap resample.

    Resampling unit: the cohort row (one month-0 decision per loan; the
    simulator configs draw one loan per borrower, so a row is a borrower and
    rows are independent given the regional shocks, which stay fixed). Each
    resample recomputes the context weights and the cell means of the
    full-resolution tabular model, with the same global-mean fallback for an
    empty cell, so the interval includes the sampling variability of the fitted
    model — what the conditional (fixed-model) interval of
    :func:`estimate_panel` leaves out. Returns the percentile interval and the
    bootstrap standard deviation.
    """
    ctx = np.asarray(logs["context"], dtype=np.int64)
    act = np.asarray(logs["action"], dtype=np.int64)
    r = np.asarray(logs["reward"], dtype=np.float64)
    n = r.shape[0]
    acts_t = np.asarray(target.actions_per_context(), dtype=np.int64)
    cell = ctx * N_ACTIONS + act
    tcell = np.arange(N_CONTEXTS) * N_ACTIONS + acts_t
    n_cells = N_CONTEXTS * N_ACTIONS

    def _dm(w: np.ndarray) -> float:
        cnt_ctx = np.bincount(ctx, weights=w, minlength=N_CONTEXTS)
        cnt = np.bincount(cell, weights=w, minlength=n_cells)[tcell]
        tot = np.bincount(cell, weights=w * r, minlength=n_cells)[tcell]
        gmean = float((w * r).sum() / w.sum())
        m = np.where(cnt > 0, tot / np.maximum(cnt, 1e-300), gmean)
        return float((cnt_ctx * m).sum() / w.sum())

    value = _dm(np.ones(n))
    rng = np.random.default_rng(seed)
    draws = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        w = np.bincount(rng.integers(0, n, size=n), minlength=n).astype(np.float64)
        draws[b] = _dm(w)
    lo, hi = np.quantile(draws, [alpha / 2, 1.0 - alpha / 2])
    return {"value": value, "ci_low": float(lo), "ci_high": float(hi),
            "boot_sd": float(draws.std(ddof=1)), "n_boot": int(n_boot)}


def truth_matrix_from_twin(
    twin_cohort: pd.DataFrame, terciles: np.ndarray, target: TargetPolicy
) -> np.ndarray:
    """(N_CONTEXTS × N_ACTIONS) per-context mean reward of a policy-injected
    cohort at the target cells (the annotator's source; zeros elsewhere)."""
    ctx = context_ids(twin_cohort, terciles)
    r = twin_cohort["reward"].to_numpy(np.float64)
    acts = target.actions_per_context()
    mat = np.zeros((N_CONTEXTS, N_ACTIONS), dtype=np.float64)
    global_mean = float(r.mean()) if len(r) else 0.0
    for c in range(N_CONTEXTS):
        m = ctx == c
        mat[c, acts[c]] = float(r[m].mean()) if m.any() else global_mean
    return mat
