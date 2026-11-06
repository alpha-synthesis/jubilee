"""Core synthetic data generation.

Random streams (generator version 2, ``keyed-streams-v2``)
----------------------------------------------------------
Every source of randomness has its own generator, keyed through
:class:`numpy.random.SeedSequence` by ``(seed, role, replicate, batch)``:

* ``regional``   — the per-region macro shock, keyed by ``seed`` only, so every
  population replicate of a world shares the same shock vector;
* ``population`` — borrower demographics and loan contracts;
* ``latent``     — the hidden borrower factors (standard normals scaled by the
  confounding strength);
* ``actions``    — the behaviour policy's randomisation, including ε exploration;
* ``outcomes``   — outcome noise, recovery / charge-off draws and one Beta slot
  per (loan, month) that model 2.0.0 used for the paid share. Model 2.1.0 still
  draws that slot, so the stream layout is unchanged, but no longer reads it.

Action and outcome randomness is drawn for every (loan, month) slot when a batch
starts, before any loan is stepped. Consequences, all covered by tests:

* For a fixed config, ``seed``, ``replicate`` and batch size, borrowers, loans,
  hidden factors and regional shocks are identical under every policy, every
  exploration rate and either assignment mode. A policy can no longer change the
  population of later batches by consuming a different number of draws.
* Two policies use the same uniform and normal draws at a (loan, month) slot that
  both reach. Trajectories still diverge as soon as the actions differ, so a twin
  world is a coupled realisation of the same population, not a replay of the
  logged world and not its exact counterfactual.
* Different ``replicate`` indices give independent populations, actions and
  outcomes under the same regional shocks (independent Monte-Carlo replicates of
  one world).
* The population depends on the batch size: the batch size is part of the
  reproduction configuration.

Generator version 1 used one stream for everything; with batch streaming its
populations agreed across policies in the first batch only. It produced the
archived 190-run campaign and is preserved as a source snapshot, not as a runtime
option.

Model versions (``GENERATOR_VERSION``) and the random-stream scheme
(``RNG_SCHEME``) are versioned separately:

* 2.0.0 (``keyed-streams-v2``) — a recovering borrower paid the settlement
  times a random share ``min(1, 0.7 + Beta(2, 5))``; the payment was subtracted
  from the balance, and the loan returned to ``performing`` unless the balance
  fell below ``max(50, 0.05 × principal)``. Source snapshot:
  :mod:`collection_simulator.legacy.generator_2_0_0`.
* 2.1.0 (``keyed-streams-v2``, current) — full settlement: when a loan
  recovers in month t the borrower pays the whole offer
  ``S_t = round(B_t × (1 − d_t), 2)`` on the balance ``B_t`` just before the
  payment, the discounted remainder is written off, the balance becomes 0 and
  the loan ends in the terminal state ``cured``: no later rows, contacts,
  accrual or payments. Recovery and charge-off probabilities, balance accrual
  before the payment, policies, populations and every random draw are those of
  2.0.0. Until a loan's first recovery the two models step it identically.

The evaluation score of :func:`simulate_cohort` and
``ope_bench.panel.load_cohort`` is unchanged by the model version:
``1{first recovery in months 0..h-1} × B0 × (1 − d0)`` with the month-0
balance ``B0`` and discount ``d0`` (``SCORE_DEFINITION``). It is a synthetic
score, not the cash collected: the collected cash is ``recovered_amount``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from collection_simulator.dictionaries import (
    ALLOWED_STATES,
    CHANNELS,
    GENDERS,
    INCOME_BANDS,
    LOCATIONS,
    PRODUCTS,
    TERMINAL_STATES,
)
from collection_simulator.storage import SimulationResult

GENERATOR_VERSION = "2.1.0"  # model version (see the module docstring)
RNG_SCHEME = "keyed-streams-v2"  # random-stream layout, unchanged since 2.0.0
SETTLEMENT_RULE = "full-settlement"  # 2.0.0: "partial-share-with-continuation"
SCORE_DEFINITION = "1{first recovery in months 0..h-1} * B0 * (1 - d0)"
# The cash a cohort loan pays inside the window (``recovered_amount`` summed over
# months 0..h-1). Under full settlement (2.1.0) at most one payment occurs: the
# whole offer S_t on the balance just before it, so the cash carries the
# discount and the balance accrual of the month of recovery, not of month 0.
CASH_DEFINITION = "sum of recovered_amount over months 0..h-1"

# Stream roles: the integers are part of the stream keys — never renumber them.
# Roles >= 16 are reserved for consumers outside the generator (annotator,
# bootstrap, cross-fitting folds, ...), see :func:`derived_seed`.
ROLE_REGIONAL = 0
ROLE_POPULATION = 1
ROLE_LATENT = 2
ROLE_ACTIONS = 3
ROLE_OUTCOMES = 4

# Per-(loan, month) action uniforms: exploration coin, exploration channel,
# exploration discount, incumbent channel. (The incumbent discount uses a Beta draw.)
_N_ACTION_UNIFORMS = 4

# Delinquency stage boundary used by stage-dependent channel effects (DPD >= 90 is
# the ``credito_em_liquidacao`` stage).
LATE_STAGE_DPD = 90


def stream(seed: int, *key: int) -> np.random.Generator:
    """Independent generator for the key ``(seed, *key)``."""
    ss = np.random.SeedSequence(int(seed), spawn_key=tuple(int(k) for k in key))
    return np.random.Generator(np.random.PCG64(ss))


def derived_seed(seed: int, *key: int) -> int:
    """Deterministic integer seed for a consumer outside the generator."""
    ss = np.random.SeedSequence(int(seed), spawn_key=tuple(int(k) for k in key))
    return int(ss.generate_state(1, dtype=np.uint64)[0])


def _logit(p: float) -> float:
    p = min(max(float(p), 1e-6), 1.0 - 1e-6)
    return log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = exp(-x)
        return 1.0 / (1.0 + z)
    z = exp(x)
    return z / (1.0 + z)


def _weighted_choice(rng: np.random.Generator, records: list[dict[str, Any]], key: str, n: int):
    weights = np.asarray([float(r.get("weight", 1.0)) for r in records], dtype=float)
    weights = weights / weights.sum()
    idx = rng.choice(len(records), size=n, p=weights)
    return [records[i][key] for i in idx], idx


@dataclass(frozen=True)
class RecoveryInputs:
    channel: str
    discount_offer: float
    age: int
    loan_age_months: int
    days_past_due: int
    days_in_credito_em_liquidacao: int
    borrower_resilience: float
    payment_friction: float
    regional_macro_stress: float
    contactability: float
    noise: float = 0.0


CHANNEL_EFFECT = {
    "none": -0.85,
    "sms": 0.10,
    "app_message": 0.18,
    "phone": 0.35,
    "field_visit": 0.48,
}


def channel_effect(oracle_cfg: dict[str, Any], channel: str, days_past_due: int) -> float:
    """Log-odds effect of ``channel`` at the given delinquency.

    ``oracle.channel_effects`` (optional) replaces :data:`CHANNEL_EFFECT`;
    ``oracle.channel_effects_late`` (optional) applies from
    :data:`LATE_STAGE_DPD` days past due on. Both absent → the default table at
    every stage (the original mechanism).
    """
    table = oracle_cfg.get("channel_effects") or CHANNEL_EFFECT
    late = oracle_cfg.get("channel_effects_late")
    if late and days_past_due >= LATE_STAGE_DPD:
        table = late
    return float(table.get(channel, 0.0))


def uses_default_channel_effects(oracle_cfg: dict[str, Any]) -> bool:
    """True when the config does not change the channel-effect mechanism."""
    table = oracle_cfg.get("channel_effects")
    late = oracle_cfg.get("channel_effects_late")
    same = table is None or {k: float(v) for k, v in table.items()} == CHANNEL_EFFECT
    return same and not late


def recovery_probability(inputs: RecoveryInputs, oracle_cfg: dict[str, Any]) -> float:
    """True monthly recovery probability used by the simulator."""
    target = float(oracle_cfg["target_monthly_recovery_rate"])
    offer = float(oracle_cfg["offer_effect"]) * (
        1.0 - exp(-float(oracle_cfg["offer_sensitivity"]) * inputs.discount_offer)
    )
    age_curve = -0.0009 * ((inputs.age - 43) / 10.0) ** 2 + 0.07
    dpd = float(oracle_cfg["dpd_effect"]) * (inputs.days_past_due / 30.0)
    liq = float(oracle_cfg["liquidacao_age_effect"]) * (
        inputs.days_in_credito_em_liquidacao / 30.0
    )
    loan_age = float(oracle_cfg["loan_age_effect"]) * (inputs.loan_age_months / 12.0)
    hidden = (
        0.55 * inputs.borrower_resilience
        - 0.60 * inputs.payment_friction
        - 0.45 * inputs.regional_macro_stress
        + (0.35 * inputs.contactability if inputs.channel != "none" else 0.0)
    )
    logit = (
        _logit(target)
        + channel_effect(oracle_cfg, inputs.channel, inputs.days_past_due)
        + offer
        + age_curve
        + dpd
        + liq
        + loan_age
        + hidden
        + inputs.noise
    )
    return _sigmoid(logit)


def regional_shocks(config: dict[str, Any]) -> dict[str, float]:
    """Per-region macro shock of the world ``config['seed']`` (shared by replicates)."""
    strength = float(config["oracle"]["hidden_confounding_strength"])
    z = stream(int(config["seed"]), ROLE_REGIONAL).standard_normal(len(LOCATIONS))
    return {loc["uf"]: float(0.45 * strength * zi) for loc, zi in zip(LOCATIONS, z, strict=True)}


def generate(
    config: dict[str, Any],
    out_dir: str | Path,
    batch_size: int | None = None,
    policy: Any | None = None,
    replicate: int = 0,
) -> SimulationResult:
    """Generate a DuckDB-backed synthetic collection dataset.

    ``policy`` (optional) injects a TARGET policy in place of the incumbent+ε
    assignment: a callable receiving the observable loan-month state as
    keyword arguments (``month, state, days_past_due,
    days_in_credito_em_liquidacao, outstanding_balance, loan_age_months,
    remaining_maturity_months, contacts_last_3m``) and returning
    ``(channel, discount)``, or ``None`` to fall through to the incumbent+ε
    assignment. With the same config, seed, replicate and batch size, the
    policy-injected run has the same borrowers, loans, hidden factors, regional
    shocks and per-(loan, month) random draws as the run without it; the
    outcome trajectories differ once the actions differ.

    ``replicate`` selects an independent population of the same world: same
    regional shocks, independent borrowers, loans, hidden factors, actions and
    outcomes (see the module docstring).

    Borrowers are produced in batches and each batch's rows are appended to the
    DuckDB before the next is built, so peak memory tracks a single batch:

    * ``None`` — one batch over the whole population; the in-memory tables are also
      returned in ``SimulationResult.tables`` (what small callers/tests rely on).
    * an int — stream in batches of that many borrowers; ``tables`` is left empty —
      read from the returned ``db_path``. The batch size is part of the
      reproduction configuration: a different batch size gives a different
      population. ``None`` equals any batch size at least as large as the
      population.
    """
    import duckdb

    _validate_assignment(config)
    _validate_channel_effects(config)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = int(config["population"]["borrowers"])
    streaming = batch_size is not None
    step = total if not streaming else int(batch_size)
    regional = regional_shocks(config)

    db_path = out_dir / "sim.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    loan_next, action_next, created = 1, 1, False
    kept: dict[str, pd.DataFrame] = {}
    n_batches = 0
    try:
        for batch_idx, start, n in _batches(total, step):
            borrowers, hidden, loans = _generate_population(
                config, replicate, batch_idx, n, start, loan_next, regional
            )
            tables = _generate_panel(
                config, borrowers, hidden, loans,
                replicate=replicate, batch=batch_idx,
                action_start=action_next, policy=policy,
            )
            batch = {"borrowers": borrowers, "loans": loans, **tables}
            for name, frame in batch.items():
                con.register("_chunk", frame)
                con.execute(
                    f"INSERT INTO {name} SELECT * FROM _chunk"
                    if created
                    else f"CREATE TABLE {name} AS SELECT * FROM _chunk"
                )
                con.unregister("_chunk")
            created = True
            loan_next += len(loans)
            action_next += len(tables["actions"])
            n_batches += 1
            if not streaming:
                kept = batch  # one-shot: hand the tables back in memory
    finally:
        con.close()
    return SimulationResult(
        db_path=db_path, tables=kept, meta=_meta(config, replicate, step, n_batches)
    )


def simulate_cohort(
    config: dict[str, Any],
    policy: Any | None = None,
    replicate: int = 0,
    batch_size: int | None = None,
    horizon: int = 9,
    months: int | None = None,
    cohort_states: tuple[str, ...] | None = ("delinquent", "credito_em_liquidacao"),
    cohort_max_liq_days: int | None = 180,
    simulate_all_loans: bool = False,
    with_covariates: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Month-0 decision cohort of one world, without writing a database.

    Runs the same population, streams and monthly dynamics as :func:`generate`
    (identical random draws for the same config, seed, replicate and batch
    size) and returns one row per cohort loan: its month-0 state and action and
    whether it recovered within the first ``horizon`` months. The cohort is the
    loans whose month-0 state is in ``cohort_states`` (and, for
    ``credito_em_liquidacao``, at most ``cohort_max_liq_days`` days in
    liquidation); ``cohort_states=None`` keeps every loan.

    Only cohort loans are stepped, and only for ``months`` months (default
    ``horizon``), unless ``simulate_all_loans`` is set: then every loan is
    stepped and ``meta['recovery_12m']`` — the share of all loans recovering in
    months 0–11 — is reported when ``months >= 12``. Truncating the months or
    skipping loans never changes the draws of the loan-months that are stepped.

    ``with_covariates`` adds the observable borrower and loan attributes and,
    in separate ``hidden_*`` columns, the latent factors (diagnostics only —
    estimators must not read them).

    The ``reward`` column is the evaluation score :data:`SCORE_DEFINITION`
    (``paid_within_h × start_balance × (1 − discount_logged)``), not the cash
    collected; ``cash_within_h`` is the cash collected inside the window
    (:data:`CASH_DEFINITION`) from the same simulation. ``meta`` records the
    model version, the random-stream scheme, the settlement rule and both
    definitions.
    """
    _validate_assignment(config)
    _validate_channel_effects(config)
    months_cfg = int(config["panel"]["months"])
    n_months = int(months) if months is not None else int(horizon)
    if simulate_all_loans:
        n_months = max(n_months, min(12, months_cfg))
    n_months = min(n_months, months_cfg)
    if horizon > n_months:
        raise ValueError(f"horizon ({horizon}) exceeds the simulated months ({n_months})")
    total = int(config["population"]["borrowers"])
    step = total if batch_size is None else int(batch_size)
    regional = regional_shocks(config)

    frames: list[pd.DataFrame] = []
    n_all, rec12_all = 0, 0
    loan_next, n_batches = 1, 0
    for batch_idx, start, n in _batches(total, step):
        borrowers, hidden, loans = _generate_population(
            config, replicate, batch_idx, n, start, loan_next, regional
        )
        loan_next += len(loans)
        n_batches += 1
        state0 = loans["initial_status"].to_numpy(dtype=object)
        liq0 = loans["days_in_credito_em_liquidacao"].to_numpy(dtype=np.int64)
        in_cohort = np.ones(len(loans), dtype=bool)
        if cohort_states is not None:
            in_cohort = np.isin(state0, list(cohort_states))
            if cohort_max_liq_days is not None:
                in_cohort &= ~((state0 == "credito_em_liquidacao") & (liq0 > cohort_max_liq_days))
        step_mask = None if simulate_all_loans else in_cohort
        rec = _simulate_batch(
            config, borrowers, hidden, loans, replicate, batch_idx, policy,
            n_months=n_months, loan_mask=step_mask,
        )
        if simulate_all_loans and n_months >= 12:
            first = rec["first_recovery_month"]
            n_all += len(loans)
            rec12_all += int(((first >= 0) & (first < 12)).sum())
        sel = np.flatnonzero(in_cohort)
        first = rec["first_recovery_month"][sel]
        df = pd.DataFrame({
            "loan_id": loans["loan_id"].to_numpy()[sel],
            "start_balance": loans["outstanding_balance"].to_numpy(np.float64)[sel],
            "state": state0[sel],
            "dpd": loans["days_past_due"].to_numpy(np.int64)[sel],
            "liq_days": liq0[sel],
            "channel_logged": rec["channel0"][sel],
            "discount_logged": rec["discount0"][sel],
            "is_exploration": rec["is_exploration0"][sel],
            "exploration_epsilon": rec["eps0"][sel],
            "paid_within_h": ((first >= 0) & (first < int(horizon))).astype(np.int64),
            "first_recovery_month": first,
            "cash_within_h": rec["recovered_amount"][sel][:, :int(horizon)].sum(axis=1),
        })
        if with_covariates:
            df = _attach_covariates(df, sel, borrowers, hidden, loans)
        frames.append(df)
    cohort = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    cohort["reward"] = (
        cohort["paid_within_h"].astype(np.float64)
        * cohort["start_balance"].astype(np.float64)
        * (1.0 - cohort["discount_logged"].astype(np.float64))
    )
    meta = _meta(config, replicate, step, n_batches)
    meta.update({
        "horizon": int(horizon),
        "months_simulated": int(n_months),
        "simulate_all_loans": bool(simulate_all_loans),
        "reward_definition": SCORE_DEFINITION,
        "cash_definition": CASH_DEFINITION,
        "n_cohort": int(len(cohort)),
        "recovery_12m": (rec12_all / n_all) if (simulate_all_loans and n_all) else None,
    })
    return cohort, meta


