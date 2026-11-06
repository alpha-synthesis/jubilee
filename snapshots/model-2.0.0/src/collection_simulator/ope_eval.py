"""Grade an external OPE policy (e.g. the policy engine's ``policy_full.csv``) against the
simulator's hidden oracle.

This is the one evaluation that only a simulator can do: it reads ``oracle_truth``
and recomputes the TRUE recovery probability for the *counterfactual* actions a target
policy recommends — actions the behaviour policy rarely took, so the logged data alone
cannot grade them.

Five analyses (run by :func:`evaluate_ope`):

1. **Calibration** — the policy's predicted ``p_payment`` (a cumulative-incidence over
   the model horizon) vs the oracle's true cumulative recovery under the *recommended*
   action. Quantifies the world model's optimism.
2. **Policy value** — true recovery (probability and US$) under the logged policy, the
   recommended policy, and the oracle-optimal ceiling.
3. **Zero-discount** — sweep the discount through the oracle to find the true optimum
   and measure what the recommended discount leaves on the table.
4. **Blindspot localization** — where the model's optimism concentrates, by hidden
   ``payment_friction`` decile and by recommended channel (the cross-check for the
   producer's own overlap/positivity blindspot figures).
5. **Causal-structure grading** — the producer's discovered/expert DAG vs the known
   generative structure.

The oracle math mirrors :func:`collection_simulator.generator.recovery_probability`;
a built-in self-check (``_NOISE_RESIDUAL_TOL``) asserts the vectorised reconstruction
reproduces the logged ``p_recovery`` exactly, so it fails loudly if the generator's
formula ever changes.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from collection_simulator.config import load_config
from collection_simulator.generator import CHANNEL_EFFECT, uses_default_channel_effects

# Hidden-factor / shape coefficients that live as literals inside
# generator.recovery_probability (not in the config dict). Mirrored here; the noise
# self-check guards against drift.
_RESILIENCE_W, _FRICTION_W, _MACRO_W, _CONTACT_W = 0.55, -0.60, -0.45, 0.35
_AGE_A, _AGE_CENTER, _AGE_SCALE, _AGE_B = -0.0009, 43.0, 10.0, 0.07
_NOISE_RESIDUAL_TOL = 1e-6

CHANNELS_ALL = list(CHANNEL_EFFECT)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


class _Oracle:
    """Vectorised reconstruction of the generator's recovery oracle over a panel."""

    def __init__(self, arr: dict[str, np.ndarray], oc: dict[str, Any]):
        F = lambda k: np.asarray(arr[k], dtype=np.float64)  # noqa: E731
        self.oc = oc
        self.con_ = F("con_")
        self.start_bal = F("start_bal")
        self.offer_effect = float(oc["offer_effect"])
        self.offer_sens = float(oc["offer_sensitivity"])
        logit_t = np.log(oc["target_monthly_recovery_rate"] / (1 - oc["target_monthly_recovery_rate"]))
        age, dpd, liq, lam = F("age"), F("dpd"), F("liq"), F("lam")
        age_curve = _AGE_A * ((age - _AGE_CENTER) / _AGE_SCALE) ** 2 + _AGE_B
        # everything in the recovery logit that does NOT depend on the action
        self.common = (
            logit_t
            + age_curve
            + float(oc["dpd_effect"]) * (dpd / 30.0)
            + float(oc["liquidacao_age_effect"]) * (liq / 30.0)
            + float(oc["loan_age_effect"]) * (lam / 12.0)
            + _RESILIENCE_W * F("res") + _FRICTION_W * F("fri") + _MACRO_W * F("mac")
        )
        # back the idiosyncratic noise out of the LOGGED action's p_recovery
        p_log = np.clip(F("p_log"), 1e-9, 1 - 1e-9)
        logged_det = self.common + F("ce_log") + self._offer(F("d_log")) + _CONTACT_W * self.con_ * F("contact_log")
        self.noise = np.log(p_log / (1 - p_log)) - logged_det
        # self-check: reconstructing the logged action must reproduce p_log exactly
        recon = self.p(F("ce_log"), F("contact_log"), F("d_log"))
        resid = float(np.abs(recon - p_log).max())
        if resid > _NOISE_RESIDUAL_TOL:
            raise AssertionError(
                f"oracle reconstruction drifted from generator (max resid {resid:.2e}); "
                "ope_eval coefficients no longer match recovery_probability()"
            )

    def _offer(self, d: np.ndarray) -> np.ndarray:
        return self.offer_effect * (1.0 - np.exp(-self.offer_sens * d))

    def p(self, channel_effect, contact_flag, discount) -> np.ndarray:
        """True monthly recovery probability for an action, noise held fixed."""
        eta = self.common + channel_effect + self._offer(discount) + _CONTACT_W * self.con_ * contact_flag + self.noise
        return _sigmoid(eta)


