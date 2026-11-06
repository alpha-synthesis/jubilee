#!/usr/bin/env python3
"""T-31 — grade the grader: validate OPE against the synthetic oracle.

The whole point of the Oracle Program is to *replace* the simulator-oracle when
it no longer exists (real client data).  Before trusting OPE there, we validate
the instrument here, where the true policy value IS known in closed form.

We compare, for the target = oracle-optimal policy:

  - DM (self-graded)  — the Direct Method on a reward model: this is the analogue
                        of today's ``expected_return`` (the model grading itself)
  - IS                — importance sampling on logged rewards
  - DR                — doubly robust (cross-fitted)
  - DM⁺-IS            — DR + simulator annotations in the reward-model fit

against the TRUE value, sweeping the pilot design (ε, N).  Outputs an RMSE bar
chart and CI-width sizing curves into ``outputs/ope_meta_validation/``.

Run:  python scripts/benchmark/ope_meta_validation.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ope_bench.annotator import (  # noqa: E402
    OracleAnnotator,
    build_annotations,
    dm_plus_is_value,
)
from ope_bench.bandit import collections_bandit  # noqa: E402
from ope_bench.confidence import bootstrap_ci  # noqa: E402
from ope_bench.estimators import (  # noqa: E402
    DeterministicPolicy,
    TabularRewardModel,
    cross_fitted_dr_value,
    direct_method_value,
    importance_sampling_value,
)
from ope_bench.logging_policy import (  # noqa: E402
    LoggingPolicy,
    generate_logs,
    suboptimal_incumbent,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "ope_meta_validation"

ESTIMATORS = ["DM (self-graded)", "IS", "DR", "DM⁺-IS"]
COLORS = {
    "DM (self-graded)": "#c0392b",
    "IS": "#e67e22",
    "DR": "#2980b9",
    "DM⁺-IS": "#27ae60",
}


def _estimates(bandit, behavior, target, annotator, n, seed, resolution):
    """One draw of all four estimators.

    ``resolution`` is the reward-model fidelity for DM/DR/DM⁺-IS:
    ``"full"`` = well-specified; ``"action_only"`` = misspecified (ignores the
    customer profile) — the honest analogue of a world model grading itself with
    structural blind spots (Levine et al. 2020).
    """
    logs = generate_logs(bandit, behavior, n=n, seed=seed)

    def fit(train):
        return TabularRewardModel(
            bandit.n_contexts, bandit.n_actions, resolution
        ).fit(train["context"], train["action"], train["reward"])

    annotations = build_annotations(
        logs, target, annotator, rng=np.random.default_rng(seed))
    return {
        "DM (self-graded)": direct_method_value(logs, target, fit(logs)),
        "IS": importance_sampling_value(logs, target),
        "DR": cross_fitted_dr_value(logs, target, fit, seed=seed),
        "DM⁺-IS": dm_plus_is_value(
            logs, annotations, target, bandit.n_contexts, bandit.n_actions,
            seed=seed, resolution=resolution),
    }


def run_rmse(bandit, behavior, target, annotator, n, n_seeds, resolution):
    truth = bandit.policy_value(target)
    errs = {e: [] for e in ESTIMATORS}
    for seed in range(n_seeds):
        est = _estimates(bandit, behavior, target, annotator, n, seed, resolution)
        for e in ESTIMATORS:
            errs[e].append(est[e] - truth)
    return {
        e: {
            "rmse": float(np.sqrt(np.mean(np.square(errs[e])))),
            "bias": float(np.mean(errs[e])),
            "std": float(np.std(errs[e])),
            # per-seed errors: enables MC SEs and PAIRED comparisons across
            # estimators (shared seeds) — required for any "lowest RMSE"
            # claim to carry uncertainty.
            "per_seed_err": [float(v) for v in errs[e]],
        }
        for e in ESTIMATORS
    }, truth


def ci_width_curve(bandit, behavior, target, ns, n_seeds):
    """Median CI width of the DR estimator vs N (pilot sizing)."""

    def fit(train):
        return TabularRewardModel(
            bandit.n_contexts, bandit.n_actions, "full"
        ).fit(train["context"], train["action"], train["reward"])

    def estimate(sub):
        return cross_fitted_dr_value(sub, target, fit, seed=0)

    widths = []
    for n in ns:
        w = []
        for seed in range(n_seeds):
            logs = generate_logs(bandit, behavior, n=n, seed=seed)
            lo, hi = bootstrap_ci(estimate, logs, n_boot=150, alpha=0.1, seed=seed)
            w.append(hi - lo)
        widths.append(float(np.median(w)))
    return widths


def plot_rmse(stats, truth, out_path, title):
    fig, ax = plt.subplots(figsize=(8, 5))
    names = ESTIMATORS
    rmse = [stats[e]["rmse"] for e in names]
    bias = [abs(stats[e]["bias"]) for e in names]
    x = np.arange(len(names))
    ax.bar(x, rmse, color=[COLORS[e] for e in names], edgecolor="white",
           label="RMSE")
    ax.bar(x, bias, color="black", alpha=0.35, width=0.4, label="|bias|")
    for i, e in enumerate(names):
        ax.text(i, rmse[i] + 0.001, f"{rmse[i]:.4f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.set_ylabel("Error vs TRUE policy value")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  ↳ {out_path}")


def plot_ci_curve(ns, widths, out_path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(ns, widths, "o-", color="#2980b9", linewidth=2)
    for n, w in zip(ns, widths):
        ax.text(n, w, f"{w:.3f}", fontsize=8, va="bottom")
    ax.set_xscale("log")
    ax.set_xlabel("pilot size N (log)")
    ax.set_ylabel("median 90% CI width (DR)")
    ax.set_title("Pilot sizing — CI width shrinks with N", fontsize=12,
                 fontweight="bold")
    ax.grid(alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"  ↳ {out_path}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bandit = collections_bandit()
    inc = suboptimal_incumbent(bandit)
    target = DeterministicPolicy(bandit.optimal_actions(), bandit.n_actions)
    annotator = OracleAnnotator(bandit.true_reward_matrix)  # calibrated simulator
    truth = bandit.policy_value(target)
    optimal = bandit.optimal_value()

    print(f"True value of target (oracle-optimal policy): {truth:.4f}")
    print(f"Achievable ceiling (optimal_value):           {optimal:.4f}\n")

    eps, n, seeds = 0.10, 2000, 200
    behavior = LoggingPolicy(inc, bandit.n_actions, epsilon=eps)

    regimes = {
        "well_specified": ("full", "Reward model WELL-SPECIFIED — DM suffices"),
        "misspecified": ("action_only",
                         "Reward model MISSPECIFIED (self-grading blind spots)"),
    }
    all_stats = {}
    for key, (resolution, title) in regimes.items():
        print(f"RMSE sweep [{key}] @ ε={eps}, N={n}, {seeds} seeds ...")
        stats, _ = run_rmse(
            bandit, behavior, target, annotator, n, seeds, resolution)
        all_stats[key] = stats
        print(f"\n{'estimator':<18}{'RMSE':>10}{'|bias|':>10}{'std':>10}")
        print("-" * 48)
        for e in ESTIMATORS:
            s = stats[e]
            print(f"{e:<18}{s['rmse']:>10.4f}{abs(s['bias']):>10.4f}{s['std']:>10.4f}")
        plot_rmse(stats, truth, OUT / f"rmse_{key}.png",
                  f"{title}\n(ε={eps}, N={n})")
        print()

    # Pilot sizing: CI width vs N at a realistic ε
    ns = [250, 500, 1000, 2000, 4000, 8000]
    print(f"CI-width sizing curve over N={ns} ...")
    widths = ci_width_curve(
        bandit, LoggingPolicy(inc, bandit.n_actions, epsilon=0.15), target,
        ns, n_seeds=40)
    plot_ci_curve(ns, widths, OUT / "pilot_sizing_ci_width.png")

    summary = {
        "true_value": truth,
        "optimal_value": optimal,
        "epsilon": eps,
        "n": n,
        "seeds": seeds,
        "regimes": all_stats,
        "pilot_sizing": {"n": ns, "median_ci_width": widths},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  ↳ {OUT / 'summary.json'}")

    print("\n" + "=" * 64)
    print("VERDICT — error vs the TRUE value (lower is better):")
    for key, (_, title) in regimes.items():
        s = all_stats[key]
        print(f"\n  [{title}]")
        for e in ("DM (self-graded)", "DR", "DM⁺-IS"):
            print(f"    {e:<18} RMSE {s[e]['rmse']:.4f}  bias {s[e]['bias']:+.4f}")
    print("=" * 64)


if __name__ == "__main__":
    main()
