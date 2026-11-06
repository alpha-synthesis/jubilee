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
from collection_simulator.generator import (
    GENERATOR_VERSION,
    RNG_SCHEME,
    RecoveryInputs,
    generate,
    recovery_probability,
    simulate_cohort,
)

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


def test_trajectories_diverge_once_actions_differ(tmp_path):
    """The twin is a coupled realisation, not a replay: an action change moves the
    recovery probability of that loan-month."""
    base = _cfg()
    logged = _world(tmp_path, "logged", base)
    twin = _world(tmp_path, "twin", base, policy=_always)
    keys = ["loan_id", "month"]
    a = logged["actions"].merge(twin["actions"], on=keys, suffixes=("_l", "_t"))
    t = logged["oracle_truth"].merge(twin["oracle_truth"], on=keys, suffixes=("_l", "_t"))
    m = a.merge(t, on=keys)
    differ = m["channel_l"] != m["channel_t"]
    assert differ.any()
    assert (m.loc[differ, "p_recovery_l"] != m.loc[differ, "p_recovery_t"]).all()


def test_repeatable(tmp_path):
    cfg = _cfg()
    a = _world(tmp_path, "a", cfg, policy=_one_shot)
    b = _world(tmp_path, "b", copy.deepcopy(cfg), policy=_one_shot)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name], obj=name)


def test_replicates_share_regional_shocks_only(tmp_path):
    cfg = _cfg()
    r0 = _tables(generate(cfg, tmp_path / "r0", batch_size=BATCH, replicate=0))
    r1 = _tables(generate(cfg, tmp_path / "r1", batch_size=BATCH, replicate=1))
    shock = lambda t: (t["oracle_truth"].merge(  # noqa: E731
        t["borrowers"][["borrower_id", "uf"]], on="borrower_id")
        .groupby("uf")["regional_macro_stress"].agg(["min", "max"]))
    s0, s1 = shock(r0), shock(r1)
    assert (s0["min"] == s0["max"]).all()  # one shock per region
    common = s0.index.intersection(s1.index)
    assert len(common) >= 5
    np.testing.assert_array_equal(s0.loc[common, "min"], s1.loc[common, "min"])
    # ...but the populations are independent draws
    assert (r0["borrowers"]["age"].to_numpy() != r1["borrowers"]["age"].to_numpy()).mean() > 0.5
    assert not np.array_equal(r0["loans"]["outstanding_balance"],
                              r1["loans"]["outstanding_balance"])


def test_replicate_populations_are_uncorrelated():
    """No stream is accidentally shared between replicates: hidden factors and
    balances of replicates 0 and 1 are uncorrelated position by position."""
    from collection_simulator.generator import _generate_population, regional_shocks

    cfg = _cfg()
    cfg["population"]["borrowers"] = 3000
    reg = regional_shocks(cfg)
    pops = [_generate_population(cfg, r, 0, 3000, 0, 1, reg) for r in (0, 1)]
    for col in ("borrower_resilience", "payment_friction", "contactability"):
        a, b = (p[1][col].to_numpy() for p in pops)
        assert abs(np.corrcoef(a, b)[0, 1]) < 0.1, col  # sampling SD about 0.018
    a, b = (p[2]["outstanding_balance"].to_numpy() for p in pops)
    assert abs(np.corrcoef(a, b)[0, 1]) < 0.1


def test_batch_size_is_part_of_the_reproduction_configuration(tmp_path):
    """Same batch size -> same population; another batch size -> another
    population (no batch-size invariance is promised); ``None`` equals one
    batch covering the whole population."""
    cfg = _cfg()
    b7 = generate(cfg, tmp_path / "b7", batch_size=7)
    b13 = generate(cfg, tmp_path / "b13", batch_size=13)
    one = generate(cfg, tmp_path / "one", batch_size=None)
    big = generate(cfg, tmp_path / "big", batch_size=1000)
    t7, t13, t1, tb = _tables(b7), _tables(b13), _tables(one), _tables(big)
    assert not t7["borrowers"].equals(t13["borrowers"])
    for name in t1:
        pd.testing.assert_frame_equal(t1[name], tb[name], obj=name)
    assert b7.meta["batch_size"] == 7 and b7.meta["n_batches"] == 9
    assert one.meta["batch_size"] == 60 and one.meta["n_batches"] == 1
    assert b7.meta["rng_scheme"] == RNG_SCHEME
    assert b7.meta["generator_version"] == GENERATOR_VERSION


