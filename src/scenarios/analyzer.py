"""Template Method: project option value at each horizon given user price estimates."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.market_data.fetcher import MarketDataResult
from src.option_search.searcher import OptionCandidate
from src.valuation import blackscholes as bs

logger = logging.getLogger(__name__)


@dataclass
class HorizonResult:
    months: int
    spot_target: float          # user-provided price estimate
    spot_flat: float            # "nothing happens" price
    T_remaining: float          # time to expiry after this horizon (years)
    option_value_target: float  # BS value at target price
    option_value_flat: float    # BS value at flat price
    prob_profit_target: float   # probability of profit at expiry given target path
    prob_profit_flat: float


@dataclass
class CandidateAnalysis:
    candidate: OptionCandidate
    horizons: list[HorizonResult] = field(default_factory=list)


class ScenarioAnalyzer:
    """Template Method — analyse() is the fixed pipeline; _horizon_result() is the variable step."""

    def __init__(self, market: MarketDataResult, cfg: dict) -> None:
        self._market = market
        self._cfg = cfg
        self._horizons: list[int] = cfg["analysis"]["horizons_months"]
        self._prices: dict[int, float] = {
            3: float(cfg["scenario"]["price_3m"]),
            6: float(cfg["scenario"]["price_6m"]),
            12: float(cfg["scenario"]["price_12m"]),
        }
        raw_flat = cfg["scenario"].get("flat_price")
        self._flat_price: float = float(raw_flat) if raw_flat is not None else market.spot

    def analyse(self, candidates: list[OptionCandidate]) -> list[CandidateAnalysis]:
        results: list[CandidateAnalysis] = []
        for c in candidates:
            horizons = [self._horizon_result(c, m) for m in self._horizons]
            results.append(CandidateAnalysis(candidate=c, horizons=horizons))
        logger.info("scenario analysis complete for %d candidates", len(results))
        return results

    def _horizon_result(self, c: OptionCandidate, months: int) -> HorizonResult:
        T_total = c.days_to_expiry / 365.0
        T_remaining = max(T_total - months / 12.0, 0.0)
        r = self._market.risk_free_rate
        q: float = self._cfg["underlying"]["dividend_yield"]
        iv = c.implied_vol
        otype = c.option_type
        K = c.strike

        spot_target = self._prices.get(months, self._market.spot)
        spot_flat = self._flat_price

        val_target = bs.price(otype, spot_target, K, T_remaining, r, iv, q)
        val_flat = bs.price(otype, spot_flat, K, T_remaining, r, iv, q)

        prob_target = bs.prob_profit_at_expiry(otype, spot_target, K, T_remaining, r, iv, q, c.market_price)
        prob_flat = bs.prob_profit_at_expiry(otype, spot_flat, K, T_remaining, r, iv, q, c.market_price)

        return HorizonResult(
            months=months,
            spot_target=spot_target,
            spot_flat=spot_flat,
            T_remaining=T_remaining,
            option_value_target=val_target,
            option_value_flat=val_flat,
            prob_profit_target=prob_target,
            prob_profit_flat=prob_flat,
        )


def run(cfg: dict, market: MarketDataResult, candidates: list[OptionCandidate]) -> list[CandidateAnalysis]:
    analyzer = ScenarioAnalyzer(market, cfg)
    return analyzer.analyse(candidates)
