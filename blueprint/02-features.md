# 02 Features

## In one paragraph
A feature turns raw prices into a number a model can use, such as "how far did the price move in the last
day". Two things make a feature honest: it may only use data that existed at the moment it is stamped,
and it should behave the same way over time (stationary), otherwise a model learns a pattern that belonged
to one period only.

## Purpose
Compute point-in-time, mostly stationary inputs from the store: returns, volatility, carry, flow and
cross-asset features, each stamped at the bar close it was computed on.

## Design rules
1. **A feature at t uses only rows with close time ≤ t.** Anything else is look-ahead, and look-ahead turns noise into apparent skill.
2. **Warm-up values are NaN, never zero or back-filled.** A filled zero is a real-looking input that never existed.
3. **Work in log returns, not prices.** Prices wander without a fixed mean; log returns add over time and are much closer to stationary.
4. **Test every candidate for stationarity in rolling windows, with ADF and KPSS together.** ADF alone has little power near a unit root, so "not rejected" is not proof; two tests with opposite nulls disagree informatively.
5. **Do not difference what is already mean-reverting** (funding, basis). Over-differencing adds noise and a fake negative autocorrelation.
6. **Test lead-lag on prewhitened series.** Cross-correlating two trending series finds relationships that are not there.
7. **Default smoother: an EWMA whose decay is fitted, not picked.** It is the forecast of a simple integrated model, so its one parameter has a meaning you can estimate.
8. **Remove seasonality that is a schedule, not a signal** (hour-of-day volume, funding-time spikes) before modelling.

## Interface
`Feature` in [`pipeline/protocols.py`](../pipeline/protocols.py) (`compute(bars) -> Series`, same index,
NaN warm-up of `lookback - 1` rows); frame shape from `bars_to_frame` in [`pipeline/types.py`](../pipeline/types.py).
Suite: [`test_features.py`](../conformance/stages/test_features.py).

## Crypto specifics
- Volatility clusters strongly and tails are heavy; standardise features by a volatility forecast, not by a full-sample standard deviation (which leaks).
- Funding and basis are natural carry features; they mean-revert because arbitrage bounds them (see 04).
- Activity has an hour-of-day and weekday pattern even though markets never close.
- With millions of ticks almost every autocorrelation is "significant"; judge effect size, not p-values.

## Common failure modes
- **Centred window**: a rolling statistic with `center=True`; perfect-looking backtest, flat live.
- **Full-sample z-score**: normalising with the whole history's mean and sd; mild but systematic leak.
- **Filled warm-up**: the first trades of every run act on zeros.
- **Spurious regression**: price level regressed on price level; high R-squared, no out-of-sample power.

## Acceptance tests
| id | input -> expected | mutant it kills |
|---|---|---|
| AT-02-1 | 400 random-walk bars cut at 3 points -> values up to each cut unchanged by later rows | `feature_peeks_ahead` |
| AT-02-2 | first `lookback - 1` outputs NaN, the rest finite | `feature_fills_warmup` |
| AT-02-3 | output index equals input index | (shape contract) |

## Evidence
- **EXP-02-1** backs rule 1. Hypothesis: a leaked feature shows skill on pure noise. Setup: a Gaussian random walk (no predictability by construction), feature = 24-bar mean return computed trailing vs centred. Control: the trailing feature. Metric: rank correlation (IC) with the next-bar return, out of sample, with standard error. Expected: centred IC clearly above 0, trailing IC within noise of 0. The rule is wrong if the leaked IC is inside two standard errors of 0. `result: does not support: leaked IC 0.191 (SE 0.002) vs trailing IC -0.009 (SE 0.002) on pure noise; trailing IC outside 2 SE of 0 (uncentred -0.0026, SE 0.0024); the blueprint's own falsification condition (leaked IC within 2 SE of 0) is not met`
- **EXP-02-2** backs rule 3. Hypothesis: regressing one price level on another independent one rejects "no relation" far more than 5% of the time. Setup: 1,000 pairs of independent random walks of 500 steps. Control: the same regression on their differences (returns). Metric: rejection rate of the slope t-test at 5%. Expected: levels far above 5%, returns near 5%. The rule is wrong if levels reject at about 5%. `result: supports: levels reject 87.5% (SE 1.0%) of independent pairs; returns reject 4.3% (SE 0.6%)`
- **EXP-02-3** backs rule 4. Hypothesis: ADF often fails to reject a unit root for a persistent but stationary series. Setup: AR(1) with phi 0.98 (stationary) and phi 1.0 (random walk), lengths 250 to 5,000. Control: phi 0.5. Metric: ADF rejection rate and KPSS rejection rate per length. Expected: low ADF power at phi 0.98 for short samples. The rule is wrong if ADF power at phi 0.98 is high at every length. `result: supports: ADF power at phi 0.98: 13% at T = 250, 100% at T = 5000 (below 80% at T = 250, 500, 1000); phi 0.5: 100%; size at phi 1: 4.4%`

## Sources
- Cryer & Chan, *Time Series Analysis with Applications in R* (2008): ch. 2 (stationarity), ch. 5 (differencing, log returns), ch. 6 (ADF, order selection), ch. 9 (EWMA as a forecast), ch. 11 (spurious correlation, prewhitening), ch. 3 (seasonal means).
- Dickey & Fuller (1979), *J. Amer. Statist. Assoc.*: the unit-root test.
- Kwiatkowski, Phillips, Schmidt & Shin (1992), *J. Econometrics*: KPSS, stationarity as the null.
- López de Prado (2018), ch. 3 and ch. 5 (labels and features computed point-in-time).
