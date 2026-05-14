"""Strategy pattern — market data fetching (yfinance implementation)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
import yfinance as yf

from src.utils.paths import PathRepository

logger = logging.getLogger(__name__)


class MarketDataStrategy(ABC):
    @abstractmethod
    def fetch_history(self, ticker: str, lookback_years: int) -> pd.DataFrame: ...

    @abstractmethod
    def fetch_spot(self, ticker: str) -> float: ...

    @abstractmethod
    def fetch_risk_free_rate(self, rf_ticker: str) -> float: ...

    @abstractmethod
    def fetch_realised_vol(self, history: pd.DataFrame) -> float: ...

    @abstractmethod
    def fetch_implied_vol(self, ticker: str) -> float: ...


class YFinanceFetcher(MarketDataStrategy):
    """Fetches market data via yfinance. Pattern: Strategy."""

    def fetch_history(self, ticker: str, lookback_years: int) -> pd.DataFrame:
        start = pd.Timestamp.now(tz="UTC") - pd.DateOffset(years=lookback_years)
        df: pd.DataFrame = yf.download(
            ticker,
            start=start.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        idx = cast(pd.DatetimeIndex, df.index)
        if idx.tz is None:
            df.index = idx.tz_localize("UTC")
        else:
            df.index = idx.tz_convert("UTC")
        logger.info("fetched %d rows for %s", len(df), ticker)
        return df

    def fetch_spot(self, ticker: str) -> float:
        info = yf.Ticker(ticker).fast_info
        try:
            price = float(info.last_price)
        except (AttributeError, TypeError):
            price = 0.0
        logger.info("spot %s = %.4f", ticker, price)
        return price

    def fetch_risk_free_rate(self, rf_ticker: str) -> float:
        info = yf.Ticker(rf_ticker).fast_info
        try:
            # ^TNX quotes the yield in percent (e.g. 4.5 = 4.5%)
            rate = float(info.last_price) / 100.0
        except (AttributeError, TypeError):
            rate = 0.045
            logger.warning("could not fetch risk-free rate — using fallback %.4f", rate)
        logger.info("risk-free rate (%s) = %.4f", rf_ticker, rate)
        return rate

    def fetch_realised_vol(self, history: pd.DataFrame) -> float:
        close = cast(pd.Series, history["Close"].squeeze())
        returns = close.pct_change().dropna()
        vol = float(returns.std() * (252**0.5))
        logger.info("realised vol (annualised) = %.4f", vol)
        return vol

    def fetch_eur_usd(self) -> float:
        """Fetches live EUR/USD rate from EURUSD=X. Falls back to 1.09 on failure."""
        try:
            info = yf.Ticker("EURUSD=X").fast_info
            rate = float(info.last_price)
            if 0.5 < rate < 3.0:
                logger.info("EUR/USD live rate = %.4f", rate)
                return rate
        except (AttributeError, TypeError):
            pass
        logger.warning("EUR/USD rate unavailable — using fallback 1.09")
        return 1.09

    def fetch_implied_vol(self, ticker: str, realised_vol: float = 0.40) -> float:
        """Approximates IV from nearest ATM option. Falls back to realised vol if unavailable."""
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            logger.warning("no option chain for %s — using realised vol %.4f", ticker, realised_vol)
            return realised_vol
        # Try first 3 expirations to find a valid IV
        for exp in expirations[:3]:
            try:
                chain = t.option_chain(exp)
                spot = self.fetch_spot(ticker)
                calls = chain.calls[chain.calls["impliedVolatility"] > 0.01]
                if calls.empty:
                    continue
                atm = calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]
                iv = float(atm["impliedVolatility"].iloc[0])
                if iv > 0.01:
                    logger.info("implied vol for %s = %.4f (from %s)", ticker, iv, exp)
                    return iv
            except Exception:
                continue
        logger.warning("IV lookup failed for %s — using realised vol %.4f", ticker, realised_vol)
        return realised_vol


@dataclass
class MarketDataResult:
    ticker: str
    spot: float
    history: pd.DataFrame
    realised_vol: float
    implied_vol: float
    risk_free_rate: float
    eur_usd_rate: float = 1.09


def run(cfg: dict[str, Any]) -> MarketDataResult:
    ticker: str = cfg["underlying"]["ticker"]
    lookback: int = cfg["analysis"]["lookback_years"]
    rf_ticker: str = cfg["analysis"]["risk_free_ticker"]

    fetcher = YFinanceFetcher()
    paths = PathRepository(cfg)
    paths.ensure_dirs()

    history = fetcher.fetch_history(ticker, lookback)
    spot = fetcher.fetch_spot(ticker)
    realised_vol = fetcher.fetch_realised_vol(history)
    implied_vol = fetcher.fetch_implied_vol(ticker, realised_vol)
    rf = fetcher.fetch_risk_free_rate(rf_ticker)
    eur_usd = fetcher.fetch_eur_usd()

    raw_path = paths.raw_file(ticker.lower())
    if raw_path.exists():
        existing: pd.DataFrame = pd.read_parquet(raw_path)
        combined = pd.concat([existing, history])
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)
        combined.to_parquet(raw_path)
    else:
        history.to_parquet(raw_path)
    logger.info("history stored: %s", raw_path)

    return MarketDataResult(
        ticker=ticker,
        spot=spot,
        history=history,
        realised_vol=realised_vol,
        implied_vol=implied_vol,
        risk_free_rate=rf,
        eur_usd_rate=eur_usd,
    )
