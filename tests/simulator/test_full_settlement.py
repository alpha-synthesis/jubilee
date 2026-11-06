"""Full settlement (model 2.1.0): a recovery pays the whole offer and closes the loan.

The settlement rule changes what happens at a loan's first recovery and after
it; it must not change anything before it. The first group of tests pins the
rule on the per-(loan, month) arrays and on the database; the second pins what
the evaluation score depends on, against the 2.0.0 source snapshot and between
the database and ``simulate_cohort`` routes. The full per-loan equivalence
check over worlds, seeds, roles and candidates is
``scripts/settlement_equivalence.py`` (separate processes per model).
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from collection_simulator import generator as gen
from collection_simulator.config import load_config
from collection_simulator.legacy import generator_2_0_0 as legacy
from collection_simulator.validation import validate_database
from ope_bench.panel import PI_FAR, load_cohort

BATCH = 150  # 400 borrowers -> 3 batches (the last one partial)
CURED = gen._STATE_IDX["cured"]


def _cfg(recovery: float = 0.25) -> dict:
    cfg = load_config("configs/tiny_ci.yaml")
    cfg["population"]["borrowers"] = 400
    cfg["panel"]["months"] = 12
    cfg["oracle"]["target_monthly_recovery_rate"] = recovery
    cfg["actions"]["exploration"] = {
        "epsilon": 0.2, "explore_states": ["delinquent", "credito_em_liquidacao"],
        "explore_max_liquidacao_days": 180}
    return cfg


def _half_free(*, outstanding_balance, **_):
    """Every loan-month: field visit, discount 0 on half the loans (even cents of
    the balance) and 0.3 on the rest, so settlements with and without discount."""
    d = 0.0 if round(outstanding_balance * 100) % 2 == 0 else 0.3
    return "field_visit", d


def _batches(cfg, simulate, policy=None):
    regional = gen.regional_shocks(cfg)
    loan_next = 1
    for b, start, n in gen._batches(int(cfg["population"]["borrowers"]), BATCH):
        borrowers, hidden, loans = gen._generate_population(cfg, 0, b, n, start, loan_next,
                                                            regional)
        loan_next += len(loans)
        yield loans, simulate(cfg, borrowers, hidden, loans, 0, b, policy)


# ── the rule ───────────────────────────────────────────────────────────────
def test_settlement_is_paid_in_full_and_closes_the_loan():
    cfg = _cfg()
    n_rec = n_free = 0
    for loans, rec in _batches(cfg, gen._simulate_batch, _half_free):
        # Python floats, as in the generator (numpy's round differs at half-cents)
        b0 = loans["outstanding_balance"].to_numpy(np.float64).tolist()
        rate = loans["interest_rate_monthly"].to_numpy(np.float64).tolist()
        for i in range(len(loans)):
            hits = np.flatnonzero(rec["recovered"][i] & rec["alive"][i])
            assert len(hits) <= 1, "a loan pays at most once"
            # the balance on which each month's offer is computed (no payment before)
            bal = b0[i]
            for m in range(rec["alive"].shape[1]):
                if not rec["alive"][i, m]:
                    assert not rec["alive"][i, m:].any(), "rows stop once the loan ends"
                    break
                d = float(rec["discount"][i, m])
                s = float(rec["settlement"][i, m])
                assert s == round(bal * (1.0 - d), 2)
                assert rec["balance_before"][i, m] == round(bal, 2)
                if rec["recovered"][i, m]:
                    n_rec += 1
                    w = float(rec["written_off"][i, m])
                    assert rec["recovered_amount"][i, m] == s, "the whole offer is paid"
                    cents = round(float(rec["balance_before"][i, m]) * 100)
                    assert cents == round(s * 100) + round(w * 100), "balance = paid + written off"
                    assert w >= 0.0
                    if d == 0.0:
                        n_free += 1
                        assert w == 0.0 and s == rec["balance_before"][i, m]
                    else:
                        assert w > 0.0
                    assert rec["balance_after"][i, m] == 0.0
                    assert rec["next_status"][i, m] == CURED
                    assert rec["dpd_after"][i, m] == 0
                    assert not rec["alive"][i, m + 1:].any(), "no row after the settlement"
                    assert rec["first_recovery_month"][i] == m
                    break
                assert rec["recovered_amount"][i, m] == 0.0 and rec["written_off"][i, m] == 0.0
                if rec["charged_off"][i, m]:
                    break
                bal = bal * (1.0 + rate[i] * 0.35)
    assert n_rec > 100 and 20 < n_free < n_rec, (n_rec, n_free)


def test_database_records_full_settlements_and_validator_enforces_them(tmp_path):
    cfg = _cfg()
    res = gen.generate(cfg, tmp_path / "w", batch_size=BATCH, policy=_half_free)
    assert validate_database(res.db_path).ok
    con = duckdb.connect(str(res.db_path), read_only=True)
    try:
        m = con.execute("""
            SELECT p.loan_id, p.month, p.recovered, p.recovered_amount, p.next_status,
                   p.outstanding_balance AS bal_after, a.settlement_offer_amount AS s,
                   a.discount_offer AS d,
                   COALESCE(lag(p.outstanding_balance) OVER (PARTITION BY p.loan_id
                            ORDER BY p.month), l.outstanding_balance) AS bal_before
            FROM monthly_panel p JOIN actions a ON a.action_id = p.action_id
            JOIN loans l ON l.loan_id = p.loan_id ORDER BY p.loan_id, p.month""").df()
    finally:
        con.close()
    r = m[m["recovered"]]
    assert len(r) > 100 and r["loan_id"].is_unique
    assert (r["recovered_amount"] == r["s"]).all()
    assert (r["bal_after"] == 0).all() and (r["next_status"] == "cured").all()
    written = (r["bal_before"] * 100).round() - (r["s"] * 100).round()
    assert (written >= 0).all() and (written[r["d"] == 0] == 0).all()
    assert (written[r["d"] > 0] > 0).all()
    last = m.groupby("loan_id")["month"].max()
    assert (r.set_index("loan_id")["month"] == last.loc[r["loan_id"]]).all()
    # the validator rejects a recovery that leaves a balance (a 2.0.0-style row)
    bad = tmp_path / "bad.duckdb"
    bad.write_bytes(res.db_path.read_bytes())
    con = duckdb.connect(str(bad))
    try:
        con.execute("""UPDATE monthly_panel SET outstanding_balance = 10.0,
                       next_status = 'performing'
                       WHERE action_id = (SELECT min(action_id) FROM monthly_panel
                                          WHERE recovered)""")
    finally:
        con.close()
    report = validate_database(bad)
    assert not report.ok and any("full settlements" in e for e in report.errors)


def test_validator_flags_each_violation_separately(tmp_path):
    """One edit per condition: amount below the offer, a balance left, a non-terminal
    next state, a row after the terminal transition."""
    res = gen.generate(_cfg(), tmp_path / "w", batch_size=BATCH)
    target = "(SELECT min(action_id) FROM monthly_panel WHERE recovered)"
    edits = {
        "amount": (f"UPDATE monthly_panel SET recovered_amount = recovered_amount - 1 "
                   f"WHERE action_id = {target}", "full settlements"),
        "balance": (f"UPDATE monthly_panel SET outstanding_balance = 1.0 "
                    f"WHERE action_id = {target}", "full settlements"),
        "state": (f"UPDATE monthly_panel SET next_status = 'performing' "
                  f"WHERE action_id = {target}", "full settlements"),
        "row_after_end": (f"INSERT INTO monthly_panel SELECT * REPLACE (month + 1 AS month) "
                          f"FROM monthly_panel WHERE action_id = {target}",
                          "follow a terminal transition"),
    }
    for name, (sql, message) in edits.items():
        db = tmp_path / f"{name}.duckdb"
        db.write_bytes(res.db_path.read_bytes())
        con = duckdb.connect(str(db))
        try:
            con.execute(sql)
        finally:
            con.close()
        report = validate_database(db)
        assert not report.ok and any(message in e for e in report.errors), (name, report.errors)
        assert len(report.errors) == 1, (name, report.errors)


def test_score_extraction_is_identical_under_both_models():
    """``simulate_cohort`` of the 2.0.0 snapshot and of 2.1.0: every score column
    equal, in the same row order (logs-style with covariates, and a
    policy-injected cohort); 2.1.0 adds only the ``cash_within_h`` column (the
    cash is what the settlement rule changes); the meta differs only in the
    version keys and the cash definition."""
    cfg = _cfg(recovery=0.08)
    for kw in ({"policy": None, "months": 12, "simulate_all_loans": True,
                "with_covariates": True},
               {"policy": PI_FAR.generator_policy()}):
        new, meta_new = gen.simulate_cohort(cfg, batch_size=BATCH, horizon=9, **kw)
        old, meta_old = legacy.simulate_cohort(cfg, batch_size=BATCH, horizon=9, **kw)
        assert set(new.columns) - set(old.columns) == {"cash_within_h"}
        pd.testing.assert_frame_equal(new[old.columns], old, check_exact=True)
        assert new["paid_within_h"].sum() > 10
        drop = ("generator_version", "settlement_rule", "reward_definition", "cash_definition")
        assert ({k: v for k, v in meta_new.items() if k not in drop}
                == {k: v for k, v in meta_old.items() if k not in drop})


def test_versions_and_metadata():
    assert gen.GENERATOR_VERSION == "2.1.0" and legacy.GENERATOR_VERSION == "2.0.0"
    assert gen.RNG_SCHEME == legacy.RNG_SCHEME == "keyed-streams-v2"
    _, meta = gen.simulate_cohort(_cfg(), batch_size=BATCH, horizon=9)
    assert meta["generator_version"] == "2.1.0" and meta["rng_scheme"] == "keyed-streams-v2"
    assert meta["settlement_rule"] == "full-settlement"
    assert meta["reward_definition"] == gen.SCORE_DEFINITION


# ── what the score depends on ───────────────────────────────────────────────
def test_draws_are_unchanged_by_the_settlement_rule():
    for key in ((5, 0, 0), (5, 2, 1)):
        new, old = gen._panel_draws(*key, 30, 12), legacy._panel_draws(*key, 30, 12)
        assert set(new) == set(old)
        for k in new:
            assert np.array_equal(new[k], old[k]), k


def test_models_agree_until_the_first_recovery():
    """2.0.0 and 2.1.0 step every loan identically up to and including its first
    recovery; afterwards only 2.0.0 can continue (and does, for some loans)."""
    cfg = _cfg()
    pre = ("status", "channel", "discount", "settlement", "is_exploration", "explore_prob",
           "loan_age", "remaining", "contacts", "recovered", "charged_off", "p_recovery",
           "p_chargeoff")
    post = ("dpd_after", "liq_after", "balance_after", "next_status")
    continued = 0
    for policy in (None, PI_FAR.generator_policy(), _half_free):
        news = list(_batches(cfg, gen._simulate_batch, policy))
        olds = list(_batches(cfg, legacy._simulate_batch, policy))
        for (loans, new), (loans_old, old) in zip(news, olds, strict=True):
            pd.testing.assert_frame_equal(loans, loans_old)
            for k in ("first_recovery_month", "channel0", "discount0", "is_exploration0",
                      "eps0"):
                assert np.array_equal(new[k], old[k], equal_nan=k == "discount0"), k
            first = new["first_recovery_month"]
            for i in range(len(loans)):
                k_new = int(new["alive"][i].sum())
                end = first[i] if first[i] >= 0 else k_new - 1  # last month that must agree
                assert np.array_equal(new["alive"][i, :end + 1], old["alive"][i, :end + 1])
                for name in pre:
                    assert np.array_equal(new[name][i, :end + 1], old[name][i, :end + 1]), name
                stop = end if first[i] >= 0 else end + 1  # post-transition values
                for name in post:
                    assert np.array_equal(new[name][i, :stop], old[name][i, :stop]), name
                if first[i] < 0:
                    assert k_new == int(old["alive"][i].sum())
                else:
                    continued += int(old["alive"][i, first[i] + 1:].any())
                    assert not new["alive"][i, first[i] + 1:].any()
    assert continued > 0  # the old rule did keep some recovered loans open


def test_score_extraction_database_equals_simulate_cohort(tmp_path):
    """Per loan, ``load_cohort`` on the database and ``simulate_cohort`` give the
    same month-0 state, action and 9-month score, logged and policy-injected."""
    cfg = _cfg(recovery=0.08)
    for name, pol in (("logged", None), ("pi_far", PI_FAR.generator_policy())):
        res = gen.generate(cfg, tmp_path / name, batch_size=BATCH, policy=pol)
        db = load_cohort(res.db_path).set_index("loan_id").sort_index()
        coh, _ = gen.simulate_cohort(cfg, policy=pol, batch_size=BATCH, horizon=9,
                                     cohort_states=None)
        coh = coh.set_index("loan_id").sort_index()
        cols = ["start_balance", "state", "dpd", "liq_days", "channel_logged",
                "discount_logged", "is_exploration", "exploration_epsilon", "paid_within_h",
                "reward"]
        assert db.index.equals(coh.index) and len(db) == 400
        pd.testing.assert_frame_equal(db[cols], coh[cols], check_dtype=False, obj=name)
        assert db["paid_within_h"].sum() > 20