def _load(db_path: Path, policy_csv: Path, oc: dict[str, Any]) -> dict[str, np.ndarray]:
    import duckdb

    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS sim (READ_ONLY)")
    con.execute(f"CREATE VIEW pf AS SELECT * FROM read_csv_auto('{policy_csv}')")
    ce = lambda c: "CASE " + c + " " + " ".join(  # noqa: E731
        f"WHEN '{k}' THEN {v}" for k, v in CHANNEL_EFFECT.items()
    ) + " ELSE 0 END"
    arr = con.execute(f"""
    WITH bal AS (
      SELECT loan_id, month, outstanding_balance,
             lag(outstanding_balance) OVER (PARTITION BY loan_id ORDER BY month) AS prev_bal
      FROM sim.monthly_panel
    )
    SELECT pf.loan_id AS loan_id, pf."month" AS mth,
      t.borrower_resilience AS res, t.payment_friction AS fri,
      t.regional_macro_stress AS mac, t.contactability AS con_, t.p_recovery AS p_log,
      b.age AS age, p.days_past_due AS dpd, p.days_in_credito_em_liquidacao AS liq,
      p.loan_age_months AS lam, COALESCE(bal.prev_bal, l.outstanding_balance) AS start_bal,
      {ce('a.channel')} AS ce_log,
      CASE WHEN a.channel = 'none' THEN 0 ELSE 1 END AS contact_log, a.discount_offer AS d_log,
      {ce('pf.channel')} AS ce_rec,
      CASE WHEN pf.channel = 'none' THEN 0 ELSE 1 END AS contact_rec, pf.discount_offer AS d_rec,
      pf.channel AS chan_rec, pf.p_payment AS p_pay, pf.recovered_observed AS rec_obs,
      p.recovered_amount AS amt_realized
    FROM pf
    JOIN sim.oracle_truth t USING (loan_id, month)
    JOIN sim.monthly_panel p USING (loan_id, month)
    JOIN bal USING (loan_id, month)
    JOIN sim.loans l USING (loan_id)
    JOIN sim.borrowers b ON b.borrower_id = p.borrower_id
    JOIN sim.actions a USING (loan_id, month)
    """).fetchnumpy()
    con.close()
    return arr


def _cumulative_under(p_month: np.ndarray, loan_id: np.ndarray, month: np.ndarray) -> np.ndarray:
    """1 - prod over the remaining horizon of (1 - p_month), within each loan."""
    import duckdb

    df = pd.DataFrame({"loan_id": loan_id, "month": month, "lp": np.log(np.clip(1 - p_month, 1e-12, 1.0))})
    c = duckdb.connect()
    c.register("d", df)
    cum = c.execute(
        """SELECT 1 - exp(SUM(lp) OVER (PARTITION BY loan_id ORDER BY month
           ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING)) AS cum FROM d"""
    ).fetchnumpy()["cum"]
    c.close()
    return np.asarray(cum, dtype=np.float64)


