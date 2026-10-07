# Options and volatility

## Why it matters for the template
Options are out of scope for the blueprint's [pricing stage](../../blueprint/04-pricing.md), but the same no-arbitrage
logic prices futures and funding there. Implied volatility also feeds [risk](../../blueprint/05-risk.md) as a forward-looking
input, and variance-swap logic explains why realised variance is the natural thing to forecast in
[features](../../blueprint/02-features.md).

## Core results
**Black–Scholes–Merton** (1973): under a lognormal underlying with constant volatility $\sigma$, constant rate $r$,
dividend yield $q$, continuous frictionless trading and no arbitrage, a European call is
$$C = S e^{-qT}N(d_1) - K e^{-rT}N(d_2),\quad d_{1,2}=\frac{\ln(S/K)+(r-q\pm\tfrac12\sigma^2)T}{\sigma\sqrt T}.$$
The same price solves $\partial_t V+\tfrac12\sigma^2S^2V_{SS}+(r-q)SV_S-rV=0$ with the payoff as terminal condition.

**Greeks** (same assumptions): $\Delta=\partial V/\partial S$, $\Gamma=\partial^2V/\partial S^2$, $\nu=\partial V/\partial\sigma$,
$\Theta=\partial V/\partial t$. For a delta-hedged position the PDE gives
$$\Theta+\tfrac12\sigma^2S^2\Gamma = rV - (r-q)S\Delta,$$
so with $r=q=0$ long gamma pays theta: P&L over $dt$ is $\tfrac12\Gamma S^2(\sigma_{\rm real}^2-\sigma_{\rm imp}^2)\,dt$.

**Put-call parity** (model-free for European options, no arbitrage, no early exercise, known carry):
$$C-P=S e^{-qT}-K e^{-rT}.$$

**Implied vs realised.** Implied vol is the $\sigma$ that makes the model price equal the market price; it is a
price quotation, not a forecast. The variance risk premium is $E^{\mathbb Q}[\text{var}]-E^{\mathbb P}[\text{var}]$,
typically positive for equity indices (sellers of variance are paid for bearing crash risk).

**Smile and skew.** If BSM held, implied vol would be flat in strike. Observed curves are not flat. Under
no arbitrage the call price must be decreasing and convex in strike, and calendar spreads non-negative
(Gatheral and Jacquier, 2014, "Arbitrage-free SVI volatility surfaces").

**SVI** (Gatheral, 2004, "A parsimonious arbitrage-free implied volatility parameterization"): total variance
$w(k)=\sigma_{\rm imp}^2T$ at log-moneyness $k=\ln(K/F)$ is
$$w(k)=a+b\left\{\rho(k-m)+\sqrt{(k-m)^2+s^2}\right\},\quad b\ge0,\ |\rho|<1,\ s>0.$$
Wings are linear in $k$ (Lee, 2004, "The moment formula for implied volatility at extreme strikes"), and
$b(1+|\rho|)\le 4/T$ is the usual condition for no moment explosion.

**Variance swap** (Demeterfi, Derman, Kamal, Zou, 1999, "More than you ever wanted to know about volatility swaps"):
assuming continuous prices without jumps, the fair strike is a log-contract replicated by options:
$$K_{\rm var}=\frac{2e^{rT}}{T}\left[\int_0^{F}\frac{P(K)}{K^2}dK+\int_F^\infty\frac{C(K)}{K^2}dK\right],$$
with $F$ the forward and $P,C$ out-of-the-money option prices.
This is the model-free basis of VIX-style indices.

## Where practice differs from the textbook
- Vol is not constant: desks quote in implied vol and treat BSM as a quoting convention, hedging with
  sticky-strike or sticky-delta rules depending on the market.
- Delta hedging is discrete and costly, so the gamma P&L identity holds only roughly; hedge bands trade
  tracking error against fees.
- Surfaces are fitted, then checked for butterfly and calendar arbitrage; raw SVI fits per expiry can
  violate calendar arbitrage unless constrained.
- American exercise, discrete dividends and borrow costs break parity into an inequality.
- Jumps make variance-swap replication with a finite strike grid biased; crypto smiles are often steep on
  both wings.

## Checks this implies
- Put-call parity residual is within the bid-ask band for every quoted pair.
- BSM price is monotone in $\sigma$; implied-vol inversion round-trips price to within tolerance.
- Fitted call prices are convex and decreasing in strike; total variance non-decreasing in maturity.
- Delta from finite differences matches the analytic delta; gamma $\ge0$ for vanilla options.
- A delta-hedged book's simulated P&L matches $\tfrac12\Gamma S^2(\sigma_r^2-\sigma_i^2)dt$ on GBM paths.

## Sources
- Black, F. and Scholes, M. (1973), "The Pricing of Options and Corporate Liabilities".
- Merton, R. C. (1973), "Theory of Rational Option Pricing".
- Gatheral, J. (2004), "A parsimonious arbitrage-free implied volatility parameterization with application to the valuation of volatility derivatives" (Global Derivatives talk).
- Gatheral, J. and Jacquier, A. (2014), "Arbitrage-free SVI volatility surfaces".
- Lee, R. (2004), "The moment formula for implied volatility at extreme strikes".
- Demeterfi, Derman, Kamal, Zou (1999), "More than you ever wanted to know about volatility swaps".
- See also: Gatheral, "The Volatility Surface"; Hull, "Options, Futures, and Other Derivatives".
