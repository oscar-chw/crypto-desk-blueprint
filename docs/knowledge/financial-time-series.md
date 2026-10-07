# Financial time series

## Why it matters for the template
Defines what the series in [data](../../blueprint/01-data.md) look like, how [features](../../blueprint/02-features.md) such as
realised volatility are built, how [risk](../../blueprint/05-risk.md) forecasts covariance, and which spreads a
[strategy](../../blueprint/03-strategy.md) may treat as mean-reverting.

## Core results
**Stylised facts** (Cont, 2001, "Empirical properties of asset returns: stylized facts and statistical issues"):
returns show little linear autocorrelation, heavy tails (tail index roughly 3 to 5 for many assets), volatility
clustering ($|r_t|$ is positively autocorrelated, slowly decaying), a leverage effect in equities, and
aggregational Gaussianity (returns approach normality as the horizon grows).

**GARCH(1,1)** (Engle, 1982, ARCH; Bollerslev, 1986):
$$r_t=\sigma_t z_t,\quad \sigma_t^2=\omega+\alpha r_{t-1}^2+\beta\sigma_{t-1}^2,$$
with $z_t$ i.i.d. mean 0, variance 1. Covariance stationary iff $\alpha+\beta<1$, with
$\mathrm{Var}(r)=\omega/(1-\alpha-\beta)$. Even with Gaussian $z$ the unconditional kurtosis exceeds 3. Variants: EGARCH
(Nelson, 1991) and GJR (Glosten, Jagannathan, Runkle, 1993) capture asymmetry.

**Realised variance** (Andersen, Bollerslev, Diebold, Labys, 2003, "Modeling and forecasting realized volatility"):
$$\mathrm{RV}_t=\sum_{i=1}^{M}r_{t,i}^2\ \xrightarrow{M\to\infty}\ \int_{t-1}^{t}\sigma_s^2ds+\sum \text{jumps}^2$$
for a semimartingale without microstructure noise. With noise, RV is biased upward as the sampling interval
shrinks (volatility signature plot). HAR-RV (Corsi, 2009, "A simple approximate long-memory model of realized
volatility") regresses next-day RV on daily, weekly and monthly RV averages.

**DCC** (Engle, 2002, "Dynamic conditional correlation"): $H_t=D_tR_tD_t$ with $D_t$ from univariate GARCH and
$$Q_t=(1-a-b)\bar Q+a\,\varepsilon_{t-1}\varepsilon_{t-1}^\top+b\,Q_{t-1},\quad R_t=\mathrm{diag}(Q_t)^{-1/2}Q_t\,\mathrm{diag}(Q_t)^{-1/2}.$$
Needs $a,b\ge0$, $a+b<1$ for stationarity and positive definiteness.

**Cointegration** (Engle and Granger, 1987): $x_t,y_t\sim I(1)$ are cointegrated if some $y_t-\beta x_t$ is $I(0)$.
Test by regressing and applying an augmented Dickey–Fuller test to residuals (with Engle–Granger critical values, not
standard ones), or Johansen (1988) for several series. Spreads then follow an error-correction model.

## Where practice differs from the textbook
- Desks use EWMA ($\lambda\approx0.94$, RiskMetrics) or HAR as often as full GARCH: robust and cheap.
- Realised vol from 5-minute bars is the default compromise between noise and discretisation; crypto trades
  24/7, so there is no overnight gap and "daily" needs an explicit cut-off.
- Cointegrating relations drift and break; the hedge ratio is re-estimated on a rolling window, and pairs are
  selected from many candidates, which inflates false positives unless the selection is in the test.
- Heavy tails mean Gaussian VaR understates risk; use Student-t or filtered historical simulation.

## Checks this implies
- Simulated GARCH satisfies $\alpha+\beta<1$ and reproduces the unconditional variance within error.
- Squared-return autocorrelation of real data is positive and decaying (Ljung–Box on $r^2$ rejects white noise).
- RV estimate stabilises across sampling intervals before microstructure noise dominates.
- DCC correlation matrices are positive definite with unit diagonal at every date.
- Cointegration is tested out of sample, and the spread's half-life is finite and shorter than the holding window.
- Feature timestamps use only data available at the decision time (no look-ahead in rolling windows).

## Sources
- Cont, R. (2001), "Empirical properties of asset returns: stylized facts and statistical issues".
- Engle, R. (1982), "Autoregressive conditional heteroscedasticity with estimates of the variance of United Kingdom inflation".
- Bollerslev, T. (1986), "Generalized autoregressive conditional heteroskedasticity".
- Nelson, D. (1991), "Conditional heteroskedasticity in asset returns: a new approach".
- Andersen, T., Bollerslev, T., Diebold, F., Labys, P. (2003), "Modeling and forecasting realized volatility".
- Corsi, F. (2009), "A simple approximate long-memory model of realized volatility".
- Engle, R. (2002), "Dynamic conditional correlation".
- Engle, R. and Granger, C. (1987), "Co-integration and error correction".
- Johansen, S. (1988), "Statistical analysis of cointegration vectors".
- See also: Tsay, "Analysis of Financial Time Series".