def _meta(config: dict[str, Any], replicate: int, batch_size: int, n_batches: int) -> dict:
    return {
        "generator_version": GENERATOR_VERSION,
        "rng_scheme": RNG_SCHEME,
        "settlement_rule": SETTLEMENT_RULE,
        "seed": int(config["seed"]),
        "replicate": int(replicate),
        "batch_size": int(batch_size),
        "n_batches": int(n_batches),
    }


def _batches(total: int, step: int):
    """Yield ``(batch_index, start, n)`` over a population of ``total`` borrowers."""
    if step <= 0:
        raise ValueError("batch_size must be positive")
    start, batch_idx = 0, 0
    while start < total:
        n = min(step, total - start)
        yield batch_idx, start, n
        start += n
        batch_idx += 1


def _generate_population(
    config: dict[str, Any],
    replicate: int,
    batch: int,
    n: int,
    start_idx: int,
    loan_start: int,
    regional: dict[str, float],
):
    seed = int(config["seed"])
    rng_pop = stream(seed, ROLE_POPULATION, replicate, batch)
    rng_latent = stream(seed, ROLE_LATENT, replicate, batch)
    borrowers, hidden = _generate_borrowers(
        config, rng_pop, rng_latent, n=n, start_idx=start_idx, regional=regional
    )
    loans = _generate_loans(config, borrowers, rng_pop, loan_start=loan_start)
    return borrowers, hidden, loans


