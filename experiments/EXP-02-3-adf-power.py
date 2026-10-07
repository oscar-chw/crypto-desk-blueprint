"""EXP-02-3: the ADF test has low power against a persistent but stationary series.

Generating process: AR(1) y_t = phi y_{t-1} + e_t, e_t ~ N(0, 1), started from its stationary
distribution (y_0 = 0 for phi = 1). phi in {0.98 (treatment), 1.0 (unit root: checks the test's size),
0.5 (control)}; lengths 250, 500, 1,000, 2,500, 5,000; 1,000 series per cell (quick: 50, lengths 250
and 1,000). Seed 6.

Tests: ADF with a constant and int(4 (T/100)^0.25) lagged differences, 5% MacKinnon (2010) critical value;
KPSS (level) with a Bartlett long-run variance and int(12 (T/100)^0.25) lags, 5% critical value 0.463.
Metric: rejection rate per cell with binomial SE. For ADF a rejection is the right answer when phi < 1;
for KPSS a rejection is the wrong answer when phi < 1.
Verdict rule (from blueprint/02-features.md): "high power" = rejection rate >= 0.80; supports if ADF power
at phi 0.98 is below 0.80 at some length (the rule is wrong if it is high at every length).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, prop_se, synthetic, verdict  # noqa: E402
from experiments._tsa import KPSS_5PCT_LEVEL, adf_rejects, kpss_stat, schwert_lags  # noqa: E402

META = {
    "id": "EXP-02-3", "backs": "02-features rule 4",
    "claim": "ADF has low power near a unit root",
    "script": "experiments/EXP-02-3-adf-power.py",
    "data": synthetic("Gaussian AR(1), phi 0.98 / 1.0 / 0.5"),
}
SEED, PHIS, HIGH_POWER = 6, (0.98, 1.0, 0.5), 0.80


def ar1(rng: np.random.Generator, phi: float, n: int) -> np.ndarray:
    e = rng.standard_normal(n)
    y = np.empty(n)
    y[0] = e[0] / np.sqrt(1 - phi**2) if phi < 1 else 0.0
    for t in range(1, n):
        y[t] = phi * y[t - 1] + e[t]
    return y


def passes(power_by_length: list[float]) -> bool:
    return any(p < HIGH_POWER for p in power_by_length)


def run(quick: bool) -> dict:
    reps, lengths = (50, (250, 1_000)) if quick else (1_000, (250, 500, 1_000, 2_500, 5_000))
    rng = np.random.default_rng(SEED)
    cells = {}
    for phi in PHIS:
        for n in lengths:
            adf = kpss = 0
            for _ in range(reps):
                y = ar1(rng, phi, n)
                adf += adf_rejects(y, schwert_lags(n, 4))
                kpss += kpss_stat(y, schwert_lags(n, 12)) > KPSS_5PCT_LEVEL
            a, k = adf / reps, kpss / reps
            cells.setdefault(str(phi), {})[str(n)] = {"adf_reject": a, "adf_se": prop_se(a, reps),
                                                      "kpss_reject": k, "kpss_se": prop_se(k, reps)}
    p98 = cells["0.98"]
    short = str(lengths[0])
    ok = passes([c["adf_reject"] for c in p98.values()])
    weak = [n for n, c in p98.items() if c["adf_reject"] < HIGH_POWER]
    return {
        "inputs": {"reps_per_cell": reps, "lengths": list(lengths), "phis": list(PHIS),
                   "adf_lags": "int(4 (T/100)^0.25)", "kpss_lags": "int(12 (T/100)^0.25)"},
        "seeds": [SEED], "metric": "rejection rate at 5% per (phi, length)",
        "treatment": {"arm": "phi 0.98 (stationary, persistent)", "by_length": p98},
        "control": {"arm": "phi 0.5", "by_length": cells["0.5"],
                    "size_check_phi_1": cells["1.0"]},
        "effect": {"estimate": p98[short]["adf_reject"], "se": p98[short]["adf_se"],
                   "what": f"ADF power at phi 0.98, T = {short}"},
        "verdict_rule": "supports if ADF power at phi 0.98 < 0.80 at some length",
        "verdict": verdict(ok),
        "summary": (f"ADF power at phi 0.98: {p98[short]['adf_reject']:.0%} at T = {short}, "
                    f"{p98[str(lengths[-1])]['adf_reject']:.0%} at T = {lengths[-1]} (below 80% at T = {', '.join(weak) or 'none'}); "
                    f"phi 0.5: {cells['0.5'][short]['adf_reject']:.0%}; size at phi 1: "
                    f"{cells['1.0'][short]['adf_reject']:.1%}"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
