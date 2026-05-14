"""Shared data models — no dependencies on other src modules (prevents circular imports)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class OptionCandidate:
    ticker: str
    expiration: date
    strike: float
    option_type: str
    market_price: float
    implied_vol: float
    days_to_expiry: int
    open_interest: int
    volume: int
    # populated by valuation.pricer.run()
    bs_price: float = 0.0
    delta_val: float = 0.0
    gamma_val: float = 0.0
    theta_day: float = 0.0
    vega_val: float = 0.0
    omega_val: float = 0.0
    breakeven: float = 0.0
