"""EXP-05-3: a dollar-neutral altcoin book still carries BTC beta; a beta-neutral one does not.

Generating process: one-factor daily returns, r_i = beta_i * r_BTC + e_i, r_BTC ~ N(0, 0.03^2),
e_i ~ N(0, 0.03^2), 10 altcoins with beta_i evenly spaced from 0.6 to 1.6. 500 books (quick: 50); each
draws 5 longs and 5 shorts at random (a signal with no information), estimates betas by OLS on 250 days,
then holds for 250 out-of-sample days. Seed 53.

Control: dollar-neutral weights, +1/5 on each long and -1/5 on each short. Treatment: beta-neutral, the
short leg rescaled so that the estimated book beta is 0. Metric: |realised beta| of the out-of-sample book
returns on BTC returns (OLS slope), mean over books with SE; paired difference.
Verdict rule (from blueprint/05-risk.md): supports if mean |beta| of the dollar-neutral book exceeds that
of the beta-neutral book by more than 2 SE (the rule is wrong if both are near 0).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, mean_se, synthetic, verdict  # noqa: E402
from pipeline.types import TargetPortfolio  # noqa: E402

META = {
    "id": "EXP-05-3", "backs": "05-risk rule 7",
    "claim": "dollar-neutral altcoin book keeps BTC beta",
    "script": "experiments/EXP-05-3-beta-neutral.py",
    "data": synthetic("one-factor returns, beta 0.6..1.6, BTC and idiosyncratic vol 3%/day"),
}
SEED, N, EST, OOS, VOL = 53, 10, 250, 250, 0.03
BETAS = np.linspace(0.6, 1.6, N)


def slope(y: np.ndarray, x: np.ndarray) -> float:
    xc = x - x.mean()
    return float(xc @ (y - y.mean()) / (xc @ xc))


def run(quick: bool) -> dict:
    books = 50 if quick else 500
    rng = np.random.default_rng(SEED)
    dn, bn = [], []
    for b in range(books):
        btc = rng.normal(0, VOL, EST + OOS)
        r = btc[:, None] * BETAS[None, :] + rng.normal(0, VOL, (EST + OOS, N))
        side = rng.permutation(np.r_[np.ones(N // 2), -np.ones(N // 2)])
        b_hat = np.array([slope(r[:EST, i], btc[:EST]) for i in range(N)])
        w_dn = side / (N // 2)
        w_bn = w_dn.copy()
        short = side < 0
        w_bn[short] *= (w_dn[~short] @ b_hat[~short]) / (-(w_dn[short] @ b_hat[short]))
        for w, out in ((w_dn, dn), (w_bn, bn)):
            tp = TargetPortfolio(b, {f"ALT{i}": float(w[i]) for i in range(N)})  # validated weights
            wv = np.array([tp.weights[f"ALT{i}"] for i in range(N)])
            out.append(abs(slope(r[EST:] @ wv, btc[EST:])))
    dn_m, dn_se = mean_se(dn)
    bn_m, bn_se = mean_se(bn)
    d_m, d_se = mean_se(np.array(dn) - np.array(bn))
    ok = d_m > 2 * d_se
    return {
        "inputs": {"books": books, "coins": N, "betas": "0.6..1.6", "estimation_days": EST, "oos_days": OOS},
        "seeds": [SEED], "metric": "|realised out-of-sample beta of the book to BTC|",
        "treatment": {"arm": "beta-neutral (estimated betas)", "mean_abs_beta": bn_m, "se": bn_se},
        "control": {"arm": "dollar-neutral", "mean_abs_beta": dn_m, "se": dn_se},
        "effect": {"estimate": d_m, "se": d_se, "what": "paired dollar-neutral minus beta-neutral |beta|"},
        "verdict_rule": "supports if mean |beta| dollar-neutral - beta-neutral > 2 SE",
        "verdict": verdict(ok),
        "summary": f"mean absolute BTC beta {dn_m:.3f} dollar-neutral vs {bn_m:.3f} beta-neutral (paired diff SE {d_se:.3f})",
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
