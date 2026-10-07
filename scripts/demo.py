"""Offline toy end-to-end: data -> features -> strategy -> risk -> portfolio -> execution (paper).

Uses the conformance toy implementation. The strategy is a placeholder; the summary reports pipeline
activity (counts), never performance.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from conformance import toy
from pipeline.risk import RiskLimits
from pipeline.types import NS_PER_HOUR, AccountState, bars_to_frame

STEPS = 200


def main() -> int:
    data, feat, strat = toy.make_data_source(), toy.make_feature(), toy.make_strategy()
    riskm, gate = toy.make_risk_model(), toy.make_risk_engine(RiskLimits())
    port, execu, venue = toy.make_portfolio(), toy.make_executor(), toy.make_venue()
    bars = data.bars(toy.TOY_ID, toy.T0, toy.T0 + 1_000 * NS_PER_HOUR)
    frame = bars_to_frame(bars)
    close = frame["close"]
    volume = frame["volume"]
    equity, qty, n_orders, n_breach = 100_000.0, 0.0, 0, 0
    first = 300
    for i in range(first, first + STEPS):
        t = int(bars[i].close_time)
        sub = frame.iloc[: i + 1]
        value = float(feat.compute(sub).iloc[-1])
        sig = strat.signal(toy.TOY_ID, t, {"momentum": value})
        rets = pd.DataFrame({toy.TOY_ID: close.iloc[: i + 1].pct_change().dropna()})
        rets.index = [int(bars[j].close_time) for j in range(1, i + 1)]
        forecast = riskm.forecast(t, rets)
        target = port.target(t, [sig], forecast)
        price = float(close.iloc[i])
        equity = equity + qty * (price - float(close.iloc[i - 1]))
        gate.update_equity(t, equity)
        decision = gate.check(target, {toy.TOY_ID: qty * price / equity})
        n_breach += len(decision.breaches)
        account = AccountState(t, equity, {toy.TOY_ID: qty}, {toy.TOY_ID: price})
        for order in execu.orders(decision.target, account):
            fill = venue.submit(order, price, float(volume.iloc[i]))
            qty += fill.qty
            equity -= fill.fee
            n_orders += 1
    print(f"toy demo: {STEPS} hourly steps over synthetic data (offline, paper only)")
    print("  stages run: data, features, strategy, risk, portfolio, execution")
    print(f"  orders filled: {n_orders}; risk breaches: {n_breach}; final position qty: {qty:.4f}")
    print("  placeholder strategy; no performance claim")
    return 0 if n_orders > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
