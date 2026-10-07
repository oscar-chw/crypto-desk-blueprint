# experiments/

Runnable demonstrations behind the design rules. Specifications (hypothesis, setup, control, metric,
expected direction, falsification condition) live in each `blueprint/0N-*.md` under `## Evidence`;
the generated results table is [blueprint/EVIDENCE.md](../blueprint/EVIDENCE.md).

One script per id, `EXP-0N-k-<slug>.py`, built on the `pipeline/` blocks where one exists. Each states its
generating process (or public data source) and its verdict rule in the docstring, fixes its seeds, runs
the control in the same run and writes `results/EXP-0N-k.json`: inputs, seeds, both arms, the effect
with its standard error, the verdict and the runtime. `_common.py` holds the result schema and the
offline loader for the committed public extract in `data/`; `_tsa.py` holds the ADF, KPSS and
Engle-Granger tests (numpy only).

```bash
python scripts/run_experiments.py                       # all, then regenerate the docs
python experiments/EXP-08-1-purged-cv.py --quick --out /tmp/x   # one, small n, same code path
pytest tests/test_experiments.py                        # every experiment in quick mode (CI)
```

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
