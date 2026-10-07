"""EXP-01-1: a survivors-only universe inflates an equal-weight backtest.

Generating process: 200 coins, each a zero-drift GBM (dP/P = sigma dW, so the expected simple return is 0;
daily log returns N(-sigma^2/2, sigma^2) with sigma = 5%), 1,095 days. A coin is delisted at the end of
the first day its price closes below 10% of its start price; it is excluded from the next day on.
50 independent universes, seeds 100..149 (quick: 3 universes of 50 coins over 365 days).

Treatment: survivors-only universe (coins still listed on the last day), equal weight, rebalanced daily.
Control: the point-in-time universe (every coin listed on that day, including those later delisted).
Metric: mean daily return of each portfolio; the effect is the mean over universes of the difference,
with its standard error across universes.
Verdict rule (from blueprint/01-data.md): supports if survivors-only minus point-in-time > 2 SE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from experiments._common import main, mean_se, synthetic, verdict

META = {
    "id": "EXP-01-1", "backs": "01-data rule 5",
    "claim": "survivors-only universe inflates returns",
    "script": "experiments/EXP-01-1-survivorship.py",
    "data": synthetic("200 zero-drift GBM coins, daily sigma 5%, delisted below 10% of start"),
}
SIGMA, FLOOR = 0.05, 0.10


def one_universe(rng: np.random.Generator, n_coins: int, days: int) -> tuple[float, float, float]:
    logr = rng.normal(-SIGMA**2 / 2, SIGMA, (days, n_coins))
    rel = np.exp(np.cumsum(logr, axis=0))  # price / start price at each day's close
    simple = np.expm1(logr)
    below = rel < FLOOR
    first_below = np.where(below.any(axis=0), below.argmax(axis=0), days)
    listed = np.arange(days)[:, None] <= first_below[None, :]  # the delisting day's return still counts
    pit = (simple * listed).sum(axis=1) / listed.sum(axis=1)
    survivors = first_below == days
    surv = simple[:, survivors].mean(axis=1)
    return float(surv.mean()), float(pit.mean()), float(survivors.mean())


def passes(diff: float, se: float) -> bool:
    return diff > 2 * se


def run(quick: bool) -> dict:
    n_univ, n_coins, days = (3, 50, 365) if quick else (50, 200, 1_095)
    seeds = list(range(100, 100 + n_univ))
    res = np.array([one_universe(np.random.default_rng(s), n_coins, days) for s in seeds])
    surv_m, surv_se = mean_se(res[:, 0])
    pit_m, pit_se = mean_se(res[:, 1])
    d_m, d_se = mean_se(res[:, 0] - res[:, 1])
    ok = passes(d_m, d_se)
    return {
        "inputs": {"universes": n_univ, "coins": n_coins, "days": days, "daily_sigma": SIGMA,
                   "delist_below": FLOOR},
        "seeds": seeds, "metric": "mean daily return of the equal-weight portfolio",
        "treatment": {"arm": "survivors only", "mean_daily_return": surv_m, "se": surv_se,
                      "share_surviving": float(res[:, 2].mean())},
        "control": {"arm": "point-in-time universe", "mean_daily_return": pit_m, "se": pit_se},
        "effect": {"estimate": d_m, "se": d_se, "annualised_365": d_m * 365},
        "verdict_rule": "supports if survivors-only minus point-in-time mean daily return > 2 SE",
        "verdict": verdict(ok),
        "summary": (f"survivors-only {surv_m * 1e4:.1f} bp/day vs point-in-time {pit_m * 1e4:.1f} bp/day; "
                    f"bias {d_m * 1e4:.1f} bp/day (SE {d_se * 1e4:.1f}), about {d_m * 365:.0%} a year, "
                    f"with {res[:, 2].mean():.0%} of coins surviving"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
