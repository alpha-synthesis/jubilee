"""Per-row counterfactual CATE truth via common random numbers (C0 arc).

For every loan-month the generator drew one idiosyncratic logit noise; backing
it out of the logged ``p_recovery`` (exactly as :mod:`ope_eval` does) lets us
re-evaluate the SAME row under any counterfactual action with everything but
the action held fixed. The result is the per-row ground truth an estimator of
heterogeneous treatment effects can be graded against:

* ``p_cf_<channel>`` — true recovery probability under each channel arm, at a
  single reference discount ``d_ref`` (the median logged discount among
  contacted rows; the ``none`` arm is always evaluated at discount 0, matching
  the generator's behaviour policy);
* ``tau_<channel>`` = ``p_cf_<channel> − p_cf_none`` — the true individual
  effect of "act with this channel at the reference offer" vs "do nothing";
* ``p_dose_<dd>`` — the discount dose-response for one channel, for the
  secondary dose analysis.

Feature columns are the ENTERING (start-of-month) values — the state the
behaviour policy actually acted on — reconstructed by lagging the panel; the
panel's own ``days_past_due`` is post-transition (0 for recovered rows) and
would leak the outcome if used as a feature.

Exactness does not depend on which covariate snapshot enters the linear
predictor: the backed-out noise absorbs every non-action term, so swapping only
the action terms reproduces the generator's probabilities to machine precision.
A self-check asserts this on the logged action (``p_true_check``), mirroring
the :mod:`ope_eval` drift guard.

The exported CSV is the cross-repo contract consumed by the policy engine's
``benchmark/cate_recovery.py`` (cross-repo C0 contract).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from collection_simulator.dictionaries import CHANNELS
from collection_simulator.generator import CHANNEL_EFFECT, uses_default_channel_effects
from collection_simulator.ope_eval import (
    _AGE_A,
    _AGE_B,
    _AGE_CENTER,
    _AGE_SCALE,
    _CONTACT_W,
    _FRICTION_W,
    _MACRO_W,
    _NOISE_RESIDUAL_TOL,
    _RESILIENCE_W,
)

DOSE_GRID_DEFAULT: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
DOSE_CHANNEL_DEFAULT = "phone"

#: Columns the policy engine's cate_recovery benchmark requires (the CSV contract).
CONTRACT_COLUMNS: tuple[str, ...] = (
    "loan_id", "month",
    "age", "monthly_income", "dependents", "uf", "product_type",
    "days_past_due", "days_in_credito_em_liquidacao", "loan_age_months",
    "outstanding_balance_start", "contacts_last_3m",
    "channel", "discount_offer", "is_exploration", "recovered",
    "p_logged", "d_ref",
    "p_cf_none", "p_cf_sms", "p_cf_app_message", "p_cf_phone", "p_cf_field_visit",
    "tau_sms", "tau_app_message", "tau_phone", "tau_field_visit",
    "payment_friction",
)

_PANEL_SQL = """
WITH ordered AS (
  SELECT p.*,
         lag(days_past_due) OVER w AS prev_dpd,
         lag(days_in_credito_em_liquidacao) OVER w AS prev_liq,
         lag(outstanding_balance) OVER w AS prev_bal
  FROM monthly_panel p
  WINDOW w AS (PARTITION BY loan_id ORDER BY month)
)
SELECT
  o.loan_id, o.month,
  b.age, b.monthly_income, b.dependents, b.uf,
  l.product_type,
  COALESCE(o.prev_dpd, l.days_past_due)                    AS days_past_due,
  COALESCE(o.prev_liq, l.days_in_credito_em_liquidacao)    AS days_in_credito_em_liquidacao,
  o.loan_age_months,
  COALESCE(o.prev_bal, l.outstanding_balance)              AS outstanding_balance_start,
  o.contacts_last_3m,
  a.channel, a.discount_offer, a.is_exploration,
  CAST(o.recovered AS INTEGER)                             AS recovered,
  t.p_recovery                                             AS p_logged,
  t.borrower_resilience, t.payment_friction,
  t.regional_macro_stress, t.contactability
