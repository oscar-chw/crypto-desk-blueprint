# 06 Portfolio

## In one paragraph
Portfolio turns "what we think" (signals) and "how risky it is" (risk forecasts) into "how much to hold".
The default bets half of what theory calls optimal, because the inputs are estimates and betting the full
amount on a wrong estimate loses badly, and it never bets so much that one bad day could use up the whole
drawdown budget. Several signals are blended in a way that does not swing wildly when one view changes a little.

## Purpose
Build a `TargetPortfolio` (signed weights of equity) from signals and risk forecasts, inside the gross cap,
for the risk gate to check and the executor to trade toward.

## Design rules
1. **Default sizing: half-Kelly, capped so the worst observed one-period loss cannot exceed the drawdown budget.** Full Kelly is optimal only with known inputs; half keeps about three quarters of the growth for far smaller drawdowns, and the cap guards fat tails.
2. **Size by risk: weight falls as forecast volatility rises.** Equal conviction should mean equal risk, not equal dollars.
3. **Respect the gross cap inside the constructor, not only in the risk gate.** Two independent guards catch one another's bugs.
4. **Shrink the covariance matrix (default Ledoit-Wolf) before any optimisation.** A sample covariance of many coins over short windows is mostly noise, and optimisers amplify noise.
5. **Combine several strategies with Black-Litterman: equilibrium prior plus views weighted by their confidence.** Plain mean-variance flips weights on small input changes; a prior keeps weak views from dominating.
6. **Recompute sizes as equity changes (smaller after losses).** That is what makes Kelly-style sizing survive a losing streak.
7. **Once a strategy hits capacity, add uncorrelated strategies, not leverage.** Returns do not scale past the liquidity they were measured in.

## Interface
`PortfolioConstructor` in [`pipeline/protocols.py`](../pipeline/protocols.py); `kelly_leverage`,
`capped_kelly` in [`pipeline/sizing.py`](../pipeline/sizing.py); toy `VolScaledPortfolio` in
[`conformance/toy`](../conformance/toy/__init__.py). Suite: [`test_portfolio.py`](../conformance/stages/test_portfolio.py).

## Crypto specifics
- One common factor (the crypto market, close to BTC) explains much of the variance; the effective number of independent bets is small.
- Market-cap weights are a crude equilibrium prior here; a BTC-beta anchor and a larger prior uncertainty are more honest.
- Rebalance on a schedule that fits the funding clock and fee tier, not every bar.

## Common failure modes
- **Full Kelly on estimated edge**: deep drawdowns whenever the edge was overestimated.
- **Vol-blind sizing**: the most volatile coin dominates the risk.
- **Corner solutions**: mean-variance puts everything in one or two coins and flips next rebalance.
- **Cap only in the gate**: a gate bug ships an over-levered book.

## Acceptance tests
| id | input -> expected | mutant it kills |
|---|---|---|
| AT-06-1 | 10 full-conviction signals, tiny vols -> gross <= `max_gross` | `portfolio_no_gross_cap` |
| AT-06-2 | score 0 -> weight 0 | (contract) |
| AT-06-3 | same small score, vol doubled -> position strictly smaller | `portfolio_ignores_vol` |
| unit | half-Kelly 1.25 with worst loss 0.5 and budget 0.2 -> capped at 0.4 | `tests/test_blocks.py` |

## Evidence
- **EXP-06-1** backs rule 1. Hypothesis: when the edge is estimated with error, half-Kelly gives nearly the growth of full Kelly with much smaller drawdowns, and beats full Kelly once the edge is overestimated. Setup: synthetic iid normal bets with known edge; sizing from an estimate with noise of known size; 10,000 paths. Control: full Kelly with the true and with the estimated edge. Metric: median log growth; distribution of max drawdown. Expected: half-Kelly drawdowns far smaller; with true inputs its growth near three quarters of full Kelly's (a known property of the growth curve). The rule is wrong if half-Kelly's drawdowns are not smaller. `result: supports: true edge: half Kelly keeps 74% of full Kelly's median growth with p95 max drawdown 69% vs 93%; edge overestimated 2x: half Kelly growth 12.84 vs 0.35 bp/period, drawdown 93% vs 100%`
- **EXP-06-2** backs rules 4 and 5. Hypothesis: Black-Litterman weights move far less than mean-variance weights when views are noisy. Setup: 10 synthetic assets with a known covariance; views = true means plus noise, redrawn 500 times. Control: mean-variance on the same noisy means. Metric: average L1 distance between successive weight vectors; largest single weight. Expected: BL far more stable and less concentrated. The rule is wrong if BL turnover is not lower. `result: supports: turnover per rebalance 0.83 (BL) vs 1.13 (MV) in L1 at gross 1; largest weight 0.27 vs 0.26`

## Sources
- Kelly (1956), *Bell System Technical Journal*: the growth-optimal bet.
- Thorp (2006), "The Kelly criterion in blackjack, sports betting and the stock market", *Handbook of Asset and Liability Management*: fractional Kelly in practice.
- Chan, *Quantitative Trading* (2009), ch. 6 (Kelly leverage, half-Kelly, worst-loss cap) and ch. 8 (capacity).
- Markowitz (1952), *J. Finance*; Michaud (1989), *Financial Analysts Journal*: mean-variance and its instability.
- Black & Litterman (1992), *Financial Analysts Journal*: equilibrium prior plus views.
- Ledoit & Wolf (2004), *J. Multivariate Analysis*: covariance shrinkage.
- López de Prado (2018), ch. 10 (bet sizing from predicted probabilities).
