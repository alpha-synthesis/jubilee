"""Keyed random streams (generator version 2): what is shared across policies,
replicates and batches, and what is not.

Each test states one guarantee of :mod:`collection_simulator.generator`; the
module docstring lists them. The worlds are small but always span several
batches, because the version-1 defect only appeared after the first batch.
"""

from __future__ import annotations

import copy

import duckdb
import numpy as np
import pandas as pd
import pytest

from collection_simulator.config import load_config
from collection_simulator.generator import generate

BATCH = 7  # 60 borrowers -> 9 batches (the last one partial)


def _cfg(epsilon: float = 0.2, coupling: bool = True, mode: str = "confounded") -> dict:
    cfg = load_config("configs/tiny_ci.yaml")
    cfg["population"]["borrowers"] = 60
    cfg["panel"]["months"] = 12
    cfg["actions"]["intensity_confounds_with_friction"] = coupling
    cfg["actions"]["assignment_mode"] = mode
    cfg["actions"]["exploration"] = {
        "epsilon": epsilon,
        "explore_states": ["delinquent", "credito_em_liquidacao"],
        "explore_max_liquidacao_days": 180,
    }
    return cfg


def _one_shot(month, state, days_in_credito_em_liquidacao, **_):
    """Month-0 deviation on explorable rows (consumes no action draws there)."""
    if month == 0 and state in ("delinquent", "credito_em_liquidacao") \
            and days_in_credito_em_liquidacao <= 180:
        return "sms", 0.125
    return None


def _always(**_):
    """Overrides every loan-month: never consumes an action draw."""
    return "field_visit", 0.30


def _tables(res) -> dict[str, pd.DataFrame]:
    con = duckdb.connect(str(res.db_path), read_only=True)
    try:
        return {
            name: con.execute(f"SELECT * FROM {name} ORDER BY ALL").df()
            for name in ("borrowers", "loans", "actions", "monthly_panel", "oracle_truth")
        }
    finally:
        con.close()


def _hidden_per_borrower(truth: pd.DataFrame) -> pd.DataFrame:
    cols = ["borrower_resilience", "payment_friction", "contactability", "regional_macro_stress"]
    return (truth.sort_values(["borrower_id", "month"]).groupby("borrower_id")[cols]
            .first().sort_index())


def _world(tmp_path, name, cfg, **kw):
    return _tables(generate(cfg, tmp_path / name, batch_size=BATCH, **kw))


def test_population_identical_across_policies_and_assignment_settings(tmp_path):
    """Borrowers, loans, hidden factors and regional shocks do not depend on the
    actions: not on an injected policy (one-shot or every month), not on ε, not
    on the coupling switch, not on the assignment mode — in every batch."""
    base = _cfg()
    worlds = {
        "logged": _world(tmp_path, "logged", base),
        "one_shot": _world(tmp_path, "one_shot", base, policy=_one_shot),
        "always": _world(tmp_path, "always", base, policy=_always),
        "eps0": _world(tmp_path, "eps0", _cfg(epsilon=0.0)),
        "coupling_off": _world(tmp_path, "coupling_off", _cfg(coupling=False)),
        "deterministic": _world(tmp_path, "deterministic", _cfg(mode="deterministic_dpd")),
    }
    ref = worlds["logged"]
    assert ref["borrowers"]["borrower_id"].nunique() == 60
    for name, w in worlds.items():
        pd.testing.assert_frame_equal(w["borrowers"], ref["borrowers"], obj=name)
        pd.testing.assert_frame_equal(w["loans"], ref["loans"], obj=name)
        pd.testing.assert_frame_equal(
            _hidden_per_borrower(w["oracle_truth"]), _hidden_per_borrower(ref["oracle_truth"]),
            obj=name,
        )
    # the policies did change the actions (the test is not vacuous)
    assert worlds["always"]["actions"]["channel"].eq("field_visit").all()
    assert not ref["actions"]["channel"].eq("field_visit").all()


def test_draws_identical_at_shared_loan_months(tmp_path):
    """Two policies use the same recovery / charge-off draws at every (loan, month)
    both reach, so outcomes stay coupled until the actions differ."""
    base = _cfg()
    logged = _world(tmp_path, "logged", base)["oracle_truth"]
    twin = _world(tmp_path, "twin", base, policy=_one_shot)["oracle_truth"]
    keys = ["loan_id", "month"]
    both = logged.merge(twin, on=keys, suffixes=("_l", "_t"))
    assert len(both) > 100
    np.testing.assert_array_equal(both["recovery_draw_l"], both["recovery_draw_t"])
    np.testing.assert_array_equal(both["chargeoff_draw_l"], both["chargeoff_draw_t"])

