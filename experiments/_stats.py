"""Shared statistics helpers for the summarizers (mean/median/std/percentiles + CIs)."""

from __future__ import annotations

import math

import numpy as np

Z = 1.959963984540054  # 95%


def describe(values: list[float]) -> dict:
    if not values:
        return {k: 0.0 for k in ("mean", "median", "std", "min", "max", "p50", "p95", "p99", "n")}
    a = np.asarray(values, dtype=float)
    return {
        "mean": float(a.mean()), "median": float(np.median(a)),
        "std": float(a.std(ddof=1)) if a.size > 1 else 0.0,
        "min": float(a.min()), "max": float(a.max()),
        "p50": float(np.percentile(a, 50)), "p95": float(np.percentile(a, 95)),
        "p99": float(np.percentile(a, 99)), "n": int(a.size),
    }


def wilson(k: int, n: int) -> dict:
    if n == 0:
        return {"p": 0.0, "lo": 0.0, "hi": 0.0, "k": 0, "n": 0}
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return {"p": p, "lo": max(0.0, c - h), "hi": min(1.0, c + h), "k": k, "n": n}


def mean_ci(values: list[float]) -> dict:
    if not values:
        return {"mean": 0.0, "lo": 0.0, "hi": 0.0, "std": 0.0, "n": 0}
    a = np.asarray(values, dtype=float)
    n = a.size
    m = float(a.mean())
    s = float(a.std(ddof=1)) if n > 1 else 0.0
    h = Z * s / math.sqrt(n) if n > 1 else 0.0
    return {"mean": m, "lo": m - h, "hi": m + h, "std": s, "n": n}
