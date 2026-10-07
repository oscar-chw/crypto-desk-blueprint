"""EXP-02-2: regressing one random-walk level on another independent one rejects "no relation" far more
often than 5% (Granger and Newbold 1974); the same regression on differences holds its size.

Generating process: 1,000 pairs (quick: 100) of independent Gaussian random walks of 500 steps with unit
step variance, x and y independent by construction. Seed 5.

Treatment: OLS y_t = a + b x_t + e on levels. Control: the same regression on first differences.
Metric: rejection rate of H0: b = 0 with the two-sided classical t test at 5% (critical value 1.9647, the
Student-t 97.5% quantile for about 500 degrees of freedom), binomial SE.
Verdict rule (from blueprint/02-features.md): supports if the levels rate exceeds 5% by more than 2 SE and
the differences rate is within 2 SE of 5%.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from experiments._common import main, prop_se, synthetic, verdict
from experiments._tsa import ols_t

META = {
    "id": "EXP-02-2", "backs": "02-features rule 3",
    "claim": "level-on-level regression rejects far above 5%",
    "script": "experiments/EXP-02-2-spurious-regression.py",
    "data": synthetic("independent Gaussian random walks, 500 steps"),
}
SEED, STEPS, T_CRIT = 5, 500, 1.9647


def passes(levels: float, levels_se: float, returns: float, n: int) -> bool:
    return levels - 0.05 > 2 * levels_se and abs(returns - 0.05) <= 2 * prop_se(0.05, n)


def run(quick: bool) -> dict:
    n_pairs = 100 if quick else 1_000
    rng = np.random.default_rng(SEED)
    rej = {"levels": 0, "returns": 0}
    for _ in range(n_pairs):
        x, y = np.cumsum(rng.standard_normal((2, STEPS)), axis=1)
        for arm, (xx, yy) in {"levels": (x, y), "returns": (np.diff(x), np.diff(y))}.items():
            _, t = ols_t(yy, np.column_stack([np.ones(len(xx)), xx]))
            rej[arm] += abs(t[1]) > T_CRIT
    lv, rt = rej["levels"] / n_pairs, rej["returns"] / n_pairs
    lv_se, rt_se = prop_se(lv, n_pairs), prop_se(rt, n_pairs)
    ok = passes(lv, lv_se, rt, n_pairs)
    return {
        "inputs": {"pairs": n_pairs, "steps": STEPS, "test": "two-sided t, 5%", "t_crit": T_CRIT},
        "seeds": [SEED], "metric": "rejection rate of slope = 0 at nominal 5%",
        "treatment": {"arm": "levels on levels", "rejection_rate": lv, "se": lv_se},
        "control": {"arm": "returns on returns", "rejection_rate": rt, "se": rt_se},
        "effect": {"estimate": lv - rt, "se": float(np.hypot(lv_se, rt_se))},
        "verdict_rule": "supports if levels rate > 5% + 2 SE and returns rate within 2 SE of 5%",
        "verdict": verdict(ok),
        "summary": f"levels reject {lv:.1%} (SE {lv_se:.1%}) of independent pairs; returns reject {rt:.1%} (SE {rt_se:.1%})",
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
