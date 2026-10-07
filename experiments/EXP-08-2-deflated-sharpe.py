"""EXP-08-2: the best of N skill-less strategies passes a raw Sharpe test, and fails the deflated one.

Generating process: in each of 1,000 repeats (quick: 50), N strategies (N = 1, 10, 100, 1,000; quick:
1, 10, 100) each produce 250 iid N(0, 0.01^2) daily returns: no strategy has skill. Seed 82.

Per repeat the best strategy by Sharpe is selected. Raw test: pipeline.stats.probabilistic_sharpe_ratio
of its Sharpe against 0 with 250 observations. Deflated test: pipeline.stats.deflated_sharpe_ratio with
n_trials = N and var_trials = the variance of the N per-period Sharpes in that repeat. A test "passes"
at > 0.95. Control: N = 1 (no selection). Metric: false-pass rate per N with binomial SE.
Verdict rule (from blueprint/08-validation.md): supports if the raw false-pass rate rises with N (strictly
across the N grid, and at the largest N above the N = 1 rate by more than 2 SE) and the deflated
false-pass rate stays within 2 SE of 5% or below at every N.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, prop_se, synthetic, verdict  # noqa: E402
from pipeline.stats import deflated_sharpe_ratio, probabilistic_sharpe_ratio  # noqa: E402

META = {
    "id": "EXP-08-2", "backs": "08-validation rules 3, 4",
    "claim": "best of N noise strategies passes raw Sharpe, fails deflated",
    "script": "experiments/EXP-08-2-deflated-sharpe.py",
    "data": synthetic("iid N(0, 0.01^2) daily returns, 250 days, no skill"),
}
SEED, T = 82, 250


def run(quick: bool) -> dict:
    reps, grid = (50, (1, 10, 100)) if quick else (1_000, (1, 10, 100, 1_000))
    rng = np.random.default_rng(SEED)
    by_n = {}
    for n in grid:
        raw = dsr = 0
        best_sr = []
        for _ in range(reps):
            r = rng.normal(0, 0.01, (T, n))
            sr = r.mean(axis=0) / r.std(axis=0, ddof=1)
            best = float(sr.max())
            best_sr.append(best)
            raw += probabilistic_sharpe_ratio(best, 0.0, T) > 0.95
            dsr += deflated_sharpe_ratio(best, T, n, float(sr.var(ddof=1)) if n > 1 else 0.0) > 0.95
        by_n[str(n)] = {"raw_false_pass": raw / reps, "raw_se": prop_se(raw / reps, reps),
                        "deflated_false_pass": dsr / reps, "deflated_se": prop_se(dsr / reps, reps),
                        "mean_best_annual_sharpe": float(np.mean(best_sr) * np.sqrt(365))}
    rates = [by_n[str(n)]["raw_false_pass"] for n in grid]
    top, base = by_n[str(grid[-1])], by_n["1"]
    rises = all(a < b for a, b in zip(rates, rates[1:])) and \
        top["raw_false_pass"] - base["raw_false_pass"] > 2 * np.hypot(top["raw_se"], base["raw_se"])
    dsr_ok = all(c["deflated_false_pass"] <= 0.05 + 2 * prop_se(0.05, reps) for c in by_n.values())
    raw_txt = ", ".join(f"{by_n[str(n)]['raw_false_pass']:.0%}" for n in grid)
    dsr_txt = ", ".join(f"{by_n[str(n)]['deflated_false_pass']:.1%}" for n in grid)
    return {
        "inputs": {"repeats": reps, "n_grid": list(grid), "days": T, "pass_threshold": 0.95},
        "seeds": [SEED], "metric": "share of repeats where the best strategy passes (false-pass rate)",
        "treatment": {"arm": "best of N > 1", **{k: v for k, v in by_n.items() if k != "1"}},
        "control": {"arm": "N = 1", **base},
        "effect": {"estimate": top["raw_false_pass"] - base["raw_false_pass"],
                   "se": float(np.hypot(top["raw_se"], base["raw_se"])),
                   "what": f"raw false-pass rate at N = {grid[-1]} minus N = 1",
                   "deflated_at_max_n": top["deflated_false_pass"]},
        "verdict_rule": "supports if raw false-pass rises with N (strictly, top vs N=1 > 2 SE) and deflated "
                        "false-pass <= 5% + 2 SE at every N",
        "verdict": verdict(rises and dsr_ok),
        "summary": (f"raw PSR false-pass {raw_txt} for N = {', '.join(str(n) for n in grid)}; deflated {dsr_txt}"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
