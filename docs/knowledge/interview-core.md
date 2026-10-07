# Interview core

## Why it matters for the template
Quant interviews test the same primitives the pipeline relies on. This note lists topic types only, no questions,
each mapped to the stage and note where the idea is used.

## Core results
Topic types and the formula each leans on (assumptions stated):
- **Conditional probability and Bayes.** $P(A\mid B)=P(B\mid A)P(A)/P(B)$; base-rate neglect is the usual trap.
  Used in adverse selection, see [microstructure-and-execution.md](microstructure-and-execution.md).
- **Expectation, variance, linearity.** $E[\sum X_i]=\sum E[X_i]$ always; $\mathrm{Var}(\sum X_i)=\sum\mathrm{Var}+2\sum\mathrm{Cov}$.
  Behind portfolio variance, see [portfolio-and-active-management.md](portfolio-and-active-management.md).
- **Random walks and gambler's ruin.** For a simple symmetric walk, hitting probabilities are linear in the start; expected
  hitting time between $-a$ and $b$ is $ab$. Martingale optional stopping needs integrability, see
  [stochastic-calculus-core.md](stochastic-calculus-core.md).
- **Distributions.** Normal, lognormal, exponential (memoryless), Poisson; sums and maxima. Lognormal moments follow
  from Itô, see [options-and-volatility.md](options-and-volatility.md).
- **Regression and estimation.** OLS as projection, $\hat\beta=(X^\top X)^{-1}X^\top y$; bias versus variance; omitted
  variables; multicollinearity; standard errors under autocorrelation. See [ml-for-finance.md](ml-for-finance.md).
- **Hypothesis testing and multiple comparisons.** p-values, power, false discovery; the effect of searching many strategies.
  See [ml-for-finance.md](ml-for-finance.md) and [08-validation](../../blueprint/08-validation.md).
- **Law of large numbers, CLT.** The CLT needs finite variance, which heavy tails may not give.
  See [financial-time-series.md](financial-time-series.md).
- **Linear algebra.** Eigenvalues of covariance, PSD matrices, PCA. See [ml-for-finance.md](ml-for-finance.md).
- **Option intuition.** Parity, payoff diagrams, delta and gamma meaning, why vol is a price. See [options-and-volatility.md](options-and-volatility.md).
- **Market-making and betting games.** Quote a two-sided market, size by edge and variance (Kelly: for even-odds win
  probability $p$, optimal fraction $2p-1$ under log utility; Kelly, 1956, "A new interpretation of information rate").
- **Estimation and mental maths.** Order-of-magnitude, scaling by $\sqrt T$, annualising, Fermi-style sizing.
- **Brainteaser types.** Symmetry arguments, recursion on states, invariants, extremal principle, pigeonhole, and
  induction. Reward is clear structure and stated assumptions, not trick recall.
- **Coding.** Arrays, hash maps, complexity, simulation to check an analytic answer, vectorisation.

## Where practice differs from the textbook
- Interviewers care about reasoning aloud and sanity checks more than the final number.
- On-the-job questions are messier: missing data, non-i.i.d. samples, costs. Always ask what assumptions are allowed.
- A simulation that confirms the closed form is a common and welcome cross-check.

## Checks this implies
- Each topic type above links to a note in this folder; a missing link is a gap in the layer.
- Every closed form in a note has a simulation test in the template's tests where feasible.
- Notes cite only primary papers by author, year and title, and books only under "see also".

## Sources
- Kelly, J. (1956), "A new interpretation of information rate".
- See also: Crack, "Heard on the Street"; Joshi, Denson, Downes, "Quant Job Interview Questions and Answers"; Grimmett and Stirzaker, "Probability and Random Processes".
