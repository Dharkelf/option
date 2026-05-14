"""CLI entry point — wires modules together, no business logic."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

import src.costs as costs
import src.market_data as market_data
import src.option_search as option_search
import src.report as report
import src.scenarios as scenarios
import src.valuation as valuation


def _load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def main() -> None:
    parser = argparse.ArgumentParser(description="CBOE option analysis for flatex.at investors")
    parser.add_argument("--config", default="config/settings.yaml", help="Path to settings YAML")
    parser.add_argument("--ticker", help="Override underlying ticker from config")
    parser.add_argument("--type", dest="option_type", choices=["call", "put"], help="Override option type")
    args = parser.parse_args()

    cfg: dict = _load_config(args.config)
    if args.ticker:
        cfg["underlying"]["ticker"] = args.ticker
    if args.option_type:
        cfg["option"]["type"] = args.option_type

    logging.basicConfig(
        level=getattr(logging, cfg["logging"]["level"]),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    mkt = market_data.run(cfg)
    candidates = option_search.run(cfg, mkt)
    if not candidates:
        logging.getLogger(__name__).warning("no candidates found — check ticker and leverage settings")
        return
    candidates = valuation.run(cfg, mkt, candidates)
    analyses = scenarios.run(cfg, mkt, candidates)
    analyses = costs.run(cfg, analyses)
    report.run(cfg, analyses)


if __name__ == "__main__":
    main()
