"""Revision-campaign driver logic: reference summaries and selection grading."""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "tmlr_campaign", REPO / "scripts" / "tmlr_campaign.py")
tc = importlib.util.module_from_spec(_spec)
sys.modules["tmlr_campaign"] = tc
_spec.loader.exec_module(tc)


def _write_refs(tmp_path, means_per_rep, covs, n=1000):
    # an absolute out_dir replaces the repository root in run_dir()
    proto = {"out_dir": str(tmp_path),
             "reference_replicates": list(range(2, 2 + len(means_per_rep)))}
    run = tmp_path / "C" / "seed1"
    run.mkdir(parents=True, exist_ok=True)
    names = ["pi_b", "pi_near", "pi_far"]
    for r, (m, c) in zip(proto["reference_replicates"], zip(means_per_rep, covs, strict=True),
                         strict=True):
        (run / f"reference_r{r}.json").write_text(json.dumps(
            {"candidates": names, "n_cohort": n, "means": dict(zip(names, m, strict=True)),
             "cov": c}))
    return proto


def test_reference_summary_paired_se_and_signs(tmp_path):
    cov = [[100.0, 90.0, 80.0], [90.0, 100.0, 85.0], [80.0, 85.0, 100.0]]
    proto = _write_refs(tmp_path, [[300, 310, 280], [302, 311, 283]], [cov, cov], n=1000)
    ref = tc.reference_summary(proto, "C", 1)
    assert ref["mean"]["pi_near"] == pytest.approx(310.5)
    # SE of the mean of 2 replicates: sqrt(sum_r var/n) / R
    assert ref["se_within"]["pi_b"] == pytest.approx(math.sqrt(2 * 100 / 1000) / 2)
    g = ref["gaps"]["pi_b-pi_near"]
    assert g["mean"] == pytest.approx(-9.5)
    assert g["se_within"] == pytest.approx(math.sqrt(2 * (100 + 100 - 180) / 1000) / 2)
    assert g["corr_within"] == pytest.approx(0.9)
    assert tc._gap(ref, "pi_near", "pi_b") == (pytest.approx(9.5), pytest.approx(g["se_within"]))
    assert tc._gap(ref, "pi_far", "pi_far") == (0.0, 0.0)


def test_selection_resolved_correct_and_ambiguous(tmp_path):
    cov = np.eye(3) * 400.0
    cov = cov.tolist()
    proto = _write_refs(tmp_path, [[300, 320, 280]] * 4, [cov] * 4, n=1000)
    ref = tc.reference_summary(proto, "C", 1)
    cands = ["pi_b", "pi_near", "pi_far"]
    s = tc.selection({"pi_b": 299.0, "pi_near": 290.0, "pi_far": 200.0}, ref, cands, z=1.96)
    assert s["ref_best"] == "pi_near" and s["picked"] == "pi_b" and not s["correct"]
    assert s["top_resolved"] and s["regret"] == pytest.approx(20.0)
    assert s["gain_vs_incumbent"] == 0.0
    assert s["pairwise"]["pi_b-pi_near"] == {"ref_sign": -1, "resolved": True, "est_sign": 1}
    # a gap far below its paired SE is ambiguous
    proto2 = _write_refs(tmp_path / "amb", [[300, 300.1, 280]] * 4, [cov] * 4, n=1000)
    ref2 = tc.reference_summary(proto2, "C", 1)
    s2 = tc.selection({"pi_b": 1.0, "pi_near": 2.0, "pi_far": 0.0}, ref2, cands, z=1.96)
    assert not s2["top_resolved"] and s2["correct"]


def test_bin_uniform_target_doses_stay_in_the_bin():
    pol = tc.CANDIDATES["pi_near_binU"].generator_policy()
    doses = [pol(month=0, state="delinquent", days_in_credito_em_liquidacao=0,
                 outstanding_balance=b / 100)[1] for b in range(100_000, 140_000, 7)]
    assert min(doses) >= 0.10 and max(doses) < 0.15
    assert abs(np.mean(doses) - 0.125) < 0.001  # equidistributed over the bin
    assert pol(month=1, state="delinquent", days_in_credito_em_liquidacao=0,
               outstanding_balance=1000.0) is None


def _proto(**kw):
    base = {"name": "t", "out_dir": "x", "seeds": [1, 2], "reference_replicates": [2, 3],
            "annotator_replicate": 1, "candidates": ["pi_b", "pi_near", "pi_far"],
            "extra_reference_candidates": [], "nontabular": True,
            "gbm": {"n_folds": 2}}
    base.update(kw)
    return base


@pytest.mark.parametrize("bad", [
    {"reference_replicates": [2, 2]},          # duplicates are not independent
    {"reference_replicates": [1, 2]},          # 1 is the annotator source
    {"reference_replicates": [0, 2]},          # 0 is the logs
    {"reference_replicates": [2]},             # no between-replicate check possible
    {"reference_replicates": "TO_BE_SET_FROM_PILOT"},
    {"gbm": "TO_BE_SET_BY_RULE"},
    {"gbm": {"n_folds": 3}},                   # folds must match the tabular DR
    {"candidates": ["pi_near", "pi_far"]},     # incumbent missing
    {"candidates": ["pi_b", "pi_near_binU"]},  # diagnostic-only candidate
    {"seeds": [1, 1]},
])
def test_protocol_validation_rejects(bad):
    with pytest.raises(ValueError):
        tc.validate_protocol(_proto(**bad))


def test_protocol_validation_accepts_the_campaign_shape():
    tc.validate_protocol(_proto(candidates=["pi_b", "pi_near", "pi_far", "pi_stage"],
                                reference_replicates=[2, 3, 4]))


def test_run_provenance_must_agree(tmp_path):
    proto = _proto(out_dir=str(tmp_path))
    run = tmp_path / "C" / "seed1"
    run.mkdir(parents=True)
    meta = {"code": {"tree_sha256": "a"}, "generator_version": "2.0.0",
            "rng_scheme": "keyed-streams-v2", "config_effective_sha256": "c",
            "meta": {"batch_size": 50000}}
    for name in ("logs_meta.json", "annotator_meta.json", "reference_r2.json",
                 "reference_r3.json"):
        (run / name).write_text(json.dumps(meta))
    assert tc.check_run_provenance(proto, "C", 1)["files_checked"] == 4
    (run / "reference_r3.json").write_text(json.dumps({**meta, "code": {"tree_sha256": "b"}}))
    with pytest.raises(RuntimeError):
        tc.check_run_provenance(proto, "C", 1)
