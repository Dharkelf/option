"""Fetches CBOE option chain via yfinance and filters by leverage target."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


class OptionSearcher:
    """Repository + Strategy: fetches chain, applies leverage filter, returns candidates."""

    def __init__(self, market: MarketDataResult, cfg: dict[str, Any]) -> None:
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
            target_naive = (
                target.tz_localize(None) if target.tzinfo is None else target.tz_convert(None)
            )
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
        fallback_iv = self._market.implied_vol or self._market.realised_vol

        # Vectorized pre-filtering
        work = df.copy()
        work["_oi"] = pd.to_numeric(  # type: ignore[call-overload]
            work.get("openInterest"), errors="coerce"
        ).fillna(0).astype(int)
        work = work[work["_oi"] >= self._min_oi]
        if work.empty:
            return []

        bid = pd.to_numeric(work.get("bid"), errors="coerce").fillna(0.0)  # type: ignore[call-overload]
        ask = pd.to_numeric(work.get("ask"), errors="coerce").fillna(0.0)  # type: ignore[call-overload]
        last = pd.to_numeric(work.get("lastPrice"), errors="coerce").fillna(0.0)  # type: ignore[call-overload]
        work["_mid"] = ((bid + ask) / 2.0).where((bid > 0) & (ask > 0), last)
        work = work[work["_mid"] > 0.0]
        if work.empty:
            return []

        raw_iv = pd.to_numeric(work.get("impliedVolatility"), errors="coerce")  # type: ignore[call-overload]
        iv_valid = raw_iv.notna() & (raw_iv > 0.01) & (raw_iv <= 5.0)
        work["_iv"] = raw_iv.where(iv_valid, fallback_iv)

        results: list[OptionCandidate] = []
        for _, row in work.iterrows():
            strike = float(row["strike"])
            iv = float(row["_iv"])
            mid = float(row["_mid"])
            oi = int(row["_oi"])
            bid_val = float(bid.get(row.name, 0.0))
            ask_val = float(ask.get(row.name, 0.0))

            om = bs.omega(self._otype, spot, strike, T, r, iv, q)
            if abs(om - self._target_leverage) > self._tolerance:
                continue

            if self._otype == "call":
                intrinsic = max(spot - strike, 0.0)
            else:
                intrinsic = max(strike - spot, 0.0)
            stale = (bid_val == 0 and ask_val == 0) or (intrinsic > 0 and mid < intrinsic * 0.95)

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
                    stale_quote=stale,
                )
            )

        return results


def run(cfg: dict[str, Any], market: MarketDataResult) -> list[OptionCandidate]:
    searcher = OptionSearcher(market, cfg)
    candidates = searcher.search()
    logger.info("total candidates before valuation: %d", len(candidates))
    return candidates
