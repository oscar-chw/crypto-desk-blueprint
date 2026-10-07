"""EXP-06-2: Black-Litterman weights move far less than mean-variance weights when views are noisy.

Generating process: 10 assets with a known one-factor covariance (annual factor vol 60%, betas evenly
0.8..1.4, idiosyncratic vols evenly 30%..60%), market-cap weights from a Dirichlet(2, ..., 2) draw, risk
aversion delta = 2.5, equilibrium returns Pi = delta * Sigma * w_mkt, and true means equal to Pi. Each of
500 rebalances (quick: 50) receives views Q = true means + N(0, 0.10^2) per asset, independently. Seed 62.

Control: mean-variance, w = (delta Sigma)^-1 Q. Treatment: Black-Litterman with absolute views on every
asset (P = I), Omega = diag(0.10^2) (the true view noise), tau = 0.05, w = (delta Sigma)^-1 mu_BL.
Both weight vectors are scaled to gross 1, so the comparison is about allocation, not leverage.
Metric: mean L1 distance between successive weight vectors (turnover) with SE, paired; mean largest |weight|.
Verdict rule (from blueprint/06-portfolio.md): supports if BL turnover is lower than MV turnover by more
than 2 SE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from experiments._common import main, mean_se, synthetic, verdict

META = {
    "id": "EXP-06-2", "backs": "06-portfolio rules 4, 5",
    "claim": "Black-Litterman weights are stable under noisy views",
    "script": "experiments/EXP-06-2-black-litterman.py",
    "data": synthetic("10 assets, one-factor covariance, true means = equilibrium, views = truth + N(0, 0.1^2)"),
}
SEED, N, DELTA, TAU, VIEW_SD = 62, 10, 2.5, 0.05, 0.10


def gross_one(w: np.ndarray) -> np.ndarray:
    return w / np.abs(w).sum()


def passes(diff: float, se: float) -> bool:
    return diff < -2 * se


def run(quick: bool) -> dict:
    draws = 50 if quick else 500
    rng = np.random.default_rng(SEED)
    beta, idio = np.linspace(0.8, 1.4, N), np.linspace(0.3, 0.6, N)
    sigma = 0.6**2 * np.outer(beta, beta) + np.diag(idio**2)
    w_mkt = rng.dirichlet(np.full(N, 2.0))
    pi = DELTA * sigma @ w_mkt
    inv_ts, inv_om = np.linalg.inv(TAU * sigma), np.eye(N) / VIEW_SD**2
    post = np.linalg.inv(inv_ts + inv_om)
    inv_ds = np.linalg.inv(DELTA * sigma)
    mv, bl = [], []
    for _ in range(draws):
        q = pi + rng.normal(0, VIEW_SD, N)
        mv.append(gross_one(inv_ds @ q))
        bl.append(gross_one(inv_ds @ (post @ (inv_ts @ pi + inv_om @ q))))
    mv, bl = np.array(mv), np.array(bl)
    l1_mv, l1_bl = np.abs(np.diff(mv, axis=0)).sum(axis=1), np.abs(np.diff(bl, axis=0)).sum(axis=1)
    mv_m, mv_se = mean_se(l1_mv)
    bl_m, bl_se = mean_se(l1_bl)
    d_m, d_se = mean_se(l1_bl - l1_mv)
    ok = passes(d_m, d_se)
    return {
        "inputs": {"assets": N, "rebalances": draws, "delta": DELTA, "tau": TAU, "view_noise_sd": VIEW_SD,
                   "normalisation": "gross 1"},
        "seeds": [SEED], "metric": "mean L1 distance between successive weights; mean max |weight|",
        "treatment": {"arm": "Black-Litterman", "turnover_l1": bl_m, "se": bl_se,
                      "max_abs_weight": float(np.abs(bl).max(axis=1).mean()),
                      "l1_to_market": float(np.abs(bl - w_mkt).sum(axis=1).mean())},
        "control": {"arm": "mean-variance", "turnover_l1": mv_m, "se": mv_se,
                    "max_abs_weight": float(np.abs(mv).max(axis=1).mean()),
                    "l1_to_market": float(np.abs(mv - w_mkt).sum(axis=1).mean())},
        "effect": {"estimate": d_m, "se": d_se, "what": "paired BL minus MV turnover (L1)"},
        "verdict_rule": "supports if BL turnover - MV turnover < -2 SE (paired)",
        "verdict": verdict(ok),
        "summary": (f"turnover per rebalance {bl_m:.2f} (BL) vs {mv_m:.2f} (MV) in L1 at gross 1; largest weight "
                    f"{np.abs(bl).max(axis=1).mean():.2f} vs {np.abs(mv).max(axis=1).mean():.2f}"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
