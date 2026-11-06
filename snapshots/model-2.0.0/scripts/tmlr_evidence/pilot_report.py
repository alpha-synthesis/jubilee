"""Pilot report: cost, memory and reference precision → campaign sizing.

Reads the aggregated pilot tables (``scripts/tmlr_aggregate.py`` output) and
writes ``pilot_report.md`` + ``pilot_sizing.json``. The precision rule and
the cost ceiling are inputs (fixed before the pilot was inspected); the
script reports what each condition needs and what the campaign would cost.

Usage::

    python scripts/tmlr_evidence/pilot_report.py --tables DIR --protocol P.json \
        --value-se 2.0 --gap-se 1.0 --cpu-hours-ceiling 150 --runs 80 --out DIR
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

DECISION = ["pi_b", "pi_near", "pi_far", "pi_stage"]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", type=Path, required=True)
    ap.add_argument("--protocol", type=Path, required=True)
    ap.add_argument("--value-se", type=float, required=True)
    ap.add_argument("--gap-se", type=float, required=True)
    ap.add_argument("--cpu-hours-ceiling", type=float, required=True)
    ap.add_argument("--runs", type=int, required=True, help="campaign runs (conditions × seeds)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    proto = json.loads(a.protocol.read_text())
    vals = pd.read_csv(a.tables / "reference_values_by_run.csv")
    gaps = pd.read_csv(a.tables / "reference_gaps_by_run.csv")
    jobs = pd.read_csv(a.tables / "job_costs.csv")
    R = int(vals["R"].iloc[0])

    # per-replicate Monte-Carlo SE (one replicate of the protocol's population)
    v = vals[vals["candidate"].isin(DECISION)].copy()
    v["ratio_between_within"] = v["se_between"] / v["se_within"]
    g = gaps.copy()
    a_, b_ = zip(*[p.split("-") for p in g["pair"]], strict=True)
    g["a"], g["b"] = a_, b_
    g = g[g["a"].isin(DECISION) & g["b"].isin(DECISION)].copy()
    g["se_one_replicate"] = g["se_within"] * math.sqrt(R)
    g["ratio_between_within"] = g["se_between"] / g["se_within"]
    g["variance_reduction_vs_independent"] = (g["se_if_independent"] / g["se_within"]) ** 2

    need_v = v.groupby("cond")["se_one_replicate"].max().map(
        lambda s: math.ceil((s / a.value_se) ** 2))
    need_g = g.groupby("cond")["se_one_replicate"].max().map(
        lambda s: math.ceil((s / a.gap_se) ** 2))
    r_needed = int(max(need_v.max(), need_g.max(), 1))

    # shock component: spread of the reference value across seeds (separate component)
    shock = v.groupby(["cond", "candidate"])["mean"].agg(["mean", "std", "count"]).reset_index()

    # bin diagnostic: centre dose minus dose uniform over the bin
    bins = gaps[gaps["pair"].isin(["pi_near-pi_near_binU", "pi_far-pi_far_binU"])]
    bin_tab = bins.groupby(["cond", "pair"]).agg(mean_gap=("mean", "mean"),
                                                 mean_se=("se_within", "mean"),
                                                 n=("mean", "size")).reset_index()

    # costs: CPU seconds per job (under the pilot's concurrency) and per simulated world
    n_ref = len(proto["candidates"]) + len(proto.get("extra_reference_candidates", []))
    n_tgt = len(proto["candidates"]) - 1
    cost = jobs.groupby("kind").agg(n=("wall_seconds", "size"),
                                    wall_median=("wall_seconds", "median"),
                                    wall_max=("wall_seconds", "max"),
                                    cpu_median=("cpu_seconds", "median"),
                                    rss_max_mb=("peak_rss_mb", "max")).reset_index()
    per_world = {
        "logs": float(jobs.loc[jobs["kind"] == "logs", "cpu_seconds"].median()),
        "annotator_per_target": float(jobs.loc[jobs["kind"] == "annotator", "cpu_seconds"].median()) / n_tgt,
        "reference_per_candidate": float(jobs.loc[jobs["kind"] == "reference", "cpu_seconds"].median()) / n_ref,
    }
    est = jobs.loc[jobs["kind"] == "estimate", "cpu_seconds"]
    per_world["estimate_per_run"] = float(est.median()) if len(est) else float("nan")
    k_campaign = 4  # incumbent + three targets
    def campaign_cpu_h(r):
        per_run = (per_world["logs"] + per_world["annotator_per_target"] * (k_campaign - 1)
                   + per_world["reference_per_candidate"] * k_campaign * r
                   + per_world["estimate_per_run"])
        return per_run * a.runs / 3600

    sizing = {
        "R_pilot": R, "value_se_target": a.value_se, "gap_se_target": a.gap_se,
        "R_needed_value_by_condition": need_v.to_dict(),
        "R_needed_gap_by_condition": need_g.to_dict(),
        "R_needed": r_needed,
        "cpu_seconds_per_unit_under_pilot_concurrency": per_world,
        "campaign_runs": a.runs,
        "campaign_cpu_hours_by_R": {r: round(campaign_cpu_h(r), 1) for r in (1, 2, 3, 4, 6, 8)},
        "cpu_hours_ceiling": a.cpu_hours_ceiling,
    }
    affordable = [r for r, h in sizing["campaign_cpu_hours_by_R"].items() if h <= a.cpu_hours_ceiling]
    sizing["R_affordable_max"] = max(affordable) if affordable else 0
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "pilot_sizing.json").write_text(json.dumps(sizing, indent=2, default=float))

    def md(df: pd.DataFrame, floatfmt: str = "{:.3g}") -> str:
        cols = list(df.columns)
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for _, r in df.iterrows():
            lines.append("| " + " | ".join(
                floatfmt.format(x) if isinstance(x, (float, np.floating)) else str(x)
                for x in r) + " |")
        return "\n".join(lines)

    vt = v.groupby(["cond", "candidate"]).agg(
        mean_value=("mean", "mean"), se_one_replicate_median=("se_one_replicate", "median"),
        se_one_replicate_max=("se_one_replicate", "max"),
        between_over_within_median=("ratio_between_within", "median")).reset_index()
    gt = g.groupby(["cond", "pair"]).agg(
        mean_gap=("mean", "mean"), se_one_replicate_median=("se_one_replicate", "median"),
        se_one_replicate_max=("se_one_replicate", "max"),
        corr_within_median=("corr_within", "median"),
        variance_reduction_median=("variance_reduction_vs_independent", "median")).reset_index()
    text = f"""# Pilot report — {proto['name']}

