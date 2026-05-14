"""Detects the most liquid exchange for options on an underlying — used for non-US stocks."""
from __future__ import annotations

import logging

import yfinance as yf

logger = logging.getLogger(__name__)

# Known alternative tickers per underlying keyword.
# The detector tries each in order and picks the one with the largest total open interest.
_TICKER_CANDIDATES: dict[str, list[str]] = {
    "CATL": ["3750.HK", "300750.SZ", "CAT1.DE"],
    "CATL.HK": ["3750.HK"],
    "BABA": ["BABA", "9988.HK"],
    "JD": ["JD", "9618.HK"],
}


def _total_open_interest(ticker: str) -> int:
    """Returns the summed open interest across all expiration chains for a ticker."""
    try:
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            return 0
        total = 0
        for exp in expirations[:4]:  # check first 4 expirations only for speed
            try:
                chain = t.option_chain(exp)
                total += int(chain.calls["openInterest"].fillna(0).sum()
                              + chain.puts["openInterest"].fillna(0).sum())
            except Exception:
                pass
        logger.debug("ticker %s total OI across 4 expirations: %d", ticker, total)
        return total
    except Exception as exc:
        logger.debug("OI check failed for %s: %s", ticker, exc)
        return 0


def detect_best_ticker(raw_ticker: str) -> str:
    """
    Given a raw ticker (e.g. "CATL"), returns the ticker with the best option liquidity.
    Falls back to the input ticker if no alternatives are known or none have options.
    """
    candidates = _TICKER_CANDIDATES.get(raw_ticker.upper())
    if not candidates:
        return raw_ticker

    logger.info("detecting best exchange for %s — candidates: %s", raw_ticker, candidates)
    best_ticker = raw_ticker
    best_oi = -1

    for ticker in candidates:
        oi = _total_open_interest(ticker)
        logger.info("  %s: total OI = %d", ticker, oi)
        if oi > best_oi:
            best_oi = oi
            best_ticker = ticker

    if best_oi == 0:
        logger.warning(
            "no option chain found for any candidate of %s — check ticker manually",
            raw_ticker,
        )
        return candidates[0]

    logger.info("selected ticker: %s (OI = %d)", best_ticker, best_oi)
    return best_ticker
