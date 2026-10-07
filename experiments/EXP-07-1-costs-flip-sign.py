"""EXP-07-1: trading costs can flip a small, high-turnover edge from positive to negative.

Arms, all rebalanced every hour:
  synthetic known edge: 43,800 hourly returns (5 years) r ~ N(0, 0.006^2); signal s_t = rho z_{t+1} +
    sqrt(1 - rho^2) e_t with z = r / 0.006, rho = 0.02 and e ~ N(0, 1); position sign(s_t). Seed 71.
  public known edge: the same planted signal (rho 0.02, seed 71) on real Binance BTCUSDT spot hourly
    returns for 2025 (committed extract; https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/).
  public placeholder: the conformance toy's momentum feature and placeholder strategy on the same BTC
    hours, position = its score in [-1, 1].
Costs: pipeline.costs.CostModel with taker fee c bps and no spread or impact, charged on |dw| each hour,
c in {0, 1, 2, 3, 5, 10, 15, 20}. Control: the zero-cost arm (c = 0).
Metric: net Sharpe ratio per hour (pipeline.stats.sharpe_ratio; annualised x sqrt(8760) for display),
SE sqrt((1 + SR^2 / 2) / T) (Lo 2002); break-even cost = gross mean / mean turnover.
Verdict rule: supports if net Sharpe falls strictly as c rises in every arm and, in the synthetic arm, the
zero-cost Sharpe is above 0 by more than 2 SE and turns negative at some c <= 20 bps. This is stricter than
blueprint/07-execution.md, whose only falsification condition is "net Sharpe does not fall as cost rises";
that condition is a check that the cost is applied and holds by construction whenever turnover > 0, so it
is reported beside the verdict, not counted as evidence. Context, not verdict: the realised IC of the
planted synthetic position over seeds 0..199, to show where seed 71 falls in its sampling distribution.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import itertools

import numpy as np
import pandas as pd

from conformance import toy
from experiments._common import load_csv, main, verdict
from pipeline.costs import CostModel
from pipeline.stats import sharpe_ratio

META = {
    "id": "EXP-07-1", "backs": "07-execution rule 4",
    "claim": "costs flip a small high-turnover edge negative",
    "script": "experiments/EXP-07-1-costs-flip-sign.py",
}
SEED, SIGMA, RHO, COSTS = 71, 0.006, 0.02, (0, 1, 2, 3, 5, 10, 15, 20)
HOURLY = "binance_hourly_2025.csv"


def planted(rng: np.random.Generator, r: np.ndarray) -> np.ndarray:
    z = r / r.std()
    s = RHO * np.r_[z[1:], 0.0] + math.sqrt(1 - RHO**2) * rng.standard_normal(len(r))
    return np.sign(s)  # position held from t to t+1


def sweep(w: np.ndarray, r: np.ndarray) -> dict:
    gross = w[:-1] * r[1:]
    turn = np.abs(np.diff(np.r_[0.0, w[:-1]]))
    out = {}
    for c in COSTS:
        fee = CostModel(taker_fee_bps=c, half_spread_bps=0.0, impact_bps_at_full_volume=0.0).fee(1.0)
        sr = sharpe_ratio(gross - turn * fee)
        out[str(c)] = {"sharpe_hourly": sr, "se": math.sqrt((1 + sr**2 / 2) / len(gross)),
                       "sharpe_annual": sr * math.sqrt(8_760)}
    srs = [out[str(c)]["sharpe_hourly"] for c in COSTS]
    flip = next((c for c, s in zip(COSTS, srs, strict=False) if s < 0), None)
    return {"by_cost_bps": out, "break_even_bps": float(gross.mean() / turn.mean() * 1e4),
            "mean_turnover": float(turn.mean()), "falls": bool(all(a > b for a, b in itertools.pairwise(srs))),
            "first_negative_cost_bps": flip, "hours": len(gross)}


def placeholder_positions(close: pd.Series) -> np.ndarray:
    feat, strat = toy.make_feature(), toy.make_strategy()
    mom = feat.compute(pd.DataFrame({"close": close}))
    return np.array([strat.signal(toy.TOY_ID, i, {"momentum": float(m)}).score for i, m in enumerate(mom)])


def seed_ic(seed: int, n: int) -> float:
    """Realised IC of the synthetic arm's position for one seed (the same draws run() makes)."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0, SIGMA, n)
    w = planted(rng, r)
    return float(np.corrcoef(w[:-1], r[1:])[0, 1])


