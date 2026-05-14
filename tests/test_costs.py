"""Unit tests for flatex cost model."""
from __future__ import annotations

import pytest

from src.costs.model import CostModelFactory, FlatexCostModel, CostParams


@pytest.fixture()
def model() -> FlatexCostModel:
    params = CostParams(
        base_fee_eur=5.90,
        exchange_fee_eur=3.00,
        spread_buffer_pct=2.0,
        eur_usd_rate=1.09,
        contracts=1,
    )
    return FlatexCostModel(params)


def test_entry_cost_positive(model: FlatexCostModel) -> None:
    cost = model.entry_cost_eur(2.25)
    assert cost > 0.0


def test_entry_cost_includes_fixed_fees(model: FlatexCostModel) -> None:
    cost = model.entry_cost_eur(2.25)
    # Fixed portion is 5.90 + 3.00 = 8.90 EUR
    assert cost > 8.90


def test_net_pnl_positive_on_big_gain(model: FlatexCostModel) -> None:
    # Buy at 2.25, exit at 6.00 — should be profitable after costs
    pnl = model.net_pnl_eur(2.25, 6.00)
    assert pnl > 0.0


def test_net_pnl_negative_on_loss(model: FlatexCostModel) -> None:
    pnl = model.net_pnl_eur(2.25, 0.50)
    assert pnl < 0.0


def test_factory_from_config(base_cfg: dict) -> None:
    m = CostModelFactory.from_config(base_cfg)
    assert isinstance(m, FlatexCostModel)
    assert m.entry_cost_eur(2.0) > 0.0
