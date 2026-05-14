"""Unit tests for sensitivity grid."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.sensitivity.grid import build_sensitivity_grid


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


def test_grid_not_empty(market_result: MarketDataResult, base_cfg: dict) -> None:
    df = build_sensitivity_grid(make_candidate(), market_result, base_cfg)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0


def test_grid_has_spot_column(market_result: MarketDataResult, base_cfg: dict) -> None:
    df = build_sensitivity_grid(make_candidate(), market_result, base_cfg)
    assert "spot_usd" in df.columns
    assert "aenderung_pct" in df.columns


def test_expected_price_row_present(market_result: MarketDataResult, base_cfg: dict) -> None:
    expected = 17.00
    df = build_sensitivity_grid(make_candidate(), market_result, base_cfg, expected_price=expected)
    marked = df[df["markierung"] == "ziel"]
    assert len(marked) == 1
    assert marked.iloc[0]["spot_usd"] == pytest.approx(expected, abs=0.01)


def test_higher_spot_higher_call_value_at_heute(
    market_result: MarketDataResult, base_cfg: dict
) -> None:
    df = build_sensitivity_grid(make_candidate(), market_result, base_cfg)
    df_sorted = df.sort_values("spot_usd")
    vals = df_sorted["wert_heute_usd"].tolist()
    assert all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
