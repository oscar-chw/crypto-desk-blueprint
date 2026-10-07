"""EXP-03-1: a Kalman-filtered hedge ratio tracks a regime shift that a static OLS ratio misses.

Generating process: 200 paths (quick: 20) of 1,000 bars. x is a random walk from 100 with N(0, 1) steps;
y_t = beta_t x_t + u_t with u an AR(1), phi 0.9, N(0, 1) innovations. Break arm: beta = 1.0 for the first
500 bars and 1.5 after. No-break arm: beta = 1.0 throughout. Seed 7.

Treatment: a Kalman filter on y_t = beta_t x_t + v_t, beta_t = beta_{t-1} + w_t, with Q = 1e-4 fixed in
advance and R = the variance of the first-half OLS residuals; the spread at t uses the prior beta_{t|t-1}
(known before y_t). Control: the OLS ratio (no intercept) fitted on the first 500 bars and held fixed.
Metric, on bars 500..999 (out of sample): spread variance and RMS error of the ratio against the true
beta. The effect is the paired mean log ratio of spread variances (Kalman / OLS) with SE across paths.
Verdict rule (from blueprint/03-strategy.md): supports if, with the break, Kalman's log variance ratio is
below 0 by more than 2 SE, and without the break Kalman's spread variance is not clearly worse, stated in
advance as a geometric-mean ratio no more than 1.10.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, mean_se, synthetic, verdict  # noqa: E402

META = {
    "id": "EXP-03-1", "backs": "03-strategy rule 6",
    "claim": "Kalman hedge ratio tracks a regime shift",
    "script": "experiments/EXP-03-1-kalman-hedge.py",
    "data": synthetic("x random walk; y = beta_t x + AR(1) noise; beta 1.0 -> 1.5 at mid-sample"),
}
SEED, N, Q, PHI, NOT_WORSE = 7, 1_000, 1e-4, 0.9, 1.10


def kalman_prior(y: np.ndarray, x: np.ndarray, r: float, q: float) -> np.ndarray:
    """beta_{t|t-1} for every t: the estimate available before y_t is seen."""
    b, p, out = 0.0, 1.0, np.empty(len(y))
    for t in range(len(y)):
        p += q
        out[t] = b
        k = p * x[t] / (x[t] ** 2 * p + r)
        b += k * (y[t] - b * x[t])
        p *= 1 - k * x[t]
    return out


def one_path(rng: np.random.Generator, brk: bool) -> tuple[float, float, float, float]:
    x = 100 + np.cumsum(rng.standard_normal(N))
    u = np.zeros(N)
    e = rng.standard_normal(N)
    for t in range(1, N):
        u[t] = PHI * u[t - 1] + e[t]
    beta = np.where((np.arange(N) >= N // 2) & brk, 1.5, 1.0)
    y = beta * x + u
    h = N // 2
    b_ols = float(x[:h] @ y[:h] / (x[:h] @ x[:h]))
    r = float(np.var(y[:h] - b_ols * x[:h]))
    b_kf = kalman_prior(y, x, r, Q)
    oos = slice(h, None)
    var_k, var_o = np.var(y[oos] - b_kf[oos] * x[oos]), np.var(y[oos] - b_ols * x[oos])
    te_k = float(np.sqrt(np.mean((b_kf[oos] - beta[oos]) ** 2)))
    te_o = float(np.sqrt(np.mean((b_ols - beta[oos]) ** 2)))
    return float(var_k), float(var_o), te_k, te_o


def arm(rng: np.random.Generator, paths: int, brk: bool) -> dict:
    r = np.array([one_path(rng, brk) for _ in range(paths)])
    lr_m, lr_se = mean_se(np.log(r[:, 0] / r[:, 1]))
    te_m, te_se = mean_se(r[:, 2] - r[:, 3])
    return {"kalman_spread_var": float(np.mean(r[:, 0])), "ols_spread_var": float(np.mean(r[:, 1])),
            "log_var_ratio": lr_m, "log_var_ratio_se": lr_se, "gm_var_ratio": float(np.exp(lr_m)),
            "kalman_ratio_rmse": float(np.mean(r[:, 2])), "ols_ratio_rmse": float(np.mean(r[:, 3])),
            "rmse_diff": te_m, "rmse_diff_se": te_se}


def run(quick: bool) -> dict:
    paths = 20 if quick else 200
    rng = np.random.default_rng(SEED)
    brk, flat = arm(rng, paths, True), arm(rng, paths, False)
    ok = brk["log_var_ratio"] < -2 * brk["log_var_ratio_se"] and flat["gm_var_ratio"] <= NOT_WORSE
    return {
        "inputs": {"paths": paths, "bars": N, "q": Q, "noise_ar1_phi": PHI, "break_at": N // 2,
                   "not_worse_threshold": NOT_WORSE},
        "seeds": [SEED], "metric": "out-of-sample spread variance; ratio RMSE vs true beta",
        "treatment": {"arm": "Kalman ratio", "with_break": {k: brk[k] for k in ("kalman_spread_var", "kalman_ratio_rmse")},
                      "no_break": {k: flat[k] for k in ("kalman_spread_var", "kalman_ratio_rmse")}},
        "control": {"arm": "static OLS ratio (first half)",
                    "with_break": {k: brk[k] for k in ("ols_spread_var", "ols_ratio_rmse")},
                    "no_break": {k: flat[k] for k in ("ols_spread_var", "ols_ratio_rmse")}},
        "effect": {"estimate": brk["log_var_ratio"], "se": brk["log_var_ratio_se"],
                   "what": "mean log(Kalman / OLS spread variance) with the break",
                   "no_break_log_var_ratio": flat["log_var_ratio"], "no_break_se": flat["log_var_ratio_se"],
                   "with_break_rmse_diff": brk["rmse_diff"], "with_break_rmse_diff_se": brk["rmse_diff_se"],
                   "no_break_rmse_diff": flat["rmse_diff"], "no_break_rmse_diff_se": flat["rmse_diff_se"]},
        "verdict_rule": "supports if break log var ratio < -2 SE and no-break geometric-mean var ratio <= 1.10",
        "verdict": verdict(ok),
        "summary": (f"after the break Kalman spread variance is {brk['gm_var_ratio']:.2f}x OLS's (ratio RMSE "
                    f"{brk['kalman_ratio_rmse']:.3f} vs {brk['ols_ratio_rmse']:.3f}); with no break "
                    f"{flat['gm_var_ratio']:.2f}x (RMSE {flat['kalman_ratio_rmse']:.3f} vs {flat['ols_ratio_rmse']:.3f})"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
