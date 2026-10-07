"""EXP-07-2: for orders larger than the top of the book, slicing under a participation cap lowers
implementation shortfall, at the price of more timing risk.

Generating process: a synthetic ask book quoted relative to mid, one level per 1 bp, depth at level k
D_k = D0 (1 + 0.1 (k - 1)) with D0 = 1 unit (the top-of-book depth), 400 levels. After each step every
level refills 20% of its missing depth (exponential resilience). Mid follows an arithmetic random walk
with N(0, 1 bp^2) steps and no drift (no alpha decay, no permanent impact). Parent buy orders of
0.1, 0.5, 1, 2 and 5 x D0; 2,000 simulations per size (quick: 100). Seed 72.

Control: one market order at step 0 that walks the full book. Treatment: slicing, one child market order
per step of at most 0.5 x D0 (participation cap), each walking the current, partly refilled book.
Metric: implementation shortfall against the arrival mid, in bps: mean and standard deviation; SE of the
mean difference across simulations (the single order is deterministic here).
Verdict rule (from blueprint/07-execution.md): supports if, at 2x and 5x top-of-book depth, sliced mean
shortfall is below the single order's by more than 2 SE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from experiments._common import main, mean_se, synthetic, verdict

META = {
    "id": "EXP-07-2", "backs": "07-execution rule 5",
    "claim": "slicing beats one market order for large orders",
    "script": "experiments/EXP-07-2-slicing.py",
    "data": synthetic("1 bp ladder, depth D0 (1 + 0.1 (k-1)), 20% refill per step, mid RW 1 bp per step"),
}
SEED, LEVELS, REFILL, CAP, MID_BP = 72, 400, 0.20, 0.5, 1.0
PROFILE = 1.0 + 0.1 * np.arange(LEVELS)
SIZES = (0.1, 0.5, 1.0, 2.0, 5.0)


def walk(book: np.ndarray, qty: float) -> float:
    """Take qty from the book in place; return the cost in bps above mid (sum of qty x level offset)."""
    cost, k = 0.0, 0
    while qty > 1e-12:
        take = min(qty, book[k])
        book[k] -= take
        cost += take * (k + 1)
        qty -= take
        k += 1
    return cost


def single(qty: float) -> float:
    return walk(PROFILE.copy(), qty) / qty


def sliced(qty: float, rng: np.random.Generator) -> float:
    book, mid, left, cost = PROFILE.copy(), 0.0, qty, 0.0
    while left > 1e-12:
        child = min(left, CAP * PROFILE[0])
        cost += child * mid + walk(book, child)
        left -= child
        book += REFILL * (PROFILE - book)
        mid += rng.normal(0, MID_BP)
    return cost / qty


def passes(single_minus_sliced_and_se: list[tuple[float, float]]) -> bool:
    return all(g > 2 * se for g, se in single_minus_sliced_and_se)


def run(quick: bool) -> dict:
    sims = 100 if quick else 2_000
    rng = np.random.default_rng(SEED)
    treat, ctrl, ok = {}, {}, True
    for q in SIZES:
        s = np.array([sliced(q, rng) for _ in range(sims)])
        one = single(q)
        m, se = mean_se(s)
        treat[str(q)] = {"mean_bps": m, "se": se, "sd_bps": float(s.std(ddof=1)), "children": int(np.ceil(q / CAP))}
        ctrl[str(q)] = {"mean_bps": one, "sd_bps": 0.0}
        if q >= 2:
            ok &= passes([(one - m, se)])
    big = str(SIZES[-1])
    return {
        "inputs": {"sims_per_size": sims, "sizes_x_top_depth": list(SIZES), "levels": LEVELS, "refill_per_step": REFILL,
                   "child_cap_x_top_depth": CAP, "mid_step_bps": MID_BP},
        "seeds": [SEED], "metric": "implementation shortfall vs arrival mid (bps): mean and sd",
        "treatment": {"arm": "sliced, child <= 0.5 x top depth per step", "by_size": treat},
        "control": {"arm": "one market order", "by_size": ctrl},
        "effect": {"estimate": treat[big]["mean_bps"] - ctrl[big]["mean_bps"], "se": treat[big]["se"],
                   "what": "sliced minus single mean shortfall at 5x top depth"},
        "verdict_rule": "supports if sliced mean shortfall < single by > 2 SE at 2x and 5x top-of-book depth",
        "verdict": verdict(ok),
        "summary": (f"at 5x top depth: sliced {treat[big]['mean_bps']:.2f} bp (sd {treat[big]['sd_bps']:.2f}) vs single "
                    f"{ctrl[big]['mean_bps']:.2f} bp (sd 0); at 0.1x: {treat['0.1']['mean_bps']:.2f} vs "
                    f"{ctrl['0.1']['mean_bps']:.2f} bp"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
