# Stochastic calculus core

## Why it matters for the template
This is the derivation backbone behind [pricing](../../blueprint/04-pricing.md) (no-arbitrage and the risk-neutral
measure), the simulations used in [validation](../../blueprint/08-validation.md), and the continuous-time
models of [execution](../../blueprint/07-execution.md). Read it before [options-and-volatility.md](options-and-volatility.md).

## Core results
**Brownian motion.** $W$ is a process with $W_0=0$, independent increments, $W_t-W_s\sim N(0,t-s)$ and continuous
paths. Paths are nowhere differentiable and have quadratic variation $[W]_t=t$, written $dW^2=dt$.

**Itô integral.** For adapted $H$ with $E\int_0^T H^2dt<\infty$, $\int H\,dW$ is a martingale with
$E[(\int H dW)^2]=E\int H^2dt$ (Itô isometry). Integrand evaluated at the left endpoint.

**Itô's lemma** (Itô, 1944/1951): for $dX=\mu\,dt+\sigma\,dW$ and $f\in C^{1,2}$,
$$df=\left(f_t+\mu f_x+\tfrac12\sigma^2f_{xx}\right)dt+\sigma f_x\,dW.$$
Application: $dS=\mu S\,dt+\sigma S\,dW$ gives $S_T=S_0\exp\{(\mu-\tfrac12\sigma^2)T+\sigma W_T\}$.
The $-\tfrac12\sigma^2$ term is why mean log return differs from log of mean return.

**Girsanov** (1960): if $\theta$ satisfies Novikov's condition $E\,e^{\frac12\int_0^T\theta^2dt}<\infty$, define
$$\frac{d\mathbb Q}{d\mathbb P}\Big|_{\mathcal F_T}=\exp\Big\{-\!\int_0^T\theta\,dW-\tfrac12\int_0^T\theta^2dt\Big\}.$$
Then $\tilde W_t=W_t+\int_0^t\theta\,ds$ is a $\mathbb Q$-Brownian motion: the change of measure alters drift, not volatility.

**Risk-neutral pricing.** With market price of risk $\theta=(\mu-r)/\sigma$, discounted traded prices are
$\mathbb Q$-martingales, and under completeness the price of a payoff $X$ is
$$V_t=E^{\mathbb Q}\!\left[e^{-r(T-t)}X\mid\mathcal F_t\right].$$
Feynman–Kac links this expectation to the pricing PDE.

**Fundamental theorems** (Harrison–Kreps, 1979; Harrison–Pliska, 1981; Delbaen–Schachermayer, 1994): no
arbitrage (in the NFLVR sense) iff an equivalent martingale measure exists; the market is complete iff it is unique.

**Ornstein–Uhlenbeck** $dX=\kappa(\bar x-X)dt+\sigma dW$: $E[X_t]=\bar x+(X_0-\bar x)e^{-\kappa t}$, stationary variance
$\sigma^2/2\kappa$, half-life $\ln 2/\kappa$. Standard model for spreads and basis.

## Where practice differs from the textbook
- Real data are discrete and gappy; Itô terms appear as bias when one averages simple returns versus log returns.
- Markets are incomplete (jumps, stochastic vol, transaction costs), so $\mathbb Q$ is not unique and desks
  calibrate it to option prices; $\mathbb P$-measure forecasts and $\mathbb Q$-measure prices must not be mixed.
- Crypto basis and funding are priced by carry arbitrage with funding, borrow and margin frictions, so the
  no-arbitrage identity is a band, not an equality.
- Monte Carlo is the workhorse: Euler schemes carry discretisation bias; use antithetic variates and exact
  lognormal steps where available.

## Checks this implies
- Simulated GBM satisfies $E[S_T]=S_0e^{\mu T}$ and $E[\ln S_T]=\ln S_0+(\mu-\tfrac12\sigma^2)T$ within Monte Carlo error.
- Sample quadratic variation of a simulated path converges to $\sigma^2T$ as step size shrinks.
- Under simulated $\mathbb Q$ dynamics, the discounted asset price has constant mean (martingale test).
- Monte Carlo price of a vanilla option matches the closed form within a few standard errors.
- OU simulation recovers $\kappa$ and half-life from a fit within tolerance.

## Sources
- Itô, K. (1944), "Stochastic integral"; (1951) "On a formula concerning stochastic differentials".
- Girsanov, I. V. (1960), "On transforming a certain class of stochastic processes by absolutely continuous substitution of measures".
- Harrison, J. M. and Kreps, D. M. (1979), "Martingales and arbitrage in multiperiod securities markets".
- Harrison, J. M. and Pliska, S. R. (1981), "Martingales and stochastic integrals in the theory of continuous trading".
- Delbaen, F. and Schachermayer, W. (1994), "A general version of the fundamental theorem of asset pricing".
- See also: Shreve, "Stochastic Calculus for Finance II"; Øksendal, "Stochastic Differential Equations".
