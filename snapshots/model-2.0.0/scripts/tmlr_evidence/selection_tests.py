"""Post hoc selection tests on the revision campaign (not in the frozen plan).

The frozen analysis plan lists selection summaries per condition and the
condition contrasts of the errors. The paired tests below were added after
the confirmation runs were seen and are labelled post hoc wherever reported.
Seeds are the independent unit; conditions at the same seed share every random
draw, so a seed block averages conditions before testing.

Writes one CSV with every test, its estimate, SE, p-value and the Holm-adjusted
p-value over the family of tests in the file, plus the top-two gap analysis
(estimated minus reference π_stage − π_sms gap).

Usage::

    python scripts/tmlr_evidence/selection_tests.py --tables CAMPAIGN/tables \
        --runs CAMPAIGN/runs --out selection_tests.csv
"""

from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def _t(x: np.ndarray) -> tuple[float, float, float]:
    m, se = float(x.mean()), float(x.std(ddof=1) / math.sqrt(len(x)))
    return m, se, float(2 * stats.t.sf(abs(m / se), len(x) - 1)) if se > 0 else 1.0


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", type=Path, required=True)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    sel = pd.read_csv(a.tables / "selection_by_run.csv")
    sel = sel[sel["defined"]]
    reg = sel.set_index(["cond", "seed", "regime", "estimator"])["regret"]
    cor = sel.set_index(["cond", "seed", "regime", "estimator"])["correct"].astype(int)
    seeds = sorted(sel["seed"].unique())
    conds = sorted(sel["cond"].unique())
    rows = []

    def block(a_key, b_key, use, label):
        d = np.array([np.mean([reg[(c, s) + a_key] - reg[(c, s) + b_key] for c in use])
                      for s in seeds])
        m, se, p = _t(d)
        rows.append({"test": label, "conditions": "+".join(use), "estimate": m, "se": se,
                     "p": p, "n_seed_blocks": len(d), "kind": "seed-block t"})

    pairs = [(("tabular", "pilot_is"), ("tabular", "dr"), "regret: pilot-IS minus tabular DR"),
             (("tabular", "pilot_dr"), ("tabular", "dr"), "regret: pilot-DR minus tabular DR"),
             (("nontabular", "dr"), ("tabular", "dr"), "regret: boosted DR minus tabular DR")]
    ctrl = [c for c in conds if c.endswith("_off")]
    coup = [c for c in conds if c.endswith("_on")]
    for a_key, b_key, label in pairs:
        for use in (conds, ctrl, coup):
            block(a_key, b_key, use, label)
    # coupling effect on tabular-DR regret (on minus off, per world and averaged)
    for worlds in (["A"], ["B"], ["A", "B"]):
        d = np.array([np.mean([reg[(f"{w}_on", s, "tabular", "dr")]
                               - reg[(f"{w}_off", s, "tabular", "dr")] for w in worlds])
                      for s in seeds])
        m, se, p = _t(d)
        rows.append({"test": "regret: tabular DR, coupling on minus off",
                     "conditions": "+".join(worlds), "estimate": m, "se": se, "p": p,
                     "n_seed_blocks": len(d), "kind": "seed-block t"})
        w = stats.wilcoxon(d) if np.any(d != 0) else None
        rows.append({"test": "regret: tabular DR, coupling on minus off",
                     "conditions": "+".join(worlds), "estimate": float(np.median(d)), "se": None,
                     "p": float(w.pvalue) if w else 1.0, "n_seed_blocks": len(d),
                     "kind": "Wilcoxon signed-rank (median)"})
        for wd in worlds:
            on = np.array([cor[(f"{wd}_on", s, "tabular", "dr")] for s in seeds])
            off = np.array([cor[(f"{wd}_off", s, "tabular", "dr")] for s in seeds])
            n10, n01 = int(((on == 1) & (off == 0)).sum()), int(((on == 0) & (off == 1)).sum())
            if len(worlds) == 1:
                p = stats.binomtest(min(n10, n01), n10 + n01, 0.5).pvalue if n10 + n01 else 1.0
                rows.append({"test": "correct picks: tabular DR, coupling on vs off",
                             "conditions": wd, "estimate": float(on.sum() - off.sum()),
                             "se": None, "p": float(p), "n_seed_blocks": len(seeds),
                             "kind": f"exact McNemar ({n10} vs {n01} discordant)"})
    out = pd.DataFrame(rows)
    # Holm adjustment over the t-tests of this file (one family)
    t_rows = out["kind"] == "seed-block t"
    ps = out.loc[t_rows, "p"].to_numpy()
    order = np.argsort(ps)
    adj = np.empty_like(ps)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(ps) - rank) * ps[i]))
        adj[i] = running
    out.loc[t_rows, "p_holm"] = adj
    out["status"] = "post hoc (not in the frozen analysis plan)"

    # top-two gap: estimated minus reference (pi_stage - pi_near), tabular DR
    gap_rows = []
    for f in sorted(glob.glob(str(a.runs / "*" / "seed*" / "panel.json"))):
        p = json.loads(Path(f).read_text())
        for regime in ("tabular", "nontabular"):
            est = {t: p["targets"][t][regime]["dr"]["value"] for t in ("pi_stage", "pi_near")}
            ref = {t: p["targets"][t]["reference"] for t in ("pi_stage", "pi_near")}
            gap_rows.append({"cond": p["cond"], "seed": p["seed"], "regime": regime,
                             "estimated_gap": est["pi_stage"] - est["pi_near"],
                             "reference_gap": ref["pi_stage"] - ref["pi_near"]})
    g = pd.DataFrame(gap_rows)
    g["gap_error"] = g["estimated_gap"] - g["reference_gap"]
    gs = (g.groupby(["cond", "regime"])
          .agg(mean_estimated_gap=("estimated_gap", "mean"),
               mean_reference_gap=("reference_gap", "mean"),
               mean_gap_error=("gap_error", "mean"),
               se_gap_error=("gap_error", lambda x: x.std(ddof=1) / math.sqrt(len(x))),
               share_negative_estimated_gap=("estimated_gap", lambda x: float((x < 0).mean())))
          .reset_index())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False, float_format="%.6g", lineterminator="\n")
    gs.to_csv(a.out.with_name(a.out.stem + "_top_two_gap.csv"), index=False,
              float_format="%.6g", lineterminator="\n")
    print(out.round(3).to_string(index=False))
    print(gs.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