def _generate_borrowers(
    config: dict[str, Any],
    rng: np.random.Generator,
    rng_latent: np.random.Generator,
    n: int,
    start_idx: int,
    regional: dict[str, float],
):
    """Sample ``n`` borrowers with ids starting at ``B{start_idx+1}``.

    Demographics come from ``rng`` (population stream), the hidden factors from
    ``rng_latent`` and the per-region shock from ``regional`` (one vector per world).
    """
    cfg = config["demographics"]

    _, loc_idx = _weighted_choice(rng, LOCATIONS, "city", n)
    locs = [LOCATIONS[i] for i in loc_idx]
    income_bands, inc_idx = _weighted_choice(rng, INCOME_BANDS, "band", n)
    bands = [INCOME_BANDS[i] for i in inc_idx]

    gender_weights = np.array([cfg["gender_weights"].get(g, 0.0) for g in GENDERS], dtype=float)
    gender_weights = gender_weights / gender_weights.sum()
    genders = rng.choice(GENDERS, size=n, p=gender_weights)
    ages = np.clip(
        rng.normal(float(cfg["age_mean"]), float(cfg["age_std"]), size=n).round(),
        int(cfg["age_min"]),
        int(cfg["age_max"]),
    ).astype(int)
    monthly_income = np.array([rng.uniform(b["min"], b["max"]) for b in bands]).round(2)

    borrowers = pd.DataFrame(
        {
            "borrower_id": [f"B{i:06d}" for i in range(start_idx + 1, start_idx + n + 1)],
            "uf": [loc["uf"] for loc in locs],
            "city": [loc["city"] for loc in locs],
            "lat": [loc["lat"] for loc in locs],
            "lon": [loc["lon"] for loc in locs],
            "age": ages,
            "gender": genders,
            "income_band": income_bands,
            "monthly_income": monthly_income,
            "dependents": rng.poisson(1.1, size=n).clip(0, 5),
        }
    )

    strength = float(config["oracle"]["hidden_confounding_strength"])
    z = rng_latent.standard_normal((3, n))
    hidden = pd.DataFrame(
        {
            "borrower_id": borrowers["borrower_id"],
            "borrower_resilience": strength * z[0],
            "payment_friction": strength * z[1],
            "contactability": strength * z[2],
            "regional_macro_stress": [regional[uf] for uf in borrowers["uf"]],
        }
    )
    return borrowers, hidden


