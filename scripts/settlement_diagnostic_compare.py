"""Policy-reward diagnostic under simulator model 2.1.0 against its 2.0.0 records.

Reads the per-world-seed records of ``scripts/policy_reward_diagnostic.py``
run with model 2.1.0 (full settlement) and the records of the same design run
with model 2.0.0, and writes:

* ``score_identity_by_seed.csv`` — whether the synthetic score's values,
  Monte-Carlo SEs, paired gaps, ranking and the month-0 / first-recovery
  descriptives are exactly equal under both models (a full-scale check of the
  score equivalence); the same for the first-recovery-discount valuation,
  which also reads nothing after the first recovery;
* ``score_cash_values_by_world.csv`` / ``score_cash_gaps_by_world.csv`` — the
  model-2.1.0 score and cash: mean over seeds, 95% t interval (4 df), RMS
  Monte-Carlo SE per seed, rank counts, resolved seeds; gaps are oriented
  candidate − π_b and challenger − challenger as in the 2.0.0 report;
* ``rankings_by_seed.csv`` — score and cash rankings per world-seed, resolved
  adjacent pairs, winner change score → cash;
* ``cash_by_model_by_world.csv`` — cash under 2.1.0 next to the historical 2.0.0
  cash (partial payments, open balances), labelled by model;
* ``tables.md`` — the same in Markdown.

Usage::

    python scripts/settlement_diagnostic_compare.py --new-protocol P_2_1_0 \
        --old-protocol P_2_0_0 --dest DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
CANDIDATES = ("pi_b", "pi_near", "pi_far", "pi_stage")
OBJ = {"score": "benchmark", "cash": "cash"}  # report name -> record key
# gap orientation in the report: (first, second) -> first − second
PAIRS = [("pi_near", "pi_b"), ("pi_far", "pi_b"), ("pi_stage", "pi_b"),
         ("pi_far", "pi_near"), ("pi_stage", "pi_near"), ("pi_far", "pi_stage")]
DESCRIPTIVE_SCORE_SIDE = ("recovery_rate", "recoveries_at_month0_share", "mean_d0_recovered",
                          "mean_d_first_recovered", "month0_contact_share")


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _records(protocol: Path) -> dict:
    proto = json.loads(Path(protocol).read_text())
    out = {}
    for world in proto["worlds"]:
        for seed in proto["seeds"]:
            p = REPO / proto["out_dir"] / world / f"seed{seed}_r{proto['replicate']}.json"
            out[(world, seed)] = (json.loads(p.read_text()), p)
    return out


def _gap(summary: dict, a: str, b: str) -> tuple[float, float, bool]:
    key = f"{a}-{b}" if f"{a}-{b}" in summary["gaps"] else f"{b}-{a}"
    g = summary["gaps"][key]
    sign = 1.0 if key == f"{a}-{b}" else -1.0
    return sign * g["gap"], g["se"], g["resolved"]


def _t_ci(x) -> dict:
    from scipy import stats

    x = np.asarray(x, dtype=np.float64)
    k = len(x)
    se = float(x.std(ddof=1) / math.sqrt(k))
    t = float(stats.t.ppf(0.975, k - 1))
    return {"mean": float(x.mean()), "sd_between_seeds": float(x.std(ddof=1)),
            "ci95_low": float(x.mean() - t * se), "ci95_high": float(x.mean() + t * se)}


def _md(df: pd.DataFrame, fmt: dict) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt.get(c, "{}").format(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def compare(new_protocol: Path, old_protocol: Path, dest: Path) -> dict:
    new, old = _records(new_protocol), _records(old_protocol)
    dest.mkdir(parents=True, exist_ok=True)
    ident, vals, gaps, ranks, cash_models = [], [], [], [], []
    for (world, seed), (rn, pn) in sorted(new.items()):
        ro, po = old[(world, seed)]
        sn, so = rn["objectives"]["benchmark"], ro["objectives"]["benchmark"]
        desc_eq = all(rn["descriptive"][c][k] == ro["descriptive"][c][k]
                      for c in CANDIDATES for k in DESCRIPTIVE_SCORE_SIDE)
        ident.append({"world": world, "seed": seed,
                      "generator_new": rn["generator_version"],
                      "generator_old": ro["generator_version"],
                      "n_cohort_equal": rn["n_cohort"] == ro["n_cohort"],
                      "score_values_equal": sn["values"] == so["values"],
                      "score_se_equal": sn["se"] == so["se"],
                      "score_gaps_equal": sn["gaps"] == so["gaps"],
                      "score_ranking_equal": sn["ranking"] == so["ranking"],
                      "summary_identical": sn == so,
                      "first_recovery_discount_identical": (
                          rn["objectives"]["first_recovery_discount"]
                          == ro["objectives"]["first_recovery_discount"]),
                      "first_recovery_descriptives_equal": desc_eq,
                      "validation_ok_new": rn["validation"].get("ok"),
                      "record_new_sha256": _sha(pn), "record_old_sha256": _sha(po)})
        for label, key in OBJ.items():
            s = rn["objectives"][key]
            for c in CANDIDATES:
                vals.append({"world": world, "seed": seed, "objective": label, "candidate": c,
                             "value": s["values"][c], "mc_se": s["se"][c],
                             "rank": s["ranking"].index(c) + 1})
            for a, b in PAIRS:
                g, se, res = _gap(s, a, b)
                gaps.append({"world": world, "seed": seed, "objective": label,
                             "gap": f"{a} - {b}", "value": g, "mc_se": se, "resolved": res})
            ranks.append({"world": world, "seed": seed, "objective": label,
                          "ranking": " > ".join(s["ranking"]), "best": s["best"],
                          "top_gap": s["top_gap"], "top_gap_se": s["top_gap_se"],
                          "top_resolved": s["top_resolved"],
                          "adjacent_resolved": "/".join("y" if x else "n"
                                                        for x in s["adjacent_resolved"]),
                          "winner_change_from_score": (rn["winner_change_vs_benchmark"]["cash"]
                                                       if label == "cash" else "")})
        for c in CANDIDATES:
            cash_models.append({"world": world, "seed": seed, "candidate": c,
                                "cash_model_2_1_0": rn["objectives"]["cash"]["values"][c],
                                "cash_model_2_0_0_historical":
                                    ro["objectives"]["cash"]["values"][c]})
    ident, vals, gaps, ranks, cash_models = (pd.DataFrame(x) for x in (
        ident, vals, gaps, ranks, cash_models))
    agg_v = []
    for (w, o, c), g in vals.groupby(["world", "objective", "candidate"], sort=False):
        agg_v.append({"world": w, "objective": o, "candidate": c, **_t_ci(g["value"]),
                      "mc_se_rms": float(np.sqrt((g["mc_se"] ** 2).mean())),
                      "rank_counts": json.dumps({str(k): int(v) for k, v in
                                                 g["rank"].value_counts().sort_index().items()})})
    agg_g = []
    for (w, o, p), g in gaps.groupby(["world", "objective", "gap"], sort=False):
        agg_g.append({"world": w, "objective": o, "gap": p, **_t_ci(g["value"]),
                      "mc_se_rms": float(np.sqrt((g["mc_se"] ** 2).mean())),
                      "seeds_resolved": int(g["resolved"].sum()),
                      "seeds_positive": int((g["value"] > 0).sum())})
    agg_c = []
    for (w, c), g in cash_models.groupby(["world", "candidate"], sort=False):
        agg_c.append({"world": w, "candidate": c,
                      "cash_2_1_0_mean": float(g["cash_model_2_1_0"].mean()),
                      "cash_2_0_0_historical_mean": float(g["cash_model_2_0_0_historical"].mean()),
                      "difference_mean": float((g["cash_model_2_1_0"]
                                                - g["cash_model_2_0_0_historical"]).mean())})
    agg_v, agg_g, agg_c = pd.DataFrame(agg_v), pd.DataFrame(agg_g), pd.DataFrame(agg_c)
    ident.to_csv(dest / "score_identity_by_seed.csv", index=False)
    vals.to_csv(dest / "score_cash_values_by_seed.csv", index=False)
    gaps.to_csv(dest / "score_cash_gaps_by_seed.csv", index=False)
    agg_v.to_csv(dest / "score_cash_values_by_world.csv", index=False)
    agg_g.to_csv(dest / "score_cash_gaps_by_world.csv", index=False)
    ranks.to_csv(dest / "rankings_by_seed.csv", index=False)
    cash_models.to_csv(dest / "cash_by_model_by_seed.csv", index=False)
    agg_c.to_csv(dest / "cash_by_model_by_world.csv", index=False)
    f2, s2 = "{:.2f}", "{:+.2f}"
    md = [
        "# Policy-reward diagnostic under simulator model 2.1.0 (full settlement)", "",
        "Exploratory; worlds A_on and B_on, development seeds 9301-9305 (shared by the two "
        "worlds), replicate 2, 1,000,000 borrowers, batch 50,000, month-0 explorable cohort, "
        "window months 0-8. US$ per decision.", "",
        "* **score** (synthetic evaluation score, unchanged definition): 1{first recovery in "
        "months 0-8} x B0 x (1 - d0).",
        "* **cash** (model 2.1.0): the settlement paid at the first recovery, round(B_t x "
        "(1 - d_t), 2) on the balance just before the payment; the loan then closes. Not net "
        "profit: no channel costs, no time discounting.",
        "* Per world: mean over the 5 seeds, 95% t interval over seeds (4 df), RMS Monte-Carlo "
        "SE per seed; a pair is resolved in a seed if |gap| > 1.96 paired SE.", "",
        "## Score: identical to the model-2.0.0 records", "",
        _md(ident[["world", "seed", "generator_old", "generator_new", "summary_identical",
                   "first_recovery_descriptives_equal", "first_recovery_discount_identical",
                   "validation_ok_new"]], {}), "",
        "## Values (model 2.1.0)", "",
        _md(agg_v[["world", "objective", "candidate", "mean", "ci95_low", "ci95_high",
                   "mc_se_rms", "rank_counts"]],
            {"mean": f2, "ci95_low": f2, "ci95_high": f2, "mc_se_rms": f2}), "",
        "## Gaps (model 2.1.0)", "",
        _md(agg_g[["world", "objective", "gap", "mean", "ci95_low", "ci95_high", "mc_se_rms",
                   "seeds_resolved", "seeds_positive"]],
            {"mean": s2, "ci95_low": s2, "ci95_high": s2, "mc_se_rms": f2}), "",
        "## Rankings per seed (model 2.1.0)", "",
        _md(ranks[["world", "seed", "objective", "ranking", "top_gap", "top_gap_se",
                   "top_resolved", "adjacent_resolved", "winner_change_from_score"]],
            {"top_gap": f2, "top_gap_se": f2}), "",
        "## Cash by model (2.0.0 values are historical: partial payments, open balances)", "",
        _md(agg_c, {"cash_2_1_0_mean": f2, "cash_2_0_0_historical_mean": f2,
                    "difference_mean": s2}), ""]
    (dest / "tables.md").write_text("\n".join(md))
    summary = {"new_protocol": str(new_protocol), "old_protocol": str(old_protocol),
               "world_seeds": len(ident),
               "score_identical_all": bool(ident["summary_identical"].all()
                                           and ident["first_recovery_descriptives_equal"].all()),
               "first_recovery_discount_identical_all": bool(
                   ident["first_recovery_discount_identical"].all()),
               "validation_ok_all": bool(ident["validation_ok_new"].all()),
               "outputs": sorted(p.name for p in dest.iterdir() if p.is_file())}
    (dest / "comparison_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--new-protocol", type=Path, required=True)
    ap.add_argument("--old-protocol", type=Path, required=True)
    ap.add_argument("--dest", type=Path, required=True)
    a = ap.parse_args(argv)
    print(json.dumps(compare(a.new_protocol, a.old_protocol, a.dest), indent=1))


if __name__ == "__main__":
    main()
