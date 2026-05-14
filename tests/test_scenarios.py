"""Unit tests for scenario analysis."""
from __future__ import annotations

from datetime import date

import pytest

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
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


def test_horizons_include_holding_months(market_result: MarketDataResult, base_cfg: dict) -> None:
    analyzer = ScenarioAnalyzer(market_result, base_cfg)
    c = make_candidate()
    results = analyzer.analyse([c])
    assert len(results) == 1
    months = {h.months for h in results[0].horizons}
    assert base_cfg["analysis"]["holding_months"] in months


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
    c = make_candidate(dte=60)  # expires before 12m horizon -> T_remaining = 0
    results = analyzer.analyse([c])
    h12 = next(h for h in results[0].horizons if h.months == 12)
    expected = max(base_cfg["scenario"]["expected_price"] - c.strike, 0.0)
    assert h12.option_value_target == pytest.approx(expected, abs=0.01)


def test_expected_price_via_pct(market_result: MarketDataResult, base_cfg: dict) -> None:
    cfg = dict(base_cfg)
    cfg["scenario"] = {"expected_price": None, "expected_change_pct": 30.0, "flat_price": None}
    analyzer = ScenarioAnalyzer(market_result, cfg)
    expected = market_result.spot * 1.30
    assert analyzer.expected_price == pytest.approx(expected, rel=1e-6)


def test_run_returns_tuple(market_result: MarketDataResult, base_cfg: dict) -> None:
    from src.scenarios.analyzer import run
    result = run(base_cfg, market_result, [make_candidate()])
    assert isinstance(result, tuple)
    assert len(result) == 2
