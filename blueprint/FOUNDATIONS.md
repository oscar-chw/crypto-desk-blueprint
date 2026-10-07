# Foundations: the sixteen ideas the pipeline rests on

Each row is one idea a quant interviewer expects you to own: what it is in plain words, the one formula,
the mistake it prevents, where it lives in this pipeline, the experiment that demonstrates it
([EVIDENCE.md](EVIDENCE.md)) and where to read more. Formulas use per-period quantities unless stated.

## 1. Returns and time series

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Returns and log returns | Work with changes, not price levels. Log returns add up over time and treat up and down moves symmetrically. | $r_t=\ln P_t-\ln P_{t-1}$ | Regressing or averaging price levels; compounding simple returns by adding them | [02](02-features.md) | EXP-02-2 | Cryer & Chan (2008) ch. 5 |
| Stationarity and unit roots | A series is usable for estimation when its mean and autocorrelation do not drift. Prices have a unit root; returns, funding and basis usually do not. | $\Delta y_t=a\,y_{t-1}+\sum_j \phi_j\Delta y_{t-j}+e_t$, test $a=0$ | Fitting a model to a series whose statistics change, then trusting its fit | [02](02-features.md) | EXP-02-3 | Dickey & Fuller (1979); Cryer & Chan ch. 6 |
| Volatility clustering (GARCH) | Big moves follow big moves. Today's variance depends on yesterday's shock and yesterday's variance. | $\sigma_t^2=\omega+\alpha r_{t-1}^2+\beta\sigma_{t-1}^2$ | Sizing with a constant volatility, so positions stay large into a crash | [05](05-risk.md) | EXP-05-1 | Engle (1982); Bollerslev (1986); Cryer & Chan ch. 12 |
| Mean reversion and cointegration | Two prices can wander yet keep a stable spread; the spread's pull-back speed gives a half-life that sets holding time. | $dz=-\theta(z-\mu)dt+\sigma dW$, $t_{1/2}=\ln 2/\theta$ | Trading a "pair" whose spread has no anchor; arbitrary exits | [03](03-strategy.md) | EXP-03-2 | Engle & Granger (1987); Chan (2009) ch. 7 |
| State estimation (Kalman) | Track a hidden quantity, such as a hedge ratio, that drifts over time, updating the estimate as each observation arrives. | $x_{t\mid t}=x_{t\mid t-1}+K_t\,(y_t-C x_{t\mid t-1})$ | A static hedge ratio that silently stops hedging after a regime change | [03](03-strategy.md) | EXP-03-1 | Kalman (1960) |

## 2. Honest data and honest tests

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Look-ahead and point-in-time data | Use a fact only after the moment you could have known it, including corrections published later. | value at $t$ uses rows with $\text{available\_at}\le t$ | Centred windows, full-sample normalisation, using revised data as if first published | [00](00-infrastructure.md), [02](02-features.md) | EXP-02-1 | López de Prado (2018) ch. 2; Chan (2009) ch. 3 |
| Survivorship and selection bias | A universe of today's survivors hides everything that died; the backtest only sees winners. | universe at $t$ = instruments listed at $t$ | Backtests that fade the day they go live | [01](01-data.md) | EXP-01-1 | Chan (2009) ch. 3; López de Prado (2018) ch. 11 |
| Overfitting and multiple testing | Try enough variants and one looks great by luck. Discount the best result by how many you tried. | $\mathbb{E}[\max SR]\approx\sqrt{V}\big((1-\gamma)\Phi^{-1}(1-\tfrac1N)+\gamma\Phi^{-1}(1-\tfrac1{Ne})\big)$ | Promoting the best of a hundred backtests as if it were the only one | [08](08-validation.md) | EXP-08-2 | Bailey & López de Prado (2014); López de Prado (2018) ch. 14 |
| Cross-validation for time series | Labels that span time overlap; drop training samples that overlap the test period and a buffer after it. | drop $i$ if $[t_{0,i},t_{1,i}]\cap[t^{test}_{start},t^{test}_{end}+h]\neq\emptyset$ | Plain k-fold showing skill on pure noise | [08](08-validation.md) | EXP-08-1 | López de Prado (2018) ch. 7 |

## 3. Pricing

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| No-arbitrage and carry (forwards, basis, perp funding) | A future must cost spot plus the cost of holding the coin until expiry, or a riskless trade exists; perpetual funding plays the same role without an expiry. | $F=S\,e^{(r_{quote}-r_{base})\tau}$ | Calling carry "alpha"; a funding sign error; trading inside the cost band | [04](04-pricing.md) | EXP-04-1 | Baxter & Rennie (1996) ch. 1, 4 |

## 4. Risk and portfolio

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Position sizing (Kelly) and risk of ruin | The bet size that maximises long-run growth is edge over variance; betting more lowers growth and risks ruin. Use a fraction because the edge is estimated. | $f^*=\mu/\sigma^2$, growth $g(f)=r+f\mu-\tfrac12 f^2\sigma^2$ | Full Kelly on an overestimated edge; levering until one bad run ends the account | [06](06-portfolio.md) | EXP-06-1 | Kelly (1956); Thorp (2006); Chan (2009) ch. 6 |
| Drawdown and risk limits | Decide in advance how much you can lose in a day and from the peak, and stop automatically when you get there. | $DD_t=1-E_t/\max_{s\le t}E_s$ | Limits invented during the loss; a stop that only logs | [05](05-risk.md) | EXP-05-2 | Chan (2009) ch. 3, 6 |
| Factor models and beta | Most of a coin's move is the market's move times its beta; the rest is specific. Measure and cap the shared part. | $r_i=\alpha_i+\beta_i f+\epsilon_i$, $\Sigma=B\Omega B^\top+D$ | A "diversified" book that is one BTC bet | [05](05-risk.md) | EXP-05-3 | Fama & French (1993); MSCI Barra risk-model documentation |
| Portfolio construction | Mean-variance weights swing on small input changes; anchor them to a prior and blend views by confidence. | $\mu_{BL}=[(\tau\Sigma)^{-1}+P^\top\Omega^{-1}P]^{-1}[(\tau\Sigma)^{-1}\Pi+P^\top\Omega^{-1}Q]$ | Corner portfolios that flip every rebalance | [06](06-portfolio.md) | EXP-06-2 | Markowitz (1952); Black & Litterman (1992) |

## 5. Execution

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Transaction costs and capacity | Fees, spread and impact are paid on every trade; a small edge traded often can be all cost. Capacity is the size at which costs eat the edge. | net $=$ gross $-$ turnover $\times$ cost per trade | Reporting gross results; scaling a strategy past its liquidity | [07](07-execution.md) | EXP-07-1 | Chan (2009) ch. 2, 3, 8 |
| Market impact and slippage | Your own order moves the price, roughly with the square root of its share of volume; slicing trades impact for timing risk. | impact $\approx k\,\sigma\sqrt{q/V}$ | Assuming fills at mid; one large market order into a thin book | [07](07-execution.md) | EXP-07-2 | Almgren & Chriss (2000); Almgren et al. (2005) |

Notation: $\gamma$ is the Euler-Mascheroni constant, $V$ the variance of Sharpe ratios across trials, $N$
the number of trials, $\Phi$ the standard normal CDF, $h$ the embargo, $\Pi$ the equilibrium returns,
$P,Q,\Omega$ the view matrix, view returns and view uncertainty. Full citations are in each stage file.
