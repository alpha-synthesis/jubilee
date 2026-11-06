"""Validation checks for generated simulator databases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from collection_simulator.dictionaries import ALLOWED_STATES, PUBLIC_TABLES


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    counts: dict[str, int]
    errors: list[str]


REQUIRED_TABLES = [*PUBLIC_TABLES, "oracle_truth"]
HIDDEN_COLUMNS = {
    "borrower_resilience",
    "payment_friction",
    "regional_macro_stress",
    "contactability",
    "p_recovery",
    "p_chargeoff",
    "recovery_draw",
    "chargeoff_draw",
}


def validate_database(db_path: str | Path) -> ValidationReport:
    con = duckdb.connect(str(db_path), read_only=True)
    errors: list[str] = []
    counts: dict[str, int] = {}
    try:
        existing = {
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        for table in REQUIRED_TABLES:
            if table not in existing:
                errors.append(f"missing table: {table}")
                continue
            counts[table] = int(con.execute(f"SELECT count(*) FROM {table}").fetchone()[0])
            if counts[table] == 0:
                errors.append(f"empty table: {table}")

        for table in PUBLIC_TABLES:
            if table not in existing:
                continue
            cols = {
                row[1]
                for row in con.execute(f"PRAGMA table_info('{table}')").fetchall()
            }
            leaked = sorted(cols & HIDDEN_COLUMNS)
            if leaked:
                errors.append(f"{table} leaks hidden columns: {leaked}")

        if "monthly_panel" in existing:
            states = {
                row[0]
                for row in con.execute(
                    """
                    SELECT status FROM monthly_panel
                    UNION
                    SELECT next_status FROM monthly_panel
                    """
                ).fetchall()
            }
            bad = sorted(states - ALLOWED_STATES)
            if bad:
                errors.append(f"invalid panel states: {bad}")
            # a loan generates no row after its terminal transition
            after_end = con.execute(
                """
                SELECT count(*) FROM monthly_panel p JOIN (
                    SELECT loan_id, min(month) AS m_end FROM monthly_panel
                    WHERE next_status IN ('cured', 'charged_off') GROUP BY loan_id
                ) e USING (loan_id)
                WHERE p.month > e.m_end
                """
            ).fetchone()[0]
            if after_end:
                errors.append(f"{after_end} panel rows follow a terminal transition")

        if "monthly_panel" in existing and "actions" in existing:
            # full settlement (model >= 2.1.0): a recovery pays the whole offer,
            # writes the balance off to zero and ends the loan as ``cured``.
            # Databases of earlier models (partial payments) fail this check.
            not_full = con.execute(
                """
                SELECT count(*) FROM monthly_panel p JOIN actions a USING (action_id)
                WHERE p.recovered AND (p.next_status <> 'cured'
                    OR p.outstanding_balance <> 0
                    OR p.recovered_amount <> a.settlement_offer_amount)
                """
            ).fetchone()[0]
            if not_full:
                errors.append(f"{not_full} recovery rows are not full settlements")
    finally:
        con.close()
    return ValidationReport(ok=not errors, counts=counts, errors=errors)
