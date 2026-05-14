"""Fetches CBOE option chain via yfinance and filters by leverage target."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import yfinance as yf

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


class OptionSearcher:
    """Repository + Strategy: fetches chain, applies leverage filter, returns candidates."""

    def __init__(self, market: MarketDataResult, cfg: dict) -> None:
        self._market = market
        self._cfg = cfg
        self._otype: str = cfg["option"]["type"].lower()
        self._target_leverage: float = cfg["option"]["target_leverage"]
        self._tolerance: float = cfg["option"]["leverage_tolerance"]
        self._min_oi: int = cfg["option"]["min_open_interest"]
        self._max_candidates: int = cfg["option"]["max_candidates"]
        self._horizons: list[int] = cfg["analysis"]["horizons_months"]
        self._div_yield: float = cfg["underlying"]["dividend_yield"]

    def search(self) -> list[OptionCandidate]:
        t = yf.Ticker(self._market.ticker)
        expirations: list[str] = list(t.options or [])
        if not expirations:
            logger.warning("no option chain found for %s", self._market.ticker)
            return []

        target_timestamps = [
            pd.Timestamp.now(tz="UTC") + pd.DateOffset(months=m) for m in self._horizons
        ]
        selected = self._select_expirations(expirations, target_timestamps)
        logger.info("selected expirations: %s", selected)

        today = pd.Timestamp.now(tz="UTC").date()
        candidates: list[OptionCandidate] = []

        for exp_str in selected:
            try:
                chain = t.option_chain(exp_str)
                df = chain.calls if self._otype == "call" else chain.puts
                exp_date = pd.Timestamp(exp_str).date()
                T = (exp_date - today).days / 365.0
                if T <= 0.0:
                    continue
                batch = self._filter_chain(df, exp_date, int(T * 365), T)
                candidates.extend(batch)
                logger.info("expiration %s: %d candidates after filter", exp_str, len(batch))
            except Exception as exc:
                logger.warning("chain load failed for %s: %s", exp_str, exc)

        candidates.sort(key=lambda c: abs(c.omega_val - self._target_leverage))
        return candidates[: self._max_candidates * len(selected)]

    def _select_expirations(
        self, expirations: list[str], targets: list[pd.Timestamp]
    ) -> list[str]:
        seen: set[str] = set()
        selected: list[str] = []
        for target in targets:
            target_naive = target.tz_localize(None) if target.tzinfo is None else target.tz_convert(None)
            best = min(
                expirations,
                key=lambda e: abs((pd.Timestamp(e) - target_naive).days),
            )
            if best not in seen:
                selected.append(best)
                seen.add(best)
        return selected

    def _filter_chain(
        self, df: pd.DataFrame, exp_date: date, dte: int, T: float
    ) -> list[OptionCandidate]:
        spot = self._market.spot
        r = self._market.risk_free_rate
        q = self._div_yield
        results: list[OptionCandidate] = []

        for _, row in df.iterrows():
            strike = float(row["strike"])
            oi = int(row.get("openInterest") or 0)
            if oi < self._min_oi:
                continue

            raw_iv = row.get("impliedVolatility")
            iv_ok = raw_iv is not None and not pd.isna(raw_iv) and float(raw_iv) > 0.01
            iv = float(raw_iv) if iv_ok else (self._market.implied_vol or self._market.realised_vol)
            if iv > 5.0:
                iv = self._market.realised_vol

            bid = float(row.get("bid") or 0.0)
            ask = float(row.get("ask") or 0.0)
            mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else float(row.get("lastPrice") or 0.0)
            if mid <= 0.0:
                continue

            # Quick omega estimate to pre-filter before full Greek calculation
            om = bs.omega(self._otype, spot, strike, T, r, iv, q)
            if abs(om - self._target_leverage) > self._tolerance:
                continue

            results.append(
                OptionCandidate(
                    ticker=self._market.ticker,
                    expiration=exp_date,
                    strike=strike,
                    option_type=self._otype,
                    market_price=mid,
                    implied_vol=iv,
                    days_to_expiry=dte,
                    open_interest=oi,
                    volume=int(row.get("volume") or 0),
                )
            )

        return results


def run(cfg: dict, market: MarketDataResult) -> list[OptionCandidate]:
    searcher = OptionSearcher(market, cfg)
    candidates = searcher.search()
    logger.info("total candidates before valuation: %d", len(candidates))
    return candidates
