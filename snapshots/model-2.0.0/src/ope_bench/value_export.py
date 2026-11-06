"""Post-processing OPE value exporter (Split B).

Compute scalar policy-value estimates — Direct Method (DM), Importance
Sampling (IPS), self-normalised IPS (SNIPS) and Doubly Robust (DR) — each with
a bootstrap confidence interval, for a deterministic *target* policy π_e, from
**existing artifacts**: the logged simulator data (DuckDB) plus the policy engine's
exported ``policy_full*.csv``.  No model retraining; this is a pure
post-processing pass that reuses the estimators in
:mod:`ope_bench.estimators` and writes ``ope_estimates.json`` beside the
policy CSV.

The canonical estimand (must match the oracle grader exactly)::

    V(π_e) = mean over logged decisions of
             [ P(pay within 9 months | x, π_e(x)) · balance(x) · (1 − d(π_e(x))) ]

  * per-decision MEAN (US$ per decision), horizon H = 9 months,
  * ``balance(x)`` = outstanding balance at the START of the decision month.

Logging policy / propensity (ε-floor micro-randomised pilot)
------------------------------------------------------------
Action ``a`` = (channel, discount-bin), discounts discretised into the SAME
11 bins as π_e: ``{0.00, 0.05, …, 0.50}`` (width 0.05).  In "explorable" states
(``exploration_epsilon = ε = 0.08``) the logging policy with probability ε draws
a uniform-random action — channel uniform over the 4 ACTIVE channels
{sms, app_message, phone, field_visit} (NOT 'none') and discount uniform on
[0, 0.55] — and otherwise (prob 1−ε) plays the deterministic incumbent::

    π_b(a | x) = (1 − ε)·1[a = incumbent(x)] + ε·u(a)            (explorable)
    π_b(a | x) = 1[a = incumbent(x)]                             (non-explorable, ε=0)

with the exploration density discretised onto the same 0.05 grid::

    u(channel, bin) = (1/4) · (1/11)   for channel ∈ 4 active channels,
                                       bin ∈ the 11 discount bins covering [0,0.55)
    u(a) = 0                           otherwise (channel 'none', or out of grid)

The 11-bin exploration grid covers [0, 0.55) in 0.05 steps; π_e's bins
{0,…,0.50} are its first 11 left edges, so π_e's support is fully covered →
positivity holds (every reachable action has π_b ≥ ε/44 > 0).

Per-row propensity of the *observed* logged action:
  * ``is_exploration = 0`` → action = incumbent → π_b = (1−ε) + ε·u(a) on an
    explorable row, else 1.0 (the incumbent also collects its ε·u share).
  * ``is_exploration = 1`` → action = exploration draw → π_b = ε·u(a).  The
    incumbent-collision term (1−ε)·1[incumbent = a] is dropped: the incumbent is
    unobserved on exploration rows and the collision probability is negligible.
    This is the standard ε-greedy reconstruction and the documented assumption.

Because π_e is DETERMINISTIC (always ``field_visit`` at a recommended bin), the
IPS weight is ``1[a_logged = π_e(x)] / π_b(a_logged | x)``: only logged rows
whose (channel, discount-bin) equals the recommendation contribute.

Realized logged reward (oracle-matched 9-month inclusive window)::

    r_i = paid_i · balance(x_i) · (1 − d_logged_i),
    paid_i = 1 if recovered=1 in ANY month in [m, m+8] (the 9-month window
             INCLUDING the decision month m), else 0.

Estimators (per-decision mean, US$)
----------------------------------
  * DM    — mean of the policy engine's ``expected_return`` (its reward-model q̂(x,π_e(x))).
  * IPS   — ``mean_i ρ_i r_i``               (``importance_sampling_value``).
  * SNIPS — ``Σ ρ_i r_i / Σ ρ_i``           (self-normalised).
  * DR    — ``mean_i [ q̂(x,π_e) + ρ_i (r_i − q̂(x,a_logged)) ]``
            (``doubly_robust_value``).  q̂(x,π_e) = ``expected_return``;
            q̂(x,a_logged) comes from a :class:`TabularRewardModel` fit on the
            logs, keyed by (channel, discount-bin) — see ``DR_QHAT_NOTE``.

To reuse the policy engine's matrix-shaped estimators without materialising an
(n_rows × 55) matrix, each row is collapsed to a 2-action space that is exact
for a deterministic target: action 0 = the logged action, action 1 = π_e's
action.  π_e puts all mass on action 1; π_b(action 0) is the logged-action
propensity above; the reward model returns [q̂(x,a_logged), q̂(x,π_e)].
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ope_bench.estimators import (
    DeterministicPolicy,
    TabularRewardModel,
    direct_method_value,
    doubly_robust_value,
    importance_sampling_value,
)

# ── estimand / policy constants ──────────────────────────────────────────
HORIZON_MONTHS = 9
EPSILON = 0.08
ACTIVE_CHANNELS = ("sms", "app_message", "phone", "field_visit")  # explore support
N_ACTIVE_CHANNELS = len(ACTIVE_CHANNELS)
DISCOUNT_BIN_WIDTH = 0.05
EXPLORE_DISCOUNT_MAX = 0.55  # exploration draws discount ~ U[0, 0.55]
# 11 discount bins covering [0, 0.55): left edges 0.00, 0.05, …, 0.50
N_DISCOUNT_BINS = int(round(EXPLORE_DISCOUNT_MAX / DISCOUNT_BIN_WIDTH))  # = 11
# uniform exploration mass on a single (active channel, valid bin) cell
U_CELL = 1.0 / (N_ACTIVE_CHANNELS * N_DISCOUNT_BINS)  # = 1/44

PROPENSITY_FORMULA = (
    "epsilon-floor micro-randomised pilot, eps=0.08. "
    "pi_b(a|x) = (1-eps)*1[a=incumbent] + eps*u(a) in explorable states "
    "(exploration_epsilon=0.08), else 1[a=incumbent]. "
    "u(channel,bin) = (1/4)*(1/11) for channel in {sms,app_message,phone,field_visit} "
    "and discount-bin in the 11 width-0.05 bins covering [0,0.55), else 0. "
    "Observed-action propensity: is_exploration=0 -> (1-eps)+eps*u(a) if explorable "
    "else 1.0; is_exploration=1 -> eps*u(a) (incumbent-collision term dropped). "
    "Discounts discretised to bins {0.00,0.05,...,0.50} (width 0.05), matching pi_e."
)

DR_QHAT_NOTE = (
    "DR q-hat for the logged action is a TabularRewardModel (empirical mean "
    "realized reward) fit on the logs, keyed by (channel, discount-bin); q-hat "
    "for the target action pi_e is the policy engine's exported expected_return. No torch "
    "checkpoint is loaded. Unseen (channel,bin) cells fall back to the global "
    "mean reward."
)


def discretize_discount(d: np.ndarray) -> np.ndarray:
    """Map a continuous discount to a π_e bin index (0..N_DISCOUNT_BINS-1).

    Bin k covers ``[k*0.05, (k+1)*0.05)``.  Values are clamped into
    ``[0, N_DISCOUNT_BINS-1]`` so a logged discount of exactly 0.55 lands in the
    last (10) bin rather than spilling out of the grid. A tolerance of 1e-9 bins
    keeps exact edges in the upper bin despite floating point (0.15 / 0.05 is
    2.9999999999999996); without it, doses on an edge — the generator rounds
    doses to 4 decimals — fell into the lower bin, so bins 2, 5 and 6 held
    1/500 more of the uniformly explored mass than ``U_CELL`` assumes.
    """
    x = np.asarray(d, dtype=np.float64) / DISCOUNT_BIN_WIDTH
    k = np.floor(x + 1e-9).astype(np.int64)
    return np.clip(k, 0, N_DISCOUNT_BINS - 1)


# ── log assembly (single SQL pass) ───────────────────────────────────────
_LOG_SQL = f"""
WITH bal AS (
    SELECT
        p.loan_id,
        p.month,
        p.recovered,
        COALESCE(
            lag(p.outstanding_balance) OVER (
                PARTITION BY p.loan_id ORDER BY p.month),
            l.outstanding_balance
        ) AS start_balance
    FROM monthly_panel p
    JOIN loans l USING (loan_id)
),
paid AS (
    -- paid within the inclusive 9-month window [m, m+8]
    SELECT
        b.loan_id,
        b.month,
        b.start_balance,
        MAX(CASE WHEN w.month BETWEEN b.month AND b.month + {HORIZON_MONTHS - 1}
                 THEN w.recovered ELSE 0 END) AS paid_within_h
    FROM bal b
    JOIN bal w
      ON w.loan_id = b.loan_id
     AND w.month BETWEEN b.month AND b.month + {HORIZON_MONTHS - 1}
    GROUP BY b.loan_id, b.month, b.start_balance
)
SELECT
    a.loan_id,
    a.month,
    a.channel                AS channel_logged,
    a.discount_offer         AS discount_logged,
    a.is_exploration,
    a.exploration_epsilon,
    paid.start_balance,
    paid.paid_within_h