FROM ordered o
JOIN actions a       USING (loan_id, month)
JOIN oracle_truth t  USING (loan_id, month)
JOIN loans l         USING (loan_id)
JOIN borrowers b     ON b.borrower_id = o.borrower_id
ORDER BY o.loan_id, o.month
"""


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -60.0, 60.0)))


def _offer(d: np.ndarray | float, oc: dict[str, Any]) -> np.ndarray:
    return float(oc["offer_effect"]) * (
        1.0 - np.exp(-float(oc["offer_sensitivity"]) * np.asarray(d, dtype=np.float64))
    )


def true_cate_table(
    db_path: str | Path,
    config: dict[str, Any],
    *,
    dose_grid: tuple[float, ...] = DOSE_GRID_DEFAULT,
    dose_channel: str = DOSE_CHANNEL_DEFAULT,
) -> pd.DataFrame:
    """Build the per-row counterfactual truth table for one simulated run."""
    import duckdb

    oc = config["oracle"]
    if not uses_default_channel_effects(oc):
        raise NotImplementedError(
            "true_cate_table mirrors the default channel-effect table; configs that set "
            "oracle.channel_effects / channel_effects_late are not supported"
        )
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        df = con.execute(_PANEL_SQL).df()
    finally:
        con.close()

    F = lambda k: df[k].to_numpy(dtype=np.float64)  # noqa: E731
    p_log = np.clip(F("p_logged"), 1e-9, 1.0 - 1e-9)
    target = float(oc["target_monthly_recovery_rate"])
    age_curve = _AGE_A * ((F("age") - _AGE_CENTER) / _AGE_SCALE) ** 2 + _AGE_B
    common = (
        np.log(target / (1.0 - target))
        + age_curve
        + float(oc["dpd_effect"]) * (F("days_past_due") / 30.0)
        + float(oc["liquidacao_age_effect"]) * (F("days_in_credito_em_liquidacao") / 30.0)
        + float(oc["loan_age_effect"]) * (F("loan_age_months") / 12.0)
        + _RESILIENCE_W * F("borrower_resilience")
        + _FRICTION_W * F("payment_friction")
        + _MACRO_W * F("regional_macro_stress")
    )
    channel = df["channel"].astype(str).to_numpy()
    contact_log = (channel != "none").astype(np.float64)
    ce_log = np.vectorize(CHANNEL_EFFECT.get)(channel).astype(np.float64)
    con_ = F("contactability")
    logged_det = (
        common + ce_log + _offer(F("discount_offer"), oc) + _CONTACT_W * con_ * contact_log
    )
    # CRN: the row's idiosyncratic noise, backed out of the logged probability.
    noise = np.log(p_log / (1.0 - p_log)) - logged_det

    def p_cf(ch: str, d: np.ndarray | float) -> np.ndarray:
        contact = 0.0 if ch == "none" else 1.0
        eta = common + noise + CHANNEL_EFFECT[ch] + _offer(d, oc) + _CONTACT_W * con_ * contact
        return _sigmoid(eta)

    # Self-check (drift guard, mirrors ope_eval): logged action must reproduce.
    p_true_check = _sigmoid(logged_det + noise)
    resid = float(np.abs(p_true_check - p_log).max())
    if resid > _NOISE_RESIDUAL_TOL:
        raise AssertionError(
            f"counterfactual reconstruction drifted from the generator "
            f"(max resid {resid:.2e}); coefficients no longer match "
            "recovery_probability()"
        )

    contacted = df["channel"] != "none"
    d_ref = float(df.loc[contacted, "discount_offer"].median()) if contacted.any() else 0.0

    out = df[[
        "loan_id", "month", "age", "monthly_income", "dependents", "uf",
        "product_type", "days_past_due", "days_in_credito_em_liquidacao",
        "loan_age_months", "outstanding_balance_start", "contacts_last_3m",
        "channel", "discount_offer", "is_exploration", "recovered",
        "p_logged", "payment_friction",
    ]].copy()
    out["p_true_check"] = p_true_check
    out["d_ref"] = d_ref
    out["p_cf_none"] = p_cf("none", 0.0)
    for ch in CHANNELS:
        if ch == "none":
            continue
        out[f"p_cf_{ch}"] = p_cf(ch, d_ref)
        out[f"tau_{ch}"] = out[f"p_cf_{ch}"] - out["p_cf_none"]
    for d in dose_grid:
        out[f"p_dose_{int(round(d * 100)):02d}"] = p_cf(dose_channel, float(d))
    return out


def export_cate_truth(
    db_path: str | Path,
    config: dict[str, Any],
    out_csv: str | Path,
    **kwargs: Any,
) -> Path:
    """Write the truth table to CSV (the cross-repo contract file)."""
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df = true_cate_table(db_path, config, **kwargs)
    missing = [c for c in CONTRACT_COLUMNS if c not in df.columns]
    if missing:  # defensive: the contract is what downstream pins against
        raise AssertionError(f"contract columns missing: {missing}")
    df.to_csv(out_csv, index=False)
    return out_csv