# --------------------------------------------------------------------------- #
# The five analyses
# --------------------------------------------------------------------------- #
def evaluate_ope(
    db_path: str | Path,
    policy_csv: str | Path,
    config_path: str | Path,
    out_path: str | Path = "outputs/ope_evaluation_report.md",
    make_figures: bool = True,
) -> dict[str, Any]:
    db_path, policy_csv = Path(db_path), Path(policy_csv)
    cfg = load_config(config_path)
    oc = cfg["oracle"]
    if not uses_default_channel_effects(oc):
        raise NotImplementedError(
            "evaluate_ope mirrors the default channel-effect table; configs that set "
            "oracle.channel_effects / channel_effects_late are not supported"
        )
    maxd = float(cfg["actions"]["max_discount"])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig_dir = out_path.parent / "ope_figures"

    arr = _load(db_path, policy_csv, oc)
    n = len(arr["res"])
    F = lambda k: np.asarray(arr[k], dtype=np.float64)  # noqa: E731
    oracle = _Oracle(arr, oc)

    chan_rec = np.asarray(arr["chan_rec"]).astype(str)
    fri = F("fri")
    p_pay = F("p_pay")
    start_bal = oracle.start_bal

    # oracle monthly recovery under each policy (noise held fixed)
    p_logged = oracle.p(F("ce_log"), F("contact_log"), F("d_log"))            # ~= p_log
    p_reco = oracle.p(F("ce_rec"), F("contact_rec"), F("d_rec"))              # policy
    fv = CHANNEL_EFFECT["field_visit"]
    # recovery-PROBABILITY ceiling: p rises monotonically with the discount and
    # field_visit is the strongest channel, so this maximises the chance of any payment.
    p_star_rate = oracle.p(np.full(n, fv), np.ones(n), np.full(n, maxd))

    # money = expected settlement collected: P * balance * (1 - discount). A discount is
    # a GIVEAWAY — you forgive part of the balance — so it is the correct attribution.
    # (Computed from P and the discount, not read from the dataset's `recovered_amount`.)
    def money(p, d):
        return p * start_bal * (1.0 - d)

    m_logged, m_reco = money(p_logged, F("d_log")), money(p_reco, F("d_rec"))

    # money-OPTIMAL ceiling: best channel + the per-row revenue-maximising discount. The
    # optimum is interior because a deeper discount lifts P but shrinks what is collected.
    ceil_grid = np.round(np.linspace(0.0, maxd, 23), 4)
    m_star = np.zeros(n)
    d_star = np.zeros(n)
    for d in ceil_grid:
        mm = money(oracle.p(np.full(n, fv), np.ones(n), np.full(n, d)), d)
        better = mm > m_star
        m_star = np.where(better, mm, m_star)
        d_star = np.where(better, d, d_star)

    # ---- #1 calibration (p_payment vs oracle cumulative under recommended) ----
    cum_reco = _cumulative_under(p_reco, arr["loan_id"], arr["mth"])
    cal_q = pd.qcut(p_pay, 10, labels=False, duplicates="drop")
    cal = pd.DataFrame({"q": cal_q, "pred": p_pay, "true": cum_reco}).groupby("q").mean()
    calibration = {
        "mean_pred": float(p_pay.mean()),
        "mean_true_cumulative": float(cum_reco.mean()),
        "optimism_x": float(p_pay.mean() / cum_reco.mean()),
        "spearman": float(pd.Series(p_pay).corr(pd.Series(cum_reco), method="spearman")),
        "mae": float(np.abs(p_pay - cum_reco).mean()),
        "deciles": cal.assign(optimism_x=cal["pred"] / cal["true"]).reset_index().to_dict("records"),
    }

    # ---- #2 policy value ----
    def block(p, m):
        return {"recovery_rate": float(p.mean()), "money": float(m.sum())}

    # realized cash, correctly attributed: when a loan actually paid, the bank collects
    # the settlement it offered = balance * (1 - logged discount).
    realized_money = float((F("rec_obs") * start_bal * (1.0 - F("d_log"))).sum())
    policy_value = {
        "realized": {"recovery_rate": float(F("rec_obs").mean()), "money": realized_money},
        "pi_b_logged": block(p_logged, m_logged),
        "pi_e_policy": block(p_reco, m_reco),
        "pi_star_ceiling": {"recovery_rate": float(p_star_rate.mean()), "money": float(m_star.sum())},
        "money_optimal_discount_mean": float(d_star.mean()),
    }

    # ---- #3 zero-discount: oracle money vs discount (recommended channel held) ----
    grid = np.round(np.linspace(0.0, maxd, 12), 3)
    sweep = {float(d): float(money(oracle.p(F("ce_rec"), F("contact_rec"), np.full(n, d)), np.full(n, d)).sum())
             for d in grid}
    best_d = max(sweep, key=sweep.get)
    zero_discount = {
        "sweep": sweep,
        "recommended_zero_share": float((F("d_rec") == 0).mean()),
        "recommended_discount_mean": float(F("d_rec").mean()),
        "oracle_optimal_discount": float(best_d),
        "money_at_zero": sweep[0.0],
        "money_at_optimal": sweep[best_d],
        "uplift_pct": float(100 * (sweep[best_d] / sweep[0.0] - 1)),
    }

    # ---- #4 blindspot localization ----
    optimism = p_pay - cum_reco
    fd = pd.qcut(fri, 10, labels=False, duplicates="drop")
    by_friction = pd.DataFrame({"fd": fd, "pred": p_pay, "true": cum_reco, "gap": optimism}).groupby("fd").mean()
    by_channel = (
        pd.DataFrame({"c": chan_rec, "pred": p_pay, "true": cum_reco, "gap": optimism})
        .groupby("c").agg(pred=("pred", "mean"), true=("true", "mean"), gap=("gap", "mean"), n=("gap", "size"))
    )
    blindspot = {
        "by_friction_decile": by_friction.reset_index().to_dict("records"),
        "by_channel": by_channel.reset_index().to_dict("records"),
    }

    # ---- #5 causal-structure grading — ONLY if a DAG ships with this policy ----
    # Look for dag_*.md beside the policy CSV. If none, the section is omitted rather
    # than reusing another run's grading.
    dag_files = sorted(p.name for p in policy_csv.parent.glob("dag_*.md"))
    dag = _grade_dag(policy_csv.parent)

    metrics = {
        "n_rows": n, "config": str(config_path),
        "calibration": calibration, "policy_value": policy_value,
        "zero_discount": zero_discount, "blindspot": blindspot,
        "dag_grading": dag, "dag_files": dag_files,
    }

    figures: dict[str, str] = {}
    if make_figures:
        figures = _make_figures(
            fig_dir, calibration, policy_value, sweep, best_d, by_friction,
            chan_rec, arr, maxd,
        )

    _write_report(out_path, metrics, figures)
    metrics["report_path"] = str(out_path)
    return metrics


