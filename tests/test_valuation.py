"""Unit tests for Black-Scholes pricing and Greeks."""
from __future__ import annotations

import pytest

from src.valuation.blackscholes import (
    breakeven_spot,
    call_price,
    delta,
    omega,
    prob_profit_at_expiry,
    put_price,
    theta_per_day,
    vega,
)

S, K, T, r, sigma = 13.10, 12.0, 0.5, 0.045, 0.44


def test_call_price_positive() -> None:
    p = call_price(S, K, T, r, sigma)
    assert p > 0.0


def test_put_call_parity() -> None:
    c = call_price(S, K, T, r, sigma)
    p = put_price(S, K, T, r, sigma)
    # C - P = S*e^{-qT} - K*e^{-rT}  (with q=0)
    import numpy as np
    parity = S - K * np.exp(-r * T)
    assert abs(c - p - parity) < 1e-6


def test_call_delta_between_zero_and_one() -> None:
    d = delta("call", S, K, T, r, sigma)
    assert 0.0 < d < 1.0


def test_put_delta_between_minus_one_and_zero() -> None:
    d = delta("put", S, K, T, r, sigma)
    assert -1.0 < d < 0.0


def test_itm_call_omega_positive() -> None:
    om = omega("call", S, K, T, r, sigma)
    assert om > 1.0


def test_theta_negative_for_call() -> None:
    th = theta_per_day("call", S, K, T, r, sigma)
    assert th < 0.0


def test_vega_positive() -> None:
    v = vega(S, K, T, r, sigma)
    assert v > 0.0


def test_expired_call_intrinsic_only() -> None:
    assert call_price(15.0, 12.0, 0.0, r, sigma) == pytest.approx(3.0)
    assert call_price(10.0, 12.0, 0.0, r, sigma) == pytest.approx(0.0)


def test_breakeven_call() -> None:
    assert breakeven_spot("call", 12.0, 1.80) == pytest.approx(13.80)


def test_breakeven_put() -> None:
    assert breakeven_spot("put", 12.0, 1.80) == pytest.approx(10.20)


def test_prob_profit_between_zero_and_one() -> None:
    p = prob_profit_at_expiry("call", S, K, T, r, sigma, premium_paid=1.80)
    assert 0.0 <= p <= 1.0
