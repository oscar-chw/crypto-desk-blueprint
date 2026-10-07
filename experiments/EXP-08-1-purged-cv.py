"""EXP-08-1: on pure noise with overlapping labels, shuffled ("plain") k-fold shows false skill and purged
k-fold with an embargo does not. Narrower than the blueprint's rules 1 and 2: in this setup the false
skill comes from shuffling; contiguous folds without purging are reported to show whether purging and the
embargo add a measurable benefit on top (no embargo-length sweep is run, so rule 2 is not tested).

Generating process: 20 independent paths (quick: 2) of 2,000 hourly bars (quick: 600); log price is a
Gaussian random walk with N(0, 0.01^2) steps, so no feature can predict the label. Seed 81.
Features at t (trailing only): log returns over 1, 5, 10, 20 and 50 bars, and the 20-bar return std.
Label at t: sign of the return from t to t+20 (labels of neighbouring samples overlap for 20 bars).
Model: scikit-learn RandomForestClassifier, 50 trees (quick: 10), min_samples_leaf 1, random_state 81.

Treatment ("plain k-fold", as most tutorials run it): 5-fold KFold with shuffling. Control:
pipeline.cv.PurgedKFold, 5 contiguous folds, label intervals [t, t+20] purged, embargo 50 bars (the longest
feature window). Also reported, not part of the verdict: 5 contiguous folds without purging, and the paired difference
contiguous-unpurged minus purged (the benefit of purging and embargo).
Metric: out-of-fold accuracy, mean over folds per path; mean over paths with SE across paths.
Verdict rule (from blueprint/08-validation.md): supports if plain accuracy exceeds 0.5 by more than 2 SE and
purged accuracy is within 2 SE of 0.5.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold

from experiments._common import main, mean_se, synthetic, verdict
from pipeline.cv import PurgedKFold
from pipeline.types import NS_PER_HOUR

META = {
    "id": "EXP-08-1", "backs": "08-validation rule 1",
    "claim": "shuffled k-fold finds skill in noise; purged k-fold does not",
    "script": "experiments/EXP-08-1-purged-cv.py",
    "data": synthetic("Gaussian random walk, sigma 1% per bar; labels = sign of next 20-bar return"),
}
SEED, H, EMBARGO, FOLDS = 81, 20, 50, 5


def dataset(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lp = pd.Series(np.cumsum(rng.normal(0, 0.01, n)))
    X = pd.concat([lp.diff(k) for k in (1, 5, 10, 20, 50)] + [lp.diff().rolling(20).std()], axis=1)
    y = np.sign(lp.shift(-H) - lp)
    ok = X.notna().all(axis=1) & y.notna() & (y != 0)
    idx = np.flatnonzero(ok.to_numpy())
    return X.to_numpy()[idx], y.to_numpy()[idx], idx


def cv_accuracy(X, y, splits, trees: int) -> float:
    acc = []
    for tr, te in splits:
        m = RandomForestClassifier(n_estimators=trees, random_state=SEED, n_jobs=-1).fit(X[tr], y[tr])
        acc.append(float((m.predict(X[te]) == y[te]).mean()))
    return float(np.mean(acc))


def passes(plain: float, plain_se: float, purged: float, purged_se: float) -> bool:
    return plain - 0.5 > 2 * plain_se and abs(purged - 0.5) <= 2 * purged_se


def run(quick: bool) -> dict:
    paths, n, trees = (2, 600, 10) if quick else (20, 2_000, 50)
    rng = np.random.default_rng(SEED)
    accs = {"plain_shuffled": [], "contiguous_unpurged": [], "purged_embargo": []}
    for p in range(paths):
        X, y, idx = dataset(rng, n)
        t0 = idx.astype(np.int64) * NS_PER_HOUR
        t1 = t0 + H * NS_PER_HOUR
        accs["plain_shuffled"].append(cv_accuracy(X, y, KFold(FOLDS, shuffle=True, random_state=SEED + p).split(X), trees))
        accs["contiguous_unpurged"].append(cv_accuracy(X, y, KFold(FOLDS).split(X), trees))
        accs["purged_embargo"].append(cv_accuracy(X, y, PurgedKFold(FOLDS, EMBARGO * NS_PER_HOUR).split(t0, t1), trees))
    st = {k: mean_se(v) for k, v in accs.items()}
    (pl, pl_se), (pu, pu_se), (cu, cu_se) = st["plain_shuffled"], st["purged_embargo"], st["contiguous_unpurged"]
    d_m, d_se = mean_se(np.array(accs["plain_shuffled"]) - np.array(accs["purged_embargo"]))
    ok = passes(pl, pl_se, pu, pu_se)
    b_m, b_se = mean_se(np.array(accs["contiguous_unpurged"]) - np.array(accs["purged_embargo"]))
    benefit = "a measurable" if b_m > 2 * b_se else "no measurable"
    return {
        "inputs": {"paths": paths, "bars": n, "label_horizon": H, "embargo_bars": EMBARGO, "folds": FOLDS, "trees": trees},
        "seeds": [SEED], "metric": "out-of-fold accuracy on unpredictable labels (truth: 0.5)",
        "treatment": {"arm": "plain k-fold (shuffled)", "accuracy": pl, "se": pl_se,
                      "contiguous_unpurged": {"accuracy": cu, "se": cu_se}},
        "control": {"arm": "purged k-fold + embargo", "accuracy": pu, "se": pu_se},
        "effect": {"estimate": d_m, "se": d_se, "what": "paired plain minus purged accuracy",
                   "purge_benefit": b_m, "purge_benefit_se": b_se,
                   "purge_benefit_what": "paired contiguous-unpurged minus purged accuracy"},
        "series": accs,
        "verdict_rule": "supports if plain accuracy - 0.5 > 2 SE and |purged accuracy - 0.5| <= 2 SE",
        "verdict": verdict(ok),
        "summary": (f"accuracy on pure noise: plain shuffled k-fold {pl:.3f} (SE {pl_se:.3f}), contiguous unpurged "
                    f"{cu:.3f} (SE {cu_se:.3f}), purged + embargo {pu:.3f} (SE {pu_se:.3f}). Shuffling creates the false skill; "
                    f"purging and embargo add {benefit} benefit here (contiguous minus purged {b_m:+.3f}, SE {b_se:.3f})"),
    }


def figure(res: dict, path: Path) -> None:
    import matplotlib.pyplot as plt

    labels = {"plain_shuffled": "plain k-fold\n(shuffled)", "contiguous_unpurged": "contiguous,\nno purge",
              "purged_embargo": "purged k-fold\n+ embargo"}
    colors = {"plain_shuffled": "#b45309", "contiguous_unpurged": "#64748b", "purged_embargo": "#1d4ed8"}
    fig, ax = plt.subplots(figsize=(7, 3), dpi=110)
    for i, (k, v) in enumerate(res["series"].items()):
        v = np.array(v)
        m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
        ax.bar(i, m - 0.5, bottom=0.5, color=colors[k], width=0.55)
        ax.errorbar(i, m, yerr=2 * se, color="#0b1220", capsize=4, lw=1)
        ax.scatter(np.full(len(v), i + 0.33), v, s=6, color=colors[k], alpha=0.6)
    ax.axhline(0.5, color="#0b1220", lw=0.8, ls="--")
    ax.text(2.45, 0.5, "truth: 0.5", va="bottom", ha="right", fontsize=8)
    ax.set_xticks(range(3), [labels[k] for k in res["series"]], fontsize=8)
    ax.set_ylabel("CV accuracy")
    ax.set_title(f"Random forest on a random walk ({res['inputs']['paths']} paths, mean +/- 2 SE)", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main(META, run))
