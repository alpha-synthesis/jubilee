"""Model-based check of the month-0 action law of one generator version.

For every month-0 decision the behaviour policy's channel probabilities are a
known function of the loan's state and hidden factors: with probability
``explore_prob`` a uniform contact channel, otherwise the incumbent's
(confounded) channel weights. Summing those probabilities over the loans gives
the expected count of each channel; the observed counts must agree within
binomial error (z = (observed − expected) / sqrt(Σ p(1 − p))). Exploration
share and the incumbent's discount ramp are checked the same way. Works for
version 1 or version 2 (``--src``).

Usage::

    python scripts/tmlr_evidence/action_law_check.py --src src --config CFG \
        --seeds 9201 9202 --borrowers 200000 --out law.json
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb
import numpy as np

_GEN = """
import sys
sys.path.insert(0, {src!r})
from collection_simulator.config import load_config
from collection_simulator.generator import generate
cfg = load_config({config!r}); cfg["seed"] = {seed}; cfg["population"]["borrowers"] = {n}
generate(cfg, {out!r}, batch_size={batch})
"""
CHANNELS = ["none", "sms", "app_message", "phone", "field_visit"]


def check(src: str, config: Path, seed: int, n: int, batch: int, work: Path) -> dict:
    sys.path.insert(0, src)
    from collection_simulator.config import load_config

    cfg = load_config(config)
    out = work / f"w{seed}"
    subprocess.run([sys.executable, "-c", _GEN.format(src=src, config=str(config), seed=seed,
                                                       n=n, batch=batch, out=str(out))], check=True)
    con = duckdb.connect(str(out / "sim.duckdb"), read_only=True)
    df = con.execute("""
        SELECT a.channel, a.discount_offer, a.is_exploration, l.days_past_due AS dpd,
               l.initial_status AS state, l.days_in_credito_em_liquidacao AS liq,
               t.payment_friction AS fric, t.contactability AS cont
        FROM actions a JOIN loans l USING (loan_id)
        JOIN oracle_truth t ON t.loan_id = a.loan_id AND t.month = 0
        WHERE a.month = 0""").df()
    con.close()
    (out / "sim.duckdb").unlink()
    act = cfg["actions"]
    exp_cfg = act.get("exploration") or {}
    eps = float(exp_cfg.get("epsilon", 0.0))
    states = exp_cfg.get("explore_states", ["delinquent", "credito_em_liquidacao"])
    max_liq = int(exp_cfg.get("explore_max_liquidacao_days", 180))
    explorable = df["state"].isin(states).to_numpy() & ~(
        (df["state"] == "credito_em_liquidacao").to_numpy() & (df["liq"].to_numpy() > max_liq))
    pe = np.where(explorable, eps, 0.0)
    w = np.tile(np.array([float(act["channel_weights"][c]) for c in CHANNELS]), (len(df), 1))
    if act.get("intensity_confounds_with_friction", True):
        inten = np.clip(df["dpd"].to_numpy() / 180.0 + df["fric"].to_numpy()
                        - 0.4 * df["cont"].to_numpy(), -2, 2)
        w[:, 0] *= np.exp(-0.55 * inten)
        w[:, 3] *= np.exp(0.35 * inten)
        w[:, 4] *= np.exp(0.55 * inten)
    w /= w.sum(axis=1, keepdims=True)
    p = (1 - pe)[:, None] * w
    p[:, 1:] += pe[:, None] / 4.0
    res = {}
    for k, ch in enumerate(CHANNELS):
        obs = float((df["channel"] == ch).sum())
        exp = float(p[:, k].sum())
        sd = math.sqrt(float((p[:, k] * (1 - p[:, k])).sum()))
        res[f"channel_{ch}"] = {"observed": obs, "expected": exp, "z": (obs - exp) / sd}
    obs = float(df["is_exploration"].sum())
    res["explored"] = {"observed": obs, "expected": float(pe.sum()),
                       "z": (obs - pe.sum()) / math.sqrt(float((pe * (1 - pe)).sum()))}
    # incumbent discount: contacted, non-explored rows; base Beta(2,5)*max + DPD ramp, capped
    m = (df["channel"] != "none").to_numpy() & ~df["is_exploration"].to_numpy()
    maxd = float(act["max_discount"])
    rng = np.random.default_rng(0)
    sim = np.minimum(maxd, rng.beta(2, 5, size=(200, m.sum())) * maxd
                     + np.maximum(0, df["dpd"].to_numpy()[m] - 60) / 360.0).mean(axis=1)
    obs_mean = float(df["discount_offer"].to_numpy()[m].mean())
    res["incumbent_discount_mean"] = {"observed": obs_mean, "expected": float(sim.mean()),
                                      "z": (obs_mean - sim.mean()) / float(np.sqrt(
                                          np.var(df["discount_offer"].to_numpy()[m]) / m.sum()))}
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--seeds", type=int, nargs="+", required=True)
    ap.add_argument("--borrowers", type=int, default=200_000)
    ap.add_argument("--batch-size", type=int, default=50_000)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as work:
        per_seed = {s: check(str(Path(a.src).resolve()), a.config.resolve(), s, a.borrowers,
                             a.batch_size, Path(work)) for s in a.seeds}
    zs = [v["z"] for r in per_seed.values() for v in r.values()]
    rec = {"src": a.src, "config": str(a.config), "borrowers": a.borrowers, "seeds": a.seeds,
           "per_seed": per_seed, "max_abs_z": max(abs(z) for z in zs), "n_tests": len(zs)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2))
    for s, r in per_seed.items():
        print(s, {k: round(v["z"], 2) for k, v in r.items()})
    print(json.dumps({"max_abs_z": rec["max_abs_z"], "n_tests": rec["n_tests"]}))


if __name__ == "__main__":
    main()
