"""Factory pattern — flatex.at transaction cost model."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.scenarios.analyzer import CandidateAnalysis, HorizonResult

logger = logging.getLogger(__name__)

_SHARES_PER_CONTRACT = 100


@dataclass
class CostParams:
    base_fee_eur: float
    exchange_fee_eur: float
    spread_buffer_pct: float
    eur_usd_rate: float
    contracts: int

    @property
    def total_fixed_eur(self) -> float:
        """Round-trip fixed costs (entry + exit)."""
        return 2.0 * (self.base_fee_eur + self.exchange_fee_eur)


class FlatexCostModel:
    """Models flatex.at option trading costs per candidate."""

    def __init__(self, params: CostParams) -> None:
        self._p = params

    def entry_cost_usd(self, option_mid_price: float) -> float:
        """Total USD cost to enter one round (contracts * 100 shares * price + spread buffer)."""
        notional_usd = option_mid_price * _SHARES_PER_CONTRACT * self._p.contracts
        spread_usd = notional_usd * self._p.spread_buffer_pct / 100.0
        return notional_usd + spread_usd

    def entry_cost_eur(self, option_mid_price: float) -> float:
        usd = self.entry_cost_usd(option_mid_price)
        fixed = self._p.base_fee_eur + self._p.exchange_fee_eur
        return usd / self._p.eur_usd_rate + fixed

    def exit_value_eur(self, option_exit_price: float) -> float:
        """EUR proceeds from selling (spread buffer reduces exit)."""
        notional_usd = option_exit_price * _SHARES_PER_CONTRACT * self._p.contracts
        spread_usd = notional_usd * self._p.spread_buffer_pct / 100.0
        net_usd = notional_usd - spread_usd
        fixed = self._p.base_fee_eur + self._p.exchange_fee_eur
        return net_usd / self._p.eur_usd_rate - fixed

    def net_pnl_eur(self, entry_price: float, exit_price: float) -> float:
        return self.exit_value_eur(exit_price) - self.entry_cost_eur(entry_price)

    def net_pnl_pct(self, entry_price: float, exit_price: float) -> float:
        entry_eur = self.entry_cost_eur(entry_price)
        if entry_eur <= 0.0:
            return 0.0
        return self.net_pnl_eur(entry_price, exit_price) / entry_eur * 100.0


class CostModelFactory:
    """Factory — constructs a cost model from config."""

    @staticmethod
    def from_config(cfg: dict) -> FlatexCostModel:
        c = cfg["costs"]
        params = CostParams(
            base_fee_eur=float(c["flatex_base_fee_eur"]),
            exchange_fee_eur=float(c["flatex_exchange_fee_eur"]),
            spread_buffer_pct=float(c["spread_buffer_pct"]),
            eur_usd_rate=float(c["eur_usd_rate"]),
            contracts=int(c["contracts"]),
        )
        return FlatexCostModel(params)


def run(cfg: dict, analyses: list[CandidateAnalysis]) -> list[CandidateAnalysis]:
    """Attaches entry cost and net P&L (EUR) to each horizon result in-place."""
    model = CostModelFactory.from_config(cfg)

    for analysis in analyses:
        entry = analysis.candidate.market_price
        entry_eur = model.entry_cost_eur(entry)
        logger.debug(
            "%s K=%.2f entry=%.4f USD => %.2f EUR",
            analysis.candidate.expiration, analysis.candidate.strike, entry, entry_eur,
        )
        for h in analysis.horizons:
            h.entry_cost_eur = entry_eur
            h.exit_value_target_eur = model.exit_value_eur(h.option_value_target)
            h.exit_value_flat_eur = model.exit_value_eur(h.option_value_flat)
            h.net_pnl_target_eur = model.net_pnl_eur(entry, h.option_value_target)
            h.net_pnl_flat_eur = model.net_pnl_eur(entry, h.option_value_flat)
            h.net_pnl_target_pct = model.net_pnl_pct(entry, h.option_value_target)
            h.net_pnl_flat_pct = model.net_pnl_pct(entry, h.option_value_flat)

    logger.info("costs applied to %d analyses", len(analyses))
    return analyses
