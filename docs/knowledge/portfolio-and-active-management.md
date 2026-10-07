# Portfolio and active management

## Why it matters for the template
Core of [portfolio](../../blueprint/06-portfolio.md): turning forecasts into weights. It also sets what a good
[strategy](../../blueprint/03-strategy.md) signal must deliver, how [risk](../../blueprint/05-risk.md) models enter, and why
[execution](../../blueprint/07-execution.md) costs cap turnover.

## Core results
**Markowitz (1952)**: with expected returns $\mu$ and covariance $\Sigma$, minimise $\tfrac12 w^\top\Sigma w$ subject to
$w^\top\mu=m$, $w^\top\mathbf 1=1$. Unconstrained mean–variance utility $\mu^\top w-\tfrac{\lambda}{2}w^\top\Sigma w$
gives
$$w^*=\tfrac1\lambda\Sigma^{-1}\mu.$$
Assumes known $\mu,\Sigma$; the optimiser amplifies estimation error in $\mu$ and in small eigenvalues of $\Sigma$.

**Fundamental law** (Grinold, 1989, "The fundamental law of active management"): in its basic form
$$\mathrm{IR}\approx \mathrm{IC}\cdot\sqrt{N},$$
where IC is the correlation between forecast and realised return, $N$ the number of independent bets per year.
Assumes independent bets, unconstrained optimal weights and costless trading. Information ratio is
$\mathrm{IR}=\alpha/\omega$ (active return over tracking error). Clarke, de Silva and Thorley (2002, "Portfolio
constraints and the fundamental law of active management") add a transfer coefficient: $\mathrm{IR}\approx \mathrm{TC}\cdot\mathrm{IC}\sqrt N$.

**Sharpe ratio** (Sharpe, 1966): $\mathrm{SR}=E[r-r_f]/\sigma$. Annualising from period $\Delta$ by $\sqrt{1/\Delta}$ assumes
i.i.d. returns; autocorrelation breaks it (Lo, 2002, "The statistics of Sharpe ratios").

**Black–Litterman (1992)**: prior equilibrium returns $\Pi=\lambda\Sigma w_{\rm mkt}$, views $P\mu=q+\varepsilon$ with
$\varepsilon\sim N(0,\Omega)$, prior $\mu\sim N(\Pi,\tau\Sigma)$. Posterior mean
$$\mu_{BL}=\Pi+\tau\Sigma P^\top(P\tau\Sigma P^\top+\Omega)^{-1}(q-P\Pi).$$
With no views it returns the market portfolio; views tilt it in proportion to their confidence.

**HRP** (López de Prado, 2016, "Building diversified portfolios that outperform out of sample"): cluster assets on the
distance $d_{ij}=\sqrt{\tfrac12(1-\rho_{ij})}$, quasi-diagonalise $\Sigma$, then split weights recursively by inverse
cluster variance. It needs no inversion of $\Sigma$, so it stays stable when $\Sigma$ is ill-conditioned.

**Transaction costs.** A common model charges $c_1|\Delta w|+c_2|\Delta w|^{3/2}$ (spread plus concave impact);
the optimiser then trades only when the marginal alpha gain exceeds marginal cost, producing a no-trade band.

**Risk models.** Factor form $\Sigma=B F B^\top+D$ with $D$ diagonal. Fewer parameters, more stable estimates.

## Where practice differs from the textbook
- Desks seldom use raw $\Sigma^{-1}\mu$: they shrink $\Sigma$ (Ledoit and Wolf, 2004, "A well-conditioned
  estimator for large-dimensional covariance matrices"), cap positions and gross, and include costs in the optimiser.
- Fundamental-law breadth is overstated when signals are correlated; the effective $N$ is much smaller.
- Gross IC is not net IC; turnover eats IC decay faster than a naive forecast horizon suggests.
- Volatility targeting and drawdown rules are applied on top of the optimiser.
- Crypto: few assets, one dominant factor, 24/7 trading, funding as a carry cost, so effective breadth is small.

## Checks this implies
- Weights satisfy stated constraints (budget, gross, net, per-name caps) to numerical tolerance.
- With zero costs and identity covariance, optimiser output is proportional to $\mu$.
- Black–Litterman with empty views returns the prior; $\Omega\to\infty$ is equivalent.
- Backtest IC and IR are reported net of cost, with turnover and the IC half-life beside them.
- Optimiser weights are stable under a small perturbation of $\Sigma$ (condition-number test).
- HRP weights are non-negative and sum to one.

## Sources
- Markowitz, H. (1952), "Portfolio selection".
- Sharpe, W. (1966), "Mutual fund performance".
- Grinold, R. (1989), "The fundamental law of active management".
- Clarke, R., de Silva, H., Thorley, S. (2002), "Portfolio constraints and the fundamental law of active management".
- Black, F. and Litterman, R. (1992), "Global portfolio optimization".
- López de Prado, M. (2016), "Building diversified portfolios that outperform out of sample".
- Ledoit, O. and Wolf, M. (2004), "A well-conditioned estimator for large-dimensional covariance matrices".
- Lo, A. (2002), "The statistics of Sharpe ratios".
- See also: Grinold and Kahn, "Active Portfolio Management".
