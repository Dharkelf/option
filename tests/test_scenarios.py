"""Unit tests for scenario analysis."""
from __future__ import annotations

from datetime import date

import pytest

from src.market_data.fetcher import MarketDataResult
from src.option_search.searcher import OptionCandidate
from src.scenarios.analyzer import ScenarioAnalyzer


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


def test_horizons_count(market_result: MarketDataResult, base_cfg: dict) -> None:
    analyzer = ScenarioAnalyzer(market_result, base_cfg)
    c = make_candidate()
    results = analyzer.analyse([c])
    assert len(results) == 1
    assert len(results[0].horizons) == 3


def test_target_price_higher_gives_higher_call_value(
    market_result: MarketDataResult, base_cfg: dict
) -> None:
    analyzer = ScenarioAnalyzer(market_result, base_cfg)
    c = make_candidate()
    results = analyzer.analyse([c])
    h6 = next(h for h in results[0].horizons if h.months == 6)
    # target price (17) > flat price (13.10) => call worth more under target
    assert h6.option_value_target >= h6.option_value_flat


def test_expired_option_has_only_intrinsic(
    market_result: MarketDataResult, base_cfg: dict
) -> None:
    analyzer = ScenarioAnalyzer(market_result, base_cfg)
    c = make_candidate(dte=90)  # expires before 6m horizon -> T_remaining = 0
    results = analyzer.analyse([c])
    h12 = next(h for h in results[0].horizons if h.months == 12)
    # After expiry, value = max(spot_target - K, 0)
    expected = max(base_cfg["scenario"]["price_12m"] - c.strike, 0.0)
    assert h12.option_value_target == pytest.approx(expected, abs=0.01)
