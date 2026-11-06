"""CSV export helpers (local files; optional structured sample layout)."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path

import duckdb

from collection_simulator.dictionaries import PUBLIC_TABLES

# Field-level docs shipped with every export so a downstream reader always gets the
# schema next to the data (and it rides along to S3 with --s3).
_DATA_DICTIONARY_RESOURCE = "data_dictionary.md"
_DATA_DICTIONARY_FILENAME = "DATA_DICTIONARY.md"


def _write_data_dictionary(out_dir: Path) -> Path:
    """Copy the bundled data dictionary into ``out_dir`` and return its path."""
    text = (
        resources.files("collection_simulator")
        .joinpath(_DATA_DICTIONARY_RESOURCE)
        .read_text(encoding="utf-8")
    )
    path = out_dir / _DATA_DICTIONARY_FILENAME
    path.write_text(text, encoding="utf-8")
    return path


# Flat = one loan-month row joined with its action, loan and borrower context.
_FLAT_SQL = """
    SELECT
        p.*,
        a.channel,
        a.discount_offer,
        a.settlement_offer_amount,
        a.is_exploration,
        a.exploration_epsilon,
        l.product_type,
        l.original_principal,
        l.interest_rate_monthly,
        b.uf,
        b.city,
        b.lat,
        b.lon,
        b.age,
        b.gender,
        b.income_band,
        b.monthly_income,
        b.dependents
    FROM monthly_panel p
    LEFT JOIN actions a ON a.action_id = p.action_id
    LEFT JOIN loans l ON l.loan_id = p.loan_id
    LEFT JOIN borrowers b ON b.borrower_id = p.borrower_id
    ORDER BY p.loan_id, p.month
"""


def export_csv(
    db_path: str | Path,
    out_dir: str | Path | None = None,
    mode: str = "split",
) -> list[Path]:
    """Export public simulator tables to CSV.

    ``mode``:
      * ``split`` — one CSV per public table (``borrowers.csv``, …),
      * ``flat``  — a single joined ``flat.csv``,
      * ``both``  — split *and* flat, in the same ``out_dir``.

    Every export — regardless of mode — also writes ``DATA_DICTIONARY.md`` describing
    the fields, so the schema always travels with the data.
    """
    db_path = Path(db_path)
    out_dir = Path(out_dir) if out_dir is not None else db_path.parent / "csv"
    modes = ("split", "flat") if mode == "both" else (mode,)
    if any(m not in ("split", "flat") for m in modes):
        raise ValueError("mode must be 'split', 'flat', or 'both'")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = [_write_data_dictionary(out_dir)]
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        if "split" in modes:
            for table in PUBLIC_TABLES:
                path = out_dir / f"{table}.csv"
                con.execute(f"COPY {table} TO ? (HEADER, DELIMITER ',')", [str(path)])
                paths.append(path)
        if "flat" in modes:
            path = out_dir / "flat.csv"
            con.execute(f"COPY ({_FLAT_SQL}) TO ? (HEADER, DELIMITER ',')", [str(path)])
            paths.append(path)
    finally:
        con.close()
    return paths


def read_seed(db_path: str | Path) -> int | None:
    """The resolved seed recorded in ``oracle_truth`` (used to name the export)."""
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        row = con.execute("SELECT DISTINCT seed FROM oracle_truth LIMIT 1").fetchone()
        return int(row[0]) if row else None
    finally:
        con.close()


def sample_subpath(scenario: str, seed: int | None, when) -> str:
    """Relative key/dir for one export run — used identically for the local dir and
    the S3 key. The ``HHMMSS`` component lets you produce more than one per day::

        collection-simulator/samples/<scenario>/<YYYY-MM-DD>/seed<seed>-<HHMMSS>
    """
    return (
        f"collection-simulator/samples/{scenario}/"
        f"{when:%Y-%m-%d}/seed{seed}-{when:%H%M%S}"
    )
