"""Smoke test for the oracle-less report + the ε-floor exploration plumbing."""

from __future__ import annotations

import duckdb

from collection_simulator import generate, load_config
from collection_simulator.oracleless_report import evaluate_oracleless


def test_oracleless_report_and_epsilon_floor(tmp_path):
    cfg = load_config("configs/tiny_ci.yaml")
    # force heavy exploration so the tiny dataset has explored rows to report on
    cfg["actions"]["exploration"] = {
        "epsilon": 0.5,
        "explore_states": ["delinquent", "credito_em_liquidacao"],
        "explore_max_liquidacao_days": 180,
    }
    out = tmp_path / "run"
    generate(cfg, out)
    db = out / "sim.duckdb"

    # the exploration columns must be present in the actions table
    con = duckdb.connect(str(db), read_only=True)
    try:
        n_explore = con.execute("SELECT count(*) FROM actions WHERE is_exploration").fetchone()[0]
        cols = {r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='actions'"
        ).fetchall()}
    finally:
        con.close()
    assert {"is_exploration", "exploration_epsilon"} <= cols
    assert n_explore > 0, "ε=0.5 should have produced exploration rows"

    report = tmp_path / "oracleless.md"
    m = evaluate_oracleless(db, "configs/tiny_ci.yaml", out_path=report, make_figures=False)
    assert report.exists()
    text = report.read_text()
    assert "Oracle-less data report" in text
    assert "Assignment dependence" in text
    assert "Exploration coverage" in text
    assert m["exploration"]["enabled"]
    assert m["exploration"]["n_explored"] > 0
    assert 0.0 <= m["assignment_dependence"] <= 1.0


def test_no_exploration_by_default(tmp_path):
    """Without an exploration config, no rows explore and ε is 0 everywhere."""
    out = tmp_path / "run"
    generate(load_config("configs/tiny_ci.yaml"), out)
    con = duckdb.connect(str(out / "sim.duckdb"), read_only=True)
    try:
        n_explore = con.execute("SELECT count(*) FROM actions WHERE is_exploration").fetchone()[0]
        max_eps = con.execute("SELECT max(exploration_epsilon) FROM actions").fetchone()[0]
    finally:
        con.close()
    assert n_explore == 0
    assert max_eps == 0.0
