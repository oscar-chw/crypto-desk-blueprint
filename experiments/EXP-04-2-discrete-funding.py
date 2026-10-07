"""EXP-04-2: accruing perpetual funding continuously misstates P&L for holds shorter than one interval.

Generating process: a perpetual with funding every 8 hours (00, 08, 16 UTC). The rate per interval is an
AR(1): r_k = 1e-4 + 0.9 (r_{k-1} - 1e-4) + e_k, e_k ~ N(0, (5e-5)^2), over 3 years. A long position of
1 unit at a constant mark of 1 (so only funding moves P&L) is held for h = 1..24 hours from a start time
drawn uniformly (continuous) over the sample; 20,000 holds per length (quick: 500). Seed 42.

Control (the venue's rule): discrete payments, pipeline.pricing.funding_cashflow at each funding time in
(start, end]. Treatment: continuous accrual, the prevailing interval's rate times the share of the interval
held. Metric: mean absolute P&L error (treatment minus control) in bps of notional by holding length, with
SE across holds, and the same as a share of the mean absolute accrued funding for that length.
Verdict rule (from blueprint/04-pricing.md): "negligible" = relative error below 10% (a threshold chosen by the author);
supports if the error is not negligible at some holding length (the rule is wrong if it is negligible at
every length). Where the error peaks is reported, not part of the verdict.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, mean_se, synthetic, verdict  # noqa: E402
from pipeline.pricing import funding_cashflow  # noqa: E402

META = {
    "id": "EXP-04-2", "backs": "04-pricing rule 4",
    "claim": "continuous funding accrual misstates short holds",
    "script": "experiments/EXP-04-2-discrete-funding.py",
    "data": synthetic("AR(1) funding rate per 8 h interval, mean 1 bp, phi 0.9, innovation sd 0.5 bp"),
}
SEED, INTERVAL_H, MEAN, PHI, SD, NEGLIGIBLE = 42, 8, 1e-4, 0.9, 5e-5, 0.10


def passes(rel_errors: list[float]) -> bool:
    return max(rel_errors) >= NEGLIGIBLE


def run(quick: bool) -> dict:
    rng = np.random.default_rng(SEED)
    n_int = 3 * 365 * 3
    r = np.empty(n_int)
    r[0] = MEAN
    for k in range(1, n_int):
        r[k] = MEAN + PHI * (r[k - 1] - MEAN) + rng.normal(0, SD)
    n_holds = 500 if quick else 20_000
    horizon_h = (n_int - 4) * INTERVAL_H
    by_len, rel = {}, {}
    for h in range(1, 25):
        start = rng.uniform(0, horizon_h, n_holds)
        end = start + h
        # funding k is paid at time k * 8 h for interval (k-1, k]; discrete = payments at k*8 in (start, end]
        k0, k1 = np.floor(start / INTERVAL_H).astype(int) + 1, np.floor(end / INTERVAL_H).astype(int)
        disc = np.array([sum(funding_cashflow(1.0, 1.0, r[k]) for k in range(a, b + 1)) for a, b in zip(k0, k1)])
        cont = np.zeros(n_holds)
        for j in range(n_holds):  # integrate the prevailing rate over the hold
            t = start[j]
            while t < end[j]:
                k = int(t // INTERVAL_H) + 1  # interval (k-1, k] is paid at funding time k
                seg = min(end[j], k * INTERVAL_H) - t
                cont[j] += funding_cashflow(1.0, 1.0, r[k]) * seg / INTERVAL_H
                t += seg
        m, se = mean_se(np.abs(cont - disc) * 1e4)
        scale = float(np.mean(np.abs(cont)) * 1e4)
        by_len[str(h)] = {"mae_bps": m, "se": se, "mean_abs_accrual_bps": scale, "rel_error": m / scale}
        rel[h] = m / scale
    worst_abs = max(by_len, key=lambda k: by_len[k]["mae_bps"])
    worst_rel = max(rel, key=rel.get)
    ok = passes(list(rel.values()))
    short, long_ = by_len["4"], by_len["8"]
    return {
        "inputs": {"holds_per_length": n_holds, "lengths_h": "1..24", "interval_h": INTERVAL_H,
                   "rate_ar1": {"mean": MEAN, "phi": PHI, "sd": SD}, "negligible_rel_error": NEGLIGIBLE},
        "seeds": [SEED], "metric": "mean |continuous - discrete| funding P&L, bps of notional",
        "treatment": {"arm": "continuous accrual", "by_hold_hours": by_len},
        "control": {"arm": "discrete payments at funding times",
                    "mean_abs_payment_bps": float(np.mean(np.abs(r)) * 1e4)},
        "effect": {"estimate": short["mae_bps"], "se": short["se"], "what": "MAE at a 4-hour hold (bps)",
                   "peak_abs_error_hold_h": int(worst_abs), "peak_rel_error_hold_h": int(worst_rel)},
        "verdict_rule": "supports if relative error >= 10% at some holding length",
        "verdict": verdict(ok),
        "summary": (f"continuous accrual is off by {short['mae_bps']:.2f} bp ({short['rel_error']:.0%} of the funding) "
                    f"on 4-hour holds vs {long_['mae_bps']:.2f} bp ({long_['rel_error']:.0%}) on 8-hour holds; "
                    f"relative error peaks at {worst_rel} h, absolute at {worst_abs} h"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
