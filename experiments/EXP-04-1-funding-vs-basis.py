"""EXP-04-1: annualised perpetual funding and annualised quarterly-futures basis are correlated. Public data,
BTC and ETH, calendar 2025. The claim is narrower than the blueprint's original one: the fair-value
formula itself is not tested (that needs the funding-market rates, which are not in the extract), and the
band and clustering parts are reported as findings, not as part of the verdict.

Data (committed extract, see data/MANIFEST.json; re-fetch with scripts/fetch_data.py):
  https://data.binance.vision/data/spot/monthly/klines/{BTC,ETH}USDT/1h/
  https://data.binance.vision/data/futures/um/monthly/klines/{BTC,ETH}USDT_{YYMMDD}/1h/  (USD-M quarterlies)
  https://data.binance.vision/data/futures/um/monthly/fundingRate/{BTC,ETH}USDT/
The quarterly column is the nearest contract with at least 14 days to expiry (08:00 UTC on its date).

Treatment: at each 8-hourly funding time, annualised funding (pipeline.pricing.annualize_funding) against
the annualised log basis of the quarterly (pipeline.pricing.implied_carry, year_fraction) at the hourly
close at that time; Pearson correlation, SE by a moving-block bootstrap (7-day blocks, 1,000 resamples,
seed 41). Control: the funding series circularly shifted by 200 random offsets of 30 to 335 days (seed 41),
which keeps each series' own persistence and breaks the alignment.
Band (reported, not part of the verdict): pipeline.pricing.no_arbitrage_band per hour with assumed rates
quote lend 4% / borrow 8%, base lend 0% / borrow 3%, round-trip cost 0.20%; share of hours outside it, and
the share of days with any out-of-band hour that are among the 10% of days with the largest absolute
BTC spot move (10% if out-of-band days are unrelated to stress; binomial SE over those days).
Verdict rule (from blueprint/04-pricing.md, stricter than its "no higher than the control"): supports if, for both coins, the
aligned correlation exceeds the 95th percentile of the shifted correlations (the rule is wrong if it is no
higher than the control).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from experiments._common import load_csv, main, prop_se, public_data, verdict
from pipeline import pricing

META = {
    "id": "EXP-04-1", "backs": "04-pricing rule 3",
    "claim": "annualised funding and futures basis are correlated (public Binance data)",
    "script": "experiments/EXP-04-1-funding-vs-basis.py",
}
SEED, N_SHIFTS, BLOCK = 41, 200, 21
RATES = {"r_quote_lend": 0.04, "r_quote_borrow": 0.08, "r_base_lend": 0.0, "r_base_borrow": 0.03,
         "round_trip_cost": 0.002}
FILES = ["binance_hourly_2025.csv", "binance_funding_2025.csv"]
URLS = ["https://data.binance.vision/data/spot/monthly/klines/",
        "https://data.binance.vision/data/futures/um/monthly/klines/",
        "https://data.binance.vision/data/futures/um/monthly/fundingRate/"]


def expiry_ns(code) -> int:
    return int(pd.Timestamp(f"20{int(code):06d}"[:8], tz="UTC").value + 8 * 3_600 * 10**9)


def coin_frame(hourly: pd.DataFrame, coin: str) -> pd.DataFrame:
    t = hourly["close_time_ms"].to_numpy(np.int64) * 1_000_000
    exp = hourly[f"{coin}_quarterly_expiry"].map(expiry_ns).to_numpy(np.int64)
    spot, fut = hourly[f"{coin}_spot"].to_numpy(), hourly[f"{coin}_quarterly"].to_numpy()
    tau = np.array([pricing.year_fraction(int(a), int(b)) for a, b in zip(t, exp, strict=False)])
    basis = np.array([pricing.implied_carry(s, f, x) for s, f, x in zip(spot, fut, tau, strict=False)])
    bands = np.array([pricing.no_arbitrage_band(s, x, **RATES) for s, x in zip(spot, tau, strict=False)])
    return pd.DataFrame({"basis": basis, "spot": spot, "fut": fut, "low": bands[:, 0], "high": bands[:, 1]},
                        index=hourly["close_time_ms"].to_numpy())


def aligned(hourly: pd.DataFrame, funding: pd.DataFrame, coin: str) -> pd.DataFrame:
    f = funding[funding["symbol"] == f"{coin.upper()}USDT"].set_index("funding_time_ms")
    ann = pd.Series([pricing.annualize_funding(r, h) for r, h in zip(f["rate"], f["interval_hours"], strict=False)], index=f.index)
    cf = coin_frame(hourly, coin)
    return pd.DataFrame({"funding": ann, "basis": cf["basis"]}).dropna()


def block_boot_se(a: np.ndarray, b: np.ndarray, rng: np.random.Generator, n_boot: int = 1_000) -> float:
    n, starts = len(a), np.arange(len(a) - BLOCK + 1)
    out = []
    for _ in range(n_boot):
        idx = np.concatenate([np.arange(s, s + BLOCK) for s in rng.choice(starts, n // BLOCK + 1)])[:n]
        out.append(np.corrcoef(a[idx], b[idx])[0, 1])
    return float(np.std(out, ddof=1))


def passes(aligned: list[float], shifted_p95: list[float]) -> bool:
    return all(a > c for a, c in zip(aligned, shifted_p95, strict=False))


def run(quick: bool) -> dict:
    hourly, funding = load_csv(FILES[0]), load_csv(FILES[1])
    if quick:  # the first quarter only; same code path
        hourly = hourly.iloc[: 24 * 90]
        funding = funding[funding["funding_time_ms"] <= hourly["close_time_ms"].iloc[-1]]
    rng = np.random.default_rng(SEED)
    n_shifts, n_boot = (20, 50) if quick else (N_SHIFTS, 1_000)
    treat, ctrl = {}, {}
    btc_day = pd.Series(hourly["btc_spot"].to_numpy(), index=pd.to_datetime(hourly["close_time_ms"], unit="ms"))
    day_move = np.log(btc_day.resample("1D").last()).diff().abs()
    stress_days = set(day_move[day_move >= day_move.quantile(0.9)].index.date)
    for coin in ("btc", "eth"):
        al = aligned(hourly, funding, coin)
        a, b = al["funding"].to_numpy(), al["basis"].to_numpy()
        r = float(np.corrcoef(a, b)[0, 1])
        lo, hi = 30 * 3, min(335 * 3, len(a) - 30 * 3)
        shifted = np.array([np.corrcoef(np.roll(a, int(k)), b)[0, 1] for k in rng.integers(lo, hi, n_shifts)])
        cf = coin_frame(hourly, coin)
        out = (cf["fut"] > cf["high"]) | (cf["fut"] < cf["low"])
        out_days = set(pd.to_datetime(cf.index[out.to_numpy()], unit="ms").date)
        on_stress = float(np.mean([d in stress_days for d in out_days])) if out_days else 0.0
        treat[coin] = {"corr": r, "se": block_boot_se(a, b, rng, n_boot), "n": len(a),
                       "mean_funding_ann": float(a.mean()), "mean_basis_ann": float(b.mean()),
                       "share_hours_outside_band": float(out.mean()),
                       "out_of_band_days": len(out_days), "share_out_of_band_days_that_are_stress_days": on_stress,
                       "stress_share_se": prop_se(on_stress, max(len(out_days), 1)), "stress_base_rate": 0.10}
        ctrl[coin] = {"corr_mean": float(shifted.mean()), "corr_p95": float(np.quantile(shifted, 0.95)),
                      "corr_sd": float(shifted.std(ddof=1))}
    ok = passes([treat[c]["corr"] for c in treat], [ctrl[c]["corr_p95"] for c in ctrl])
    bt, bc = treat["btc"], ctrl["btc"]
    clustered = [t["share_out_of_band_days_that_are_stress_days"] - 0.10 > 2 * t["stress_share_se"] for t in treat.values()]
    clustering = "clustered in stress" if all(clustered) else "no clustering in stress shown"
    return {
        "data": public_data(FILES, URLS),
        "inputs": {"period": "2025-01-01 to 2025-12-31" if not quick else "2025 Q1 (quick)", "band_rates": RATES,
                   "shifts": n_shifts, "bootstrap": n_boot, "block_obs": BLOCK, "roll_days_before_expiry": 14},
        "seeds": [SEED], "metric": "correlation of annualised funding and annualised basis",
        "treatment": {"arm": "aligned funding and basis", **treat},
        "control": {"arm": "funding shifted by a random offset", **ctrl},
        "effect": {"estimate": bt["corr"] - bc["corr_mean"], "se": float(np.hypot(bt["se"], bc["corr_sd"])),
                   "what": "BTC aligned minus mean shifted correlation",
                   "eth": treat["eth"]["corr"] - ctrl["eth"]["corr_mean"]},
        "verdict_rule": "supports if, for BTC and ETH, aligned corr > 95th percentile of shifted corr",
        "verdict": verdict(ok),
        "summary": (f"aligned corr BTC {bt['corr']:.2f} (SE {bt['se']:.2f}), ETH {treat['eth']['corr']:.2f} "
                    f"(SE {treat['eth']['se']:.2f}) vs shifted 95th pct {bc['corr_p95']:.2f} / "
                    f"{ctrl['eth']['corr_p95']:.2f}. Findings, not verdict: basis outside the assumed band in "
                    f"{bt['share_hours_outside_band']:.1%} / {treat['eth']['share_hours_outside_band']:.1%} of hours; "
                    f"{bt['share_out_of_band_days_that_are_stress_days']:.0%} (SE {bt['stress_share_se']:.0%}) / "
                    f"{treat['eth']['share_out_of_band_days_that_are_stress_days']:.0%} of out-of-band days are "
                    f"top-decile BTC move days vs 10% by chance: {clustering}"),
    }


def figure(res: dict, path: Path) -> None:
    import matplotlib.pyplot as plt

    al = aligned(load_csv(FILES[0]), load_csv(FILES[1]), "btc")
    daily = al.groupby(pd.to_datetime(al.index, unit="ms").date).mean()
    fig, ax = plt.subplots(figsize=(7, 3), dpi=110)
    ax.plot(daily.index, daily["basis"] * 100, color="#1d4ed8", lw=1.3, label="quarterly basis, annualised")
    ax.plot(daily.index, daily["funding"] * 100, color="#b45309", lw=1.3, label="perp funding, annualised")
    ax.axhline(0, color="#475569", lw=0.6)
    ax.set_ylabel("% per year")
    ax.set_title(f"BTCUSDT 2025, Binance (daily means): corr {res['treatment']['btc']['corr']:.2f} at "
                 f"funding times vs {res['control']['btc']['corr_p95']:.2f} (95th pct, shifted)", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main(META, run))
