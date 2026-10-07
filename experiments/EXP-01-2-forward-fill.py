"""EXP-01-2: forward-filling a 6-hour outage biases realised volatility down.

Generating process: 1,000 paths (quick: 100) of hourly GBM, log returns N(0, 0.01^2), 169 hourly prices =
168 returns = the 7-day window. In each path 6 consecutive prices are removed (an outage) at a start drawn
uniformly so that the gap lies inside the window. Seed 3.

Treatment: prices forward-filled through the outage (pandas .ffill()), then realised vol = sample standard
deviation of hourly log returns. Control: the gap kept missing; returns that touch a missing price are NaN
and skipped (pandas default). Same estimator in both arms.
Metric: relative bias of realised vol versus the true sigma, mean over paths with SE; the effect is the
paired difference (forward-fill minus gap-aware).
Verdict rule (from blueprint/01-data.md): supports if the forward-fill bias is below 0 by more than 2 SE
and below the gap-aware bias by more than 2 SE (paired). "Both arms show the same bias" = no support.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from experiments._common import main, mean_se, synthetic, verdict  # noqa: E402

META = {
    "id": "EXP-01-2", "backs": "01-data rule 4",
    "claim": "forward-filled outage biases volatility down",
    "script": "experiments/EXP-01-2-forward-fill.py",
    "data": synthetic("hourly GBM, sigma 1% per hour, one 6-hour outage per 7-day window"),
}
SEED, SIGMA, HOURS, GAP = 3, 0.01, 168, 6


def run(quick: bool) -> dict:
    n_paths = 100 if quick else 1_000
    rng = np.random.default_rng(SEED)
    ff, gap = [], []
    for _ in range(n_paths):
        px = pd.Series(100 * np.exp(np.r_[0, np.cumsum(rng.normal(0, SIGMA, HOURS))]))
        start = int(rng.integers(1, HOURS - GAP))  # prices start..start+GAP-1 are lost; both ends observed
        px.iloc[start:start + GAP] = np.nan
        ff.append(np.log(px.ffill()).diff().std() / SIGMA - 1)
        gap.append(np.log(px).diff().std() / SIGMA - 1)
    ff, gap = np.array(ff), np.array(gap)
    ff_m, ff_se = mean_se(ff)
    gap_m, gap_se = mean_se(gap)
    d_m, d_se = mean_se(ff - gap)
    ok = ff_m < -2 * ff_se and d_m < -2 * d_se
    return {
        "inputs": {"paths": n_paths, "hours": HOURS, "outage_hours": GAP, "sigma_per_hour": SIGMA,
                   "estimator": "sample std (ddof=1) of hourly log returns"},
        "seeds": [SEED], "metric": "relative bias of realised vol vs true sigma",
        "treatment": {"arm": "forward-filled outage", "rel_bias": ff_m, "se": ff_se},
        "control": {"arm": "gap kept missing", "rel_bias": gap_m, "se": gap_se},
        "effect": {"estimate": d_m, "se": d_se, "what": "paired difference, forward-fill minus gap-aware"},
        "verdict_rule": "supports if ffill bias < -2 SE and ffill minus gap-aware < -2 SE (paired)",
        "verdict": verdict(ok),
        "summary": (f"forward-fill bias {ff_m:+.2%} (SE {ff_se:.2%}) vs gap-aware {gap_m:+.2%} "
                    f"(SE {gap_se:.2%}); paired difference {d_m:+.2%} (SE {d_se:.2%})"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
