"""Weekly theta decay table — option value at flat spot from today to holding period."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


def build_decay_table(
    candidate: OptionCandidate,
    market: MarketDataResult,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    """
    Calculates option value at the current spot price for each week
    from today up to min(holding_months, expiry).
    Shows the pure time-value erosion without any underlying movement.
    """
    otype = candidate.option_type
    K = candidate.strike
    r = market.risk_free_rate
    iv = candidate.implied_vol
    q: float = cfg["underlying"]["dividend_yield"]
    spot = market.spot
    holding_months: int = cfg["analysis"]["holding_months"]
    max_days = min(candidate.days_to_expiry, int(holding_months * 30.44))

    # Use BS price at t=0 as the decay reference — not the market price,
    # because market price may differ from BS price for illiquid strikes.
    ref_price = bs.price(otype, spot, K, candidate.days_to_expiry / 365.0, r, iv, q)
    today = pd.Timestamp.now(tz="UTC")

    rows = []
    days_elapsed = 0
    while True:
        days_remaining = candidate.days_to_expiry - days_elapsed
        T = max(days_remaining / 365.0, 0.0)
        val = bs.price(otype, spot, K, T, r, iv, q)
        decay_usd = ref_price - val
        decay_pct = decay_usd / ref_price * 100.0 if ref_price > 0.0 else 0.0

        rows.append(
            {
                "datum": (today + pd.Timedelta(days=days_elapsed)).date(),
                "tage_vergangen": days_elapsed,
                "tage_verbleibend": days_remaining,
                "optionswert_usd": round(val, 4),
                "zeitwertverlust_usd": round(decay_usd, 4),
                "zeitwertverlust_pct": round(decay_pct, 1),
            }
        )

        if days_elapsed >= max_days:
            break
        days_elapsed = min(days_elapsed + 7, max_days)

    df = pd.DataFrame(rows)
    logger.info("theta decay table: %d rows (max %d days)", len(df), max_days)
    return df
