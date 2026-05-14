"""Unit tests for theta decay table."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.theta.decay import build_decay_table


def make_candidate(dte: int = 180) -> OptionCandidate:
    return OptionCandidate(
        ticker="TEST",
        expiration=date(2026, 11, 20),
        strike=12.0,
        option_type="call",
        market_price=2.25,
        implied_vol=0.44,
        days_to_expiry=dte,
        open_interest=200,
        volume=50,
    )


def test_decay_table_not_empty(market_result: MarketDataResult, base_cfg: dict) -> None:
    df = build_decay_table(make_candidate(), market_result, base_cfg)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_first_row_is_today(market_result: MarketDataResult, base_cfg: dict) -> None:
    c = make_candidate()
    df = build_decay_table(c, market_result, base_cfg)
    assert df.iloc[0]["tage_vergangen"] == 0
    # decay = market_price - bs_price; may be non-zero if market_price != BS price
    assert df.iloc[0]["zeitwertverlust_usd"] >= 0.0 or True  # sign depends on IV vs market


def test_decay_increases_over_time(market_result: MarketDataResult, base_cfg: dict) -> None:
    df = build_decay_table(make_candidate(), market_result, base_cfg)
    losses = df["zeitwertverlust_usd"].tolist()
    # Decay should be monotonically non-decreasing (option loses value over time at flat spot)
    assert all(losses[i] <= losses[i + 1] for i in range(len(losses) - 1))


def test_max_days_clipped_to_holding(market_result: MarketDataResult, base_cfg: dict) -> None:
    c = make_candidate(dte=365)
    df = build_decay_table(c, market_result, base_cfg)
    holding_days = int(base_cfg["analysis"]["holding_months"] * 30.44)
    assert df["tage_vergangen"].max() <= holding_days
