"""Unit tests of the shared building blocks in pipeline/."""
import math

import numpy as np
import pytest

from pipeline import pricing
from pipeline.costs import CostModel
from pipeline.cv import PurgedKFold
from pipeline.risk import KillSwitch, RiskEngine, RiskLimits
from pipeline.sizing import capped_kelly, kelly_leverage
from pipeline.stats import deflated_sharpe_ratio, expected_max_sharpe, probabilistic_sharpe_ratio, sharpe_ratio
from pipeline.store import LookAheadError, PointInTimeStore
from pipeline.types import NS_PER_DAY, NS_PER_YEAR, Bar, Signal, TargetPortfolio

pytestmark = pytest.mark.blocks


# --- types -----------------------------------------------------------------------------------------
def test_bar_rejects_known_before_close():
    with pytest.raises(ValueError):
        Bar("X", 0, 10, 1, 1, 1, 1, 0, available_at=9)


def test_bar_rejects_inconsistent_ohlc():
    with pytest.raises(ValueError):
        Bar("X", 0, 10, 1.0, 0.9, 0.8, 1.0, 1.0, 10)  # high below open


def test_signal_rejects_out_of_range_and_nan():
    for bad in (1.5, math.nan):
        with pytest.raises(ValueError):
            Signal("X", 0, bad, 1, "m")


def test_target_weights_are_read_only():
    tp = TargetPortfolio(0, {"A": 0.1})
    with pytest.raises(TypeError):
        tp.weights["A"] = 1.0


# --- point-in-time store -----------------------------------------------------------------------------
def test_store_rejects_duplicate_and_premature_publication():
    s = PointInTimeStore()
    s.append("k", 10, 10, 1)
    with pytest.raises(ValueError):
        s.append("k", 10, 10, 1)
    with pytest.raises(ValueError):
        s.append("k", 20, 19, 1)


def test_store_window_is_open_closed_and_sorted():
    s = PointInTimeStore()
    for t in (30, 10, 20):
        s.append("k", t, t, t)
    assert [r.value for r in s.view(30).read("k", 10, 30)] == [20, 30]
    with pytest.raises(LookAheadError):
        s.view(29).read("k", 0, 30)


# --- cost model ----------------------------------------------------------------------------------------
def test_costs_buy_above_sell_below_mid_and_grow_with_size():
    c = CostModel()
    assert c.fill_price(100, 1, 1_000) > 100 > c.fill_price(100, -1, 1_000)
    assert c.total_cost(100, 50, 1_000) / 50 > c.total_cost(100, 1, 1_000) / 1  # impact per unit grows


def test_costs_refuse_order_above_participation_cap():
    with pytest.raises(ValueError):
        CostModel(max_participation=0.1).fill_price(100, 200, 1_000)


def test_zero_cost_model_is_free():
    c = CostModel(0, 0, 0, 0)
    assert c.total_cost(100, 3, 1_000) == 0


# --- risk engine -------------------------------------------------------------------------------------
def test_daily_halt_allows_reduce_only_and_resets_next_day():
    e = RiskEngine(RiskLimits(daily_loss_limit=0.05, max_drawdown=0.5))
    e.update_equity(0, 100)
    e.update_equity(1, 94)
    d = e.check(TargetPortfolio(1, {"A": 0.2, "B": 0.1, "C": -0.1}), {"A": 0.1, "B": 0.2, "C": 0.1})
    assert d.target.weights == {"A": 0.1, "B": 0.1, "C": 0.0} and d.halted
    e.update_equity(NS_PER_DAY, 94)
    assert not e.check(TargetPortfolio(NS_PER_DAY, {"A": 0.2}), {"A": 0.1}).halted


def test_kill_switch_needs_named_operator():
    k = KillSwitch()
    k.trip("x")
    with pytest.raises(PermissionError):
        k.rearm("  ")
    k.rearm("oscar")
    assert not k.tripped


