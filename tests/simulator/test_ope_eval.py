"""Smoke test for the OPE-vs-oracle evaluation.

Generates a tiny simulated dataset, fabricates a policy CSV in the producer's output
schema (recommended action = the logged action, with a varying p_payment), and checks
that ``evaluate_ope`` reconstructs the oracle without drift and emits a report.
"""

from __future__ import annotations

import duckdb
import pandas as pd

from collection_simulator import generate, load_config
from collection_simulator.ope_eval import evaluate_ope


def _fake_policy_csv(db_path, csv_path):
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute(
        """SELECT a.loan_id, a.month, a.channel, a.discount_offer,
                  p.recovered AS recovered_observed, a.channel AS channel_observed
           FROM actions a JOIN monthly_panel p USING (loan_id, month)"""
    ).df()
    con.close()
    # vary p_payment so the decile binning has something to bite on
    df["p_payment"] = 0.05 + 0.01 * (df["month"] % 5)
    df["expected_return"] = df["p_payment"] * 100.0
    df = df[[
        "loan_id", "month", "channel", "discount_offer",
        "p_payment", "expected_return", "recovered_observed", "channel_observed",
    ]]
    df.to_csv(csv_path, index=False)


def test_evaluate_ope_smoke(tmp_path):
    out = tmp_path / "run"
    cfg_path = "configs/tiny_ci.yaml"
    generate(load_config(cfg_path), out)
    db = out / "sim.duckdb"

    policy = tmp_path / "policy.csv"
    _fake_policy_csv(db, policy)

    report = tmp_path / "report.md"
    metrics = evaluate_ope(db, policy, cfg_path, out_path=report, make_figures=False)

    assert report.exists()
    text = report.read_text()
    for section in ("Policy value", "Calibration", "Discount leverage", "Blindspot"):
        assert section in text, f"missing report section: {section}"

    # no dag_*.md beside this policy → §5 grading is omitted, not reused
    assert "No causal DAG was supplied" in text
    assert metrics["dag_grading"] is None

    # with a DAG beside the policy, §5 renders the grading table
    (policy.parent / "dag_yaml.md").write_text("# dag\n", encoding="utf-8")
    report2 = tmp_path / "report_with_dag.md"
    m2 = evaluate_ope(db, policy, cfg_path, out_path=report2, make_figures=False)
    assert m2["dag_grading"] is not None
    assert "generative truth" in report2.read_text()

    pv = metrics["policy_value"]
    # the recommended action == the logged action here, so their oracle values match
    assert abs(pv["pi_e_policy"]["recovery_rate"] - pv["pi_b_logged"]["recovery_rate"]) < 1e-9
    # the ceiling cannot be below the logged policy
    assert pv["pi_star_ceiling"]["recovery_rate"] >= pv["pi_b_logged"]["recovery_rate"] - 1e-9
    # the oracle self-check inside _Oracle passed (no drift) if we got here
    assert metrics["n_rows"] > 0