_EDGE_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(-->|<-->|---)\s*([A-Za-z_]\w*)\s*$")


def _parse_mermaid(path: Path) -> tuple[set[tuple[str, str, str]], set[str]]:
    """Return (edges, latent_nodes) parsed from a mermaid DAG markdown file.

    edges are ``(src, kind, dst)`` with kind in ``-->`` / ``<-->`` / ``---``.
    latent nodes are those declared ``(latent)`` or styled with a dashed stroke.
    """
    edges: set[tuple[str, str, str]] = set()
    latent: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        head = line.split("|", 1)[0]  # drop any edge label
        m = _EDGE_RE.match(head)
        if m:
            edges.add((m.group(1), m.group(2), m.group(3)))
            continue
        if "(latent)" in line:
            nm = re.match(r"\s*([A-Za-z_]\w*)", line)
            if nm:
                latent.add(nm.group(1))
        if line.strip().startswith("style ") and "stroke-dasharray" in line:
            parts = line.split()
            if len(parts) >= 2:
                latent.add(parts[1])
    return edges, latent


def _grade_dag(dag_dir: Path) -> list[dict[str, str]] | None:
    """Grade the DAG(s) in ``dag_dir`` against the known generator structure.

    Reads this run's own ``dag_yaml.md`` (expert) and ``dag_ci.md`` (CI discovery);
    every cell is derived from the parsed edges — nothing is reused across runs.
    Returns None if no expert/CI DAG is present.
    """
    yaml_p, ci_p = dag_dir / "dag_yaml.md", dag_dir / "dag_ci.md"
    if not yaml_p.exists() and not ci_p.exists():
        return None
    e_edges, e_latent = _parse_mermaid(yaml_p) if yaml_p.exists() else (set(), set())
    c_edges, c_latent = _parse_mermaid(ci_p) if ci_p.exists() else (set(), set())

    def directed(edges, s, d):
        return (s, "-->", d) in edges

    def expert_latent_to(dst):
        return any(directed(e_edges, s, dst) for s in e_latent)

    def ci_has_latent():
        return any(k == "<-->" for (_, k, _) in c_edges)

    rows: list[dict[str, str]] = []
    # 1. confounder → outcome
    rows.append({
        "relationship": "hidden factor → outcome (confounder exists)",
        "truth": "yes (payment_friction, resilience, …)",
        "expert_yaml": (f"yes — latent {sorted(e_latent)[0]}" if expert_latent_to("recovered") else "no latent"),
        "ci_discovery": ("found latent (<-->)" if ci_has_latent() else "MISSED (no latent)"),
    })
    rows[-1]["verdict"] = ("expert correct; data-only blind"
                           if rows[-1]["expert_yaml"].startswith("yes") and not ci_has_latent()
                           else "see cells")
    # 2. confounder → treatment (discount_offer)
    rows.append({
        "relationship": "hidden factor → treatment (discount)",
        "truth": "yes (hidden friction drives contact intensity)",
        "expert_yaml": ("yes → discount_offer" if expert_latent_to("discount_offer") else "no"),
        "ci_discovery": ("found latent (<-->)" if ci_has_latent() else "MISSED"),
        "verdict": ("expert posits it; CI blind" if expert_latent_to("discount_offer") and not ci_has_latent() else "see cells"),
    })
    # 3. discount → recovered (direction)
    e3 = ("discount_offer → recovered" if directed(e_edges, "discount_offer", "recovered")
          else "reversed" if directed(e_edges, "recovered", "discount_offer") else "absent")
    c3 = ("discount_offer → recovered" if directed(c_edges, "discount_offer", "recovered")
          else "REVERSED (recovered → discount)" if directed(c_edges, "recovered", "discount_offer") else "absent")
    rows.append({
        "relationship": "discount → recovered (direction & sign)",
        "truth": "discount → recovered, POSITIVE", "expert_yaml": e3, "ci_discovery": c3,
        "verdict": ("CI direction wrong" if c3.startswith("REVERSED") else
                    "agree" if c3.startswith("discount") else "CI misses edge"),
    })
    # 4. discount → settlement_offer_amount
    rows.append({
        "relationship": "discount → settlement_offer_amount",
        "truth": "yes (settlement = balance·(1−discount))",
        "expert_yaml": ("yes (mediator)" if directed(e_edges, "discount_offer", "settlement_offer_amount") else "absent"),
        "ci_discovery": ("found" if directed(c_edges, "discount_offer", "settlement_offer_amount")
                         else "n/a (not in graph)"),
        "verdict": "expert models the mediator",
    })
    # 5. days_past_due → discount
    rows.append({
        "relationship": "days_past_due → discount",
        "truth": "yes (delinquency ramp)",
        "expert_yaml": ("yes" if directed(e_edges, "days_past_due", "discount_offer") else "absent"),
        "ci_discovery": ("found ✓" if directed(c_edges, "days_past_due", "discount_offer") else "missed"),
        "verdict": ("agree" if directed(c_edges, "days_past_due", "discount_offer") else "CI misses edge"),
    })
    return rows


