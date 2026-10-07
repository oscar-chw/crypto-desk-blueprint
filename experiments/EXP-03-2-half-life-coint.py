"""EXP-03-2: an AR(1) fit recovers a known Ornstein-Uhlenbeck half-life, and the Engle-Granger
cointegration test rejects unrelated random walks at about its nominal 5%.

Generating process, part A: OU spreads sampled exactly at unit steps, z_t = e^{-theta} z_{t-1} + eps_t,
eps ~ N(0, 1), z_0 from the stationary law, 2,000 bars, true half-lives 5, 20 and 50 bars (theta =
ln 2 / half-life); 1,000 paths per half-life (quick: 50). Part B: 1,000 pairs (quick: 100) of independent
Gaussian random walks, 500 steps (never cointegrated). Seed 8.

Part A treatment: regress dz_t on [1, z_{t-1}], theta_hat = -ln(1 + b), half-life = ln 2 / theta_hat;
control: the known half-life. Paths with theta_hat <= 0 are counted and excluded. Kendall's (1954)
approximation of the AR(1) estimator's bias, E[a_hat - a] ~ -(1 + 3a)/n, is reported as a reference.
Part B treatment: Engle-Granger (OLS y on [1, x], ADF with int(4 (T/100)^0.25) lags on the residuals,
MacKinnon 2010 two-variable 5% critical value); control: the nominal 5% size. Also reported, not part of
the verdict: the same residual ADF judged with the one-variable ADF critical value (a common mistake).
Verdict rule (from blueprint/03-strategy.md): supports if every half-life's mean estimation error is within
2 SE of 0 and the Engle-Granger false-rejection rate is not above 5% by more than 2 SE.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, mean_se, prop_se, synthetic, verdict  # noqa: E402
from experiments._tsa import engle_granger_t, mackinnon_cv5, schwert_lags  # noqa: E402

META = {
    "id": "EXP-03-2", "backs": "03-strategy rule 5",
    "claim": "half-life recovers OU speed; cointegration test holds its size",
    "script": "experiments/EXP-03-2-half-life-coint.py",
    "data": synthetic("exact-discretised OU spreads; independent random-walk pairs"),
}
SEED, BARS, HALF_LIVES, STEPS = 8, 2_000, (5, 20, 50), 500


def ou(rng: np.random.Generator, theta: float, n: int) -> np.ndarray:
    a = math.exp(-theta)
    e = rng.standard_normal(n)
    z = np.empty(n)
    z[0] = e[0] / math.sqrt(1 - a * a)
    for t in range(1, n):
        z[t] = a * z[t - 1] + e[t]
    return z


def est_half_life(z: np.ndarray) -> float:
    X = np.column_stack([np.ones(len(z) - 1), z[:-1]])
    b = np.linalg.lstsq(X, np.diff(z), rcond=None)[0][1]
    theta = -math.log1p(b) if b > -1 else math.inf
    return math.log(2) / theta if theta > 0 else math.nan


def run(quick: bool) -> dict:
    paths, pairs = (50, 100) if quick else (1_000, 1_000)
    rng = np.random.default_rng(SEED)
    hl = {}
    for h in HALF_LIVES:
        est = np.array([est_half_life(ou(rng, math.log(2) / h, BARS)) for _ in range(paths)])
        good = est[np.isfinite(est)]
        m, se = mean_se(good - h)
        a = math.exp(-math.log(2) / h)
        kendall = math.log(2) / -math.log(a - (1 + 3 * a) / BARS) / h - 1  # E[a_hat - a] ~ -(1 + 3a)/n
        hl[str(h)] = {"true": h, "kendall_rel_bias": kendall, "mean_estimate": float(good.mean()), "mean_error": m, "se": se,
                      "rel_bias": m / h, "median_estimate": float(np.median(good)), "excluded": int(paths - len(good))}
    eg_rej = naive_rej = 0
    for _ in range(pairs):
        x, y = np.cumsum(rng.standard_normal((2, STEPS)), axis=1)
        t, nobs = engle_granger_t(y, x, schwert_lags(STEPS))
        eg_rej += t < mackinnon_cv5(2, nobs)
        naive_rej += t < mackinnon_cv5(1, nobs)
    eg, naive = eg_rej / pairs, naive_rej / pairs
    eg_se = prop_se(eg, pairs)
    hl_ok = all(abs(c["mean_error"]) <= 2 * c["se"] for c in hl.values())
    size_ok = eg - 0.05 <= 2 * prop_se(0.05, pairs)
    bias_txt = ", ".join(f"{c['rel_bias']:+.1%} at {k}" for k, c in hl.items())
    worst = max(hl.values(), key=lambda c: abs(c["mean_error"]) / c["se"])
    return {
        "inputs": {"ou_paths_per_half_life": paths, "ou_bars": BARS, "half_lives": list(HALF_LIVES),
                   "rw_pairs": pairs, "rw_steps": STEPS},
        "seeds": [SEED], "metric": "half-life estimation error (bars); false-rejection rate at 5%",
        "treatment": {"arm": "AR(1) half-life; Engle-Granger test", "half_life": hl,
                      "eg_false_rejection": eg, "eg_se": eg_se,
                      "naive_adf_cv_false_rejection": naive, "naive_se": prop_se(naive, pairs)},
        "control": {"arm": "known half-life; nominal size", "half_lives": list(HALF_LIVES), "nominal_size": 0.05},
        "effect": {"estimate": worst["mean_error"], "se": worst["se"],
                   "what": f"mean half-life error at true half-life {worst['true']}",
                   "eg_size_minus_nominal": eg - 0.05, "eg_size_se": eg_se},
        "verdict_rule": "supports if every mean half-life error is within 2 SE of 0 and EG size <= 5% + 2 SE",
        "verdict": verdict(hl_ok and size_ok),
        "summary": (f"half-life error {bias_txt} "
                    f"(worst {abs(worst['mean_error']) / worst['se']:.1f} SE; Kendall's AR(1) bias formula predicts "
                    f"{hl[str(HALF_LIVES[-1])]['kendall_rel_bias']:+.1%} at {HALF_LIVES[-1]}); Engle-Granger size {eg:.1%} "
                    f"(SE {eg_se:.1%}), {naive:.1%} with the plain ADF critical value"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
