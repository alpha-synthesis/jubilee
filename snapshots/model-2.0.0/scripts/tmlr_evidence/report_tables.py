"""Import-ready tables (markdown + CSV) from the aggregated campaign tables.

Reads ``scripts/tmlr_aggregate.py`` output and writes compact tables for the
manuscript integration: reference values and precision, mean error ± SE by
condition/regime/estimator/target, selection, interval diagnostic, regime and
condition contrasts. Numbers are copied, never re-estimated; units are US$ per
decision on the month-0 explorable cohort.

Usage::

    python scripts/tmlr_evidence/report_tables.py --tables DIR --out DIR
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ORDER_T = ["dm", "dm_blind", "is", "snips", "dr", "dm_plus_is", "pilot_is", "pilot_dr",
           "dm_refit"]
ORDER_G = ["dm", "is", "snips", "dr", "pilot_dr"]
TARGET_NAME = {"pi_near": "π_sms", "pi_far": "π_visit", "pi_stage": "π_stage", "pi_b": "π_b"}


def _pm(m, s, nd=1):
    if pd.isna(m):
        return "—"
    return f"{m:+.{nd}f} ± {s:.{nd}f}" if not pd.isna(s) else f"{m:+.{nd}f}"


def _md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join(out)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    t = a.tables
    a.out.mkdir(parents=True, exist_ok=True)
    blocks = []

    ref = pd.read_csv(t / "reference_values_by_run.csv")
    ref = ref[ref["candidate"].isin(TARGET_NAME)]
    r = (ref.groupby(["cond", "candidate"])
         .agg(seeds=("seed", "size"), mean_value=("mean", "mean"),
              sd_across_seeds=("mean", "std"), median_mc_se=("se_within", "median"),
              max_mc_se=("se_within", "max")).reset_index())
    r["candidate"] = r["candidate"].map(TARGET_NAME)
    r = r.round(2)
    r.to_csv(a.out / "T1_reference_values.csv", index=False)
    blocks.append("## T1. Reference values (mean over seeds) and Monte-Carlo SE per run\n\n"
                  + _md(r))

    gaps = pd.read_csv(t / "reference_gaps_by_run.csv")
    keep = [p for p in gaps["pair"].unique()
            if all(x in TARGET_NAME for x in p.split("-"))]
    g = (gaps[gaps["pair"].isin(keep)].groupby(["cond", "pair"])
         .agg(seeds=("seed", "size"), mean_gap=("mean", "mean"),
              median_paired_se=("se_within", "median"), max_paired_se=("se_within", "max"),
              median_corr=("corr_within", "median")).reset_index().round(3))
    g.to_csv(a.out / "T2_reference_gaps.csv", index=False)
    blocks.append("## T2. Reference gaps between candidates (paired Monte-Carlo SE per run)\n\n"
                  + _md(g))

    es = pd.read_csv(t / "error_summary.csv")
    for regime, order in (("tabular", ORDER_T), ("nontabular", ORDER_G)):
        sub = es[es["regime"] == regime].copy()
        sub["cell"] = [_pm(m, s) for m, s in zip(sub["mean_error"], sub["se_mean_error"],
                                                 strict=True)]
        piv = sub.pivot_table(index=["cond", "estimator"], columns="target", values="cell",
                              aggfunc="first").reset_index()
        piv["estimator"] = pd.Categorical(piv["estimator"], [o for o in order
                                                             if o in set(piv["estimator"])])
        piv = piv.sort_values(["cond", "estimator"]).rename(columns=TARGET_NAME)
        piv.to_csv(a.out / f"T3_mean_error_{regime}.csv", index=False)
        blocks.append(f"## T3 ({regime}). Mean error vs reference ± SE over seeds\n\n" + _md(piv))
        rm = sub.copy()
        rm["cell"] = [f"{x:.1f} ± {s:.1f}" if not pd.isna(s) else f"{x:.1f}"
                      for x, s in zip(rm["rmse"], rm["se_rmse"], strict=True)]
        piv = rm.pivot_table(index=["cond", "estimator"], columns="target", values="cell",
                             aggfunc="first").reset_index().rename(columns=TARGET_NAME)
        piv.to_csv(a.out / f"T4_rmse_{regime}.csv", index=False)
        blocks.append(f"## T4 ({regime}). RMSE ± bootstrap-over-seeds SE\n\n" + _md(piv))

    idt = pd.read_csv(t / "tabular_identity_dm_is_snips.csv")
    idt = (idt.groupby("cond")[["abs_dm_minus_is", "abs_dm_minus_snips"]].max()
           .reset_index().round(4))
    idt.to_csv(a.out / "T0_tabular_identity.csv", index=False)
    blocks.insert(0, "## T0. Tabular DM, IS and SNIPS coincide (largest |difference| over "
                  "runs and targets)\n\n" + _md(idt))
    fac = es[es["regime"] == "factual"][["cond", "n_defined", "mean_error", "se_mean_error"]]
    fac = fac.round(2)
    fac.to_csv(a.out / "T5_incumbent_factual_check.csv", index=False)
    blocks.append("## T5. Logged mean of the incumbent minus its independent reference "
                  "(should be 0 in expectation)\n\n" + _md(fac))

    sel = pd.read_csv(t / "selection_summary.csv")
    cols = ["cond", "regime", "estimator", "n_defined", "n_top_resolved", "correct_among_resolved",
            "correct_all", "mean_regret", "se_mean_regret", "mean_regret_resolved_runs",
            "mean_gain_vs_incumbent", "se_mean_gain_vs_incumbent",
            "n_picks_resolved_worse_than_incumbent", "n_picks_resolved_better_than_incumbent",
            "picks", "ref_best"]
    s = sel[cols].round(2)
    s.to_csv(a.out / "T6_selection.csv", index=False)
    blocks.append("## T6. Selection over the candidates (regret in recovery US$/decision)\n\n"
                  + _md(s))

    iv = pd.read_csv(t / "interval_diagnostic.csv").round(2)
    iv["target"] = iv["target"].map(TARGET_NAME)
    iv.to_csv(a.out / "T7_interval_diagnostic.csv", index=False)
    blocks.append("## T7. Interval diagnostic (containment of the reference; counts over seeds)\n\n"
                  + _md(iv))

    fa = pd.read_csv(t / "log_family_agreement.csv").round(2)
    fa["target"] = fa["target"].map(TARGET_NAME)
    fa.to_csv(a.out / "T10_log_family_agreement.csv", index=False)
    blocks.append("## T10. Spread of the log-based estimators' errors within a regime "
                  "(max − min per run)\n\n" + _md(fa))
    rc = pd.read_csv(t / "reference_replicate_consistency.csv")
    rc = (rc.groupby("kind")
          .apply(lambda g: pd.Series({"cells": len(g),
                                      "min_ratio": g["mean_variance_ratio"].min(),
                                      "max_ratio": g["mean_variance_ratio"].max(),
                                      "min_p": g["p_two_sided"].min()}),
                 include_groups=False)
          .reset_index().round(3))
    rc.to_csv(a.out / "T11_reference_replicate_consistency.csv", index=False)
    blocks.append("## T11. Between-replicate variance of the references against the per-loan "
                  "prediction (ratio 1 = independent loans; per condition, seeds independent)"
                  "\n\n" + _md(rc))
    for name, title in (("regime_contrast_nontabular_minus_tabular.csv",
                         "T8. Same logs: gradient-boosted minus tabular error"),
                        ("paired_condition_contrasts.csv",
                         "T9. Seed-paired condition contrasts of the error")):
        p = t / name
        if p.exists():
            d = pd.read_csv(p).round(2)
            if "target" in d:
                d["target"] = d["target"].map(TARGET_NAME)
            d.to_csv(a.out / (title.split(".")[0] + "_" + name), index=False)
            blocks.append(f"## {title}\n\n" + _md(d))

    (a.out / "tables.md").write_text(
        "# Import-ready tables (units: US$ per decision, month-0 explorable cohort)\n\n"
        + "\n\n".join(blocks) + "\n")
    print(json.dumps({"written": sorted(p.name for p in a.out.iterdir())}))


if __name__ == "__main__":
    main()
