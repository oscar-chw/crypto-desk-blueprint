"""EXP-00-1: backtest and paper loops that share one decision path give identical orders.

Generating process: the conformance toy's SyntheticBars, hourly geometric random walk with log-return
sigma 0.5% per bar (N(0, 0.005) increments), lognormal volumes, each bar available 1 s after its close.
Seeds 1..5 (quick: seed 1), 400 bars per path (quick: 120), decisions from bar 30 on.

Both loops call the same `decide` (toy feature -> strategy -> EWMA risk -> vol-scaled portfolio -> risk
gate -> delta executor) and the same paper venue. They differ only in where the data comes from:
  backtest: a slice of the in-memory bar frame up to bar i;
  paper (treatment): a SimClock set to bar i's available_at and a PointInTimeStore view as of that time;
  paper with a one-bar delay (control): the store view as of the previous bar's available_at.
Metric: count of mismatched orders against the backtest (a missing, extra or different-size order).
Verdict rule (from blueprint/00-infrastructure.md): supports if the shared path has 0 mismatches and the
control has > 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from conformance import toy  # noqa: E402
from experiments._common import main, synthetic, verdict  # noqa: E402
from pipeline.risk import RiskLimits  # noqa: E402
from pipeline.types import AccountState, bars_to_frame  # noqa: E402

META = {
    "id": "EXP-00-1", "backs": "00-infrastructure rule 2",
    "claim": "one code path: backtest and paper give identical orders",
    "script": "experiments/EXP-00-1-one-code-path.py",
    "data": synthetic("toy SyntheticBars: hourly GBM, log-return sigma 0.005 per bar"),
}
FIRST = 30


def decide(frame: pd.DataFrame, t: int, account: AccountState, parts) -> list:
    feat, strat, riskm, port, gate, execu = parts
    sig = strat.signal(toy.TOY_ID, t, {"momentum": float(feat.compute(frame).iloc[-1])})
    rets = pd.DataFrame({toy.TOY_ID: frame["close"].pct_change().iloc[1:]})
    target = port.target(t, [sig], riskm.forecast(int(frame.index[-1]), rets))
    gate.update_equity(t, account.equity)
    w = account.weight(toy.TOY_ID)
    return execu.orders(gate.check(target, {toy.TOY_ID: w}).target, account)


def run_loop(bars, visible_frame) -> dict[int, float]:
    """Step through bars; visible_frame(i) is the data the decision at bar i may see."""
    parts = (toy.make_feature(), toy.make_strategy(), toy.make_risk_model(), toy.make_portfolio(),
             toy.make_risk_engine(RiskLimits()), toy.make_executor())
    venue, equity, qty, prev, orders = toy.make_venue(), 100_000.0, 0.0, None, {}
    for i in range(FIRST, len(bars)):
        b = bars[i]
        equity += qty * (b.close - prev) if prev is not None else 0.0
        prev = b.close
        account = AccountState(b.available_at, equity, {toy.TOY_ID: qty}, {toy.TOY_ID: b.close})
        for o in decide(visible_frame(i), b.available_at, account, parts):
            orders[o.t] = o.qty
            try:
                fill = venue.submit(o, b.close, b.volume)
            except ValueError:  # the paper venue refuses orders above its participation cap: no fill
                continue
            qty += fill.qty
            equity -= fill.fee
    return orders


def mismatches(a: dict[int, float], b: dict[int, float]) -> int:
    keys = set(a) | set(b)
    return sum(1 for k in keys if k not in a or k not in b or abs(a[k] - b[k]) > 1e-9 * max(1.0, abs(a[k])))


def run(quick: bool) -> dict:
    seeds, n = ([1], 120) if quick else ([1, 2, 3, 4, 5], 400)
    shared, delayed, n_orders = 0, 0, 0
    for seed in seeds:
        src = toy.SyntheticBars(n=n, seed=seed)
        bars = src.bars(toy.TOY_ID, toy.T0, toy.T0 + 10**18)
        frame = bars_to_frame(bars)
        backtest = run_loop(bars, lambda i: frame.iloc[: i + 1])

        store, clock = toy.make_store(), toy.make_clock(toy.T0)
        for b in bars:
            store.append_bar(b)

        def paper_view(i: int, lag: int = 0) -> pd.DataFrame:
            clock.set(bars[i].available_at)  # the paper loop is driven by the clock, not by an index
            as_of = bars[i - lag].available_at
            recs = store.view(as_of).read(toy.TOY_ID, toy.T0 - 1, as_of)
            return bars_to_frame([r.value for r in recs])

        paper = run_loop(bars, paper_view)
        clock = toy.make_clock(toy.T0)
        paper_lag = run_loop(bars, lambda i: paper_view(i, lag=1))
        shared += mismatches(backtest, paper)
        delayed += mismatches(backtest, paper_lag)
        n_orders += len(backtest)
    ok = shared == 0 and delayed > 0
    return {
        "inputs": {"bars_per_path": n, "paths": len(seeds), "first_decision_bar": FIRST},
        "seeds": seeds, "metric": "mismatched orders vs the backtest loop",
        "treatment": {"arm": "paper loop, shared decision path", "mismatched_orders": shared,
                      "backtest_orders": n_orders},
        "control": {"arm": "paper loop with a one-bar delay", "mismatched_orders": delayed},
        "effect": {"estimate": delayed - shared, "uncertainty": "none: exact count"},
        "verdict_rule": "supports if shared-path mismatches == 0 and control mismatches > 0",
        "verdict": verdict(ok),
        "summary": f"{shared} of {n_orders} orders differ on the shared path vs {delayed} with a one-bar delay",
    }


if __name__ == "__main__":
    sys.exit(main(META, run))
