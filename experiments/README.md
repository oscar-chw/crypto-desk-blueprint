# experiments/

Runnable demonstrations behind the design rules. Specifications (hypothesis, setup, control, metric,
expected direction, falsification condition) live in each `blueprint/0N-*.md` under `## Evidence`;
the status table is [blueprint/EVIDENCE.md](../blueprint/EVIDENCE.md). Not implemented yet.

One script per id, `exp_0N_k.py`, writing `results/EXP-0N-k.json` with the seed, the control arm's
numbers next to the treatment's, and standard errors.

| id | short name |
|---|---|
| EXP-00-1 | backtest vs paper, one code path |
| EXP-00-2 | exchange time vs receive time |
| EXP-01-1 | survivorship bias |
| EXP-01-2 | forward-filled outage |
| EXP-02-1 | point-in-time vs leaked feature |
| EXP-02-2 | spurious regression on levels |
| EXP-02-3 | ADF power near a unit root |
| EXP-03-1 | static OLS vs Kalman hedge ratio |
| EXP-03-2 | half-life and cointegration size |
| EXP-04-1 | funding vs futures basis (public Binance data) |
| EXP-04-2 | discrete vs continuous funding |
| EXP-05-1 | vol targeting vs fixed notional |
| EXP-05-2 | loss limits and drawdown budget |
| EXP-05-3 | dollar-neutral vs beta-neutral |
| EXP-06-1 | full vs half Kelly |
| EXP-06-2 | Black-Litterman vs mean-variance stability |
| EXP-07-1 | costs flipping the sign |
| EXP-07-2 | sliced vs single order impact |
| EXP-08-1 | purged vs plain k-fold on noise |
| EXP-08-2 | deflated vs raw Sharpe after N trials |
