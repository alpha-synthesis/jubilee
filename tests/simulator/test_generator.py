import duckdb
import pandas as pd

from collection_simulator.config import load_config
from collection_simulator.export import export_csv
from collection_simulator.generator import (
    RecoveryInputs,
    generate,
    recovery_probability,
)
from collection_simulator.validation import HIDDEN_COLUMNS, validate_database


def test_streaming_generation_is_valid_and_deterministic(tmp_path):
    cfg = load_config("configs/tiny_ci.yaml")  # 40 borrowers

    res = generate(cfg, tmp_path / "a", batch_size=7)  # 6 uneven batches
    report = validate_database(res.db_path)
    assert report.ok, report.errors
    assert report.counts["borrowers"] == 40  # all batches written, ids continuous
    assert report.counts["monthly_panel"] > 0

    con = duckdb.connect(str(res.db_path), read_only=True)
    try:
        # ids are continuous and unique across batch boundaries
        n_loans, n_distinct = con.execute(
            "SELECT count(*), count(DISTINCT loan_id) FROM loans"
        ).fetchone()
        panel_a = con.execute("SELECT * FROM monthly_panel ORDER BY loan_id, month").df()
    finally:
        con.close()
    assert n_loans == n_distinct == 40

    # same seed + same batch_size → identical output
    res_b = generate(cfg, tmp_path / "b", batch_size=7)
    con = duckdb.connect(str(res_b.db_path), read_only=True)
    try:
        panel_b = con.execute("SELECT * FROM monthly_panel ORDER BY loan_id, month").df()
    finally:
        con.close()
    pd.testing.assert_frame_equal(panel_a, panel_b)


def test_generate_duckdb_and_validate(tmp_path):
    cfg = load_config("configs/tiny_ci.yaml")
    result = generate(cfg, tmp_path)

    assert result.db_path.exists()
    report = validate_database(result.db_path)
    assert report.ok, report.errors
    assert report.counts["borrowers"] == 40
    assert report.counts["monthly_panel"] > 0

    con = duckdb.connect(str(result.db_path), read_only=True)
    try:
        seeds = con.execute("SELECT DISTINCT seed FROM oracle_truth").fetchall()
    finally:
        con.close()
    assert seeds == [(7,)]


def test_generation_is_deterministic(tmp_path):
    cfg = load_config("configs/tiny_ci.yaml")
    a = generate(cfg, tmp_path / "a")
    b = generate(cfg, tmp_path / "b")

    con_a = duckdb.connect(str(a.db_path), read_only=True)
    con_b = duckdb.connect(str(b.db_path), read_only=True)
    try:
        first_a = con_a.execute(
            "SELECT * FROM monthly_panel ORDER BY loan_id, month LIMIT 10"
        ).fetchdf()
        first_b = con_b.execute(
            "SELECT * FROM monthly_panel ORDER BY loan_id, month LIMIT 10"
        ).fetchdf()
    finally:
        con_a.close()
        con_b.close()
    pd.testing.assert_frame_equal(first_a, first_b)


def test_export_split_and_flat_do_not_leak_hidden_columns(tmp_path):
    cfg = load_config("configs/tiny_ci.yaml")
    result = generate(cfg, tmp_path)

    split_paths = export_csv(result.db_path, tmp_path / "split", mode="split")
    flat_paths = export_csv(result.db_path, tmp_path / "flat", mode="flat")

    assert {p.name for p in split_paths if p.suffix == ".csv"} == {
        "borrowers.csv",
        "loans.csv",
        "actions.csv",
        "monthly_panel.csv",
    }
    # the field documentation ships with every export (not a data leak)
    assert "DATA_DICTIONARY.md" in {p.name for p in split_paths}
    flat_csv = next(p for p in flat_paths if p.name == "flat.csv")
    flat = pd.read_csv(flat_csv)
    public_cols = set(flat.columns)
    assert not (public_cols & HIDDEN_COLUMNS)


def test_offer_discount_monotonically_increases_recovery_probability():
    cfg = load_config("configs/tiny_ci.yaml")
    base = dict(
        channel="phone",
        age=42,
        loan_age_months=12,
        days_past_due=60,
        days_in_credito_em_liquidacao=0,
        borrower_resilience=0.0,
        payment_friction=0.0,
        regional_macro_stress=0.0,
        contactability=0.0,
    )
    low = recovery_probability(RecoveryInputs(discount_offer=0.0, **base), cfg["oracle"])
    high = recovery_probability(RecoveryInputs(discount_offer=0.45, **base), cfg["oracle"])
    assert high > low


def test_hidden_confounder_bias_is_present(tmp_path):
    cfg = load_config("configs/high_confounding.yaml")
    cfg["population"]["borrowers"] = 300
    cfg["panel"]["months"] = 6
    result = generate(cfg, tmp_path)

    con = duckdb.connect(str(result.db_path), read_only=True)
    try:
        bias = con.execute(
            """
            SELECT
                avg(CASE WHEN a.channel IN ('phone', 'field_visit')
                    THEN t.payment_friction END)
                - avg(CASE WHEN a.channel = 'none' THEN t.payment_friction END)
            FROM oracle_truth t
            JOIN actions a USING (loan_id, month)
            """
        ).fetchone()[0]
    finally:
        con.close()
    assert bias > 0.10


def test_recovered_amount_never_exceeds_settlement(tmp_path):
    """A discount is a giveaway: collection is capped at the settlement offered and is
    zero when nothing was recovered (regression for the recovered_amount mis-attribution)."""
    result = generate(load_config("configs/tiny_ci.yaml"), tmp_path)
    con = duckdb.connect(str(result.db_path), read_only=True)
    try:
        bad = con.execute(
            """SELECT count(*) FROM monthly_panel p JOIN actions a USING (loan_id, month)
               WHERE p.recovered_amount > a.settlement_offer_amount + 0.01"""
        ).fetchone()[0]
        nonzero_when_not_recovered = con.execute(
            "SELECT count(*) FROM monthly_panel WHERE NOT recovered AND recovered_amount <> 0"
        ).fetchone()[0]
    finally:
        con.close()
    assert bad == 0, f"{bad} rows collected more than the settlement offered"
    assert nonzero_when_not_recovered == 0