def _generate_loans(
    config: dict[str, Any],
    borrowers: pd.DataFrame,
    rng: np.random.Generator,
    loan_start: int = 1,
):
    lo_min, lo_max = config["population"]["loans_per_borrower"]
    counts = rng.integers(int(lo_min), int(lo_max) + 1, size=len(borrowers))
    product_names, product_idx = _weighted_choice(rng, PRODUCTS, "product_type", int(counts.sum()))
    products = [PRODUCTS[i] for i in product_idx]

    rows = []
    loan_num = loan_start
    for borrower_id, n_loans in zip(borrowers["borrower_id"], counts, strict=True):
        for _ in range(int(n_loans)):
            k = loan_num - loan_start  # batch-local index into products
            product = products[k]
            term = int(product["term_months"])
            loan_age = int(rng.integers(1, max(term, 2)))
            principal = float(
                np.exp(
                    rng.uniform(
                        np.log(float(config["loan"]["principal_min"])),
                        np.log(float(config["loan"]["principal_max"])),
                    )
                )
            )
            dpd = max(
                0,
                int(
                    rng.normal(
                        float(config["loan"]["initial_dpd_mean"]),
                        float(config["loan"]["initial_dpd_std"]),
                    )
                ),
            )
            status = "performing"
            if dpd >= 90:
                status = "credito_em_liquidacao"
            elif dpd >= 30:
                status = "delinquent"
            rows.append(
                {
                    "loan_id": f"L{loan_num:06d}",
                    "borrower_id": borrower_id,
                    "product_type": product_names[k],
                    "origination_month": -loan_age,
                    "original_principal": round(principal, 2),
                    "outstanding_balance": round(principal * rng.uniform(0.45, 1.05), 2),
                    "interest_rate_monthly": float(product["rate"]),
                    "term_months": term,
                    "loan_age_months": loan_age,
                    "remaining_maturity_months": max(term - loan_age, 0),
                    "days_past_due": dpd,
                    "days_in_credito_em_liquidacao": max(0, dpd - 90),
                    "initial_status": status,
                }
            )
            loan_num += 1
    return pd.DataFrame(rows)


