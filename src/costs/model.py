"""Factory pattern — flatex.at transaction cost model with investment-based contracts."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from src.scenarios.analyzer import CandidateAnalysis

logger = logging.getLogger(__name__)

_SHARES_PER_CONTRACT = 100


@dataclass
class CostParams:
    base_fee_eur: float
    exchange_fee_eur: float
    spread_buffer_pct: float
    eur_usd_rate: float
    investment_eur: float

    @property
    def fixed_per_trade_eur(self) -> float:
        return self.base_fee_eur + self.exchange_fee_eur


class FlatexCostModel:
    """Models flatex.at option trading costs per candidate. Pattern: Factory product."""

    def __init__(self, params: CostParams) -> None:
        self._p = params

    def entry_cost_eur(self, option_mid_price: float) -> float:
        """Total EUR cost to enter one contract (100 shares) including fees and spread."""
        spread = 1.0 + self._p.spread_buffer_pct / 100.0
        notional_usd = option_mid_price * _SHARES_PER_CONTRACT * spread
        return notional_usd / self._p.eur_usd_rate + self._p.fixed_per_trade_eur

    def exit_value_eur(self, option_exit_price: float) -> float:
        """EUR proceeds from selling one contract after fees and spread."""
        spread = 1.0 - self._p.spread_buffer_pct / 100.0
        notional_usd = option_exit_price * _SHARES_PER_CONTRACT * spread
        return notional_usd / self._p.eur_usd_rate - self._p.fixed_per_trade_eur

    def net_pnl_eur(self, entry_price: float, exit_price: float) -> float:
        return self.exit_value_eur(exit_price) - self.entry_cost_eur(entry_price)

    def net_pnl_pct(self, entry_price: float, exit_price: float) -> float:
        entry_eur = self.entry_cost_eur(entry_price)
        if entry_eur <= 0.0:
            return 0.0
        return self.net_pnl_eur(entry_price, exit_price) / entry_eur * 100.0

    def affordable_contracts(self, entry_price: float) -> int:
        """How many contracts can be bought with the configured investment_eur."""
        cost = self.entry_cost_eur(entry_price)
        if cost <= 0.0:
            return 0
        return max(math.floor(self._p.investment_eur / cost), 0)


class CostModelFactory:
    """Factory — constructs a FlatexCostModel from config."""

    @staticmethod
    def from_config(cfg: dict[str, Any]) -> FlatexCostModel:
        c = cfg["costs"]
        params = CostParams(
            base_fee_eur=float(c["flatex_base_fee_eur"]),
            exchange_fee_eur=float(c["flatex_exchange_fee_eur"]),
            spread_buffer_pct=float(c["spread_buffer_pct"]),
            eur_usd_rate=float(c["eur_usd_rate"]),
            investment_eur=float(c["investment_eur"]),
        )
        return FlatexCostModel(params)


def run(cfg: dict[str, Any], analyses: list[CandidateAnalysis]) -> list[CandidateAnalysis]:
    """Fills all cost and P&L fields on each HorizonResult in-place."""
    model = CostModelFactory.from_config(cfg)

    for analysis in analyses:
        entry = analysis.candidate.market_price
        entry_eur = model.entry_cost_eur(entry)
        contracts = model.affordable_contracts(entry)

        logger.debug(
            "%s K=%.2f entry=%.4f USD => %.2f EUR/Kontrakt, %d Kontrakte",
            analysis.candidate.expiration, analysis.candidate.strike, entry, entry_eur, contracts,
        )

        for h in analysis.horizons:
            h.entry_cost_eur = entry_eur
            h.contracts = contracts
            h.exit_value_target_eur = model.exit_value_eur(h.option_value_target)
            h.exit_value_flat_eur = model.exit_value_eur(h.option_value_flat)
            h.net_pnl_target_eur = model.net_pnl_eur(entry, h.option_value_target)
            h.net_pnl_flat_eur = model.net_pnl_eur(entry, h.option_value_flat)
            h.net_pnl_target_pct = model.net_pnl_pct(entry, h.option_value_target)
            h.net_pnl_flat_pct = model.net_pnl_pct(entry, h.option_value_flat)
            h.total_pnl_target_eur = h.net_pnl_target_eur * contracts
            h.total_pnl_flat_eur = h.net_pnl_flat_eur * contracts

    logger.info("costs applied to %d analyses", len(analyses))
    return analyses
