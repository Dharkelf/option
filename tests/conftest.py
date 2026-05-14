"""Shared fixtures for all tests."""
from __future__ import annotations

import pandas as pd
import pytest

from src.market_data.fetcher import MarketDataResult


@pytest.fixture()
def sample_history() -> pd.DataFrame:
    idx = pd.date_range("2025-01-02", periods=252, freq="B", tz="UTC")
    import numpy as np
    rng = np.random.default_rng(42)
    prices = 10.0 * (1 + rng.normal(0.0005, 0.02, len(idx))).cumprod()
    return pd.DataFrame({"Close": prices, "Open": prices, "High": prices, "Low": prices}, index=idx)


@pytest.fixture()
def market_result(sample_history: pd.DataFrame) -> MarketDataResult:
    return MarketDataResult(
        ticker="TEST",
        spot=13.10,
        history=sample_history,
        realised_vol=0.44,
        implied_vol=0.44,
        risk_free_rate=0.045,
    )


@pytest.fixture()
def base_cfg() -> dict:
    return {
        "underlying": {"ticker": "TEST", "dividend_yield": 0.025},
        "option": {
            "type": "call",
            "target_leverage": 4.0,
            "leverage_tolerance": 1.5,
            "min_open_interest": 0,
            "max_candidates": 10,
        },
        "scenario": {
            "price_3m": 15.50,
            "price_6m": 17.00,
            "price_12m": 20.00,
            "flat_price": 13.10,
        },
        "analysis": {
            "horizons_months": [3, 6, 12],
            "lookback_years": 1,
            "risk_free_ticker": "^TNX",
        },
        "costs": {
            "flatex_base_fee_eur": 5.90,
            "flatex_exchange_fee_eur": 3.00,
            "spread_buffer_pct": 2.0,
            "eur_usd_rate": 1.09,
            "contracts": 1,
        },
        "logging": {"level": "DEBUG"},
        "paths": {"data_dir": "data", "raw_dir": "data/raw", "processed_dir": "data/processed"},
    }
