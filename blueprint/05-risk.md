# 05 Risk

## In one paragraph
Risk answers two questions: how much could this lose tomorrow, and when do we stop. It forecasts
volatility (which in crypto comes in bursts), enforces hard limits on position size, total exposure,
daily loss and drawdown, and owns the kill switch. Limits are set before trading starts and are never
loosened by the system itself.

## Purpose
Forecast per-instrument volatility point-in-time, and gate every target portfolio through limits:
per-instrument weight, gross exposure, daily loss halt, drawdown budget and kill switch.

## Design rules
1. **Forecast volatility from the past only, and update every bar.** A forecast that reads later returns makes every risk number too good.
2. **Default forecaster: EWMA (lambda 0.94); promote GARCH(1,1) with t errors only if it beats EWMA out of sample.** EWMA is robust and parameter-light; GARCH must earn its extra parameters on a loss such as QLIKE.
3. **Check asymmetry.** If falls raise volatility more than rises (a GJR term is significant), use it; crypto drawdowns usually do this.
4. **Hard limits, in this precedence: kill switch (flatten) > daily loss halt (reduce only) > caps (clip).** A clear order means the gate's output is predictable in a crisis.
5. **Default limits: 25% of equity per instrument, 100% gross, 5% daily loss halt, 20% drawdown budget.** Conservative starting points for an unlevered book; change them only by a human decision record.
6. **The drawdown budget trips the kill switch; a human re-arms it.** Reaching the budget means the model of the world is wrong, which a machine cannot judge.
7. **Measure beta to BTC and cap it.** Most coins move with BTC; a book that looks diversified can be one BTC bet.
8. **Keep the liquidation price far away: at least 4 forecast daily standard deviations.** Liquidation is a forced sale at the worst price, plus a fee.

## Interface
`RiskModel` and `RiskGate` in [`pipeline/protocols.py`](../pipeline/protocols.py); `RiskLimits`,
`RiskEngine`, `KillSwitch`, `RiskDecision` in [`pipeline/risk.py`](../pipeline/risk.py); toy `EwmaVol` in
[`conformance/toy`](../conformance/toy/__init__.py). Suite: [`test_risk.py`](../conformance/stages/test_risk.py).

## Crypto specifics
- Volatility clusters strongly, with persistence close to one; tails are heavy, so a normal VaR understates losses.
- Leverage cascades: liquidations push prices, which trigger more liquidations; gaps jump straight past stops.
- Venue risk: cap equity held on any one venue (default one third) and on any one stablecoin issuer.
- The UTC day is the default risk day; there is no market close to reset on.

## Common failure modes
- **Full-sample volatility**: limits look loose enough in backtest, breached in the first live month.
- **Constant volatility**: position size unchanged into a crash.
- **Kill switch that only logs**: orders keep flowing after the trip.
- **Hidden BTC beta**: "long-short altcoins" book falls with BTC.

## Acceptance tests
| id | input -> expected | mutant it kills |
|---|---|---|
| AT-05-1 | 300 returns; forecast at row 200 with and without later rows -> equal | `risk_uses_future` |
| AT-05-2 | 200 bars at 1% sd then 20 at 5% -> forecast at least doubles | `risk_constant_vol` |
| AT-05-3 | kill switch tripped -> every weight 0, halted | `risk_ignores_kill_switch` |
| AT-05-4 | equity 100 then 79, budget 20% -> kill switch tripped | (drawdown rule) |
| AT-05-5 | target +-0.9, caps 0.25 and 0.4 gross -> inside both | (caps) |

## Evidence
- **EXP-05-1** backs rules 1 and 2. Hypothesis: volatility targeting with a GARCH or EWMA forecast keeps realised volatility closer to target and trims drawdown tails, at the cost of turnover. Setup: synthetic GARCH(1,1) returns with t(4) errors (alpha 0.1, beta 0.85), 2,000 paths; then free public Binance BTC daily klines. Control: fixed notional with the same average exposure. Metric: dispersion of rolling realised vol around target; 95th percentile of max drawdown; turnover. Expected: targeted arms tighter vol and smaller tail drawdown, higher turnover. The rule is wrong if realised-vol dispersion is not lower than the control. `result: supports: vol dispersion 0.30 vs 0.38 (synthetic, diff SE 0.001), 0.29 vs 0.43 on BTC; p95 max drawdown 81% vs 86%; turnover 0.029 vs 0 per day`
- **EXP-05-2** backs rules 4 to 6. Hypothesis: a daily loss halt and a drawdown budget cut the worst outcomes for a modest cost in the median. Setup: synthetic GARCH-t returns with a random negative-drift regime; a strategy with no edge. Control: the same strategy without limits. Metric: 99th percentile max drawdown; median terminal wealth. Expected: much smaller tail drawdown, small median cost. The rule is wrong if the tail drawdown is not lower. `result: supports: p99 max drawdown 25% with limits vs 70% without (diff SE 1.8%); median terminal wealth 0.879 vs 0.797 (diff +0.082, SE 0.009); kill switch tripped on 96% of paths`
- **EXP-05-3** backs rule 7. Hypothesis: a dollar-neutral altcoin book still carries BTC beta; a beta-neutral one does not. Setup: one-factor synthetic returns, coin = beta_i x BTC + noise, beta_i from 0.6 to 1.6. Control: dollar-neutral weights. Metric: realised beta of the book to BTC. Expected: beta-neutral near 0, dollar-neutral clearly not. The rule is wrong if both show near-zero beta. `result: supports: mean absolute BTC beta 0.174 dollar-neutral vs 0.048 beta-neutral (paired diff SE 0.006)`

## Sources
- Engle (1982), *Econometrica*: ARCH. Bollerslev (1986), *J. Econometrics*: GARCH.
- Glosten, Jagannathan & Runkle (1993), *J. Finance*: the asymmetric (GJR) term.
- J.P. Morgan/Reuters (1996), *RiskMetrics Technical Document*: the EWMA with lambda 0.94.
- Cryer & Chan, *Time Series Analysis with Applications in R* (2008), ch. 12 (ARCH/GARCH, diagnostics, asymmetry).
- Chan, *Quantitative Trading* (2009), ch. 6 (risk management, stop-losses and gaps).
- Fama & French (1993), *J. Financial Economics*; MSCI Barra risk-model documentation: factor exposures and beta.
