"""Weekly theta decay table — option value at flat spot from today to holding period."""
from __future__ import annotations

import logging

import pandas as pd

from src.market_data.fetcher import MarketDataResult
from src.option_search.searcher import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


def build_decay_table(
    candidate: OptionCandidate,
    market: MarketDataResult,
    cfg: dict,
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

    entry_price = candidate.market_price
    today = pd.Timestamp.now(tz="UTC")

    rows = []
    days_elapsed = 0
    while True:
        days_remaining = candidate.days_to_expiry - days_elapsed
        T = max(days_remaining / 365.0, 0.0)
        val = bs.price(otype, spot, K, T, r, iv, q)
        decay_usd = entry_price - val
        decay_pct = decay_usd / entry_price * 100.0 if entry_price > 0.0 else 0.0

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
