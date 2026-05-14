"""Black-Scholes closed-form pricing and Greeks."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _d1(S: float, K: float, T: float, r: float, sigma: float, q: float) -> float:
    return float((np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T)))


def _d2(S: float, K: float, T: float, r: float, sigma: float, q: float) -> float:
    return float(_d1(S, K, T, r, sigma, q) - sigma * np.sqrt(T))


def call_price(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    if T <= 0.0:
        return max(S - K, 0.0)
    d1 = _d1(S, K, T, r, sigma, q)
    d2 = _d2(S, K, T, r, sigma, q)
    return float(S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))


def put_price(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    if T <= 0.0:
        return max(K - S, 0.0)
    d1 = _d1(S, K, T, r, sigma, q)
    d2 = _d2(S, K, T, r, sigma, q)
    return float(K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1))


def price(
    option_type: str, S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    if option_type.lower() == "call":
        return call_price(S, K, T, r, sigma, q)
    return put_price(S, K, T, r, sigma, q)


def delta(
    option_type: str, S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    if T <= 0.0:
        return 1.0 if (option_type.lower() == "call" and S > K) else 0.0
    d1 = _d1(S, K, T, r, sigma, q)
    if option_type.lower() == "call":
        return float(np.exp(-q * T) * norm.cdf(d1))
    return float(np.exp(-q * T) * (norm.cdf(d1) - 1.0))


def gamma(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    if T <= 0.0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma, q)
    return float(np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T)))


def theta_per_day(
    option_type: str, S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    """Daily theta (option value lost per calendar day)."""
    if T <= 0.0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma, q)
    d2 = _d2(S, K, T, r, sigma, q)
    term = -np.exp(-q * T) * S * norm.pdf(d1) * sigma / (2.0 * np.sqrt(T))
    if option_type.lower() == "call":
        annual = (
            term - r * K * np.exp(-r * T) * norm.cdf(d2) + q * S * np.exp(-q * T) * norm.cdf(d1)
        )
    else:
        annual = (
            term + r * K * np.exp(-r * T) * norm.cdf(-d2) - q * S * np.exp(-q * T) * norm.cdf(-d1)
        )
    return float(annual / 365.0)


def vega(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
    """Vega per 1% change in IV (divided by 100 to match convention)."""
    if T <= 0.0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma, q)
    return float(S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100.0)


def omega(
    option_type: str, S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> float:
    """Effective leverage (Omega = Delta * Spot / OptionPrice)."""
    p = price(option_type, S, K, T, r, sigma, q)
    if p <= 0.0:
        return 0.0
    d = delta(option_type, S, K, T, r, sigma, q)
    return float(d * S / p)


def prob_profit_at_expiry(
    option_type: str, S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0,
    premium_paid: float = 0.0,
) -> float:
    """Probability the option expires with intrinsic value > premium paid (log-normal)."""
    if T <= 0.0:
        intrinsic = (S - K) if option_type.lower() == "call" else (K - S)
        return 1.0 if intrinsic > premium_paid else 0.0
    breakeven = (K + premium_paid) if option_type.lower() == "call" else (K - premium_paid)
    if breakeven <= 0.0:
        return 1.0
    # log-normal: P(S_T > breakeven)
    log_ratio = np.log(S / breakeven) + (r - q - 0.5 * sigma**2) * T
    d = log_ratio / (sigma * np.sqrt(T))
    if option_type.lower() == "call":
        return float(norm.cdf(d))
    return float(norm.cdf(-d))


def breakeven_spot(option_type: str, K: float, premium_paid: float) -> float:
    """Underlying price at which the position breaks even at expiry."""
    if option_type.lower() == "call":
        return K + premium_paid
    return K - premium_paid