def _is_explorable(state: str, liq_days: int, exp_cfg: dict[str, Any]) -> bool:
    """Whether this loan-month is in an active state where the discount has leverage.

    Per the OPE exploration design: concentrate exploration on ``delinquent`` and the
    *early* ``credito_em_liquidacao`` window — not the deep CL tail, which charges off
    regardless, so spending exploration budget there is wasted.
    """
    states = exp_cfg.get("explore_states", ["delinquent", "credito_em_liquidacao"])
    if state not in states:
        return False
    if state == "credito_em_liquidacao":
        if liq_days > int(exp_cfg.get("explore_max_liquidacao_days", 180)):
            return False
    return True


VALID_ASSIGNMENT_MODES = ("confounded", "deterministic_dpd")


def _validate_assignment(config: dict[str, Any]) -> None:
    """Validate the treatment-assignment knobs (called from :func:`generate`)."""
    actions = config["actions"]
    mode = str(actions.get("assignment_mode", "confounded"))
    if mode not in VALID_ASSIGNMENT_MODES:
        raise ValueError(
            f"actions.assignment_mode must be one of {VALID_ASSIGNMENT_MODES}, "
            f"got {mode!r}"
        )
    if mode == "deterministic_dpd":
        ch = str(actions.get("deterministic_channel", "phone"))
        if ch not in CHANNELS or ch == "none":
            raise ValueError(
                f"actions.deterministic_channel must be a contact channel, got {ch!r}"
            )


def _validate_channel_effects(config: dict[str, Any]) -> None:
    """``oracle.channel_effects[_late]`` must map every channel to a finite number."""
    oracle = config["oracle"]
    for key in ("channel_effects", "channel_effects_late"):
        table = oracle.get(key)
        if table is None:
            continue
        if not isinstance(table, dict) or set(table) != set(CHANNELS):
            raise ValueError(f"oracle.{key} must map exactly the channels {CHANNELS}")
        for ch, v in table.items():
            if not np.isfinite(float(v)):
                raise ValueError(f"oracle.{key}[{ch!r}] must be finite, got {v!r}")


def _choose_action(
    config: dict[str, Any],
    u: list[float],
    beta_draw: float,
    days_past_due: int,
    payment_friction: float,
    contactability: float,
    state: str,
    liq_days: int,
):
    """Return ``(channel, discount, is_exploration, explore_prob)``.

    ``u`` holds this loan-month's four action uniforms (exploration coin,
    exploration channel, exploration discount, incumbent channel) and
    ``beta_draw`` its Beta(2, 5) draw for the incumbent discount.

    The incumbent (behaviour) policy is the confounded channel mix + delinquency-ramped
    discount. On top of it sits an **ε-exploration floor** (``actions.exploration``):
    with probability ε — applied only in explorable active states — the action is
    replaced by a uniformly random contact channel and a uniform discount in
    ``[0, max_discount]``. Those explored rows have a **known propensity by
    construction** (channel 1/4, discount density 1/max_discount), which is exactly the
    coverage an OPE estimator needs to identify the discount effect under confounding.

    ``actions.assignment_mode: deterministic_dpd`` replaces all of the above with the
    strict *confounding-by-indication* regime (the C0 no-overlap scenario): treatment —
    one fixed channel and a discount that is a deterministic ramp of DPD — is given if
    and only if ``days_past_due ≥ deterministic_dpd_threshold``; below it, nothing.
    Assignment depends only on the OBSERVED state and is deterministic, so treated and
    untreated never coexist at the same DPD: the effect is not identifiable from these
    logs by any method, and an honest estimator must abstain rather than emit a number.
    """
    max_discount = float(config["actions"]["max_discount"])
    if str(config["actions"].get("assignment_mode", "confounded")) == "deterministic_dpd":
        thr = int(config["actions"].get("deterministic_dpd_threshold", 90))
        if days_past_due >= thr:
            ch = str(config["actions"].get("deterministic_channel", "phone"))
            discount = round(min(max_discount, 0.10 + (days_past_due - thr) / 360.0), 4)
            return ch, discount, False, 0.0
        return "none", 0.0, False, 0.0
    exp_cfg = config["actions"].get("exploration", {}) or {}
    epsilon = float(exp_cfg.get("epsilon", 0.0))
    explore_prob = epsilon if (epsilon > 0.0 and _is_explorable(state, liq_days, exp_cfg)) else 0.0
    if explore_prob > 0.0 and u[0] < explore_prob:
        contact_channels = CHANNELS[1:]
        k = min(int(u[1] * len(contact_channels)), len(contact_channels) - 1)
        channel = contact_channels[k]
        discount = round(float(u[2] * max_discount), 4)
        return channel, discount, True, explore_prob

    # --- incumbent (behaviour) policy ---
    channel_weights = config["actions"]["channel_weights"]
    weights = [float(channel_weights.get(ch, 0.0)) for ch in CHANNELS]
    if config["actions"].get("intensity_confounds_with_friction", True):
        intensity = min(max(days_past_due / 180.0 + payment_friction - 0.4 * contactability, -2), 2)
        weights[0] *= exp(-0.55 * intensity)
        weights[3] *= exp(0.35 * intensity)
        weights[4] *= exp(0.55 * intensity)
    # inverse-CDF draw on the normalised weights
    total = sum(weights)
    if not total > 0.0:
        raise ValueError(f"actions.channel_weights must have a positive sum, got {weights}")
    target = u[3] * total
    k, acc = len(CHANNELS) - 1, 0.0
    for idx, w in enumerate(weights):
        acc += w
        if target < acc:
            k = idx
            break
    channel = CHANNELS[k]
    if channel == "none":
        return channel, 0.0, False, explore_prob
    base_offer = beta_draw * max_discount
    stress_offer = min(max_discount, base_offer + max(0.0, days_past_due - 60) / 360.0)
    return channel, round(float(stress_offer), 4), False, explore_prob


