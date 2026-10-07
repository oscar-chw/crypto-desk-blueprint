"""EXP-06-1: half-Kelly keeps most of full Kelly's growth with far smaller drawdowns, and beats full Kelly
once the edge is overestimated.

Generating process: 10,000 paths (quick: 500) of 1,000 iid bets (quick: 250), per-period excess return
N(mu = 0.0005, sigma = 0.01), so the true Kelly leverage is mu / sigma^2 = 5 (pipeline.sizing.kelly_leverage).
Wealth compounds as W_t = W_{t-1} (1 + f r_t). Every arm sees the same returns. Seed 61.
Sizing inputs: true edge; estimated edge mu_hat = mu + N(0, (mu/2)^2) drawn once per path (noise of known
size); overestimated edge mu_hat = 2 mu.

Treatment: half Kelly, f = 0.5 * kelly_leverage(mu_hat, sigma^2). Control: full Kelly from the same input.
Metric: median log growth per period; median and 95th percentile of max drawdown. SEs by paired bootstrap
over paths (300 resamples).
Verdict rule (from blueprint/06-portfolio.md): supports if, for all three inputs, half Kelly's 95th-percentile
max drawdown is below full Kelly's by more than 2 SE. Growth ratios are reported, not part of the verdict.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from experiments._common import main, synthetic, verdict  # noqa: E402
from pipeline.sizing import kelly_leverage  # noqa: E402

META = {
    "id": "EXP-06-1", "backs": "06-portfolio rule 1",
    "claim": "half-Kelly: most of the growth, far smaller drawdowns",
    "script": "experiments/EXP-06-1-half-kelly.py",
    "data": synthetic("iid normal bets, mu 0.0005, sigma 0.01 per period"),
}
SEED, MU, SIGMA = 61, 0.0005, 0.01
QS = [round(q, 2) for q in np.linspace(0.01, 0.99, 99)]


def path_stats(r: np.ndarray, f: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gross = 1 + f[None, :] * r
    logw = np.cumsum(np.log(np.maximum(gross, 1e-300)), axis=0)
    dd = 1 - np.exp(logw - np.maximum.accumulate(np.maximum(logw, 0), axis=0))
    return logw[-1] / len(r), dd.max(axis=0)


def run(quick: bool) -> dict:
    paths, n = (500, 250) if quick else (10_000, 1_000)
    rng = np.random.default_rng(SEED)
    r = rng.normal(MU, SIGMA, (n, paths))
    inputs = {"true": np.full(paths, MU), "estimated": MU + rng.normal(0, MU / 2, paths),
              "overestimated": np.full(paths, 2 * MU)}
    treat, ctrl, effect, ok = {}, {}, {}, True
    series = {}
    for name, mu_hat in inputs.items():
        full = np.array([kelly_leverage(m, SIGMA**2) for m in mu_hat])
        g_full, dd_full = path_stats(r, full)
        g_half, dd_half = path_stats(r, 0.5 * full)
        boots = []
        for _ in range(300):
            i = rng.integers(0, paths, paths)
            boots.append((np.quantile(dd_half[i], 0.95) - np.quantile(dd_full[i], 0.95),
                          np.median(g_half[i]) - np.median(g_full[i])))
        sd = np.std(np.array(boots), axis=0, ddof=1)
        d95 = float(np.quantile(dd_half, 0.95) - np.quantile(dd_full, 0.95))
        ok &= d95 < -2 * sd[0]
        treat[name] = {"median_log_growth": float(np.median(g_half)), "max_dd_median": float(np.median(dd_half)),
                       "max_dd_p95": float(np.quantile(dd_half, 0.95)), "mean_leverage": float(np.mean(0.5 * full))}
        ctrl[name] = {"median_log_growth": float(np.median(g_full)), "max_dd_median": float(np.median(dd_full)),
                      "max_dd_p95": float(np.quantile(dd_full, 0.95)), "mean_leverage": float(np.mean(full))}
        effect[name] = {"max_dd_p95_diff": d95, "se": float(sd[0]),
                        "median_growth_diff": float(np.median(g_half) - np.median(g_full)), "growth_diff_se": float(sd[1]),
                        "growth_ratio_half_over_full": float(np.median(g_half) / np.median(g_full))}
        if name == "true":
            series = {"quantiles": QS, "max_dd_half": np.quantile(dd_half, QS).tolist(),
                      "max_dd_full": np.quantile(dd_full, QS).tolist()}
    t, c, e = treat["true"], ctrl["true"], effect["true"]
    return {
        "inputs": {"paths": paths, "periods": n, "mu": MU, "sigma": SIGMA, "kelly_true": MU / SIGMA**2,
                   "estimate_noise_sd": MU / 2},
        "seeds": [SEED], "metric": "median log growth per period; max drawdown (median, p95)",
        "treatment": {"arm": "half Kelly", **treat}, "control": {"arm": "full Kelly", **ctrl},
        "effect": {"estimate": e["max_dd_p95_diff"], "se": e["se"], "what": "p95 max drawdown, half minus full (true edge)",
                   "by_input": effect},
        "series": series,
        "verdict_rule": "supports if half-Kelly p95 max drawdown < full-Kelly's by > 2 SE for true, estimated and overestimated edges",
        "verdict": verdict(ok),
        "summary": (f"true edge: half Kelly keeps {e['growth_ratio_half_over_full']:.0%} of full Kelly's median growth with "
                    f"p95 max drawdown {t['max_dd_p95']:.0%} vs {c['max_dd_p95']:.0%}; edge overestimated 2x: half Kelly "
                    f"growth {treat['overestimated']['median_log_growth'] * 1e4:.2f} vs "
                    f"{ctrl['overestimated']['median_log_growth'] * 1e4:.2f} bp/period, drawdown "
                    f"{treat['overestimated']['max_dd_p95']:.0%} vs {ctrl['overestimated']['max_dd_p95']:.0%}"),
    }


def figure(res: dict, path: Path) -> None:
    import matplotlib.pyplot as plt

    s = res["series"]
    fig, ax = plt.subplots(figsize=(7, 3), dpi=110)
    ax.plot(np.array(s["max_dd_full"]) * 100, s["quantiles"], color="#b45309", lw=1.6, label="full Kelly (f = 5)")
    ax.plot(np.array(s["max_dd_half"]) * 100, s["quantiles"], color="#1d4ed8", lw=1.6, label="half Kelly (f = 2.5)")
    ax.set_xlabel("max drawdown over 1,000 bets (%)")
    ax.set_ylabel("share of paths")
    e = res["effect"]["by_input"]["true"]
    ax.set_title(f"Half Kelly keeps {e['growth_ratio_half_over_full']:.0%} of the growth; "
                 f"p95 drawdown {res['treatment']['true']['max_dd_p95']:.0%} vs {res['control']['true']['max_dd_p95']:.0%} "
                 f"({res['inputs']['paths']:,} paths)", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main(META, run))
