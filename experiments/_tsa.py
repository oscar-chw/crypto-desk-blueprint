"""Small time-series tests shared by the experiments (numpy only, so CI needs no statsmodels).

Critical values: MacKinnon (2010), "Critical values for cointegration tests", Queen's Economics
Department Working Paper 1227, response surfaces cv(T) = b0 + b1/T + b2/T^2 + b3/T^3; KPSS from
Kwiatkowski, Phillips, Schmidt and Shin (1992), J. Econometrics 54, table 1 (level stationarity).
Each experiment that uses them also runs a null case, so a wrong critical value would show as a wrong size.
"""
from __future__ import annotations

import numpy as np

# 5% response-surface coefficients (MacKinnon 2010, table 2)
_MACKINNON_5PCT = {
    (1, "c"): (-2.86154, -2.8903, -4.234, -40.040),  # ADF with a constant
    (2, "c"): (-3.33613, -6.1101, -6.823, 0.0),  # Engle-Granger residual test, 2 variables, constant
}
KPSS_5PCT_LEVEL = 0.463


def mackinnon_cv5(n_vars: int, nobs: int) -> float:
    b0, b1, b2, b3 = _MACKINNON_5PCT[(n_vars, "c")]
    return b0 + b1 / nobs + b2 / nobs**2 + b3 / nobs**3


def ols_t(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS coefficients and their classical t statistics."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    return beta, beta / se


def schwert_lags(n: int, k: float = 4.0) -> int:
    return int(k * (n / 100) ** 0.25)


def adf_t(y: np.ndarray, lags: int, constant: bool = True) -> tuple[float, int]:
    """ADF t statistic on y_{t-1} in dy_t = [c] + a y_{t-1} + sum_j phi_j dy_{t-j} + e_t; and nobs used."""
    y = np.asarray(y, dtype=float)
    dy = np.diff(y)
    Y = dy[lags:]
    cols = [y[lags:-1]] + [dy[lags - j:-j] for j in range(1, lags + 1)]
    if constant:
        cols.append(np.ones(len(Y)))
    _, t = ols_t(Y, np.column_stack(cols))
    return float(t[0]), len(Y)


def adf_rejects(y: np.ndarray, lags: int) -> bool:
    t, nobs = adf_t(y, lags)
    return t < mackinnon_cv5(1, nobs)


def kpss_stat(y: np.ndarray, lags: int) -> float:
    """KPSS level-stationarity statistic with a Bartlett-kernel long-run variance."""
    e = np.asarray(y, dtype=float) - np.mean(y)
    n = len(e)
    lrv = e @ e / n
    for j in range(1, lags + 1):
        lrv += 2 * (1 - j / (lags + 1)) * (e[j:] @ e[:-j]) / n
    return float(np.sum(np.cumsum(e) ** 2) / (n**2 * lrv))


def engle_granger_t(y: np.ndarray, x: np.ndarray, lags: int) -> tuple[float, int]:
    """Step 1: OLS y on [1, x]. Step 2: ADF t on the residuals with no constant (they have mean 0)."""
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return adf_t(y - X @ beta, lags, constant=False)
