"""EXP-02-1: a leaked (centred-window) feature shows skill on pure noise; a trailing one does not.

Generating process: 200 independent paths (quick: 20) of 2,000 hourly bars (quick: 500); log price is a
Gaussian random walk with N(0, 0.01^2) steps, so the next return is unpredictable by construction. Seed 4.

Both features follow the stage-02 Feature protocol (name, lookback, compute(bars) -> Series):
  treatment (leaked): 24-bar mean log return in a centred window (pandas rolling(center=True)), which
  includes bars after t;  control (point-in-time): the trailing 24-bar mean log return.
Metric: uncentred correlation IC = x.y / sqrt(x.x y.y) between the feature at t and the return from t to
t+1, measured on the second half of each path (out of sample; nothing is fitted), the same estimator for
both arms. Both series have mean 0 by construction, so no demeaning is needed. Mean IC over paths with SE
across paths. Diagnostic, not part of the verdict: the Spearman rank IC, which demeans, so it carries the
small-sample bias that demeaning an overlapping-window series adds (it made the trailing control look
non-zero).
Revision note: EXP-02-1's measurement was revised after review on 2026-10-08 because the original control
was biased (see git history). The original metric was the Spearman IC for both arms; the threshold is unchanged.
Verdict rule (from blueprint/02-features.md, stricter than its falsification condition): supports if the leaked IC exceeds 0 by
more than 2 SE and the trailing IC is within 2 SE of 0. The blueprint's narrower falsification condition
(leaked IC within 2 SE of 0) is reported beside it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from experiments._common import main, mean_se, synthetic, verdict  # noqa: E402
from pipeline.protocols import Feature  # noqa: E402

META = {
    "id": "EXP-02-1", "backs": "02-features rule 1",
    "claim": "a leaked feature shows skill on pure noise",
    "script": "experiments/EXP-02-1-leaked-feature.py",
    "data": synthetic("Gaussian random walk of log price, sigma 1% per bar"),
}
SEED, WINDOW = 4, 24


class MeanReturn:
    def __init__(self, centred: bool) -> None:
        self.centred, self.name, self.lookback = centred, "centred" if centred else "trailing", WINDOW + 1

    def compute(self, bars: pd.DataFrame) -> pd.Series:
        r = np.log(bars["close"]).diff()
        return r.rolling(WINDOW, center=self.centred).mean().rename(self.name)


def ic(feature: pd.Series, fwd: pd.Series) -> float:
    """Uncentred correlation; valid because both series have known mean 0 (no demeaning bias)."""
    ok = feature.notna() & fwd.notna()
    x, y = feature[ok].to_numpy(), fwd[ok].to_numpy()
    return float(x @ y / np.sqrt((x @ x) * (y @ y)))


def rank_ic(feature: pd.Series, fwd: pd.Series) -> float:
    ok = feature.notna() & fwd.notna()
    return float(feature[ok].rank().corr(fwd[ok].rank()))


def passes(leak: float, leak_se: float, trail: float, trail_se: float) -> bool:
    return leak > 2 * leak_se and abs(trail) <= 2 * trail_se


def run(quick: bool) -> dict:
    n_paths, n = (20, 500) if quick else (200, 2_000)
    rng = np.random.default_rng(SEED)
    feats = [MeanReturn(True), MeanReturn(False)]
    assert all(isinstance(f, Feature) for f in feats)
    ics = {f.name: [] for f in feats}
    raw = []  # diagnostic: trailing feature's demeaned Spearman IC (the original, biased metric)
    for _ in range(n_paths):
        bars = pd.DataFrame({"close": 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))})
        fwd = np.log(bars["close"]).diff().shift(-1)  # return from t to t+1
        oos = slice(n // 2, None)
        for f in feats:
            ics[f.name].append(ic(f.compute(bars).iloc[oos], fwd.iloc[oos]))
        raw.append(rank_ic(feats[1].compute(bars).iloc[oos], fwd.iloc[oos]))
    lk_m, lk_se = mean_se(ics["centred"])
    tr_m, tr_se = mean_se(ics["trailing"])
    ok = passes(lk_m, lk_se, tr_m, tr_se)
    falsified = lk_m <= 2 * lk_se  # the blueprint's falsification condition, reported beside the verdict
    return {
        "inputs": {"paths": n_paths, "bars": n, "window": WINDOW, "oos": "second half of each path"},
        "seeds": [SEED], "metric": "uncentred correlation IC with the next-bar return",
        "treatment": {"arm": "centred (leaked) window", "ic": lk_m, "se": lk_se},
        "control": {"arm": "trailing (point-in-time) window", "ic": tr_m, "se": tr_se,
                    "diagnostic_spearman_demeaned": mean_se(raw)[0], "diagnostic_se": mean_se(raw)[1]},
        "effect": {"estimate": lk_m - tr_m, "se": float(np.hypot(lk_se, tr_se)),
                   "blueprint_falsification_met": falsified},
        "verdict_rule": "supports if leaked IC > 2 SE above 0 and trailing IC within 2 SE of 0",
        "verdict": verdict(ok),
        "summary": (f"leaked IC {lk_m:.3f} (SE {lk_se:.3f}) vs trailing IC {tr_m:+.3f} (SE {tr_se:.3f}) on pure noise; "
                    f"trailing IC {'within' if abs(tr_m) <= 2 * tr_se else 'outside'} 2 SE of 0 (demeaned Spearman "
                    f"{mean_se(raw)[0]:+.4f}, SE {mean_se(raw)[1]:.4f}); the blueprint's own falsification condition "
                    f"(leaked IC within 2 SE of 0) {'is' if falsified else 'is not'} met"),
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