def passes(falls: list[bool], sr0: float, se0: float, first_negative_bps: float | None) -> bool:
    return all(falls) and sr0 > 2 * se0 and first_negative_bps is not None


def run(quick: bool) -> dict:
    rng = np.random.default_rng(SEED)
    n = 8_760 if quick else 43_800
    r_syn = rng.normal(0, SIGMA, n)
    w_syn = planted(rng, r_syn)
    syn = sweep(w_syn, r_syn)
    syn["realised_position_ic"] = float(np.corrcoef(w_syn[:-1], r_syn[1:])[0, 1])
    syn["expected_position_ic"] = RHO * math.sqrt(2 / math.pi)
    close = load_csv(HOURLY)["btc_spot"]
    if quick:
        close = close.iloc[:2_000]
    r_btc = close.pct_change().fillna(0.0).to_numpy()
    btc = sweep(planted(np.random.default_rng(SEED), r_btc), r_btc)
    ph = sweep(placeholder_positions(close.reset_index(drop=True)), r_btc)
    s0 = syn["by_cost_bps"]["0"]
    ok = passes([syn["falls"], btc["falls"], ph["falls"]], s0["sharpe_hourly"], s0["se"], syn["first_negative_cost_bps"])
    blueprint_met = all([syn["falls"], btc["falls"], ph["falls"]])
    ics = np.array([seed_ic(s, n) for s in range(20 if quick else 200)])
    context = {"seeds": "0..199" if not quick else "0..19", "ic_mean": float(ics.mean()), "ic_sd": float(ics.std(ddof=1)),
               "seed_71_ic": syn["realised_position_ic"],
               "seed_71_percentile": float(np.mean(ics < syn["realised_position_ic"]))}

    def zero(a: dict) -> dict:
        return {k: a["by_cost_bps"]["0"][k] for k in ("sharpe_hourly", "se", "sharpe_annual")}
    return {
        "data": {"kind": "synthetic+public",
                 "process": "N(0, 0.006^2) hourly returns with a planted signal of correlation 0.02 to the next return",
                 "files": [HOURLY], "source_urls": ["https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/"]},
        "inputs": {"synthetic_hours": n, "btc_hours": int(len(r_btc) - 1), "rho": RHO, "costs_bps": list(COSTS)},
        "seeds": [SEED], "metric": "net Sharpe per hour vs cost per unit turnover",
        "treatment": {"arm": "costs 1..20 bps", "synthetic": syn, "btc_planted": btc, "btc_placeholder": ph},
        "control": {"arm": "zero cost", "synthetic": zero(syn), "btc_planted": zero(btc), "btc_placeholder": zero(ph)},
        "effect": {"estimate": syn["break_even_bps"], "what": "break-even cost, synthetic arm (bps per unit turnover)",
                   "se": s0["se"] / s0["sharpe_hourly"] * syn["break_even_bps"] if s0["sharpe_hourly"] > 0 else None,
                   "se_note": "delta-method: break-even scales with the gross Sharpe",
                   "blueprint_condition_met": blueprint_met, "multi_seed_ic_context": context},
        "verdict_rule": "supports if net Sharpe strictly falls with cost in every arm, and the synthetic arm's zero-cost "
                        "Sharpe > 2 SE and turns negative at some cost <= 20 bps",
        "verdict": verdict(ok),
        "summary": (f"stricter than the blueprint (whose falls-with-cost condition is "
                    f"{'met' if blueprint_met else 'NOT met'}, by construction): synthetic edge annual Sharpe {s0['sharpe_annual']:.2f} (SE {s0['se'] * math.sqrt(8_760):.2f}) at 0 bp "
                    f"(realised position IC {syn['realised_position_ic']:.4f} vs {syn['expected_position_ic']:.4f} expected), "
                    f"break-even "
                    f"{syn['break_even_bps']:.2f} bp, {syn['by_cost_bps']['5']['sharpe_annual']:.2f} at 5 bp; "
                    f"BTC planted edge break-even {btc['break_even_bps']:.2f} bp; toy placeholder on BTC "
                    f"{ph['by_cost_bps']['0']['sharpe_annual']:.2f} gross, {ph['by_cost_bps']['10']['sharpe_annual']:.2f} at 10 bp; "
                    f"seed 71's IC is at the {context['seed_71_percentile']:.0%} point of {len(ics)} seeds "
                    f"(mean {context['ic_mean']:.4f}, sd {context['ic_sd']:.4f})"
                    f"{': an unlucky draw' if context['seed_71_percentile'] < 0.05 else ''}"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
