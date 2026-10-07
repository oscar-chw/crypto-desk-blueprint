# Foundations: the sixteen ideas the pipeline rests on

Each row is one idea a quant interviewer expects you to own: what it is in plain words, the one formula,
the mistake it prevents, where it lives in this pipeline, the experiment that demonstrates it
([EVIDENCE.md](EVIDENCE.md)) and where to read more. Formulas use per-period quantities unless stated.

## 1. Returns and time series

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Returns and log returns | Work with changes, not price levels. Log returns add up over time and treat up and down moves symmetrically. | $r_t=\ln P_t-\ln P_{t-1}$ | Regressing or averaging price levels; compounding simple returns by adding them | [02](02-features.md) | [EXP-02-2](EVIDENCE.md): supports; levels reject 87.5% (SE 1.0%) of independent pairs; returns reject 4.3% (SE 0.6%) | Cryer & Chan (2008) ch. 5 |
| Stationarity and unit roots | A series is usable for estimation when its mean and autocorrelation do not drift. Prices have a unit root; returns, funding and basis usually do not. | $\Delta y_t=a\,y_{t-1}+\sum_j \phi_j\Delta y_{t-j}+e_t$, test $a=0$ | Fitting a model to a series whose statistics change, then trusting its fit | [02](02-features.md) | [EXP-02-3](EVIDENCE.md): supports; ADF power at phi 0.98: 13% at T = 250, 100% at T = 5000 (below 80% at T = 250, 500, 1000); phi 0.5: 100%; size at phi 1: 4.4% | Dickey & Fuller (1979); Cryer & Chan ch. 6 |
| Volatility clustering (GARCH) | Big moves follow big moves. Today's variance depends on yesterday's shock and yesterday's variance. | $\sigma_t^2=\omega+\alpha r_{t-1}^2+\beta\sigma_{t-1}^2$ | Sizing with a constant volatility, so positions stay large into a crash | [05](05-risk.md) | [EXP-05-1](EVIDENCE.md): supports; vol dispersion 0.30 vs 0.38 (synthetic, diff SE 0.001), 0.29 vs 0.43 on BTC; p95 max drawdown 81% vs 86%; turnover 0.029 vs 0 per day | Engle (1982); Bollerslev (1986); Cryer & Chan ch. 12 |
| Mean reversion and cointegration | Two prices can wander yet keep a stable spread; the spread's pull-back speed gives a half-life that sets holding time. | $dz=-\theta(z-\mu)dt+\sigma dW$, $t_{1/2}=\ln 2/\theta$ | Trading a "pair" whose spread has no anchor; arbitrary exits | [03](03-strategy.md) | [EXP-03-2](EVIDENCE.md): does not support; half-life error -0.6% at 5, -3.1% at 20, -7.0% at 50 (worst 8.8 SE; Kendall's AR(1) bias formula predicts -12.7% at 50); Engle-Granger size 5.2% (SE 0.7%), 14.7% with the plain ADF critical value | Engle & Granger (1987); Chan (2009) ch. 7 |
| State estimation (Kalman) | Track a hidden quantity, such as a hedge ratio, that drifts over time, updating the estimate as each observation arrives. | $x_{t\mid t}=x_{t\mid t-1}+K_t\,(y_t-C x_{t\mid t-1})$ | A static hedge ratio that silently stops hedging after a regime change | [03](03-strategy.md) | [EXP-03-1](EVIDENCE.md): supports; after the break Kalman spread variance is 0.43x OLS's (ratio RMSE 0.037 vs 0.500); with no break 0.31x (RMSE 0.022 vs 0.004) | Kalman (1960) |

## 2. Honest data and honest tests

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Look-ahead and point-in-time data | Use a fact only after the moment you could have known it, including corrections published later. | value at $t$ uses rows with $\text{available\_at}\le t$ | Centred windows, full-sample normalisation, using revised data as if first published | [00](00-infrastructure.md), [02](02-features.md) | [EXP-02-1](EVIDENCE.md): does not support; leaked IC 0.191 (SE 0.002) vs trailing IC -0.009 (SE 0.002) on pure noise; trailing IC outside 2 SE of 0 (uncentred -0.0026, SE 0.0024); the blueprint's own falsification condition (leaked IC within 2 SE of 0) is not met | López de Prado (2018) ch. 2; Chan (2009) ch. 3 |
| Survivorship and selection bias | A universe of today's survivors hides everything that died; the backtest only sees winners. | universe at $t$ = instruments listed at $t$ | Backtests that fade the day they go live | [01](01-data.md) | [EXP-01-1](EVIDENCE.md): supports; survivors-only 9.6 bp/day vs point-in-time -0.1 bp/day; bias 9.7 bp/day (SE 0.1), about 35% a year, with 58% of coins surviving | Chan (2009) ch. 3; López de Prado (2018) ch. 11 |
| Overfitting and multiple testing | Try enough variants and one looks great by luck. Discount the best result by how many you tried. | $\mathbb{E}[\max SR]\approx\sqrt{V}\big((1-\gamma)\Phi^{-1}(1-\tfrac1N)+\gamma\Phi^{-1}(1-\tfrac1{Ne})\big)$ | Promoting the best of a hundred backtests as if it were the only one | [08](08-validation.md) | [EXP-08-2](EVIDENCE.md): supports; raw PSR false-pass 5%, 41%, 99%, 100% for N = 1, 10, 100, 1000; deflated 4.8%, 0.0%, 0.0%, 0.3% | Bailey & López de Prado (2014); López de Prado (2018) ch. 14 |
| Cross-validation for time series | Labels that span time overlap; drop training samples that overlap the test period and a buffer after it. | drop $i$ if $[t_{0,i},t_{1,i}]\cap[t^{test}_{start},t^{test}_{end}+h]\neq\emptyset$ | Plain k-fold showing skill on pure noise | [08](08-validation.md) | [EXP-08-1](EVIDENCE.md): supports; accuracy on pure noise: plain shuffled k-fold 0.662 (SE 0.005), contiguous unpurged 0.497 (SE 0.008), purged + embargo 0.495 (SE 0.008) | López de Prado (2018) ch. 7 |

