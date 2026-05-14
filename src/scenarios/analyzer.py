"""Template Method — projects option value at each horizon given user price estimate."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.market_data.fetcher import MarketDataResult
from src.models import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


@dataclass
class HorizonResult:
    months: int
    spot_target: float          # user price estimate at this horizon (linearly interpolated)
    spot_flat: float            # flat scenario: spot unchanged
    T_remaining: float          # years remaining to expiry after this horizon
    option_value_target: float
    option_value_flat: float
    prob_profit_target: float
    prob_profit_flat: float
    # populated by costs.model.run()
    entry_cost_eur: float = 0.0
    exit_value_target_eur: float = 0.0
    exit_value_flat_eur: float = 0.0
    net_pnl_target_eur: float = 0.0
    net_pnl_flat_eur: float = 0.0
    net_pnl_target_pct: float = 0.0
    net_pnl_flat_pct: float = 0.0
    contracts: int = 0
    total_pnl_target_eur: float = 0.0
    total_pnl_flat_eur: float = 0.0


@dataclass
class CandidateAnalysis:
    candidate: OptionCandidate
    horizons: list[HorizonResult] = field(default_factory=list)


class ScenarioAnalyzer:
    """Template Method — analyse() is the fixed pipeline; _horizon_result() is variable."""

    def __init__(self, market: MarketDataResult, cfg: dict) -> None:
        self._market = market
        self._cfg = cfg
        self._horizons: list[int] = cfg["analysis"]["horizons_months"]
        self._holding_months: int = cfg["analysis"]["holding_months"]

        spot = market.spot
        raw_expected = cfg["scenario"].get("expected_price")
        raw_pct = cfg["scenario"].get("expected_change_pct")

        if raw_expected is not None:
            self._expected_price: float | None = float(raw_expected)
        elif raw_pct is not None:
            self._expected_price = spot * (1.0 + float(raw_pct) / 100.0)
        else:
            self._expected_price = None

        raw_flat = cfg["scenario"].get("flat_price")
        self._flat_price: float = float(raw_flat) if raw_flat is not None else spot

        logger.info(
            "scenario: expected_price=%s, flat=%s, holding=%dm",
            self._expected_price, self._flat_price, self._holding_months,
        )

    @property
    def expected_price(self) -> float | None:
        return self._expected_price

    def analyse(self, candidates: list[OptionCandidate]) -> list[CandidateAnalysis]:
        # Always include holding_months in the evaluated horizons
        all_months = sorted(set(self._horizons + [self._holding_months]))
        results: list[CandidateAnalysis] = []
        for c in candidates:
            horizons = [self._horizon_result(c, m) for m in all_months]
            results.append(CandidateAnalysis(candidate=c, horizons=horizons))
        logger.info("scenario analysis complete for %d candidates", len(results))
        return results

    def _target_at_horizon(self, months: int) -> float:
        """Linear interpolation from current spot to expected price over holding_months."""
        if self._expected_price is None:
            return self._market.spot
        fraction = min(months / self._holding_months, 1.0) if self._holding_months > 0 else 1.0
        return self._market.spot + (self._expected_price - self._market.spot) * fraction

    def _horizon_result(self, c: OptionCandidate, months: int) -> HorizonResult:
        T_remaining = max(c.days_to_expiry / 365.0 - months / 12.0, 0.0)
        r = self._market.risk_free_rate
        q: float = self._cfg["underlying"]["dividend_yield"]
        iv = c.implied_vol
        otype = c.option_type
        K = c.strike

        spot_target = self._target_at_horizon(months)
        spot_flat = self._flat_price

        return HorizonResult(
            months=months,
            spot_target=spot_target,
            spot_flat=spot_flat,
            T_remaining=T_remaining,
            option_value_target=bs.price(otype, spot_target, K, T_remaining, r, iv, q),
            option_value_flat=bs.price(otype, spot_flat, K, T_remaining, r, iv, q),
            prob_profit_target=bs.prob_profit_at_expiry(
                otype, spot_target, K, T_remaining, r, iv, q, c.market_price
            ),
            prob_profit_flat=bs.prob_profit_at_expiry(
                otype, spot_flat, K, T_remaining, r, iv, q, c.market_price
            ),
        )


def run(
    cfg: dict, market: MarketDataResult, candidates: list[OptionCandidate]
) -> tuple[list[CandidateAnalysis], float | None]:
    analyzer = ScenarioAnalyzer(market, cfg)
    return analyzer.analyse(candidates), analyzer.expected_price
