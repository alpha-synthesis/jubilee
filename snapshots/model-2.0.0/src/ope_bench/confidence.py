"""Bootstrap confidence intervals for OPE estimates (T-30).

An OPE point estimate is not a defensible claim without an interval.  We
resample the logs with replacement, recompute the estimate, and take percentile
bounds.  The one-sided ``lower_bound`` is the conservative number to put in
front of a client ("the new policy recovers at least X, with 95% confidence") —
the spirit of high-confidence OPE (Thomas et al. 2015).
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def _resample(logs: dict, idx: np.ndarray) -> dict:
    return {k: np.asarray(v)[idx] for k, v in logs.items()}


def bootstrap_distribution(
    estimate_fn: Callable[[dict], float],
    logs: dict,
    n_boot: int = 500,
    seed: int = 0,
) -> np.ndarray:
    """Bootstrap distribution of ``estimate_fn`` over resampled logs.

    ``estimate_fn`` takes a (resampled) logs dict and returns a scalar.  Fixed
    side inputs (e.g. simulator annotations) should be captured by closure so
    they are *not* resampled — only the factual logs are.
    """
    n = len(next(iter(logs.values())))
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        out[b] = estimate_fn(_resample(logs, idx))
    return out


def bootstrap_ci(
    estimate_fn: Callable[[dict], float],
    logs: dict,
    n_boot: int = 500,
    alpha: float = 0.1,
    seed: int = 0,
) -> tuple[float, float]:
    """Two-sided ``(1-alpha)`` percentile CI."""
    dist = bootstrap_distribution(estimate_fn, logs, n_boot, seed)
    lo = float(np.quantile(dist, alpha / 2))
    hi = float(np.quantile(dist, 1 - alpha / 2))
    return lo, hi


def lower_bound(
    estimate_fn: Callable[[dict], float],
    logs: dict,
    n_boot: int = 500,
    alpha: float = 0.05,
    seed: int = 0,
) -> float:
    """One-sided ``(1-alpha)`` lower confidence bound (the conservative number)."""
    dist = bootstrap_distribution(estimate_fn, logs, n_boot, seed)
    return float(np.quantile(dist, alpha))
