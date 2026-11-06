from pathlib import Path

import duckdb

from collection_simulator.cli import main


def test_cli_smoke_generate_validate_export(tmp_path, capsys):
    out = tmp_path / "run"
    assert main(["generate", "--config", "configs/tiny_ci.yaml", "--out", str(out)]) == 0
    assert (out / "sim.duckdb").exists()

    assert main(["validate", "--db", str(out / "sim.duckdb")]) == 0
    assert main(["export", "--db", str(out / "sim.duckdb"), "--mode", "split"]) == 0
    assert main(["export", "--db", str(out / "sim.duckdb"), "--mode", "flat"]) == 0

    captured = capsys.readouterr()
    assert "sim.duckdb" in captured.out
    assert Path(out / "csv" / "flat.csv").exists()
    # the data dictionary ships with every export, regardless of mode
    assert Path(out / "csv" / "DATA_DICTIONARY.md").exists()


def test_cli_export_both_into_structured_scenario_layout(tmp_path):
    out = tmp_path / "run"
    assert main(
        ["generate", "--config", "configs/tiny_ci.yaml", "--out", str(out), "--seed", "7"]
    ) == 0
    dest = tmp_path / "exports"
    assert main([
        "export", "--db", str(out / "sim.duckdb"),
        "--mode", "both", "--scenario", "demo", "--out", str(dest),
    ]) == 0
    # structured layout: collection-simulator/samples/<scenario>/<date>/seed7-<HHMMSS>/
    runs = list((dest / "collection-simulator" / "samples" / "demo").glob("*/seed7-*"))
    assert len(runs) == 1, runs
    run = runs[0]
    assert (run / "flat.csv").exists()
    assert (run / "DATA_DICTIONARY.md").exists()
    for table in ("borrowers", "loans", "actions", "monthly_panel"):
        assert (run / f"{table}.csv").exists()


def test_cli_seed_override_is_written_to_oracle_truth(tmp_path):
    out = tmp_path / "seeded"
    assert (
        main(
            [
                "generate",
                "--config",
                "configs/tiny_ci.yaml",
                "--out",
                str(out),
                "--seed",
                "987",
            ]
        )
        == 0
    )

    con = duckdb.connect(str(out / "sim.duckdb"), read_only=True)
    try:
        seeds = con.execute("SELECT DISTINCT seed FROM oracle_truth").fetchall()
    finally:
        con.close()
    assert seeds == [(987,)]