def test_rows_obey_the_recovery_model(tmp_path):
    """Per-row invariants of the assembled tables: with the outcome noise switched
    off, every stored probability recomputes exactly from the decision-time
    state; events follow the stored draws; action ids are contiguous."""
    cfg = _cfg()
    cfg["oracle"]["noise_std"] = 0.0
    t = _world(tmp_path, "w", cfg, policy=_one_shot)
    keys = ["loan_id", "month"]
    m = (t["actions"].merge(t["monthly_panel"], on=keys)
         .merge(t["oracle_truth"].drop(columns=["borrower_id"]), on=keys)
         .merge(t["borrowers"][["borrower_id", "age"]], on="borrower_id")
         .sort_values(keys).reset_index(drop=True))
    assert len(m) == len(t["actions"]) == len(t["monthly_panel"]) == len(t["oracle_truth"])
    assert (m["recovered"] == (m["recovery_draw"] < m["p_recovery"])).all()
    assert (m["charged_off"] == (~m["recovered"] & (m["chargeoff_draw"] < m["p_chargeoff"]))).all()
    ids = sorted(int(a[1:]) for a in t["actions"]["action_id"])
    assert ids == list(range(1, len(ids) + 1))
    # decision-time DPD / liquidation days: the loan's initial values at month 0,
    # the previous row's post-transition values afterwards
    loans = t["loans"].set_index("loan_id")
    prev = m.groupby("loan_id")[["days_past_due", "days_in_credito_em_liquidacao"]].shift(1)
    dpd = prev["days_past_due"].fillna(m["loan_id"].map(loans["days_past_due"]))
    liq = prev["days_in_credito_em_liquidacao"].fillna(
        m["loan_id"].map(loans["days_in_credito_em_liquidacao"]))
    for row, d, q in zip(m.itertuples(), dpd, liq, strict=True):
        p = recovery_probability(RecoveryInputs(
            channel=row.channel, discount_offer=row.discount_offer, age=int(row.age),
            loan_age_months=int(row.loan_age_months), days_past_due=int(d),
            days_in_credito_em_liquidacao=int(q),
            borrower_resilience=row.borrower_resilience, payment_friction=row.payment_friction,
            regional_macro_stress=row.regional_macro_stress, contactability=row.contactability,
            noise=0.0), cfg["oracle"])
        assert p == row.p_recovery


def test_cohort_path_matches_database_path(tmp_path):
    """``simulate_cohort`` steps the same draws as ``generate``: month-0 actions and
    9-month recoveries of the explorable cohort are identical, for the logged
    world and for a policy-injected world, with all loans or the cohort only."""
    cfg = _cfg()
    for name, pol in (("logged", None), ("one_shot", _one_shot)):
        t = _world(tmp_path, name, cfg, policy=pol)
        a0 = t["actions"][t["actions"]["month"] == 0].set_index("loan_id")
        paid = (t["monthly_panel"][t["monthly_panel"]["month"] < 9]
                .groupby("loan_id")["recovered"].max())
        loans = t["loans"].set_index("loan_id")
        explorable = loans["initial_status"].isin(["delinquent", "credito_em_liquidacao"]) & ~(
            (loans["initial_status"] == "credito_em_liquidacao")
            & (loans["days_in_credito_em_liquidacao"] > 180))
        expected = pd.DataFrame({
            "channel_logged": a0["channel"], "discount_logged": a0["discount_offer"],
            "is_exploration": a0["is_exploration"], "paid_within_h": paid.astype(np.int64),
        }).loc[explorable[explorable].index].sort_index()
        for all_loans in (False, True):
            coh, meta = simulate_cohort(cfg, policy=pol, batch_size=BATCH, horizon=9,
                                        simulate_all_loans=all_loans)
            got = coh.set_index("loan_id")[expected.columns].sort_index()
            pd.testing.assert_frame_equal(got, expected, check_dtype=False, obj=name)
            assert meta["n_cohort"] == len(expected)


def test_recovery_12m_matches_database(tmp_path):
    cfg = _cfg()
    t = _world(tmp_path, "w", cfg)
    rec = (t["monthly_panel"].assign(r=lambda d: d["recovered"] & (d["month"] < 12))
           .groupby("loan_id")["r"].max().mean())
    _, meta = simulate_cohort(cfg, batch_size=BATCH, horizon=9, simulate_all_loans=True,
                              months=12)
    assert meta["recovery_12m"] == pytest.approx(float(rec), abs=1e-12)


def test_channel_effect_tables_default_and_validation():
    from collection_simulator.generator import (
        CHANNEL_EFFECT,
        _validate_channel_effects,
        channel_effect,
        uses_default_channel_effects,
    )

    oracle = load_config("configs/tiny_ci.yaml")["oracle"]
    assert uses_default_channel_effects(oracle)
    for ch, v in CHANNEL_EFFECT.items():
        assert channel_effect(oracle, ch, 10) == v and channel_effect(oracle, ch, 200) == v
    staged = dict(oracle, channel_effects_late={**CHANNEL_EFFECT, "sms": -0.5})
    assert not uses_default_channel_effects(staged)
    assert channel_effect(staged, "sms", 89) == CHANNEL_EFFECT["sms"]
    assert channel_effect(staged, "sms", 90) == -0.5
    with pytest.raises(ValueError):
        _validate_channel_effects({"oracle": dict(oracle, channel_effects={"sms": 0.1})})