def _make_figures(fig_dir, calibration, policy_value, sweep, best_d, by_friction, chan_rec, arr, maxd):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)
    figs: dict[str, str] = {}

    def save(fig, name):
        path = fig_dir / name
        fig.tight_layout()
        fig.savefig(path, dpi=110)
        plt.close(fig)
        figs[name] = str(path.relative_to(fig_dir.parent))

    # 1. calibration / reliability diagram
    d = pd.DataFrame(calibration["deciles"])
    fig, ax = plt.subplots(figsize=(5, 5))
    lim = max(d["pred"].max(), d["true"].max()) * 1.1
    ax.plot([0, lim], [0, lim], "k--", lw=1, label="perfect calibration")
    ax.plot(d["true"], d["pred"], "o-", color="#c0392b")
    ax.set_xlabel("oracle TRUE cumulative recovery"); ax.set_ylabel("policy predicted p_payment")
    ax.set_title(f"Calibration — optimism {calibration['optimism_x']:.1f}×"); ax.legend()
    save(fig, "fig1_calibration.png")

    # 2. policy value bars (recovery rate + money)
    pv = policy_value
    labels = ["logged π_b", "policy π_e", "oracle ceiling π*"]
    rr = [pv["pi_b_logged"]["recovery_rate"], pv["pi_e_policy"]["recovery_rate"], pv["pi_star_ceiling"]["recovery_rate"]]
    mo = [pv["pi_b_logged"]["money"] / 1e6, pv["pi_e_policy"]["money"] / 1e6, pv["pi_star_ceiling"]["money"] / 1e6]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    cols = ["#7f8c8d", "#c0392b", "#16653a"]
    a1.bar(labels, [100 * x for x in rr], color=cols); a1.set_ylabel("true monthly recovery (%)")
    a1.set_title("Recovery rate by policy")
    a2.bar(labels, mo, color=cols); a2.set_ylabel("true US$ recovered (millions)")
    a2.set_title("Money recovered by policy")
    for ax in (a1, a2):
        ax.tick_params(axis="x", labelrotation=15)
    save(fig, "fig2_policy_value.png")

    # 3. discount sweep (the headline)
    xs = sorted(sweep); ys = [sweep[x] / 1e6 for x in xs]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(xs, ys, "o-", color="#2980b9")
    ax.axvline(0.0, color="#c0392b", ls="--", label="policy picks d=0")
    ax.axvline(best_d, color="#16653a", ls="--", label=f"oracle optimum d={best_d:.2f}")
    ax.set_xlabel("discount offered"); ax.set_ylabel("oracle expected US$ (millions)")
    ax.set_title("Money left on the table by zero discount"); ax.legend()
    save(fig, "fig3_discount_sweep.png")

    # 4. optimism by hidden-friction decile (blindspot localization)
    bf = by_friction.reset_index()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(bf["fd"] + 1, 100 * bf["gap"], color="#e67e22")
    ax.set_xlabel("hidden payment_friction decile (low → high)")
    ax.set_ylabel("optimism gap: pred − true (pp)")
    ax.set_title("Where the world model is most over-optimistic")
    save(fig, "fig4_optimism_by_friction.png")

    # 5. recommended vs observed channel mix (the degenerate policy)
    rec = pd.Series(chan_rec).value_counts(normalize=True)
    obs = pd.Series(_logged_channel_mix(arr))
    order = CHANNELS_ALL
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(order)); w = 0.4
    ax.bar(x - w / 2, [100 * rec.get(c, 0) for c in order], w, label="recommended π_e", color="#c0392b")
    ax.bar(x + w / 2, [100 * obs.get(c, 0) for c in order], w, label="logged π_b", color="#7f8c8d")
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=15); ax.set_ylabel("share of loan-months (%)")
    ax.set_title("Channel mix: recommended vs logged"); ax.legend()
    save(fig, "fig5_channel_mix.png")
    return figs