def _panel_draws(seed: int, replicate: int, batch: int, n_loans: int, months: int) -> dict:
    """All action and outcome randomness of one batch, one slot per (loan, month).

    ``out_beta`` was model 2.0.0's paid share. Model 2.1.0 does not read it but
    still draws it, so that the streams stay exactly ``keyed-streams-v2``."""
    ra = stream(seed, ROLE_ACTIONS, replicate, batch)
    ro = stream(seed, ROLE_OUTCOMES, replicate, batch)
    return {
        "act_u": ra.random((n_loans, months, _N_ACTION_UNIFORMS)),
        "act_beta": ra.beta(2.0, 5.0, size=(n_loans, months)),
        "out_z": ro.standard_normal((n_loans, months)),
        "out_u": ro.random((n_loans, months, 2)),
        "out_beta": ro.beta(2.0, 5.0, size=(n_loans, months)),
    }


_STATE_CODES = ("performing", "delinquent", "credito_em_liquidacao", "cured", "charged_off")
_STATE_IDX = {s: i for i, s in enumerate(_STATE_CODES)}
_CHANNEL_IDX = {c: i for i, c in enumerate(CHANNELS)}


def _simulate_batch(
    config: dict[str, Any],
    borrowers: pd.DataFrame,
    borrower_hidden: pd.DataFrame,
    loans: pd.DataFrame,
    replicate: int,
    batch: int,
    policy: Any | None,
    n_months: int | None = None,
    loan_mask: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Step the loans of one batch month by month; return per-(loan, month) arrays.

    Every array has shape ``(n_loans, n_months)``; ``alive`` marks the slots
    that were stepped (the loan is selected and not yet terminal).
    ``balance_before`` is the balance on which the month's offer is computed,
    rounded to cents; ``written_off`` is the discounted remainder cancelled by a
    settlement (0 in every other slot). In a recovery slot
    ``balance_before = recovered_amount + written_off`` exactly, in cents.
    """
    seed = int(config["seed"])
    months_cfg = int(config["panel"]["months"])
    n_months = months_cfg if n_months is None else min(int(n_months), months_cfg)
    oracle_cfg = config["oracle"]
    noise_std = float(oracle_cfg["noise_std"])
    n = len(loans)
    # drawn with the configured horizon, so truncating months never shifts draws
    draws = _panel_draws(seed, replicate, batch, n, months_cfg)

    b_index = {bid: i for i, bid in enumerate(borrowers["borrower_id"])}
    ages = borrowers["age"].to_numpy(np.int64).tolist()
    res_all = borrower_hidden["borrower_resilience"].to_numpy(np.float64).tolist()
    fric_all = borrower_hidden["payment_friction"].to_numpy(np.float64).tolist()
    reg_all = borrower_hidden["regional_macro_stress"].to_numpy(np.float64).tolist()
    cont_all = borrower_hidden["contactability"].to_numpy(np.float64).tolist()

    shape = (n, n_months)
    out = {
        "alive": np.zeros(shape, dtype=bool),
        "status": np.zeros(shape, dtype=np.int8),
        "next_status": np.zeros(shape, dtype=np.int8),
        "channel": np.zeros(shape, dtype=np.int8),
        "discount": np.zeros(shape, dtype=np.float64),
        "settlement": np.zeros(shape, dtype=np.float64),
        "is_exploration": np.zeros(shape, dtype=bool),
        "explore_prob": np.zeros(shape, dtype=np.float64),
        "loan_age": np.zeros(shape, dtype=np.int64),
        "remaining": np.zeros(shape, dtype=np.int64),
        "dpd_after": np.zeros(shape, dtype=np.int64),
        "liq_after": np.zeros(shape, dtype=np.int64),
        "balance_after": np.zeros(shape, dtype=np.float64),
        "contacts": np.zeros(shape, dtype=np.int64),
        "recovered": np.zeros(shape, dtype=bool),
        "charged_off": np.zeros(shape, dtype=bool),
        "recovered_amount": np.zeros(shape, dtype=np.float64),
        "p_recovery": np.zeros(shape, dtype=np.float64),
        "p_chargeoff": np.zeros(shape, dtype=np.float64),
        "balance_before": np.zeros(shape, dtype=np.float64),
        "written_off": np.zeros(shape, dtype=np.float64),
    }
    first_recovery = np.full(n, -1, dtype=np.int64)
    channel0 = np.empty(n, dtype=object)
    channel0[:] = None
    discount0 = np.full(n, np.nan)
    explore0 = np.zeros(n, dtype=bool)
    eps0 = np.zeros(n, dtype=np.float64)

    init_status = loans["initial_status"].tolist()
    init_balance = loans["outstanding_balance"].to_numpy(np.float64).tolist()
    init_dpd = loans["days_past_due"].to_numpy(np.int64).tolist()
    init_liq = loans["days_in_credito_em_liquidacao"].to_numpy(np.int64).tolist()
    init_age = loans["loan_age_months"].to_numpy(np.int64).tolist()
    init_rem = loans["remaining_maturity_months"].to_numpy(np.int64).tolist()
    rate = loans["interest_rate_monthly"].to_numpy(np.float64).tolist()
    loan_borrower = loans["borrower_id"].tolist()

    for i in range(n):
        if loan_mask is not None and not loan_mask[i]:
            continue
        state = str(init_status[i])
        balance = float(init_balance[i])
        dpd = int(init_dpd[i])
        liq_days = int(init_liq[i])
        loan_age = int(init_age[i])
        remaining = int(init_rem[i])
        contacts_last_3m = 0
        j = b_index[loan_borrower[i]]
        age, res, fric, reg, cont = ages[j], res_all[j], fric_all[j], reg_all[j], cont_all[j]
        act_u = draws["act_u"][i].tolist()
        act_beta = draws["act_beta"][i].tolist()
        out_z = draws["out_z"][i].tolist()
        out_u = draws["out_u"][i].tolist()
        rows: list[tuple] = []

        for month in range(n_months):
            if state in TERMINAL_STATES:
                break
            override = None
            if policy is not None:
                override = policy(
                    month=month,
                    state=state,
                    days_past_due=dpd,
                    days_in_credito_em_liquidacao=liq_days,
                    outstanding_balance=balance,
                    loan_age_months=loan_age,
                    remaining_maturity_months=remaining,
                    contacts_last_3m=contacts_last_3m,
                )
            if override is not None:
                # policy overrides this loan-month; None falls through to the
                # incumbent+ε assignment (one-shot / partial deviation policies)
                channel, discount = override
                channel = str(channel)
                if channel not in _CHANNEL_IDX:
                    raise ValueError(f"policy returned unknown channel {channel!r}; "
                                     f"expected one of {CHANNELS}")
                discount = round(float(discount), 4)
                is_exploration, explore_prob = False, 0.0
            else:
                channel, discount, is_exploration, explore_prob = _choose_action(
                    config, act_u[month], act_beta[month], dpd, fric, cont, state, liq_days
                )
            balance_before = round(balance, 2)
            settlement_offer = round(balance * (1.0 - discount), 2)
            noise = out_z[month] * noise_std
            inputs = RecoveryInputs(
                channel=channel,
                discount_offer=discount,
                age=age,
                loan_age_months=loan_age,
                days_past_due=dpd,
                days_in_credito_em_liquidacao=liq_days,
                borrower_resilience=res,
                payment_friction=fric,
                regional_macro_stress=reg,
                contactability=cont,
                noise=noise,
            )
            p_recovery = recovery_probability(inputs, oracle_cfg)
            p_chargeoff = _chargeoff_probability(liq_days, oracle_cfg)
            u_recovery, u_chargeoff = out_u[month]
            recovered = u_recovery < p_recovery
            charged_off = (not recovered) and u_chargeoff < p_chargeoff

            recovered_amount = 0.0
            written_off = 0.0
            next_state = state
            if recovered:
                # Full settlement (model 2.1.0): the borrower pays the whole offer,
                # the discounted remainder is written off and the debt is closed
                # (terminal ``cured``: no later rows). A discount lowers what is
                # collected (a giveaway); it never raises it.
                recovered_amount = settlement_offer
                written_off = round(balance_before - settlement_offer, 2)
                balance = 0.0
                dpd = 0
                liq_days = 0
                next_state = "cured"
                if first_recovery[i] < 0:
                    first_recovery[i] = month
            elif charged_off:
                next_state = "charged_off"
            else:
                balance = balance * (1.0 + rate[i] * 0.35)
                dpd += 30
                if dpd >= 90:
                    liq_days += 30
                    next_state = "credito_em_liquidacao"
                elif dpd >= 30:
                    next_state = "delinquent"
                else:
                    next_state = "performing"

            if month == 0:
                channel0[i] = channel
                discount0[i] = discount
                explore0[i] = bool(is_exploration)
                eps0[i] = round(float(explore_prob), 4)
            rows.append((
                _STATE_IDX[state], _STATE_IDX[next_state], _CHANNEL_IDX[channel], discount,
                settlement_offer, bool(is_exploration), round(float(explore_prob), 4),
                loan_age, remaining, dpd, liq_days, round(balance, 2), contacts_last_3m,
                bool(recovered), bool(charged_off), recovered_amount, p_recovery, p_chargeoff,
                balance_before, written_off,
            ))

            state = next_state
            loan_age += 1
            remaining = max(remaining - 1, 0)
            contacts_last_3m = min(3, contacts_last_3m + (0 if channel == "none" else 1))

        if rows:
            k = len(rows)
            cols = list(zip(*rows, strict=True))
            out["alive"][i, :k] = True
            for name, col in zip(
                ("status", "next_status", "channel", "discount", "settlement",
                 "is_exploration", "explore_prob", "loan_age", "remaining", "dpd_after",
                 "liq_after", "balance_after", "contacts", "recovered", "charged_off",
                 "recovered_amount", "p_recovery", "p_chargeoff", "balance_before",
                 "written_off"),
                cols, strict=True,
            ):
                out[name][i, :k] = col

    out.update({
        "first_recovery_month": first_recovery,
        "channel0": channel0,
        "discount0": discount0,
        "is_exploration0": explore0,
        "eps0": eps0,
        "recovery_draw": draws["out_u"][:, :n_months, 0],
        "chargeoff_draw": draws["out_u"][:, :n_months, 1],
    })
    return out


def _generate_panel(
    config: dict[str, Any],
    borrowers: pd.DataFrame,
    borrower_hidden: pd.DataFrame,
    loans: pd.DataFrame,
    replicate: int = 0,
    batch: int = 0,
    action_start: int = 1,
    policy: Any | None = None,
) -> dict[str, pd.DataFrame]:
    """Simulate one batch and assemble the ``actions``, ``monthly_panel`` and
    ``oracle_truth`` tables (rows in loan-major, month-minor order)."""
    seed = int(config["seed"])
    rec = _simulate_batch(config, borrowers, borrower_hidden, loans, replicate, batch, policy)
    li, mi = np.nonzero(rec["alive"])  # C order: loan-major, month-minor
    n_rows = len(li)
    action_ids = [f"A{k:08d}" for k in range(action_start, action_start + n_rows)]
    loan_ids = loans["loan_id"].to_numpy(dtype=object)[li]
    borrower_ids = loans["borrower_id"].to_numpy(dtype=object)[li]
    states = np.asarray(_STATE_CODES, dtype=object)
    channels = np.asarray(CHANNELS, dtype=object)
    sel = (li, mi)

    hidden = borrower_hidden.set_index("borrower_id").loc[borrower_ids]
    actions = pd.DataFrame({
        "action_id": action_ids,
        "loan_id": loan_ids,
        "month": mi.astype(np.int64),
        "channel": channels[rec["channel"][sel]],
        "discount_offer": rec["discount"][sel],
        "settlement_offer_amount": rec["settlement"][sel],
        "is_exploration": rec["is_exploration"][sel],
        "exploration_epsilon": rec["explore_prob"][sel],
    })
    panel = pd.DataFrame({
        "loan_id": loan_ids,
        "borrower_id": borrower_ids,
        "month": mi.astype(np.int64),
        "status": states[rec["status"][sel]],
        "next_status": states[rec["next_status"][sel]],
        "loan_age_months": rec["loan_age"][sel],
        "remaining_maturity_months": rec["remaining"][sel],
        "days_past_due": rec["dpd_after"][sel],
        "days_in_credito_em_liquidacao": rec["liq_after"][sel],
        "outstanding_balance": rec["balance_after"][sel],
        "contacts_last_3m": rec["contacts"][sel],
        "action_id": action_ids,
        "recovered": rec["recovered"][sel],
        "charged_off": rec["charged_off"][sel],
        "recovered_amount": rec["recovered_amount"][sel],
    })
    truth = pd.DataFrame({
        "seed": np.full(n_rows, seed, dtype=np.int64),
        "loan_id": loan_ids,
        "borrower_id": borrower_ids,
        "month": mi.astype(np.int64),
        "borrower_resilience": hidden["borrower_resilience"].to_numpy(np.float64),
        "payment_friction": hidden["payment_friction"].to_numpy(np.float64),
        "regional_macro_stress": hidden["regional_macro_stress"].to_numpy(np.float64),
        "contactability": hidden["contactability"].to_numpy(np.float64),
        "p_recovery": rec["p_recovery"][sel],
        "p_chargeoff": rec["p_chargeoff"][sel],
        "recovery_draw": rec["recovery_draw"][sel],
        "chargeoff_draw": rec["chargeoff_draw"][sel],
    })
    if not panel.empty:
        bad_states = set(panel["status"]).union(panel["next_status"]) - ALLOWED_STATES
        if bad_states:
            raise ValueError(f"generated invalid states: {sorted(bad_states)}")
    return {"actions": actions, "monthly_panel": panel, "oracle_truth": truth}


_COVARIATE_BORROWER = ("uf", "age", "gender", "income_band", "monthly_income", "dependents")
_COVARIATE_LOAN = (
    "product_type", "original_principal", "interest_rate_monthly", "term_months",
    "loan_age_months", "remaining_maturity_months",
)


def _attach_covariates(df, sel, borrowers, hidden, loans):
    """Observable month-0 covariates of the selected loans (+ hidden_* diagnostics)."""
    bid = loans["borrower_id"].to_numpy(dtype=object)[sel]
    b = borrowers.set_index("borrower_id").loc[bid]
    h = hidden.set_index("borrower_id").loc[bid]
    for col in _COVARIATE_LOAN:
        df[col] = loans[col].to_numpy()[sel]
    for col in _COVARIATE_BORROWER:
        df[col] = b[col].to_numpy()
    for col in ("borrower_resilience", "payment_friction", "contactability",
                "regional_macro_stress"):
        df[f"hidden_{col}"] = h[col].to_numpy(np.float64)
    return df


def _chargeoff_probability(liq_days: int, oracle_cfg: dict[str, Any]) -> float:
    threshold = float(oracle_cfg["chargeoff_after_liquidacao_days"])
    if liq_days <= 0:
        return 0.002
    pressure = (liq_days - threshold) / 90.0
    return min(0.60, max(0.005, _sigmoid(-3.5 + pressure)))
