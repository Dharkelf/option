"""Strategy pattern — market data fetching (yfinance implementation)."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

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
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
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
        close = history["Close"].squeeze()
        returns = close.pct_change().dropna()
        vol = float(returns.std() * (252**0.5))
        logger.info("realised vol (annualised) = %.4f", vol)
        return vol

    def fetch_implied_vol(self, ticker: str) -> float:
        """Approximates IV from the nearest ATM option on the nearest expiration."""
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            logger.warning("no option chain for %s — IV fallback 0.40", ticker)
            return 0.40
        chain = t.option_chain(expirations[0])
        spot = self.fetch_spot(ticker)
        calls = chain.calls
        atm = calls.iloc[(calls["strike"] - spot).abs().argsort()[:1]]
        try:
            iv = float(atm["impliedVolatility"].iloc[0])
        except (IndexError, KeyError, ValueError):
            iv = 0.40
            logger.warning("IV lookup failed — fallback 0.40")
        logger.info("implied vol for %s = %.4f", ticker, iv)
        return iv


@dataclass
class MarketDataResult:
    ticker: str
    spot: float
    history: pd.DataFrame
    realised_vol: float
    implied_vol: float
    risk_free_rate: float


def run(cfg: dict) -> MarketDataResult:
    ticker: str = cfg["underlying"]["ticker"]
    lookback: int = cfg["analysis"]["lookback_years"]
    rf_ticker: str = cfg["analysis"]["risk_free_ticker"]

    fetcher = YFinanceFetcher()
    paths = PathRepository(cfg)
    paths.ensure_dirs()

    history = fetcher.fetch_history(ticker, lookback)
    spot = fetcher.fetch_spot(ticker)
    realised_vol = fetcher.fetch_realised_vol(history)
    implied_vol = fetcher.fetch_implied_vol(ticker)
    rf = fetcher.fetch_risk_free_rate(rf_ticker)

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
    )