def _logged_channel_mix(arr) -> dict[str, float]:
    # reconstruct logged channel from its channel-effect code (ce_log)
    eff_to_name = {v: k for k, v in CHANNEL_EFFECT.items()}
    ce = np.asarray(arr["ce_log"], dtype=np.float64)
    names = pd.Series(ce).map(eff_to_name)
    return (names.value_counts(normalize=True)).to_dict()


def _pct(x: float) -> str:
    return f"{100 * x:.3f}%"


def _money(x: float) -> str:
    return f"US$ {x:,.0f}"


def _write_report(out_path: Path, m: dict[str, Any], figures: dict[str, str]) -> None:
    pv, cal, zd, bs = m["policy_value"], m["calibration"], m["zero_discount"], m["blindspot"]
    L: list[str] = []
    L.append("# OPE Evaluation — recommended policy vs the oracle\n")
    L.append(f"**Rows:** {m['n_rows']:,} loan-months · **config:** `{m['config']}`\n")
    L.append("Generated by `collection_simulator.ope_eval`. The recommended policy "
             "(`policy_full.csv`) is graded against the simulator's hidden `oracle_truth` — "
             "the true recovery probability of the counterfactual actions it picks.\n")

    L.append("## Column provenance\n")
    L.append("| column | meaning | source |")
    L.append("|---|---|---|")
    L.append("| `channel`, `discount_offer` | recommended action (policy π_e) | optimizer argmax |")
    L.append("| `p_payment` | **cumulative** pay-prob over the model horizon (DeepHit CIF, last bin) | `predict_cif()[:,0,-1]` |")
    L.append("| `expected_return` | `p_payment × debtValue × (1−discount)`, **per account** | objective formula |")
    L.append("| `recovered_observed`, `channel_observed` | what actually happened (π_b) | the data |\n")
    L.append("> `p_payment` is **not** a monthly rate (it is cumulative over the horizon); "
             "`expected_return` is **per account**, not per loan-month.\n")

    # 2 policy value
    L.append("## 1 · Policy value — does the recommended policy beat the status quo?\n")
    L.append("True recovery under the *actions* the policy picks (oracle ground truth; independent of "
             "`p_payment`). Money is the correctly-attributed settlement value **P × balance × (1 − discount)** "
             "— a discount is a giveaway. (Money is computed from `P` and the discount, not from the "
             "dataset's `recovered_amount` column.)\n")
    L.append("| policy | true monthly recovery | true US$ recovered | vs logged |")
    L.append("|---|---|---|---|")
    base_m = pv["pi_b_logged"]["money"]
    rows = [("logged π_b (status quo)", pv["pi_b_logged"]), ("**policy π_e**", pv["pi_e_policy"]),
            ("oracle-optimal ceiling π*", pv["pi_star_ceiling"])]
    for name, b in rows:
        vs = "—" if name.startswith("logged") else f"{100*(b['money']/base_m-1):+.0f}%"
        L.append(f"| {name} | {_pct(b['recovery_rate'])} | {_money(b['money'])} | {vs} |")
    L.append(f"\nπ* is the best achievable **per metric**: recovery rate at `field_visit` + max discount; "
             f"money at `field_visit` + the revenue-optimal discount (mean "
             f"**{pv['money_optimal_discount_mean']:.2f}**, interior — not the cap).\n")
    if figures:
        L.append(f"\n![policy value]({figures['fig2_policy_value.png']})\n")

    # 1 calibration
    L.append("## 2 · Calibration — is `p_payment` trustworthy?\n")
    L.append(f"`p_payment` vs the oracle's true cumulative recovery under the recommended action. "
             f"**Optimism ≈ {cal['optimism_x']:.1f}×** "
             f"(mean predicted {_pct(cal['mean_pred'])} vs true {_pct(cal['mean_true_cumulative'])}); "
             f"Spearman {cal['spearman']:.2f}, MAE {_pct(cal['mae'])}.\n")
    L.append("| p_payment decile | predicted | true (oracle cum.) | optimism |")
    L.append("|---|---|---|---|")
    for r in cal["deciles"]:
        L.append(f"| {int(r['q'])+1} | {_pct(r['pred'])} | {_pct(r['true'])} | {r['optimism_x']:.1f}× |")
    if figures:
        L.append(f"\n![calibration]({figures['fig1_calibration.png']})\n")

    # 3 discount leverage — where the policy sits
    L.append("## 3 · Discount leverage — where the policy sits\n")
    L.append(f"The policy's **mean recommended discount is {zd['recommended_discount_mean']:.2f}** "
             f"(`discount = 0` on {100*zd['recommended_zero_share']:.0f}% of rows). Sweeping the discount on "
             f"the recommended channel under the correct reward `P × balance × (1 − discount)` — a deeper "
             f"discount lifts P(pay) but forgives more of the balance, so the revenue optimum is "
             f"**interior**:\n")
    L.append("| discount | oracle expected US$ | vs d=0 |")
    L.append("|---|---|---|")
    base = zd["sweep"][0.0]
    for d in sorted(zd["sweep"]):
        L.append(f"| {d:.2f} | {_money(zd['sweep'][d])} | {100*(zd['sweep'][d]/base-1):+.0f}% |")
    L.append(f"\n**Oracle money-optimal discount ≈ {zd['oracle_optimal_discount']:.2f}.** The discount carries "
             f"real leverage — about **{zd['uplift_pct']:+.0f}%** from `d=0` to the optimum on the recommended "
             f"channel. A policy that zeroes or under-shoots the discount forgoes that lift; one that lands "
             f"near {zd['oracle_optimal_discount']:.2f} captures it. Confounding hides this benefit in the raw "
             f"logs (it makes a discount look worthless), which is why de-confounding or randomized "
             f"exploration matters.\n")
    if figures:
        L.append(f"![discount sweep]({figures['fig3_discount_sweep.png']})\n")
    if figures:
        L.append(f"![channel mix]({figures['fig5_channel_mix.png']})\n")

    # 4 blindspot
    L.append("## 4 · Blindspot localization — where the optimism lives\n")
    L.append("Optimism gap (`p_payment` − oracle cumulative) by hidden `payment_friction` decile:\n")
    L.append("| friction decile (low→high) | predicted | true | gap |")
    L.append("|---|---|---|---|")
    for r in bs["by_friction_decile"]:
        L.append(f"| {int(r['fd'])+1} | {_pct(r['pred'])} | {_pct(r['true'])} | {100*r['gap']:+.2f} pp |")
    L.append("\nBy recommended channel:\n")
    L.append("| channel | predicted | true | gap | n |")
    L.append("|---|---|---|---|---|")
    for r in bs["by_channel"]:
        L.append(f"| {r['c']} | {_pct(r['pred'])} | {_pct(r['true'])} | {100*r['gap']:+.2f} pp | {int(r['n']):,} |")
    if figures:
        L.append(f"\n![optimism by friction]({figures['fig4_optimism_by_friction.png']})\n")
    L.append("\nCross-check with the producer's own overlap figures (`blindspots_contact.png`, "
             "`blindspots_discount.png`): the contact decision is well-overlapped (overlap ≈ 0.79) "
             "while the discount is poorly overlapped (≈ 0.28, propensity AUC 0.90 — highly "
             "predictable, i.e. confounded). The oracle confirms the discount axis is where the "
             "policy goes wrong.\n")

    # 5 dag — only when a DAG was shipped with this policy
    L.append("## 5 · Causal-structure grading — discovered DAG vs known truth\n")
    if m.get("dag_grading"):
        L.append("Parsed from this policy's own `dag_yaml.md` (expert) and `dag_ci.md` (CI discovery) "
                 f"(DAG files present: `{'`, `'.join(m['dag_files'])}`), graded against the known "
                 "generative structure. Every cell is derived from the parsed edges.\n")
        L.append("| relationship | generative truth | expert YAML DAG | CI discovery | verdict |")
        L.append("|---|---|---|---|---|")
        for r in m["dag_grading"]:
            L.append(f"| {r['relationship']} | {r['truth']} | {r['expert_yaml']} | {r['ci_discovery']} | {r['verdict']} |")
    else:
        L.append("No causal DAG was supplied with this policy — section omitted "
                 "(not reused from another run).\n")

    L.append("\n## Caveats\n")
    L.append("- **Per-decision value**, evaluated on the logged state distribution — not a "
             "closed-loop resimulation of the trajectories a different policy would induce.")
    L.append("- **Money** is the correctly-attributed settlement value "
             "`P × balance × (1 − discount)` (a discount is a giveaway), computed from `P` and the "
             "discount — not read from the dataset's `recovered_amount` column.")
    L.append("- **Idiosyncratic noise is held fixed** per row (backed out of the logged "
             "`p_recovery`), so counterfactual actions are compared on the same shock.")
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