{proto.get('purpose', '')}

Development seeds {proto['seeds']}; {R} reference replicates per run; population
{proto['borrowers']:,} borrowers per replicate (batch {proto['batch_size']:,}); every value in
US$ per decision on the month-0 explorable cohort.

## Cost and memory (measured under the pilot's concurrency)

{md(cost)}

CPU seconds per unit: {json.dumps({k: round(v_, 1) for k, v_ in per_world.items()})}.

## Reference precision (one replicate of {proto['borrowers']:,} borrowers)

Values (SE of one replicate's cohort mean, from the per-loan variance; the
between/within ratio compares the spread of the {R} replicate means with it):

{md(vt)}

Paired gaps between decision candidates (same population and draws within a
replicate; `variance_reduction` = independent-sampling variance / paired variance):

{md(gt)}

## Variation across regional shocks (a separate component, not Monte-Carlo error)

{md(shock)}

## Bin approximation (centre dose minus dose uniform over the bin)

{md(bin_tab)}

## Sizing against the precision rule (fixed before inspection)

Rule: SE of every candidate value ≤ {a.value_se} and of every gap between decision
candidates ≤ {a.gap_se} US$/decision per run, with R replicates. Needed R by condition —
values: {sizing['R_needed_value_by_condition']}; gaps: {sizing['R_needed_gap_by_condition']}.
**R needed = {r_needed}.** Projected campaign CPU-hours ({a.runs} runs, pilot concurrency):
{sizing['campaign_cpu_hours_by_R']} (ceiling {a.cpu_hours_ceiling}); largest affordable R =
{sizing['R_affordable_max']}.
"""
    (a.out / "pilot_report.md").write_text(text)
    print(json.dumps({k: sizing[k] for k in ("R_needed", "R_affordable_max",
                                             "campaign_cpu_hours_by_R")}, default=float))


if __name__ == "__main__":
    main()
