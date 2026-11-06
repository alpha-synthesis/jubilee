"""Oracle-less data report — diagnostics computable from the PUBLIC tables only.

No ``oracle_truth`` is read; everything here is what a downstream consumer (or the policy engine's
own data audit) can compute on a real institution's panel. It mirrors the metrics in
a downstream data-quality audit (recovery rate, channel mix, positivity/overlap,
model-free assignment dependence via Cramér's V, delinquency↔recovery sign) and adds
**exploration-coverage** stats for the ε-floor design (share explored, discount coverage in
active states, propensity floor) — the evidence that the counterfactual coverage an OPE
estimator needs is actually present.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from collection_simulator.config import load_config
from collection_simulator.dictionaries import CHANNELS

_COVARIATES = [
    "outstanding_balance", "days_past_due", "days_in_credito_em_liquidacao",
    "loan_age_months", "remaining_maturity_months",
]


def _cramers_v(cat: pd.Series, binned: pd.Series) -> float:
    tab = pd.crosstab(cat, binned).to_numpy(dtype=float)
    n = tab.sum()
    if n == 0 or min(tab.shape) < 2:
        return 0.0
    row = tab.sum(axis=1, keepdims=True)
    col = tab.sum(axis=0, keepdims=True)
    exp = row @ col / n
    mask = exp > 0
    chi2 = float((((tab - exp) ** 2)[mask] / exp[mask]).sum())
    denom = n * (min(tab.shape) - 1)
    return (chi2 / denom) ** 0.5 if denom > 0 else 0.0


def _load_public(db_path: Path) -> pd.DataFrame:
    import duckdb

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        cols = {r[0] for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='actions'"
        ).fetchall()}
        extra = ", ".join(c for c in ("is_exploration", "exploration_epsilon") if c in cols)
        extra = (", " + extra) if extra else ""
        df = con.execute(f"""
            SELECT p.loan_id, p.month, p.status, p.days_past_due,
                   p.days_in_credito_em_liquidacao, p.loan_age_months,
                   p.remaining_maturity_months, p.outstanding_balance, p.recovered,
                   a.channel, a.discount_offer {extra}
            FROM monthly_panel p JOIN actions a USING (loan_id, month)
        """).df()
    finally:
        con.close()
    return df


def evaluate_oracleless(
    db_path: str | Path,
    config_path: str | Path,
    out_path: str | Path = "outputs/oracleless_report.md",
    make_figures: bool = True,
) -> dict[str, Any]:
    db_path = Path(db_path)
    cfg = load_config(config_path)
    declared = {k: float(v) for k, v in cfg["actions"]["channel_weights"].items()}
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = out_path.parent / "oracleless_figures"

    df = _load_public(db_path)
    n = len(df)
    maxd = float(cfg["actions"]["max_discount"])

    # --- distribution / mix ---
    rate = float(df["recovered"].astype(float).mean())
    share = df["channel"].value_counts(normalize=True)
    mix_dev = max(abs(share.get(ch, 0.0) - w) for ch, w in declared.items())

    # --- positivity / overlap ---
    min_action_share = float(share.min())
    strata = pd.qcut(df["days_past_due"], q=4, duplicates="drop")
    stratum_tab = pd.crosstab(strata, df["channel"], normalize="index")
    min_stratum_share = float(stratum_tab.min().min())

    # --- assignment dependence (model-free) ---
    deps = {}
    for c in _COVARIATES:
        if c in df:
            deps[c] = _cramers_v(df["channel"], pd.qcut(df[c], q=4, duplicates="drop"))
    assignment_dependence = max(deps.values()) if deps else 0.0
    top_cov = max(deps, key=deps.get) if deps else None

    # --- delinquency directional sanity ---
    dpd_outcome_rho = float(
        pd.Series(df["days_past_due"]).corr(df["recovered"].astype(float), method="spearman")
    )

    # --- exploration coverage (ε-floor) ---
    exploration: dict[str, Any] = {"enabled": "is_exploration" in df}
    if exploration["enabled"]:
        expl = df["is_exploration"].astype(bool)
        active = df["status"].isin(["delinquent", "credito_em_liquidacao"])
        exploration.update({
            "share_overall": float(expl.mean()),
            "share_in_active": float(expl[active].mean()) if active.any() else 0.0,
            "n_explored": int(expl.sum()),
            "epsilon_configured": float(cfg["actions"].get("exploration", {}).get("epsilon", 0.0)),
        })
        # discount coverage within active states: how uniformly the explored discounts
        # span [0, maxd] (min share across deciles ⇒ positivity on the discount axis)
        expd = df.loc[expl & (df["channel"] != "none"), "discount_offer"]
        if len(expd) > 50:
            bins = np.clip((expd / maxd * 10).astype(int), 0, 9)
            cov = bins.value_counts(normalize=True)
            exploration["discount_decile_min_share"] = float(cov.reindex(range(10)).fillna(0).min())
        # channel coverage among explored rows
        exploration["explored_channels"] = int(df.loc[expl, "channel"].nunique())

    metrics = {
        "n_rows": n, "config": str(config_path),
        "recovery_rate": rate, "n_channels": int(df["channel"].nunique()),
        "channel_mix_max_dev": float(mix_dev), "min_action_share": min_action_share,
        "min_stratum_action_share": min_stratum_share,
        "assignment_dependence": float(assignment_dependence),
        "assignment_dependence_by_cov": deps, "assignment_top_cov": top_cov,
        "dpd_outcome_rho": dpd_outcome_rho, "declared_channel_mix": declared,
        "observed_channel_mix": share.to_dict(), "exploration": exploration,
    }

    figures: dict[str, str] = {}
    if make_figures:
        figures = _figures(fig_dir, df, declared, share, deps, maxd, exploration)

    _write(out_path, metrics, figures)
    metrics["report_path"] = str(out_path)
    return metrics


def _figures(fig_dir, df, declared, share, deps, maxd, exploration):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)
    figs: dict[str, str] = {}

    def save(fig, name):
        fig.tight_layout(); fig.savefig(fig_dir / name, dpi=110); plt.close(fig)
        figs[name] = str((fig_dir / name).relative_to(fig_dir.parent))

    order = CHANNELS
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(order)); w = 0.4
    ax.bar(x - w / 2, [100 * share.get(c, 0) for c in order], w, label="observed", color="#2980b9")
    ax.bar(x + w / 2, [100 * declared.get(c, 0) for c in order], w, label="declared", color="#7f8c8d")
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=15); ax.set_ylabel("share (%)")
    ax.set_title("Channel mix: observed vs declared"); ax.legend()
    save(fig, "fig1_channel_mix.png")

    fig, ax = plt.subplots(figsize=(6, 4))
    items = sorted(deps.items(), key=lambda kv: kv[1])
    ax.barh([k for k, _ in items], [v for _, v in items], color="#e67e22")
    ax.set_xlabel("Cramér's V (channel ↔ covariate)")
    ax.set_title("Assignment dependence (model-free)")
    save(fig, "fig2_assignment_dependence.png")

    if exploration.get("enabled") and "is_exploration" in df:
        expl = df["is_exploration"].astype(bool)
        sub = df[df["channel"] != "none"]
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(sub.loc[~expl[sub.index], "discount_offer"], bins=20, range=(0, maxd),
                density=True, alpha=0.6, label="incumbent", color="#7f8c8d")
        ax.hist(sub.loc[expl[sub.index], "discount_offer"], bins=20, range=(0, maxd),
                density=True, alpha=0.6, label="ε-floor explored", color="#16653a")
        ax.set_xlabel("discount offered"); ax.set_ylabel("density")
        ax.set_title("Discount coverage: incumbent vs ε-floor exploration"); ax.legend()
        save(fig, "fig3_discount_coverage.png")
    return figs


def _pct(x: float) -> str:
    return f"{100 * x:.3f}%"


def _write(out_path: Path, m: dict[str, Any], figures: dict[str, str]) -> None:
    L: list[str] = []
    L.append("# Oracle-less data report\n")
    L.append(f"**Rows:** {m['n_rows']:,} loan-months · **config:** `{m['config']}`\n")
    L.append("Computed from the **public tables only** (no `oracle_truth`) — the same view a "
             "downstream consumer or the policy engine's data audit would have.\n")

    L.append("## Distribution & overlap\n")
    L.append("| metric | value | reading |")
    L.append("|---|---|---|")
    L.append(f"| recovery_rate | {_pct(m['recovery_rate'])} | realized monthly payment rate |")
    L.append(f"| n_channels | {m['n_channels']} | distinct contact channels seen |")
    L.append(f"| channel_mix_max_dev | {m['channel_mix_max_dev']:.3f} | largest gap vs declared weights |")
    L.append(f"| min_action_share | {m['min_action_share']:.4f} | rarest channel (marginal positivity) |")
    L.append(f"| min_stratum_action_share | {m['min_stratum_action_share']:.4f} | rarest channel within a dpd quartile (overlap) |")
    L.append(f"| dpd_outcome_rho | {m['dpd_outcome_rho']:+.3f} | days-overdue ↔ recovery rank corr (expect ≤0) |\n")

    L.append("## Assignment dependence (model-free)\n")
    L.append(f"`assignment_dependence` (max Cramér's V over observed covariates) = "
             f"**{m['assignment_dependence']:.3f}** (strongest: `{m['assignment_top_cov']}`). "
             f">0 means assignment is not random; the footprint of an assignment dynamic. What it "
             f"is, and whether it confounds the outcome, cannot be settled from public data alone.\n")
    L.append("| covariate | Cramér's V |")
    L.append("|---|---|")
    for c, v in sorted(m["assignment_dependence_by_cov"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {c} | {v:.3f} |")
    if figures:
        L.append(f"\n![channel mix]({figures['fig1_channel_mix.png']})")
        L.append(f"![assignment dependence]({figures['fig2_assignment_dependence.png']})\n")

    ex = m["exploration"]
    L.append("## Exploration coverage (ε-floor)\n")
    if not ex.get("enabled"):
        L.append("No exploration columns present — this dataset has no ε-floor.\n")
    else:
        L.append(f"Configured ε = **{ex['epsilon_configured']:.2f}**, applied in active states "
                 f"(delinquent + early credito_em_liquidacao).\n")
        L.append("| metric | value |")
        L.append("|---|---|")
        L.append(f"| share of rows explored (overall) | {_pct(ex['share_overall'])} |")
        L.append(f"| share explored within active states | {_pct(ex['share_in_active'])} |")
        L.append(f"| explored rows | {ex['n_explored']:,} |")
        L.append(f"| distinct channels among explored | {ex.get('explored_channels', 0)} |")
        if "discount_decile_min_share" in ex:
            L.append(f"| min discount-decile share (explored) | {ex['discount_decile_min_share']:.3f} |")
        L.append("\nExplored rows carry a **known propensity by construction** "
                 "(channel ~ Uniform over contact channels, discount ~ Uniform[0, max]); this is the "
                 "randomized subset an OPE estimator can use to identify the discount effect under "
                 "the confounded incumbent policy.\n")
        if figures and "fig3_discount_coverage.png" in figures:
            L.append(f"![discount coverage]({figures['fig3_discount_coverage.png']})\n")
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
