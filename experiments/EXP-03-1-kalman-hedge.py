"""EXP-03-1: a Kalman-filtered hedge ratio tracks a regime shift that a static OLS ratio misses, and is
no worse than OLS when there is no shift.

Generating process: 200 paths (quick: 20) of 1,000 bars. x is a random walk from 100 with N(0, 1) steps;
y_t = beta_t x_t + u_t with u an AR(1), phi 0.9, N(0, 1) innovations. Break arm: beta = 1.0 for the first
500 bars and 1.5 after. No-break arm: beta = 1.0 throughout. Seed 7.

Treatment: a Kalman filter on y_t = beta_t x_t + v_t, beta_t = beta_{t-1} + w_t, with Q = 1e-4 and
R = the variance of the first-half OLS residuals; the spread at t uses the prior beta_{t|t-1} (known before
y_t). Control: the OLS ratio (no intercept) fitted on the first 500 bars and held fixed.
Metrics, on bars 500..999 (out of sample): RMS error of the ratio against the true beta (tracking error,
the verdict metric), spread variance, and the spread's lag-1 autocorrelation next to the true noise's 0.9
(a filter that absorbs the noise into the ratio shows a lower autocorrelation: it removes the mean
reversion a pairs trade lives on). Paired differences with SE across paths.
Verdict rule (from blueprint/03-strategy.md): supports if Kalman's tracking error is below OLS's by more
than 2 SE with the break, and not above OLS's by more than 2 SE without it. Failing only the second leg is
reported as "mixed: Kalman wins only after a break".
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
SEED, N, Q, PHI = 7, 1_000, 1e-4, 0.9


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


def acf1(z: np.ndarray) -> float:
    z = z - z.mean()
    return float(z[1:] @ z[:-1] / (z @ z))


def one_path(rng: np.random.Generator, brk: bool) -> tuple[float, ...]:
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
    s_k, s_o = y[oos] - b_kf[oos] * x[oos], y[oos] - b_ols * x[oos]
    te_k = float(np.sqrt(np.mean((b_kf[oos] - beta[oos]) ** 2)))
    te_o = float(np.sqrt(np.mean((b_ols - beta[oos]) ** 2)))
    return te_k, te_o, float(np.var(s_k)), float(np.var(s_o)), acf1(s_k), acf1(s_o)


def arm(rng: np.random.Generator, paths: int, brk: bool) -> dict:
    r = np.array([one_path(rng, brk) for _ in range(paths)])
    out = {}
    for j, name in enumerate(("ratio_rmse", "spread_var", "spread_acf1")):
        d_m, d_se = mean_se(r[:, 2 * j] - r[:, 2 * j + 1])
        out[name] = {"kalman": float(r[:, 2 * j].mean()), "ols": float(r[:, 2 * j + 1].mean()), "diff": d_m, "se": d_se}
    return out


def passes(brk_diff: float, brk_se: float, flat_diff: float, flat_se: float) -> bool:
    """Tracking-error differences, Kalman minus OLS, with and without the break."""
    return brk_diff < -2 * brk_se and flat_diff <= 2 * flat_se


def run(quick: bool) -> dict:
    paths = 20 if quick else 200
    rng = np.random.default_rng(SEED)
    brk, flat = arm(rng, paths, True), arm(rng, paths, False)
    b, f = brk["ratio_rmse"], flat["ratio_rmse"]
    ok = passes(b["diff"], b["se"], f["diff"], f["se"])
    mixed = b["diff"] < -2 * b["se"] and not ok
    label = "supports" if ok else ("mixed: Kalman wins only after a break" if mixed else "does not support")

    def side(k: str) -> dict:
        return {arm_name: {m: a[m][k] for m in a} for arm_name, a in (("with_break", brk), ("no_break", flat))}
    return {
        "inputs": {"paths": paths, "bars": N, "q": Q, "noise_ar1_phi": PHI, "break_at": N // 2},
        "seeds": [SEED], "metric": "out-of-sample ratio RMSE vs true beta (verdict); spread variance; spread lag-1 autocorrelation",
        "treatment": {"arm": "Kalman ratio", **side("kalman")},
        "control": {"arm": "static OLS ratio (first half)", **side("ols")},
        "effect": {"estimate": b["diff"], "se": b["se"], "what": "ratio RMSE, Kalman minus OLS, with the break",
                   "no_break_rmse_diff": f["diff"], "no_break_rmse_diff_se": f["se"], "outcome": label,
                   "with_break": brk, "no_break": flat},
        "verdict_rule": "supports if Kalman minus OLS ratio RMSE < -2 SE with the break and <= +2 SE without it",
        "verdict": verdict(ok),
        "summary": (f"{label}. Ratio RMSE with the break {b['kalman']:.3f} Kalman vs {b['ols']:.3f} OLS; without it "
                    f"{f['kalman']:.3f} vs {f['ols']:.3f} (diff SE {f['se']:.4f}). Without a break the Kalman spread's "
                    f"lag-1 autocorrelation is {flat['spread_acf1']['kalman']:.2f} vs {flat['spread_acf1']['ols']:.2f} "
                    f"for OLS (true noise 0.90): the filter absorbs part of the mean reversion"),
    }

if __name__ == "__main__":
    sys.exit(main(META, run))
