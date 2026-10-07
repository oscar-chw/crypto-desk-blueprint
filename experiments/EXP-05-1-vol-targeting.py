"""EXP-05-1: volatility targeting with an EWMA forecast steadies realised volatility and trims the tail of
drawdowns, at the cost of turnover.

Generating process (synthetic arm): 2,000 paths (quick: 50) of 1,000 daily returns (after 250 burn-in)
from GARCH(1,1), sigma2_t = omega + 0.10 r_{t-1}^2 + 0.85 sigma2_{t-1}, unconditional daily vol 3%,
standardised Student-t(4) shocks. Seed 51.
Public arm: Binance BTCUSDT spot daily closes 2018-01-02 to 2025-12-31 (committed extract;
https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/).

Treatment: weight for day t+1 = 2% / EWMA vol forecast at t (the toy stage-05 EwmaVol, lambda 0.94; the
vectorised recursion is checked against it), capped at 4x. Control: fixed notional equal to the path's
average targeted weight (same average exposure).
Metric: dispersion = standard deviation over time of log rolling 21-day realised vol (scale-free);
95th percentile across paths of max drawdown; mean daily turnover |dw|.
Verdict rule (from blueprint/05-risk.md): supports if the paired synthetic dispersion difference (treatment
minus control) is below 0 by more than 2 SE and the BTC arm's dispersion is also lower.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from conformance import toy  # noqa: E402
from experiments._common import boot_se, load_csv, mean_se, synthetic, verdict  # noqa: E402
from experiments._common import main as cli  # noqa: E402

META = {
    "id": "EXP-05-1", "backs": "05-risk rules 1, 2",
    "claim": "vol targeting steadies realised vol and trims tail drawdown",
    "script": "experiments/EXP-05-1-vol-targeting.py",
}
SEED, ALPHA, BETA, UNC_VOL, TARGET, CAP, LAM, ROLL = 51, 0.10, 0.85, 0.03, 0.02, 4.0, 0.94, 21
DAILY = "binance_btcusdt_daily.csv"


def garch_t4(rng: np.random.Generator, paths: int, days: int, burn: int = 250) -> np.ndarray:
    omega = UNC_VOL**2 * (1 - ALPHA - BETA)
    var = np.full(paths, UNC_VOL**2)
    out = np.empty((days + burn, paths))
    for t in range(days + burn):
        out[t] = np.sqrt(var) * rng.standard_t(4, paths) / np.sqrt(2.0)
        var = omega + ALPHA * out[t] ** 2 + BETA * var
    return out[burn:]


def ewma_var(r: np.ndarray) -> np.ndarray:
    """pandas ewm(alpha=1-lambda, adjust=False) of r^2 along axis 0, as toy.EwmaVol computes it."""
    v = np.empty_like(r)
    v[0] = r[0] ** 2
    for t in range(1, len(r)):
        v[t] = LAM * v[t - 1] + (1 - LAM) * r[t] ** 2
    return v


def max_dd(rets: np.ndarray) -> np.ndarray:
    eq = np.cumprod(1 + rets, axis=0)
    return np.max(1 - eq / np.maximum.accumulate(eq, axis=0), axis=0)


def book(r: np.ndarray) -> dict:
    """r: (days, paths) simple returns. Both arms, aligned so weight at t earns r[t+1]."""
    w_t = np.minimum(TARGET / np.sqrt(np.maximum(ewma_var(r), 1e-12)), CAP)[:-1]
    w_f = np.broadcast_to(w_t.mean(axis=0), w_t.shape)
    out = {}
    for name, w in (("targeted", w_t), ("fixed", w_f)):
        pnl = w * r[1:]
        rv = pd.DataFrame(pnl).rolling(ROLL).std().to_numpy()[ROLL:]
        out[name] = {"dispersion": np.std(np.log(rv), axis=0, ddof=1), "max_dd": max_dd(pnl),
                     "turnover": np.mean(np.abs(np.diff(w, axis=0)), axis=0),
                     "rv_rms_rel_to_target": np.sqrt(np.mean((rv / TARGET - 1) ** 2, axis=0))}
    return out


def run(quick: bool) -> dict:
    rng = np.random.default_rng(SEED)
    paths, days = (50, 300) if quick else (2_000, 1_000)
    r = garch_t4(rng, paths, days)
    probe = pd.DataFrame({"X": r[:, 0]}, index=np.arange(days))
    ref = toy.EwmaVol(LAM).forecast(days - 1, probe).vol["X"]
    assert np.isclose(ref, np.sqrt(ewma_var(r[:, :1])[-1, 0]), rtol=1e-9), "EWMA recursion drifted from the block"
    syn = book(r)
    t, f = syn["targeted"], syn["fixed"]
    d_m, d_se = mean_se(t["dispersion"] - f["dispersion"])
    q95 = lambda x: float(np.quantile(x, 0.95))  # noqa: E731
    daily = load_csv(DAILY)
    btc = book(daily["close"].pct_change().dropna().to_numpy()[:, None])
    bt, bf = ({k: float(v[0]) for k, v in btc[a].items()} for a in ("targeted", "fixed"))
    ok = d_m < -2 * d_se and bt["dispersion"] < bf["dispersion"]

    def arm(x: dict, b: dict) -> dict:
        return {"synthetic": {"dispersion_log_rv": float(np.mean(x["dispersion"])), "max_dd_p95": q95(x["max_dd"]),
                              "max_dd_p95_se": boot_se(x["max_dd"], lambda v: np.quantile(v, 0.95), rng),
                              "turnover": float(np.mean(x["turnover"])),
                              "rv_rms_rel_to_target": float(np.mean(x["rv_rms_rel_to_target"]))},
                "btc_daily": b}
    return {
        "data": {**synthetic("GARCH(1,1)-t(4), alpha 0.10, beta 0.85, unconditional daily vol 3%"),
                 "public": {"files": [DAILY], "source_urls": ["https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/"]}},
        "inputs": {"paths": paths, "days": days, "target_daily_vol": TARGET, "ewma_lambda": LAM, "leverage_cap": CAP,
                   "rolling_days": ROLL, "btc_days": int(len(daily) - 1)},
        "seeds": [SEED], "metric": "sd of log rolling 21-day realised vol; p95 max drawdown; turnover",
        "treatment": {"arm": "vol-targeted (EWMA)", **arm(t, bt)},
        "control": {"arm": "fixed notional, same average exposure", **arm(f, bf)},
        "effect": {"estimate": d_m, "se": d_se, "what": "paired dispersion difference (synthetic)",
                   "btc_dispersion_diff": bt["dispersion"] - bf["dispersion"]},
        "verdict_rule": "supports if synthetic dispersion diff < -2 SE and BTC dispersion lower",
        "verdict": verdict(ok),
        "summary": (f"vol dispersion {np.mean(t['dispersion']):.2f} vs {np.mean(f['dispersion']):.2f} (synthetic, "
                    f"diff SE {d_se:.3f}), {bt['dispersion']:.2f} vs {bf['dispersion']:.2f} on BTC; p95 max "
                    f"drawdown {q95(t['max_dd']):.0%} vs {q95(f['max_dd']):.0%}; turnover {np.mean(t['turnover']):.3f} "
                    f"vs 0 per day"),
    }


if __name__ == "__main__":
    sys.exit(cli(META, run))
