"""experiments/_tsa.py against independent reference values.

Reference: statsmodels 0.15.0 (adfuller with autolag=None and regression="c", kpss with regression="c",
coint with trend="c" and autolag=None, adfvalues.mackinnoncrit), computed once on the deterministic
series below and pasted here; statsmodels is not a dependency. Named failure: a wrong lag alignment,
a missing intercept or a mistyped MacKinnon coefficient would shift every ADF/EG/KPSS verdict while the
experiments still run and look plausible."""
import numpy as np
import pytest

from experiments._tsa import KPSS_5PCT_LEVEL, adf_t, engle_granger_t, kpss_stat, mackinnon_cv5, ols_t

pytestmark = pytest.mark.experiments

T = np.arange(300)
E = ((T * 7919) % 101 - 50) / 29.0  # deterministic shocks: no RNG, so the reference values never drift
RW = np.cumsum(E)
AR = np.zeros(300)
for _i in range(1, 300):
    AR[_i] = 0.6 * AR[_i - 1] + E[_i]
X = np.cumsum(((T * 104729) % 97 - 48) / 28.0)
Y = 0.8 * X + AR


@pytest.mark.parametrize("series,lags,expected", [
    (RW, 0, -7.830871758632002), (RW, 3, -4.188284970021693),
    (AR, 0, -16.36229511596194), (AR, 3, -9.033403417069408)])
def test_adf_statistic_matches_statsmodels(series, lags, expected):
    assert adf_t(series, lags)[0] == pytest.approx(expected, rel=1e-9)


@pytest.mark.parametrize("series,expected", [(RW, 0.09993909869019431), (AR, 0.02347782612615709)])
def test_kpss_statistic_matches_statsmodels(series, expected):
    assert kpss_stat(series, 8) == pytest.approx(expected, rel=1e-9)


def test_engle_granger_statistic_matches_statsmodels():
    assert engle_granger_t(Y, X, 2)[0] == pytest.approx(-9.437036278767039, rel=1e-9)


@pytest.mark.parametrize("n_vars,nobs,expected", [(1, 100, -2.89090644), (2, 250, -3.360679568),
                                                  (1, 10**9, -2.86154), (2, 10**9, -3.33613)])
def test_mackinnon_critical_values(n_vars, nobs, expected):
    assert mackinnon_cv5(n_vars, nobs) == pytest.approx(expected, abs=1e-6)


def test_kpss_critical_value_is_the_published_one():
    assert KPSS_5PCT_LEVEL == 0.463  # Kwiatkowski et al. (1992), table 1, level stationarity, 5%


def test_ols_t_matches_the_textbook_simple_regression_formula():
    x = np.arange(10.0)
    y = 2.0 + 3.0 * x + np.where(x % 2 == 0, 0.5, -0.5)
    sxx = ((x - x.mean()) ** 2).sum()
    b = ((x - x.mean()) * (y - y.mean())).sum() / sxx
    a = y.mean() - b * x.mean()
    s2 = ((y - a - b * x) ** 2).sum() / (len(x) - 2)
    beta, t = ols_t(y, np.column_stack([np.ones(10), x]))
    assert beta == pytest.approx([a, b], rel=1e-12)
    assert t[1] == pytest.approx(b / np.sqrt(s2 / sxx), rel=1e-12)
