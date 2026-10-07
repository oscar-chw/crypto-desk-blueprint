# 03 Strategy

## In one paragraph
A strategy looks at features and says what it thinks: up, down or no view, and how strongly. It does not
decide how much to buy; that is risk's and portfolio's job. Keeping it that narrow makes strategies easy
to test, compare and switch off. The strategy shipped in `reference/` and `conformance/toy` is a
deliberately simple placeholder; it shows the plumbing, not an edge.

## Purpose
Map point-in-time features to a `Signal` (score in [-1, 1] and a horizon) for each instrument at each
decision time.

## Design rules
1. **A strategy emits a view, never a size.** Sizing needs risk and portfolio context the strategy does not have, and mixing them hides which part failed.
2. **Missing input means no view (score 0).** Trading on a NaN is trading on a bug.
3. **Deterministic: same inputs, same signal.** Live trades must be reproducible from logged inputs, or divergence cannot be diagnosed.
4. **Few parameters, each with an economic reason.** Every extra knob is another chance to fit noise; five or fewer is a sane ceiling.
5. **Pairs and spreads: test cointegration and estimate the half-life before trading.** Similar coins are not automatically cointegrated, and the half-life sets the holding period and the exit.
6. **Let hedge ratios move: default to a Kalman filter for the ratio, with static OLS as the control.** Crypto relationships shift after listings, unlocks and leverage cycles; a static ratio slowly turns a hedge into a bet.
7. **Use meta-labelling to decide whether to act on a signal, not to find new ones.** It improves precision without letting a second model invent the side.
8. **Every variant you try goes in the trial log (stage 08).** The deflated Sharpe needs the true number of trials.

## Interface
`Strategy` in [`pipeline/protocols.py`](../pipeline/protocols.py) returns `Signal` from
[`pipeline/types.py`](../pipeline/types.py). Toy: `PlaceholderStrategy` in
[`conformance/toy`](../conformance/toy/__init__.py). Suite: [`test_strategy.py`](../conformance/stages/test_strategy.py).

## Crypto specifics
- Natural families: trend, cross-sectional momentum or reversal, spot-perp and cross-venue spreads, carry (funding), and volatility-regime filters.
- Regimes change fast (leverage build-ups and cascades); refit on rolling windows and expect decay.
- Capacity is small in most altcoins; a signal that needs size it cannot get is not a strategy.
- Early-history data (thin books, wide spreads) flatters old backtests; weight recent years more.

## Common failure modes
- **Strategy sizes itself**: risk limits fight the strategy and nobody can tell which caused a loss.
- **Static hedge ratio after a break**: spread variance creeps up; the "market-neutral" book tracks one leg.
- **Pairs without cointegration**: the spread drifts away and never returns; stops hit in a row.
- **Hidden randomness**: live signal cannot be recomputed from the logs.

## Acceptance tests
| id | input -> expected | mutant it kills |
|---|---|---|
| AT-03-1 | all features NaN -> score exactly 0 | `strategy_trades_on_nan` |
| AT-03-2 | features at -1e9, -1, 0, 1, 1e9 -> valid score in [-1, 1], stamped at t, same instrument | (contract) |
| AT-03-3 | two fresh instances, same inputs -> equal signals | (determinism) |

## Evidence
- **EXP-03-1** backs rule 6. Hypothesis: a Kalman hedge ratio tracks a regime shift that a static ratio misses. Setup: synthetic pair, x a random walk, y = beta_t x + AR(1) noise, beta_t = 1.0 then 1.5 from mid-sample. Control: OLS ratio fitted on the first half; a second control with no break. Metric: out-of-sample spread variance and ratio tracking error. Expected: Kalman lower after the break, no worse than OLS without it. The rule is wrong if Kalman is not better after the break or is clearly worse without one. `result: pending`
- **EXP-03-2** backs rule 5. Hypothesis: half-life from an AR(1) fit recovers a known Ornstein-Uhlenbeck speed, and cointegration tests reject at roughly their nominal size on unrelated walks. Setup: OU spreads with known theta; 1,000 pairs of independent random walks. Control: the known theta; the nominal 5% size. Metric: half-life estimation error; false-rejection rate. Expected: unbiased half-life within its standard error; false rejections near 5%. The rule is wrong if the half-life is biased beyond its standard error or false rejections are far above 5%. `result: pending`

## Sources
- Chan, *Quantitative Trading* (2009), ch. 2 (idea screening), ch. 3 (few parameters), ch. 7 (mean reversion vs momentum, cointegration, half-life exits, regimes).
- Kalman (1960), *J. Basic Engineering*: the filter.
- Engle & Granger (1987), *Econometrica*: cointegration and its test.
- Uhlenbeck & Ornstein (1930), *Physical Review*: the mean-reverting process behind half-life.
- López de Prado (2018), ch. 3 (triple barrier, meta-labelling).
