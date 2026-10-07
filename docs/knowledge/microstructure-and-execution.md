# Microstructure and execution

## Why it matters for the template
This note informs [execution](../../blueprint/07-execution.md) (sizing, scheduling, passive vs aggressive), the cost
model in [portfolio](../../blueprint/06-portfolio.md), and the fill assumptions that [validation](../../blueprint/08-validation.md)
must not make optimistic. Market data fields are defined in [data](../../blueprint/01-data.md).

## Core results
**Kyle (1985)**, "Continuous auctions and insider trading": one risk-neutral informed trader with value $v\sim N(p_0,\Sigma_0)$,
noise traders with order flow $u\sim N(0,\sigma_u^2)$, competitive risk-neutral market makers who see only total flow $x+u$.
The equilibrium price is linear, $p=p_0+\lambda(x+u)$, with
$$\lambda=\frac{1}{2}\frac{\sqrt{\Sigma_0}}{\sigma_u}.$$
$\lambda$ (Kyle's lambda) measures price impact per unit signed flow.

**Glosten–Milgrom (1985)**, "Bid, ask and transaction prices in a specialist market with heterogeneously informed traders":
with a fraction $\mu$ of informed traders and value $V\in\{V_L,V_H\}$, the ask is $E[V\mid\text{buy}]$ and the bid is
$E[V\mid\text{sell}]$. The spread is positive even with zero processing costs and risk-neutral competitive
quoting: it compensates adverse selection. Quotes update by Bayes rule after each trade.

**Almgren–Chriss (2000)**, "Optimal execution of portfolio transactions": liquidate $X$ shares over $N$ intervals
with arithmetic random walk, permanent impact $g(v)=\gamma v$ and temporary impact $h(v)=\eta v$. Minimise
$E[C]+\lambda_{\rm risk}\,\mathrm{Var}[C]$. The continuous solution is
$$x(t)=X\,\frac{\sinh\!\big(\kappa(T-t)\big)}{\sinh(\kappa T)},\quad \kappa\approx\sqrt{\lambda_{\rm risk}\sigma^2/\eta},$$
so higher risk aversion or volatility front-loads the schedule; $\lambda_{\rm risk}\to0$ gives TWAP. The efficient
frontier trades expected cost against variance.

**Avellaneda–Stoikov (2008)**, "High-frequency trading in a limit order book": a market maker with exponential
utility, inventory $q$, mid-price $dS=\sigma dW$ and Poisson fills with intensity $Ae^{-k\delta}$ at distance $\delta$ quotes around a
reservation price
$$r=s-q\gamma\sigma^2(T-t),\qquad \delta^a+\delta^b=\gamma\sigma^2(T-t)+\frac{2}{\gamma}\ln\!\Big(1+\frac{\gamma}{k}\Big).$$
Inventory skews quotes away from the side that would grow the position.

**Square-root impact law.** Empirically, metaorder impact in price units scales as
$$I \approx Y\,\sigma\sqrt{Q/V},$$
with $Q$ the metaorder size, $V$ daily volume, $\sigma$ daily volatility and $Y$ a constant of order one
(Bouchaud et al., 2009, "How markets slowly digest changes in supply and demand"; Tóth et al., 2011,
"Anomalous price impact and the critical nature of liquidity in financial markets"). This is empirical, with
models that rationalise it (latent order book); it is not a theorem.

**Queue position and adverse selection.** A passive order at the back of the queue is filled mostly when
price is about to move through its level; fills are therefore conditioned on bad news. Expected value of a
passive fill $\approx$ half-spread captured minus the post-fill drift conditioned on being filled.

## Where practice differs from the textbook
- Impact is not linear: desks use concave (about square-root) temporary impact and calibrate on their own fills.
- Almgren–Chriss assumes known $\sigma$ and static schedules; live schedulers adapt to volume and spread.
- Kyle and Glosten–Milgrom are one-asset, single-informed-agent models; real flow toxicity is estimated
  from order-flow imbalance or markouts.
- Crypto venues differ in fee tiers, maker rebates, tick size and matching (price-time vs pro-rata), changing
  which side of the queue is attractive.
- Backtests that fill at mid, or fill every passive order that touched the price, overstate performance.

## Checks this implies
- Backtest costs are at least half-spread plus a concave impact term; cost is monotone in order size.
- Almgren–Chriss schedule sums to $X$, is monotone decreasing, and approaches TWAP as risk aversion goes to 0.
- Passive fill simulation requires trade-through or queue depletion, never a mere touch.
- Markouts at 1s, 10s, 60s after fills are reported per venue and side.
- Quotes under Avellaneda–Stoikov skew toward flattening inventory; reservation price is monotone in $q$.

## Sources
- Kyle, A. S. (1985), "Continuous auctions and insider trading".
- Glosten, L. R. and Milgrom, P. R. (1985), "Bid, ask and transaction prices in a specialist market with heterogeneously informed traders".
- Almgren, R. and Chriss, N. (2000), "Optimal execution of portfolio transactions".
- Avellaneda, M. and Stoikov, S. (2008), "High-frequency trading in a limit order book".
- Bouchaud, J.-P., Farmer, J. D., Lillo, F. (2009), "How markets slowly digest changes in supply and demand".
- Tóth, B. et al. (2011), "Anomalous price impact and the critical nature of liquidity in financial markets".
- See also: Bouchaud, Bonart, Donier, Gould, "Trades, Quotes and Prices"; Harris, "Trading and Exchanges".
