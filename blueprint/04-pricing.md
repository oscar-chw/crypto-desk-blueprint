# 04 Pricing

## In one paragraph
A futures contract and a perpetual swap should cost roughly the spot price plus the cost of holding the
coin until then (interest paid, minus any yield earned). If the price strays outside that range by more
than trading costs, someone can lock in a riskless profit, so it tends not to stray far for long. This
stage computes that fair value and its band, and books funding payments with the right sign.

## Purpose
Risk-neutral fair value only where crypto uses it: dated-futures basis, cost of carry, perpetual funding,
and the no-arbitrage band. Options are out of scope for this blueprint.

## Design rules
1. **Fair value of a dated future is spot times exp((r_quote - r_base) x tau).** Holding spot costs the quote-currency rate and earns the base asset's yield; the future must match that or an arbitrage exists.
2. **Quote a band, not a point.** Borrow and lend rates differ and trading costs money, so only prices outside the band are free money; inside it is just carry.
3. **Annualise basis and funding the same way before comparing them.** A per-8-hour rate and a quarterly basis are not comparable until both are per year.
4. **Funding is a discrete cash flow at the venue's funding time, paid by longs when positive.** Accruing it continuously misstates short holds around funding times.
5. **Use the mark price for funding and liquidation, the traded price for fills.** Venues define them differently, and liquidations follow the mark.
6. **Treat "carry" as a forecast of a mean-reverting spread, not a sure thing.** The band bounds it only if capital, borrow and venue access are really available.

## Interface
`PricingModel` in [`pipeline/protocols.py`](../pipeline/protocols.py); functions `fair_forward`,
`implied_carry`, `no_arbitrage_band`, `annualize_funding`, `funding_cashflow`, `year_fraction` in
[`pipeline/pricing.py`](../pipeline/pricing.py). Suite: [`test_pricing.py`](../conformance/stages/test_pricing.py).

## Crypto specifics
- Perpetuals have no expiry; funding payments tie them to spot instead. Intervals are often 8 hours, some 1 or 4; formulas and caps differ by venue, so read them from the venue documentation and API.
- The base asset's yield (lending, staking) is real carry and can make backwardation fair.
- Stablecoin rates are not the risk-free rate; they move with leverage demand.
- Venue and stablecoin risk sit outside the formula: an "arbitrage" across a venue that later freezes withdrawals is not riskless.

## Common failure modes
- **Sign error on funding**: carry strategy shows profit where it pays; P&L reverses live.
- **Point fair value**: constant small "mispricings" traded inside the cost band; fees eat everything.
- **Expired contract priced**: negative tau, nonsense fair value near rollover.
- **Continuous accrual**: P&L error concentrated around funding timestamps.

## Acceptance tests
| id | input -> expected | mutant it kills |
|---|---|---|
| AT-04-1 | spot 100, 1 year, 8% vs 2% -> 100 exp(0.06); 1% vs 5% -> below spot | `pricing_carry_sign` |
| AT-04-2 | positive costs -> band_low < fair < band_high | (band contract) |
| AT-04-3 | long 2 at 100, rate +0.01% -> pays 0.02; short receives 0.02 | `pricing_funding_sign` |
| AT-04-4 | t at expiry -> ValueError | (expiry guard) |

## Evidence
- **EXP-04-1** backs rules 1 to 3. Hypothesis: annualised perpetual funding and annualised quarterly-futures basis move together, and the basis stays mostly inside the fee-adjusted band. Setup: free public data, Binance spot and quarterly-futures klines and perpetual funding history for BTC and ETH. Control: funding shifted by a random time offset (breaks alignment). Metric: correlation of the two annualised series; share of hours outside the band. Expected: positive correlation, clearly above the shifted control; few hours outside the band, clustered in stress. The rule is wrong if the aligned correlation is no higher than the control. `result: pending`
- **EXP-04-2** backs rule 4. Hypothesis: continuous funding accrual misstates P&L for holds shorter than one interval. Setup: synthetic perp with funding every 8 hours, rates drawn from an AR(1); positions held 1 to 24 hours from random start times. Control: discrete payments at funding times. Metric: absolute P&L error by holding length. Expected: largest error for holds under 8 hours. The rule is wrong if the error is negligible at every holding length. `result: pending`

## Sources
- Baxter & Rennie, *Financial Calculus* (1996), ch. 1 (arbitrage versus expectation pricing), ch. 4.1 to 4.2 (foreign exchange and dividend-paying assets: the carry argument used here).
- Chan, *Quantitative Trading* (2009), ch. 5 (funding and borrow costs a backtest ignores).
- He, Manela, Ross & von Wachter (2022), "Fundamentals of Perpetual Futures", working paper (arXiv).
