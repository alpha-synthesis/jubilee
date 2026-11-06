"""Development check of gradient-boosting hyper-parameters (reference-free).

Fits the cross-fitted nuisances of ``ope_bench.nontabular`` on stored
development logs with a few candidate configurations and reports diagnostics
an analyst can compute from logs alone — mean IS weight (1 for calibrated
propensities), calibration of the propensity model by decile, out-of-fold
reward fit, minimum propensity on matched rows, fit time. No reference value
or estimator error is read.

Usage::

    python scripts/tmlr_evidence/gbm_dev_check.py --logs RUN/logs.parquet [...] --out gbm_dev.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from tmlr_campaign import CANDIDATES, CATEGORIES, _read_parquet  # noqa: E402

from ope_bench.nontabular import GBMConfig, design_matrix, fit_cross_fitted_nuisances  # noqa: E402
from ope_bench.panel import balance_terciles, build_logs  # noqa: E402

CONFIGS = {
    "default": GBMConfig(),
    "regularized": GBMConfig(learning_rate=0.05, max_iter=300, max_leaf_nodes=15,
                             min_samples_leaf=1000),
}
TARGETS = ("pi_near", "pi_far", "pi_stage")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs", nargs="+", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    out = []
    for path in a.logs:
        cohort = _read_parquet(path)
        logs = build_logs(cohort, balance_terciles(cohort))
        x = design_matrix(cohort, CATEGORIES)
        folds = np.random.default_rng(0).integers(0, 2, size=len(cohort))
        t_act = {n: CANDIDATES[n].actions_per_context()[logs["context"]] for n in TARGETS}
        for name, cfg in CONFIGS.items():
            t0 = time.time()
            nuis = fit_cross_fitted_nuisances(x, logs["action"], logs["reward"], t_act, folds, cfg)
            secs = time.time() - t0
            r = logs["reward"]
            rec = {"logs": str(path), "config": name, "params": cfg.as_dict(),
                   "fit_seconds": round(secs, 1),
                   "oof_r2_logged": float(1 - np.mean((r - nuis["m_logged"]) ** 2) / np.var(r)),
                   "targets": {}}
            for t in TARGETS:
                e = nuis["e_target"][t]
                match = logs["action"] == t_act[t]
                w = np.where(match, 1 / np.clip(e, cfg.propensity_clip, 1), 0)
                dec = np.quantile(e, np.linspace(0, 1, 11))
                bins = np.clip(np.searchsorted(dec, e, side="right") - 1, 0, 9)
                calib = [[float(e[bins == b].mean()), float(match[bins == b].mean())]
                         for b in range(10) if (bins == b).any()]
                rec["targets"][t] = {
                    "mean_is_weight": float(w.mean()),
                    "match_rate": float(match.mean()),
                    "min_propensity_on_match": float(e[match].min()),
                    "n_clipped_on_match": int((e[match] < cfg.propensity_clip).sum()),
                    "calibration_by_decile_pred_vs_obs": calib,
                }
            out.append(rec)
            head = {k: rec[k] for k in ("logs", "config", "fit_seconds", "oof_r2_logged")}
            w = {t: round(v["mean_is_weight"], 4) for t, v in rec["targets"].items()}
            print(json.dumps(head | w), flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
