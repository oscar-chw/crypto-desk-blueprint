# Evidence: the experiments behind the design rules

Each design rule that matters has an experiment with a **control arm** and a stated **falsification
condition**, specified in its stage file under `## Evidence`. Implementations go in `experiments/`.
Status stays `pending` until an experiment has run and its result file is committed; no number appears
here before then.

| id | backs | claim under test (short) | control | status |
|---|---|---|---|---|
| EXP-00-1 | [00](00-infrastructure.md) rule 2 | one code path: backtest and paper give identical orders | paper loop with a one-bar delay | pending |
| EXP-00-2 | [00](00-infrastructure.md) rules 1, 3 | receive-time stamping misassigns trades to bars | exchange-time bars | pending |
| EXP-01-1 | [01](01-data.md) rule 5 | survivors-only universe inflates returns | full point-in-time universe | pending |
| EXP-01-2 | [01](01-data.md) rule 4 | forward-filled outage biases volatility down | gap kept missing | pending |
| EXP-02-1 | [02](02-features.md) rule 1 | a leaked feature shows skill on pure noise | trailing (point-in-time) feature | pending |
| EXP-02-2 | [02](02-features.md) rule 3 | level-on-level regression rejects far above 5% | same regression on returns | pending |
| EXP-02-3 | [02](02-features.md) rule 4 | ADF has low power near a unit root | phi 0.5 series | pending |
| EXP-03-1 | [03](03-strategy.md) rule 6 | Kalman hedge ratio tracks a regime shift | static OLS ratio; no-break pair | pending |
| EXP-03-2 | [03](03-strategy.md) rule 5 | half-life recovers OU speed; cointegration test holds its size | known theta; nominal 5% | pending |
| EXP-04-1 | [04](04-pricing.md) rules 1-3 | funding and futures basis co-move, basis stays in the band (public Binance data) | time-shifted funding | pending |
| EXP-04-2 | [04](04-pricing.md) rule 4 | continuous funding accrual misstates short holds | discrete payments | pending |
| EXP-05-1 | [05](05-risk.md) rules 1, 2 | vol targeting steadies realised vol and trims tail drawdown | fixed notional | pending |
| EXP-05-2 | [05](05-risk.md) rules 4-6 | loss halt and drawdown budget cut the worst outcomes | no limits | pending |
| EXP-05-3 | [05](05-risk.md) rule 7 | dollar-neutral altcoin book keeps BTC beta | dollar-neutral weights | pending |
| EXP-06-1 | [06](06-portfolio.md) rule 1 | half-Kelly: most of the growth, far smaller drawdowns | full Kelly (true and estimated edge) | pending |
| EXP-06-2 | [06](06-portfolio.md) rules 4, 5 | Black-Litterman weights are stable under noisy views | mean-variance | pending |
| EXP-07-1 | [07](07-execution.md) rule 4 | costs flip a small high-turnover edge negative | zero-cost arm | pending |
| EXP-07-2 | [07](07-execution.md) rule 5 | slicing beats one market order for large orders | single market order | pending |
| EXP-08-1 | [08](08-validation.md) rules 1, 2 | plain k-fold finds skill in noise; purged does not | purged k-fold with embargo | pending |
| EXP-08-2 | [08](08-validation.md) rules 3, 4 | best of N noise strategies passes raw Sharpe, fails deflated | N = 1 | pending |

Rules for running them: fix the seed and the generating process in the script; run the control in the
same run; report each effect with its standard error; a result inside noise is reported as "no effect",
not as support.
