"""Re-prices option candidates and logs Greeks."""
from __future__ import annotations

import logging

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


def run(cfg: dict, market: MarketDataResult, candidates: list[OptionCandidate]) -> list[OptionCandidate]:
    r = market.risk_free_rate
    spot = market.spot
    q: float = cfg["underlying"]["dividend_yield"]

    for c in candidates:
        T = c.days_to_expiry / 365.0
        iv = c.implied_vol
        otype = c.option_type
        K = c.strike

        c.bs_price = bs.price(otype, spot, K, T, r, iv, q)
        c.delta_val = bs.delta(otype, spot, K, T, r, iv, q)
        c.gamma_val = bs.gamma(spot, K, T, r, iv, q)
        c.theta_day = bs.theta_per_day(otype, spot, K, T, r, iv, q)
        c.vega_val = bs.vega(spot, K, T, r, iv, q)
        c.omega_val = bs.omega(otype, spot, K, T, r, iv, q)
        c.breakeven = bs.breakeven_spot(otype, K, c.market_price)

        logger.debug(
            "%s %s K=%.2f DTE=%d mid=%.4f bs=%.4f delta=%.3f omega=%.2f theta/d=%.4f",
            c.expiration, otype, K, c.days_to_expiry,
            c.market_price, c.bs_price, c.delta_val, c.omega_val, c.theta_day,
        )

    logger.info("valued %d candidates", len(candidates))
    return candidates
