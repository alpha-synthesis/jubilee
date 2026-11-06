"""Tests for the counterfactual CATE truth table (C0 arc, cross-repo contract).

The module under test, ``collection_simulator.counterfactual``, exposes the
generator's oracle for per-row counterfactual evaluation with the idiosyncratic
noise held fixed (common random numbers): for every loan-month it reports the
true recovery probability under EVERY channel arm (at a single reference
discount ``d_ref``) and under a discount dose grid, plus the per-row true
treatment effects ``tau_<channel> = p_cf_<channel> − p_cf_none``.

These tests pin the cross-repo CSV contract consumed by the policy engine's
``benchmark/cate_recovery.py``.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from collection_simulator.config import DEFAULT_CONFIG, load_config
from collection_simulator.counterfactual import (
    CONTRACT_COLUMNS,
    DOSE_GRID_DEFAULT,
    export_cate_truth,
    true_cate_table,
)
from collection_simulator.generator import generate


def _cfg(**overrides) -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["seed"] = 7
    cfg["population"] = {"borrowers": 60, "loans_per_borrower": [1, 1]}
    cfg["panel"] = {"months": 6}
    for key, value in overrides.items():
        node = cfg
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
    return cfg


@pytest.fixture(scope="module")
def sim(tmp_path_factory):
    cfg = _cfg()
    out = tmp_path_factory.mktemp("sim")
    result = generate(cfg, out)
    return cfg, result.db_path


# ── truth-table correctness ──────────────────────────────────────────────────


def test_reconstruction_matches_logged_p(sim):
    """CRN self-check: rebuilding the LOGGED action must reproduce the logged
    true probability exactly (same guard as ope_eval)."""
    cfg, db = sim
    df = true_cate_table(db, cfg)
    assert np.allclose(df["p_logged"], df["p_true_check"], atol=1e-9)


def test_probabilities_bounded_and_tau_signs(sim):
    cfg, db = sim
    df = true_cate_table(db, cfg)
    p_cols = [c for c in df.columns if c.startswith("p_cf_") or c.startswith("p_dose_")]
    for c in p_cols:
        assert df[c].between(0.0, 1.0).all(), c
    # Contact channels beat 'none' in the generator (CHANNEL_EFFECT + contact
    # term): the TRUE mean effect of every contact arm must be positive.
    for ch in ("sms", "app_message", "phone", "field_visit"):
        assert df[f"tau_{ch}"].mean() > 0.0, ch
    # And identical by construction: tau = p_cf_ch − p_cf_none.
    np.testing.assert_allclose(
        df["tau_phone"], df["p_cf_phone"] - df["p_cf_none"], atol=1e-12
    )


def test_cf_none_equals_logged_for_none_rows(sim):
    """For rows logged as 'none' (discount 0), the counterfactual 'none' arm is
    the factual action — CRN must give back exactly the logged probability."""
    cfg, db = sim
    df = true_cate_table(db, cfg)
    none_rows = df[df["channel"] == "none"]
    assert len(none_rows) > 0
    np.testing.assert_allclose(
        none_rows["p_cf_none"], none_rows["p_logged"], atol=1e-9
    )


def test_dose_response_monotone(sim):
    """offer_effect > 0 with saturating shape: p rises monotonically in the
    discount dose grid, row by row."""
    cfg, db = sim
    df = true_cate_table(db, cfg)
    dose_cols = [c for c in df.columns if c.startswith("p_dose_")]
    assert len(dose_cols) == len(DOSE_GRID_DEFAULT)
    doses = df[dose_cols].to_numpy()
    assert (np.diff(doses, axis=1) >= -1e-12).all()


def test_d_ref_is_contacted_median(sim):
    cfg, db = sim
    df = true_cate_table(db, cfg)
    contacted = df[df["channel"] != "none"]["discount_offer"]
    assert np.isclose(df["d_ref"].iloc[0], float(contacted.median()))
    assert df["d_ref"].nunique() == 1


# ── the cross-repo CSV contract ──────────────────────────────────────────────


def test_export_contract_columns(sim, tmp_path):
    cfg, db = sim
    out = tmp_path / "cate_truth.csv"
    path = export_cate_truth(db, cfg, out)
    assert path.exists()
    import pandas as pd

    df = pd.read_csv(path)
    missing = [c for c in CONTRACT_COLUMNS if c not in df.columns]
    assert not missing, f"contract columns missing from export: {missing}"
    assert len(df) > 0


# ── the no-overlap assignment knob (the colleague scenario) ──────────────────


def test_deterministic_dpd_assignment_has_no_overlap(tmp_path):
    """assignment_mode=deterministic_dpd: treatment iff DPD ≥ threshold —
    observed, deterministic, zero overlap. This is the literal 'treatment only
    for those who did not pay for a long time' scenario."""
    cfg = _cfg(**{
        "actions.assignment_mode": "deterministic_dpd",
        "actions.deterministic_dpd_threshold": 60,
        "actions.deterministic_channel": "phone",
    })
    result = generate(cfg, tmp_path)
    panel = result.tables["monthly_panel"]
    actions = result.tables["actions"].set_index("action_id")
    joined = panel.join(actions, on="action_id", rsuffix="_a")

    # dpd in the panel row is post-update for recovered rows; recompute the
    # entering dpd from the action decision by using the truth table instead.
    df = true_cate_table(result.db_path, cfg)
    treated = df["channel"] != "none"
    thr = 60
    assert (df.loc[treated, "days_past_due"] >= thr).all()
    assert (df.loc[~treated, "days_past_due"] < thr).all()
    assert (df.loc[treated, "channel"] == "phone").all()
    # deterministic ⇒ no exploration anywhere
    assert not df["is_exploration"].any()
    assert not joined.empty


def test_invalid_assignment_mode_rejected(tmp_path):
    cfg = _cfg(**{"actions.assignment_mode": "banana"})
    with pytest.raises(ValueError, match="assignment_mode"):
        generate(cfg, tmp_path)


def test_load_config_accepts_assignment_mode(tmp_path):
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(
        "seed: 1\n"
        "population: {borrowers: 5, loans_per_borrower: [1, 1]}\n"
        "panel: {months: 2}\n"
        "actions:\n"
        "  assignment_mode: deterministic_dpd\n"
        "  deterministic_dpd_threshold: 90\n"
    )
    cfg = load_config(yaml_path)
    assert cfg["actions"]["assignment_mode"] == "deterministic_dpd"
