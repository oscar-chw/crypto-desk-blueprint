"""EXP-05-2: a daily loss halt and a drawdown budget cut the worst outcomes for a modest median cost.

Generating process: 1,000 paths (quick: 20) of one year (quick: 60 days) of 4-hour returns from
GARCH(1,1) (alpha 0.10, beta 0.85, unconditional vol 3% a day) with standardised t(4) shocks, plus one
negative-drift regime per path: 30 days starting at a uniformly drawn bar, drift -1% a day. The strategy
has no edge: each bar its target weight is drawn from U(0, 1) (long-biased, independent of returns).
Seed 52.

Treatment: every target passes through pipeline.risk.RiskEngine (RiskLimits max_weight 1, max_gross 1, so
the caps never bind; daily_loss_limit 5% -> reduce-only for the rest of the UTC day; max_drawdown 20% ->
kill switch, flat for the rest of the path, since no human re-arms it). Control: the same targets, no limits.
Metric: 99th percentile across paths of max drawdown; median terminal wealth. SEs by paired bootstrap
over paths (500 resamples).
Verdict rule (from blueprint/05-risk.md): supports if the 99th-percentile drawdown with limits is lower
than without by more than 2 SE.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from experiments._common import main, synthetic, verdict
from pipeline.risk import RiskEngine, RiskLimits
from pipeline.types import NS_PER_HOUR, TargetPortfolio

META = {
    "id": "EXP-05-2", "backs": "05-risk rules 4-6",
    "claim": "loss halt and drawdown budget cut the worst outcomes",
    "script": "experiments/EXP-05-2-loss-limits.py",
    "data": synthetic("GARCH(1,1)-t(4) 4-hour returns with a 30-day -1%/day regime; U(0,1) target weights"),
}
SEED, BARS_PER_DAY, BAR_NS = 52, 6, 4 * NS_PER_HOUR
LIMITS = RiskLimits(max_weight=1.0, max_gross=1.0, max_drawdown=0.20, daily_loss_limit=0.05)


def returns(rng: np.random.Generator, days: int) -> np.ndarray:
    n, alpha, beta = days * BARS_PER_DAY, 0.10, 0.85
    unc = 0.03**2 / BARS_PER_DAY
    var, out = unc, np.empty(n)
    for t in range(n):
        out[t] = np.sqrt(var) * rng.standard_t(4) / np.sqrt(2.0)
        var = unc * (1 - alpha - beta) + alpha * out[t] ** 2 + beta * var
    start = int(rng.integers(0, max(1, n - 30 * BARS_PER_DAY)))
    out[start:start + 30 * BARS_PER_DAY] -= 0.01 / BARS_PER_DAY
    return out


def simulate(r: np.ndarray, u: np.ndarray, gate: RiskEngine | None) -> tuple[float, float, int]:
    eq, peak, mdd, w_cur, halts = 1.0, 1.0, 0.0, 0.0, 0
    for t in range(len(r)):
        w = u[t]
        if gate is not None:
            ts = t * BAR_NS
            gate.update_equity(ts, eq)
            dec = gate.check(TargetPortfolio(ts, {"X": w}), {"X": w_cur})
            w = dec.target.weights["X"]
            halts += dec.halted
        eq *= 1 + w * r[t]
        w_cur = w * (1 + r[t]) / (1 + w * r[t])
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    return mdd, eq, halts


def passes(dd_diff: float, se: float) -> bool:
    return dd_diff < -2 * se


def run(quick: bool) -> dict:
    paths, days = (20, 60) if quick else (1_000, 365)
    rng = np.random.default_rng(SEED)
    logging.getLogger("pipeline.risk").setLevel(logging.CRITICAL + 1)  # one kill-switch log line per path
    res, kills, halt_bars = [], 0, 0
    for _ in range(paths):
        r, u = returns(rng, days), rng.uniform(0, 1, days * BARS_PER_DAY)
        gate = RiskEngine(LIMITS)
        lim = simulate(r, u, gate)
        kills += gate.kill_switch.tripped
        halt_bars += lim[2]
        res.append((*lim[:2], *simulate(r, u, None)[:2]))
    res = np.array(res)  # columns: dd_lim, eq_lim, dd_none, eq_none
    q = lambda x: float(np.quantile(x, 0.99))  # noqa: E731
    boots = []
    for _ in range(500):
        i = rng.integers(0, paths, paths)
        boots.append((q(res[i, 0]) - q(res[i, 2]), np.median(res[i, 1]) - np.median(res[i, 3]),
                      q(res[i, 0]), q(res[i, 2]), np.median(res[i, 1]), np.median(res[i, 3])))
    sd = np.std(np.array(boots), axis=0, ddof=1)
    dd_diff = q(res[:, 0]) - q(res[:, 2])
    med_diff = float(np.median(res[:, 1]) - np.median(res[:, 3]))
    ok = passes(dd_diff, float(sd[0]))
    return {
        "inputs": {"paths": paths, "days": days, "bar_hours": 4, "limits": LIMITS.__dict__,
                   "regime": "30 days at -1%/day, random start"},
        "seeds": [SEED], "metric": "99th percentile max drawdown; median terminal wealth (start 1.0)",
        "treatment": {"arm": "RiskEngine: 5% daily halt + 20% drawdown kill switch",
                      "max_dd_p99": q(res[:, 0]), "se": float(sd[2]), "median_terminal": float(np.median(res[:, 1])),
                      "median_terminal_se": float(sd[4]), "share_paths_killed": kills / paths,
                      "share_bars_halted": halt_bars / (paths * days * BARS_PER_DAY)},
        "control": {"arm": "no limits", "max_dd_p99": q(res[:, 2]), "se": float(sd[3]),
                    "median_terminal": float(np.median(res[:, 3])), "median_terminal_se": float(sd[5])},
        "effect": {"estimate": dd_diff, "se": float(sd[0]), "what": "p99 max drawdown, limits minus none",
                   "median_terminal_diff": med_diff, "median_terminal_diff_se": float(sd[1])},
        "verdict_rule": "supports if p99 drawdown (limits) - p99 drawdown (none) < -2 SE (paired bootstrap)",
        "verdict": verdict(ok),
        "summary": (f"p99 max drawdown {q(res[:, 0]):.0%} with limits vs {q(res[:, 2]):.0%} without "
                    f"(diff SE {sd[0]:.1%}); median terminal wealth {np.median(res[:, 1]):.3f} vs "
                    f"{np.median(res[:, 3]):.3f} (diff {med_diff:+.3f}, SE {sd[1]:.3f}); "
                    f"kill switch tripped on {kills / paths:.0%} of paths"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
