"""EXP-00-2: stamping trades by receive time instead of exchange time moves trades across bar edges.

Generating process: trades arrive as a Poisson process at 5 per second for 6 hours (quick: 30 minutes),
seed 2. Trade prices follow a log random walk with 1 bp steps from 30,000. Each trade reaches us after a
lognormal delay with median 50 ms and log-sigma s in {0.5, 1.0, 1.5, 2.0} (larger s = heavier tail; s = 1.0
is taken as the "realistic" case: mean 82 ms, 99th percentile 0.5 s). Bars are 1 minute, cover
(open, close] and are built as pipeline.types.Bar.

Control: bars built on exchange time (misassigned by construction 0). Treatment: bars on receive time.
Metric: share of trades in a different bar than their exchange-time bar (binomial SE), and the mean
absolute difference in bar close (bps).
Verdict rule (from blueprint/00-infrastructure.md): supports if misassignment at s = 1.0 exceeds 0 by more
than 2 SE and rises with s.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, mean_se, prop_se, synthetic, verdict  # noqa: E402
from pipeline.types import NS_PER_SECOND, Bar  # noqa: E402

META = {
    "id": "EXP-00-2", "backs": "00-infrastructure rules 1, 3",
    "claim": "receive-time stamping misassigns trades to bars",
    "script": "experiments/EXP-00-2-receive-time.py",
    "data": synthetic("Poisson trades 5/s, 1 bp log random walk, lognormal delay median 50 ms"),
}
SEED, RATE, BAR_NS, SIGMAS = 2, 5.0, 60 * NS_PER_SECOND, (0.5, 1.0, 1.5, 2.0)


def build_bars(ts_ns: np.ndarray, px: np.ndarray, delay_ns: np.ndarray) -> dict[int, Bar]:
    """Bars keyed by close time from trades stamped at ts_ns (order of arrival = order of ts_ns)."""
    order = np.argsort(ts_ns, kind="stable")
    ts, p = ts_ns[order], px[order]
    close_t = -(-ts // BAR_NS) * BAR_NS  # bar (close - BAR, close] contains t
    out = {}
    edges = np.flatnonzero(np.diff(close_t)) + 1
    for seg_t, seg_p in zip(np.split(close_t, edges), np.split(p, edges)):
        c = int(seg_t[0])
        out[c] = Bar("sim:X:spot", c - BAR_NS, c, float(seg_p[0]), float(seg_p.max()), float(seg_p.min()),
                     float(seg_p[-1]), float(len(seg_p)), c + int(delay_ns.max()))
    return out


def passes(share_real: float, se_real: float, shares_by_tail: list[float]) -> bool:
    return share_real > 2 * se_real and all(a < b for a, b in zip(shares_by_tail, shares_by_tail[1:]))


def run(quick: bool) -> dict:
    rng = np.random.default_rng(SEED)
    seconds = 1_800 if quick else 6 * 3_600
    n = rng.poisson(RATE * seconds)
    exch = np.sort(rng.integers(1, seconds * NS_PER_SECOND, n))
    px = 30_000 * np.exp(np.cumsum(rng.normal(0, 1e-4, n)))
    z = rng.standard_normal(n)  # the same draws for every tail, so arms differ only in s
    exch_bars = build_bars(exch, px, np.zeros(1, dtype=np.int64))
    exch_bin = -(-exch // BAR_NS)
    arms = {}
    for s in SIGMAS:
        delay = (np.exp(np.log(0.05) + s * z) * NS_PER_SECOND).astype(np.int64)
        recv = exch + delay
        share = float(np.mean(-(-recv // BAR_NS) != exch_bin))
        rb = build_bars(recv, px, delay)
        common = sorted(set(rb) & set(exch_bars))
        diff_bps = [abs(rb[c].close / exch_bars[c].close - 1) * 1e4 for c in common]
        m, se = mean_se(diff_bps)
        arms[str(s)] = {"misassigned_share": share, "se": prop_se(share, n), "mean_delay_ms": float(delay.mean() / 1e6),
                        "close_abs_diff_bps": m, "close_abs_diff_se": se}
    real = arms["1.0"]
    ok = passes(real["misassigned_share"], real["se"], [arms[str(s)]["misassigned_share"] for s in SIGMAS])
    return {
        "inputs": {"trades": n, "seconds": seconds, "rate_per_s": RATE, "bar_s": 60, "delay_median_ms": 50,
                   "delay_log_sigmas": list(SIGMAS)},
        "seeds": [SEED], "metric": "share of trades assigned to a different bar; |close diff| in bps",
        "treatment": {"arm": "receive-time bars", "by_delay_log_sigma": arms},
        "control": {"arm": "exchange-time bars", "misassigned_share": 0.0, "close_abs_diff_bps": 0.0},
        "effect": {"estimate": real["misassigned_share"], "se": real["se"], "at": "log-sigma 1.0"},
        "verdict_rule": "supports if misassignment at log-sigma 1.0 > 2 SE above 0 and rises with log-sigma",
        "verdict": verdict(ok),
        "summary": (f"{real['misassigned_share']:.2%} (SE {real['se']:.2%}) of trades land in the wrong 1-min bar at "
                    f"median 50 ms delay, {arms['2.0']['misassigned_share']:.2%} with the heaviest tail; "
                    f"bar closes move {real['close_abs_diff_bps']:.2f} bp on average"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