# --- pricing -----------------------------------------------------------------------------------------
def test_round_trip_carry():
    f = pricing.fair_forward(100, 0.07, 0.02, 0.5)
    assert pricing.implied_carry(100, f, 0.5) == pytest.approx(0.05)


def test_band_widens_with_cost_and_rate_spread():
    narrow = pricing.no_arbitrage_band(100, 1, r_quote_borrow=0.05, r_quote_lend=0.05, r_base_borrow=0,
                                       r_base_lend=0, round_trip_cost=0.001)
    wide = pricing.no_arbitrage_band(100, 1, r_quote_borrow=0.08, r_quote_lend=0.03, r_base_borrow=0.01,
                                     r_base_lend=0, round_trip_cost=0.003)
    assert wide[0] < narrow[0] < narrow[1] < wide[1]


def test_annualize_funding():
    assert pricing.annualize_funding(0.0001, 8) == pytest.approx(0.1095)
    assert pricing.year_fraction(0, NS_PER_YEAR) == 1.0


# --- purged CV ---------------------------------------------------------------------------------------
def test_purge_removes_exactly_the_overlapping_neighbours():
    t0 = np.arange(10, dtype=np.int64)
    t1 = t0 + 2
    train, test = next(iter(PurgedKFold(n_splits=5, embargo_ns=0).split(t0, t1)))
    assert test.tolist() == [0, 1] and train.tolist() == [4, 5, 6, 7, 8, 9]  # 2 and 3 overlap [0, 3]


def test_embargo_removes_following_samples():
    t0 = np.arange(10, dtype=np.int64)
    train, _ = next(iter(PurgedKFold(n_splits=5, embargo_ns=3).split(t0, t0)))
    assert train.tolist() == [5, 6, 7, 8, 9]  # test [0, 1], end 1, embargo drops 2, 3, 4


def test_cv_rejects_unsorted_times():
    with pytest.raises(ValueError):
        list(PurgedKFold(2).split(np.array([2, 1, 3, 4]), np.array([2, 1, 3, 4])))


# --- statistics --------------------------------------------------------------------------------------
def test_sharpe_and_psr_basics():
    r = np.array([0.01, -0.005, 0.02, 0.0, 0.004])
    assert sharpe_ratio(r, 365) == pytest.approx(r.mean() / r.std(ddof=1) * math.sqrt(365))
    assert probabilistic_sharpe_ratio(0.1, 0.1, 100) == pytest.approx(0.5)


def test_expected_max_sharpe_grows_with_trials():
    vals = [expected_max_sharpe(n, 0.01) for n in (1, 10, 100, 1_000)]
    assert vals[0] == 0 and all(a < b for a, b in zip(vals, vals[1:]))


def test_dsr_flags_best_of_many_noise_strategies():
    """Best of 200 pure-noise strategies: raw PSR looks convincing, the deflated one does not."""
    rng = np.random.default_rng(0)
    srs = np.array([sharpe_ratio(rng.normal(0, 0.01, 500)) for _ in range(200)])
    best = srs.max()
    assert probabilistic_sharpe_ratio(best, 0, 500) > 0.95
    assert deflated_sharpe_ratio(best, 500, 200, srs.var(ddof=1)) < 0.95


# --- sizing ------------------------------------------------------------------------------------------
def test_half_kelly_capped_by_drawdown_budget():
    assert kelly_leverage(0.001, 0.0004) == pytest.approx(2.5)
    assert capped_kelly(0.001, 0.0004, worst_period_loss=0.5, max_drawdown=0.2) == pytest.approx(0.4)
    assert capped_kelly(0.001, 0.0004, worst_period_loss=0.01, max_drawdown=0.2) == pytest.approx(1.25)
    assert capped_kelly(-0.001, 0.0004, worst_period_loss=0.5, max_drawdown=0.2) == pytest.approx(-0.4)