## 3. Pricing

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| No-arbitrage and carry (forwards, basis, perp funding) | A future must cost spot plus the cost of holding the coin until expiry, or a riskless trade exists; perpetual funding plays the same role without an expiry. | $F=S\,e^{(r_{quote}-r_{base})\tau}$ | Calling carry "alpha"; a funding sign error; trading inside the cost band | [04](04-pricing.md) | [EXP-04-1](EVIDENCE.md): supports; aligned corr BTC 0.34 (SE 0.05), ETH 0.35 (SE 0.08) vs shifted 95th pct 0.17 / 0.14; basis outside the assumed band 9.3% / 9.0% of hours | Baxter & Rennie (1996) ch. 1, 4 |

## 4. Risk and portfolio

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Position sizing (Kelly) and risk of ruin | The bet size that maximises long-run growth is edge over variance; betting more lowers growth and risks ruin. Use a fraction because the edge is estimated. | $f^*=\mu/\sigma^2$, growth $g(f)=r+f\mu-\tfrac12 f^2\sigma^2$ | Full Kelly on an overestimated edge; levering until one bad run ends the account | [06](06-portfolio.md) | [EXP-06-1](EVIDENCE.md): supports; true edge: half Kelly keeps 74% of full Kelly's median growth with p95 max drawdown 69% vs 93%; edge overestimated 2x: half Kelly growth 12.84 vs 0.35 bp/period, drawdown 93% vs 100% | Kelly (1956); Thorp (2006); Chan (2009) ch. 6 |
| Drawdown and risk limits | Decide in advance how much you can lose in a day and from the peak, and stop automatically when you get there. | $DD_t=1-E_t/\max_{s\le t}E_s$ | Limits invented during the loss; a stop that only logs | [05](05-risk.md) | [EXP-05-2](EVIDENCE.md): supports; p99 max drawdown 25% with limits vs 70% without (diff SE 1.8%); median terminal wealth 0.879 vs 0.797 (diff +0.082, SE 0.009); kill switch tripped on 96% of paths | Chan (2009) ch. 3, 6 |
| Factor models and beta | Most of a coin's move is the market's move times its beta; the rest is specific. Measure and cap the shared part. | $r_i=\alpha_i+\beta_i f+\epsilon_i$, $\Sigma=B\Omega B^\top+D$ | A "diversified" book that is one BTC bet | [05](05-risk.md) | [EXP-05-3](EVIDENCE.md): supports; mean absolute BTC beta 0.174 dollar-neutral vs 0.048 beta-neutral (paired diff SE 0.006) | Fama & French (1993); MSCI Barra risk-model documentation |
| Portfolio construction | Mean-variance weights swing on small input changes; anchor them to a prior and blend views by confidence. | $\mu_{BL}=[(\tau\Sigma)^{-1}+P^\top\Omega^{-1}P]^{-1}[(\tau\Sigma)^{-1}\Pi+P^\top\Omega^{-1}Q]$ | Corner portfolios that flip every rebalance | [06](06-portfolio.md) | [EXP-06-2](EVIDENCE.md): supports; turnover per rebalance 0.83 (BL) vs 1.13 (MV) in L1 at gross 1; largest weight 0.27 vs 0.26 | Markowitz (1952); Black & Litterman (1992) |

## 5. Execution

| concept | in plain words | key formula | mistake it prevents | stage | demo | source |
|---|---|---|---|---|---|---|
| Transaction costs and capacity | Fees, spread and impact are paid on every trade; a small edge traded often can be all cost. Capacity is the size at which costs eat the edge. | net $=$ gross $-$ turnover $\times$ cost per trade | Reporting gross results; scaling a strategy past its liquidity | [07](07-execution.md) | [EXP-07-1](EVIDENCE.md): does not support; synthetic edge: annual Sharpe 0.16 (SE 0.45) at 0 bp (realised position IC 0.0017 vs 0.0160 expected), break-even 0.10 bp, -7.58 at 5 bp; BTC planted edge break-even 1.83 bp; toy placeholder on BTC -2.14 gross, -5.29 at 10 bp | Chan (2009) ch. 2, 3, 8 |
| Market impact and slippage | Your own order moves the price, roughly with the square root of its share of volume; slicing trades impact for timing risk. | impact $\approx k\,\sigma\sqrt{q/V}$ | Assuming fills at mid; one large market order into a thin book | [07](07-execution.md) | [EXP-07-2](EVIDENCE.md): supports; at 5x top depth: sliced 1.48 bp (sd 1.72) vs single 2.80 bp (sd 0); at 0.1x: 1.00 vs 1.00 bp | Almgren & Chriss (2000); Almgren et al. (2005) |

Notation: $\gamma$ is the Euler-Mascheroni constant, $V$ the variance of Sharpe ratios across trials, $N$
the number of trials, $\Phi$ the standard normal CDF, $h$ the embargo, $\Pi$ the equilibrium returns,
$P,Q,\Omega$ the view matrix, view returns and view uncertainty. Full citations are in each stage file.
