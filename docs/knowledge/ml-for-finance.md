# Machine learning for finance

## Why it matters for the template
Models live in [features](../../blueprint/02-features.md) and [strategy](../../blueprint/03-strategy.md); the main risk is
fooling yourself, which is the job of [validation](../../blueprint/08-validation.md). Covariance denoising feeds
[portfolio](../../blueprint/06-portfolio.md); see also [portfolio-and-active-management.md](portfolio-and-active-management.md).

## Core results
**Bias–variance.** For $y=f(x)+\varepsilon$, $\mathrm{Var}(\varepsilon)=\sigma^2$, and an estimator $\hat f$ trained on random data,
$$E[(y-\hat f(x))^2]=\underbrace{(E\hat f-f)^2}_{\text{bias}^2}+\underbrace{\mathrm{Var}(\hat f)}_{\text{variance}}+\sigma^2.$$
Financial returns have very low signal-to-noise, so $\sigma^2$ dominates and variance control is paramount.

**Regularisation.** Ridge: $\hat\beta=(X^\top X+\lambda I)^{-1}X^\top y$ (Hoerl and Kennard, 1970) shrinks all coefficients;
lasso (Tibshirani, 1996) adds $\lambda\|\beta\|_1$ and selects. Both are MAP estimates under Gaussian and Laplace priors.

**Tree ensembles.** Bagging (Breiman, 1996) averages trees trained on bootstrap samples, cutting variance; random
forests (Breiman, 2001) also subsample features to decorrelate trees: ensemble variance is
$\rho\sigma^2+(1-\rho)\sigma^2/B$ for $B$ trees with pairwise correlation $\rho$. Gradient boosting (Friedman, 2001) fits
trees sequentially to residuals; more rounds reduce bias but can overfit.

**CV pitfalls.** Standard k-fold assumes i.i.d. samples. With overlapping labels (a return over horizon $h$) neighbouring
rows share information, so training and test leak. Remedies: purging training rows whose label window overlaps the test fold,
and an embargo after it; combinatorial purged CV gives a distribution of out-of-sample paths (López de Prado, 2018,
"Advances in Financial Machine Learning", ch. on cross-validation, see also). Multiple testing: the best of $N$ trials has
an inflated Sharpe, corrected by the deflated Sharpe ratio (Bailey and López de Prado, 2014, "The deflated Sharpe ratio").

**Feature importance.** MDI: impurity decrease summed over splits using a feature, in-sample and biased toward
high-cardinality features. MDA: drop in out-of-sample score when a feature is permuted. SFI: out-of-sample score of a
model on one feature alone, which avoids substitution effects between correlated features.

**Marchenko–Pastur (1967).** For $T\times N$ i.i.d. data with variance $\sigma^2$ and $q=N/T\le 1$, the eigenvalues of the sample
covariance matrix fall in (for a correlation matrix, $\sigma^2=1$; for $q>1$ there is extra mass at zero)
$$\lambda_\pm=\sigma^2\big(1\pm\sqrt q\big)^2,$$
with density $\frac{\sqrt{(\lambda_+-\lambda)(\lambda-\lambda_-)}}{2\pi\sigma^2q\lambda}$. Eigenvalues above $\lambda_+$ carry signal;
the rest are noise and may be replaced by their average (constant-residual denoising) (Laloux et al., 1999, "Noise dressing of
financial correlation matrices").

## Where practice differs from the textbook
- Simple, strongly regularised models and a few robust features beat deep models on short, noisy histories.
- Labels are often triple-barrier or sign-of-return rather than raw return, with sample weights for overlap.
- Feature stationarity matters more than model class; fractional differencing is one compromise.
- Every trial counts: the number of configurations tried is logged so selection bias can be deflated.

## Checks this implies
- No training row has a label window overlapping a test row (purge and embargo test).
- Permuting labels gives a score near chance; shuffled-time features give no edge.
- A feature computed from future data fails a timestamp audit.
- Reported Sharpe is accompanied by the trial count and a deflated or probabilistic value.
- On pure noise data, the largest sample eigenvalue is below $\lambda_+$ within finite-size error.
- MDI, MDA and SFI rank a planted signal feature above planted noise.

## Sources
- Hoerl, A. and Kennard, R. (1970), "Ridge regression: biased estimation for nonorthogonal problems".
- Tibshirani, R. (1996), "Regression shrinkage and selection via the lasso".
- Breiman, L. (1996), "Bagging predictors"; (2001), "Random forests".
- Friedman, J. (2001), "Greedy function approximation: a gradient boosting machine".
- Marchenko, V. and Pastur, L. (1967), "Distribution of eigenvalues for some sets of random matrices".
- Laloux, Cizeau, Bouchaud, Potters (1999), "Noise dressing of financial correlation matrices".
- Bailey, D. and López de Prado, M. (2014), "The deflated Sharpe ratio".
- See also: López de Prado, "Advances in Financial Machine Learning"; Hastie, Tibshirani, Friedman, "The Elements of Statistical Learning".
