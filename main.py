"""CLI entry point — wires modules together, no business logic."""
from __future__ import annotations

import argparse
import logging
from typing import Any

import yaml

import src.costs as costs
import src.market_data as market_data
import src.option_search as option_search
import src.report as report
import src.scenarios as scenarios
import src.valuation as valuation
from src.exchange.detector import detect_best_ticker
from src.interactive.workflow import print_recommendation, print_verification_checklist
from src.sensitivity.grid import build_sensitivity_grid
from src.theta.decay import build_decay_table


def _load_yaml(path: str) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def _merge_input(input_cfg: dict[str, Any], tech_cfg: dict[str, Any]) -> dict[str, Any]:
    """Merges user input file into technical config. Input values take precedence."""
    cfg: dict[str, Any] = {k: dict(v) if isinstance(v, dict) else v for k, v in tech_cfg.items()}

    cfg.setdefault("underlying", {})
    cfg["underlying"]["ticker"] = input_cfg["ticker"]
    cfg["underlying"]["dividend_yield"] = float(input_cfg.get("dividend_yield", 0.0))

    cfg.setdefault("option", {})
    cfg["option"]["type"] = input_cfg["option_type"]
    cfg["option"]["target_leverage"] = float(input_cfg.get("target_leverage", 4.0))

    cfg["analysis"]["holding_months"] = int(input_cfg.get("holding_months", 6))

    cfg.setdefault("scenario", {})
    cfg["scenario"]["expected_price"] = input_cfg.get("expected_price")
    cfg["scenario"]["expected_change_pct"] = input_cfg.get("expected_change_pct")
    cfg["scenario"]["flat_price"] = input_cfg.get("flat_price")

    if "investment_eur" in input_cfg:
        cfg["costs"]["investment_eur"] = float(input_cfg["investment_eur"])

    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CBOE-Optionsanalyse für flatex.at — Erlösschätzung vor dem Kauf"
    )
    parser.add_argument("--input", required=True, help="Eingabedatei, z.B. input/sghc.yaml")
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()

    cfg = _merge_input(_load_yaml(args.input), _load_yaml(args.config))

    logging.basicConfig(
        level=getattr(logging, cfg["logging"]["level"]),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log = logging.getLogger(__name__)

    # Exchange detection for non-standard tickers (e.g. "CATL" -> "3750.HK")
    raw_ticker: str = cfg["underlying"]["ticker"]
    resolved = detect_best_ticker(raw_ticker)
    if resolved != raw_ticker:
        log.info("Ticker gewählt: %s -> %s (beste Optionsliquidität)", raw_ticker, resolved)
        cfg["underlying"]["ticker"] = resolved

    # Pipeline
    mkt = market_data.run(cfg)

    candidates = option_search.run(cfg, mkt)
    if not candidates:
        log.warning("Keine Kandidaten — Hebel-Toleranz erhöhen oder Ticker prüfen.")
        return

    candidates = valuation.run(cfg, mkt, candidates)
    analyses, expected_price = scenarios.run(cfg, mkt, candidates)
    analyses = costs.run(cfg, analyses)

    # Theta decay + sensitivity grid for top 3
    theta_tables: dict[str, Any] = {}
    sensitivity_grids: dict[str, Any] = {}
    for i, a in enumerate(analyses[:3], 1):
        c = a.candidate
        label = f"[{i}] {c.option_type.upper()} K={c.strike:.2f} Verfall {c.expiration}"
        theta_tables[label] = build_decay_table(c, mkt, cfg)
        sensitivity_grids[label] = build_sensitivity_grid(c, mkt, cfg, expected_price)

    # Output
    report.run(cfg, mkt, analyses, theta_tables, sensitivity_grids)
    print_verification_checklist(candidates, mkt, cfg)
    print_recommendation(analyses, cfg, expected_price)


if __name__ == "__main__":
    main()
