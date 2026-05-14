"""Unit tests for flatex cost model."""
from __future__ import annotations

import pytest

from src.costs.model import CostModelFactory, CostParams, FlatexCostModel


@pytest.fixture()
def model() -> FlatexCostModel:
    params = CostParams(
        base_fee_eur=5.90,
        exchange_fee_eur=3.00,
        spread_buffer_pct=2.0,
        eur_usd_rate=1.09,
        investment_eur=1000.0,
    )
    return FlatexCostModel(params)


def test_entry_cost_positive(model: FlatexCostModel) -> None:
    assert model.entry_cost_eur(2.25) > 0.0


def test_entry_cost_includes_fixed_fees(model: FlatexCostModel) -> None:
    # Fixed portion is 5.90 + 3.00 = 8.90 EUR
    assert model.entry_cost_eur(2.25) > 8.90


def test_net_pnl_positive_on_big_gain(model: FlatexCostModel) -> None:
    assert model.net_pnl_eur(2.25, 6.00) > 0.0


def test_net_pnl_negative_on_loss(model: FlatexCostModel) -> None:
    assert model.net_pnl_eur(2.25, 0.50) < 0.0


def test_affordable_contracts_nonzero(model: FlatexCostModel) -> None:
    contracts = model.affordable_contracts(2.25)
    assert contracts >= 0


def test_affordable_contracts_respects_budget(model: FlatexCostModel) -> None:
    # With 1000 EUR budget and ~220 EUR entry cost, should be ~4 contracts
    contracts = model.affordable_contracts(2.25)
    total_cost = model.entry_cost_eur(2.25) * contracts
    assert total_cost <= 1000.0


def test_factory_from_config(base_cfg: dict) -> None:
    m = CostModelFactory.from_config(base_cfg)
    assert isinstance(m, FlatexCostModel)
    assert m.entry_cost_eur(2.0) > 0.0
