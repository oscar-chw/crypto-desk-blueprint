# 01 Data

## In one paragraph
Data is a record of what happened and when you could first have known it. The store keeps everything the
exchanges sent, never overwrites it, and keeps coins and venues that died, because a history containing
only survivors makes every strategy look better than it is. Gaps from outages stay visible as gaps.

## Purpose
Ingest bars, trades, funding prints and instrument metadata from venues into the point-in-time store, check
them, and serve them back exactly as they were known at any past moment.

## Design rules
1. **Store raw first, clean second.** Keep the venue's payload unchanged so any cleaning step can be re-run when it turns out wrong.
2. **Every record has an event time and an `available_at`.** A bar is known only after it closes plus the delay to receive it.
3. **Bars are labelled by close time and cover (open, close].** One convention end to end stops off-by-one-bar leaks.
4. **Gaps stay gaps; never forward-fill prices into an outage.** Filled bars show fake zero returns, shrink volatility and invent fills at prices nobody could trade.
5. **Keep dead instruments and delisted coins in the universe with their delisting date.** Dropping them is survivorship bias.
6. **Snapshot the instrument list (tick size, lot size, fee tier, contract specs) daily.** Specs change; a backtest must use the spec in force then.
7. **Validate on ingest: OHLC consistency, positive prices, monotone time, no duplicates.** Bad prints caught at the door never reach a feature.
8. **Default bar: 1-minute venue klines for research of hourly-or-slower strategies; trades for anything faster.** Klines are cheap and complete; faster strategies need the trade stream to model fills.

## Interface
`DataSource` in [`pipeline/protocols.py`](../pipeline/protocols.py); records `Bar`, `FundingEvent`,
`Instrument` in [`pipeline/types.py`](../pipeline/types.py); storage via
[`PointInTimeStore.append_bar`](../pipeline/store.py). Suite: [`test_data.py`](../conformance/stages/test_data.py).

## Crypto specifics
- The same symbol differs by venue (price, fees, liquidity); key every series by `venue:symbol:kind`.
- Perpetual funding prints arrive on a schedule (often every 8 hours, some contracts 1 or 4); read the interval from the venue, never hard-code it.
- Stablecoin-quoted prices are not dollar prices: a USDT or USDC depeg moves every quote at once. Store the stablecoin's own price too.
- Exchanges fail and vanish; their history is still part of the universe you could have traded.
- Free public history exists (for example Binance's public klines and funding archives); record its download date.

## Common failure modes
- **Survivorship**: backtest universe built from today's listings; results fade in live trading.
- **Forward-filled outage**: volatility estimates drop after a venue incident; fills at stale prices.
- **Duplicate page**: a retried API page appended twice; doubled volume and a zero-length return.
- **Window leak**: a query returns one bar past its end; a feature sees the next bar.
- **Spec drift**: orders rejected live for a tick or lot size the backtest never checked.

## Acceptance tests
| id | input -> expected | mutant it kills |
|---|---|---|
| AT-01-1 | sample window -> close times strictly increasing, no duplicates | `data_duplicate` |
| AT-01-2 | sample window -> every bar in (start, end]; a shorter window is an exact prefix | `data_window_leak` |
| AT-01-3 | same window read twice -> identical bars | (replayability) |
| unit | `Bar` with high below open, or `available_at < close_time` -> ValueError | `tests/test_blocks.py` |

## Evidence
- **EXP-01-1** backs rule 5. Hypothesis: a survivors-only universe inflates an equal-weight backtest. Setup: 200 synthetic coins, zero-drift GBM (daily sigma 5%), a coin is delisted when its price falls below 10% of its start. Control: the full point-in-time universe including delisted coins up to their delisting. Metric: mean daily return of the equal-weight portfolio, with its standard error. Expected: survivors-only higher. The rule is wrong if the difference is inside two standard errors. `result: supports: survivors-only 9.6 bp/day vs point-in-time -0.1 bp/day; bias 9.7 bp/day (SE 0.1), about 35% a year, with 58% of coins surviving`
- **EXP-01-2** backs rule 4. Hypothesis: forward-filling a 6-hour outage biases realised volatility down. Setup: synthetic GBM hourly bars with a 6-hour gap inserted at random points, 1,000 paths. Control: gap kept as missing. Metric: realised-vol estimate over the 7 days around the gap versus the true sigma. Expected: forward-fill biased low, gap-aware unbiased. The rule is wrong if both arms show the same bias. `result: does not support: forward-fill bias -0.33% (SE 0.19%) vs gap-aware -0.18% (SE 0.17%); paired difference -0.15% (SE 0.08%)`

## Sources
- Chan, *Quantitative Trading* (2009), ch. 3 (data quality, survivorship, recording point-in-time data).
- López de Prado, *Advances in Financial Machine Learning* (2018), ch. 2 (data structures, backfill) and ch. 11 (survivorship among backtest errors).
- Cryer & Chan, *Time Series Analysis with Applications in R* (2008), ch. 11 (outliers and interventions).