FROM actions a
JOIN paid ON paid.loan_id = a.loan_id AND paid.month = a.month
"""


def load_logs_from_duckdb(duckdb_path: str | Path) -> pd.DataFrame:
    """Single-pass extraction of the logged decisions + 9-month reward window."""
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        df = con.execute(_LOG_SQL).fetch_df()
    finally:
        con.close()
    return df


def load_policy(policy_csv: str | Path) -> pd.DataFrame:
    df = pd.read_csv(policy_csv)
    required = {"loan_id", "month", "channel", "discount_offer", "expected_return"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"policy CSV missing columns: {sorted(missing)}")
    return df


# ── core: build the 2-action log dict + propensities ─────────────────────
def build_log_dict(logs: pd.DataFrame, policy: pd.DataFrame) -> dict:
    """Join logs↔policy and assemble the estimator log dict.

    Returns a dict with keys ``context`` (row index), ``action`` (0=logged,
    1=π_e), ``propensity`` (π_b of the logged action), ``reward`` (realized US$),
    ``expected_return`` (DM q̂ for π_e), plus the per-row pieces needed to fit
    the DR tabular reward model: ``logged_bin``, ``logged_channel_id``,
    ``matches_target`` (logged action == π_e action).
    """
    merged = logs.merge(
        policy[["loan_id", "month", "channel", "discount_offer", "expected_return"]],
        on=["loan_id", "month"],
        how="inner",
        suffixes=("", "_target"),
    )
    if merged.empty:
        raise ValueError("no rows after joining logs to policy on (loan_id, month)")

    # target action: π_e is deterministic (always field_visit @ recommended bin)
    target_channel = merged["channel"].to_numpy()
    target_bin = discretize_discount(merged["discount_offer"].to_numpy())

    logged_channel = merged["channel_logged"].to_numpy()
    logged_bin = discretize_discount(merged["discount_logged"].to_numpy())

    matches_target = (logged_channel == target_channel) & (logged_bin == target_bin)

    is_expl = merged["is_exploration"].to_numpy().astype(bool)
    eps_col = merged["exploration_epsilon"].to_numpy().astype(np.float64)
    explorable = eps_col > 0  # exploration_epsilon == 0.08 marks explorable states

    # logged-action active-channel membership + valid bin → exploration support
    chan_to_active = {c: i for i, c in enumerate(ACTIVE_CHANNELS)}
    logged_channel_id = np.array(
        [chan_to_active.get(c, -1) for c in logged_channel], dtype=np.int64
    )
    in_explore_support = (logged_channel_id >= 0) & (logged_bin < N_DISCOUNT_BINS)
    u_logged = np.where(in_explore_support, U_CELL, 0.0)

    # π_b of the OBSERVED logged action (see module docstring)
    prop = np.empty(len(merged), dtype=np.float64)
    #   non-explorable: incumbent w.p. 1
    prop[~explorable] = 1.0
    #   explorable, non-exploration: incumbent → (1-eps) + eps*u(a)
    m_inc = explorable & ~is_expl
    prop[m_inc] = (1.0 - EPSILON) + EPSILON * u_logged[m_inc]
    #   explorable, exploration draw → eps*u(a)
    m_draw = explorable & is_expl
    prop[m_draw] = EPSILON * u_logged[m_draw]

    balance = merged["start_balance"].to_numpy().astype(np.float64)
    paid = merged["paid_within_h"].to_numpy().astype(np.float64)
    discount_logged = merged["discount_logged"].to_numpy().astype(np.float64)
    reward = paid * balance * (1.0 - discount_logged)

    n = len(merged)
    return {
        "context": np.arange(n, dtype=np.int64),
        "action": np.zeros(n, dtype=np.int64),  # logged action == slot 0
        "propensity": prop,
        "reward": reward,
        "expected_return": merged["expected_return"].to_numpy().astype(np.float64),
        "logged_bin": logged_bin,
        "logged_channel_id": logged_channel_id,
        "matches_target": matches_target,
    }


class _TwoActionReward:
    """Reward-model adapter for the 2-action collapse.

    Column 0 = q̂(x, a_logged) (fit tabularly on the logs), column 1 =
    q̂(x, π_e(x)) = the policy engine's ``expected_return``.  ``predict_matrix`` is keyed
    by the row's context id (which is just the row index).
    """

    def __init__(self, qhat_logged: np.ndarray, qhat_target: np.ndarray) -> None:
        self._R = np.column_stack([qhat_logged, qhat_target]).astype(np.float64)

    def predict_matrix(self, context_ids: np.ndarray) -> np.ndarray:
        return self._R[np.asarray(context_ids, dtype=np.int64)]


def _fit_logged_qhat(log: dict) -> np.ndarray:
    """q̂(x, a_logged) via a TabularRewardModel keyed by (channel, bin)."""
    # cell id = channel_id (incl. -1→remap) * N_DISCOUNT_BINS + bin
    chan = log["logged_channel_id"].copy()
    # remap 'none'/unknown channel (-1) to its own slot so it is a valid cell
    chan = np.where(chan < 0, N_ACTIVE_CHANNELS, chan)  # slot 4 = 'none'/other
    n_chan = N_ACTIVE_CHANNELS + 1
    cell = chan * N_DISCOUNT_BINS + log["logged_bin"]
    model = TabularRewardModel(
        n_contexts=n_chan * N_DISCOUNT_BINS, n_actions=1, resolution="full"
    )
    model.fit(cell, np.zeros_like(cell), log["reward"])
    # predict_matrix returns (n,1); squeeze to per-row q̂(x,a_logged)
    return model.predict_matrix(cell)[:, 0]


# ── estimator contributions (vectorised; fast bootstrap) ─────────────────
def _contributions(log: dict, qhat_logged: np.ndarray) -> dict:
    """Per-row contribution arrays so the bootstrap is a cheap resample-mean.

    rho_i = 1[a=π_e] / π_b   (deterministic π_e).  Returns the per-row terms
    whose means (or ratio, for SNIPS) are the point estimates.
    """
    matches = log["matches_target"]
    rho = np.where(matches, 1.0 / log["propensity"], 0.0)
    r = log["reward"]
    er = log["expected_return"]

    ips_term = rho * r
    snips_num = rho * r
    snips_den = rho
    dr_term = er + rho * (r - qhat_logged)
    return {
        "dm": er,
        "ips": ips_term,
        "snips_num": snips_num,
        "snips_den": snips_den,
        "dr": dr_term,
    }


def _bootstrap_ci(values: np.ndarray, n_boot: int, seed: int,
                  denom: np.ndarray | None = None) -> tuple[float, float]:
    """Percentile (2.5/97.5) CI of a resampled mean, or ratio-of-means (SNIPS)."""
    rng = np.random.default_rng(seed)
    n = values.shape[0]
    out = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        if denom is None:
            out[b] = values[idx].mean()
        else:
            d = denom[idx].sum()
            out[b] = values[idx].sum() / d if d != 0 else 0.0
    return float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))


def compute_estimates(
    log: dict,
    n_boot: int = 500,
    seed: int = 0,
    bootstrap_subsample: int | None = None,
) -> dict:
    """Compute DM/IPS/SNIPS/DR point estimates + bootstrap CIs.

    Point estimates use the policy engine's estimator functions on the full log; the
    bootstrap (resample-of-means over precomputed contributions) optionally
    subsamples ``bootstrap_subsample`` rows for runtime (documented in output).
    """
    n = log["context"].shape[0]
    qhat_logged = _fit_logged_qhat(log)

    # --- point estimates via the policy engine's estimators (2-action collapse) ---
    target = DeterministicPolicy(
        actions_per_context=np.ones(n, dtype=np.int64),  # all rows → π_e (slot 1)
        n_actions=2,
    )
    reward_model = _TwoActionReward(qhat_logged, log["expected_return"])
    est_log = {
        "context": log["context"],
        "action": log["action"],          # 0 = logged
        "propensity": log["propensity"],
        "reward": log["reward"],
    }
    # IPS weight as built upstream: pi_e(a_logged)/pi_b = 1[match]/pi_b.
    # DeterministicPolicy(slot1) gives pi_e(action0)=0 for non-matching rows.
    # For matching rows the logged action IS slot1 (π_e), so override action so
    # IPS picks up pi_e(slot1)=1. DM is action-independent (mean of pi_e·rhat).
    est_log_match = dict(est_log)
    est_log_match["action"] = np.where(log["matches_target"], 1, 0).astype(np.int64)

    dm = direct_method_value(est_log_match, target, reward_model)
    ips = importance_sampling_value(est_log_match, target)

    # DR needs TWO distinct indices that the single `action` array can't carry:
    #   rho       = 1[match]/pi_b          (logged-vs-target indicator)
    #   rhat_taken= q-hat(x, a_logged)     (ALWAYS column 0 = logged action)
    # So keep action=slot0 (→ rhat_taken = qhat_logged) and pass rho explicitly
    # via `weights`. Then dm_term = pi_e·rhat = expected_return (slot1), exactly
    # the canonical DR: E[ q-hat(x,pi_e) + rho*(r - q-hat(x,a_logged)) ].
    rho = np.where(log["matches_target"], 1.0 / log["propensity"], 0.0)
    dr = doubly_robust_value(est_log, target, reward_model, weights=rho)

    # SNIPS (self-normalised) — not in the policy engine's API; computed directly.
    contrib = _contributions(log, qhat_logged)
    snips = float(contrib["snips_num"].sum() / contrib["snips_den"].sum()) \
        if contrib["snips_den"].sum() != 0 else 0.0

    # --- bootstrap CIs over per-row contributions ---
    if bootstrap_subsample is not None and bootstrap_subsample < n:
        rng = np.random.default_rng(seed + 1)
        sub = rng.choice(n, size=bootstrap_subsample, replace=False)
        c = {k: v[sub] for k, v in contrib.items()}
        boot_n = bootstrap_subsample
    else:
        c = contrib
        boot_n = n

    dm_ci = _bootstrap_ci(c["dm"], n_boot, seed)
    ips_ci = _bootstrap_ci(c["ips"], n_boot, seed)
    snips_ci = _bootstrap_ci(c["snips_num"], n_boot, seed, denom=c["snips_den"])
    dr_ci = _bootstrap_ci(c["dr"], n_boot, seed)

    return {
        "n": int(n),
        "bootstrap_n": int(boot_n),
        "estimators": {
            "dm": {"value": dm, "ci_low": dm_ci[0], "ci_high": dm_ci[1], "n": int(n)},
            "ips": {"value": ips, "ci_low": ips_ci[0], "ci_high": ips_ci[1], "n": int(n)},
            "snips": {"value": snips, "ci_low": snips_ci[0], "ci_high": snips_ci[1], "n": int(n)},
            "dr": {"value": dr, "ci_low": dr_ci[0], "ci_high": dr_ci[1], "n": int(n)},
        },
    }


def export_ope_estimates(
    duckdb_path: str | Path,
    policy_csv: str | Path,
    out_json: str | Path,
    n_boot: int = 500,
    seed: int = 0,
    bootstrap_subsample: int | None = None,
    extra_out: str | Path | None = None,
) -> dict:
    """End-to-end: load logs + policy, compute estimates, write ``ope_estimates.json``."""
    logs = load_logs_from_duckdb(duckdb_path)
    policy = load_policy(policy_csv)
    log = build_log_dict(logs, policy)
    result = compute_estimates(
        log, n_boot=n_boot, seed=seed, bootstrap_subsample=bootstrap_subsample
    )

    payload = {
        "estimand": {
            "horizon_months": HORIZON_MONTHS,
            "unit": "US$ per decision",
            "reward": "paid_within_9mo * balance * (1 - discount)",
            "propensity": PROPENSITY_FORMULA,
            "dr_qhat": DR_QHAT_NOTE,
            "n_decisions": result["n"],
            "bootstrap_reps": n_boot,
            "bootstrap_n": result["bootstrap_n"],
        },
        "estimators": result["estimators"],
    }

    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2))
    if extra_out is not None:
        extra_out = Path(extra_out)
        extra_out.parent.mkdir(parents=True, exist_ok=True)
        extra_out.write_text(json.dumps(payload, indent=2))
    return payload
