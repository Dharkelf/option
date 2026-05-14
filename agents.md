# AGENTS.md — option

This file governs how AI agents (Claude Code, Codex, etc.) work in this repository.
Read it before making any structural or architectural decisions.

---

## Project Purpose

On-demand analysis of CBOE-listed options (calls and puts) for a user-specified underlying.
The user provides: ticker, option type (call/put), target leverage, and their own price estimates
for 3, 6, and 12 months into the future.
The tool fetches live option chains from CBOE (via yfinance), filters candidates to the target
leverage (Omega), prices them with Black-Scholes, and computes projected P&L at each horizon
under the user's scenario — net of flatex.at transaction costs.

Historical data (1 yr) is fetched to derive realised volatility for BS pricing. All results are
stored as Parquet files for reproducibility.

**Broker context:** flatex.at, trading US options on CBOE. Transaction costs are modelled
explicitly per config.

---

## Standard Directory Layout

```
<project-root>/
├── AGENTS.md               # this file — agent instructions
├── README.md
├── REPORT.md
├── requirements.txt        # pinned dependencies (pip freeze output)
├── .gitignore
├── .env.example
│
├── config/
│   └── settings.yaml       # all runtime config — single source of truth
│
├── data/                   # excluded from git
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── __init__.py
│   ├── market_data/        # historical prices, spot, risk-free rate
│   ├── option_search/      # CBOE option chain fetch + leverage filter
│   ├── valuation/          # Black-Scholes pricing + Greeks
│   ├── scenarios/          # user scenario evaluation at 3/6/12m
│   ├── costs/              # flatex transaction cost model
│   ├── report/             # tabular output + Parquet export
│   └── utils/              # path helpers
│
├── tests/
│   ├── conftest.py
│   └── test_<module>.py
│
├── notebooks/
│
└── main.py
```

### Module Layout Rules

- Each functional domain lives in its own subdirectory under `src/`.
- Module names are lowercase, underscore-separated.
- No business logic in `main.py` — it only wires modules and calls `run()`.
- `config/settings.yaml` is the single source of truth. No hard-coded numeric values.
- `notebooks/` for exploration only — move any reusable logic to `src/` before committing.

---

## Modules in This Project

| Module | Path | Responsibility |
|---|---|---|
| market_data | `src/market_data/` | yfinance: 1yr history, spot, realised vol, 10yr treasury yield |
| option_search | `src/option_search/` | CBOE option chain, leverage filter (omega), candidate ranking |
| valuation | `src/valuation/` | Black-Scholes pricing, Delta/Gamma/Theta/Vega/Omega |
| scenarios | `src/scenarios/` | Project option value at horizons given user price estimate (linear interp.) |
| costs | `src/costs/` | flatex fee model; investment_eur -> affordable contracts; total P&L |
| theta | `src/theta/` | Weekly theta decay table (flat spot) from today to holding_months |
| sensitivity | `src/sensitivity/` | Spot x time P&L grid — option value at spot scenarios x time points |
| interactive | `src/interactive/` | Live-verification checklist + product recommendation printout |
| exchange | `src/exchange/` | Multi-ticker liquidity detection for non-US stocks (e.g. CATL) |
| report | `src/report/` | Candidate table + theta + sensitivity grid + Parquet export |
| utils | `src/utils/` | PathRepository — all file-system paths derived from settings.yaml |

---

## Pre-commit Hooks

Setup (once per developer machine):
```bash
pip install pre-commit
pre-commit install
```

Hooks run in order: **ruff** (lint + format) -> **mypy** (type check) -> **pytest** (full suite).
No commit may pass with errors.

To run manually:
```bash
pre-commit run --all-files
```

---

## Testing

- Unit tests for individual functions; mock external dependencies (yfinance, file I/O).
- Integration tests for module interactions; use real data structures and Parquet files.
- All tests in `tests/test_<module>.py`. Run before every commit: `pytest tests/`
- Happy path + main failure modes (no option chain, zero price, expired option) must be covered.
- If checks cannot be run, explicitly state what was skipped and why.

---

## Design Patterns

| Pattern | Where used |
|---|---|
| **Repository** | `PathRepository` in `src/utils/paths.py` — all file paths in one place |
| **Strategy** | `MarketDataStrategy` — swappable data source (yfinance today, CBOE API later) |
| **Factory** | `CostModelFactory` — constructs the right cost model from config |
| **Template Method** | `ScenarioAnalyzer.analyse()` — fixed pipeline skeleton, swappable steps |

---

## Coding Conventions

- Python 3.11+
- Type hints on all public functions and class methods.
- No `print()` in library code — use stdlib `logging`; configure level in `settings.yaml`.
- No comments explaining *what* code does — only *why* when non-obvious.
- All file I/O through `PathRepository`.
- Parquet as default storage; CSV only for human-readable exports.
- All timestamps UTC.

---

## Data Conventions

- Raw price data is append-only. Never overwrite existing Parquet files.
- All timestamps UTC, stored as `datetime64[ns, UTC]`.
- Option candidate results stored in `data/processed/candidates_<ticker>_<date>.parquet`.

---

## Key Dependencies

| Purpose | Library |
|---|---|
| Market data + option chains | `yfinance` |
| BS pricing + statistics | `numpy`, `scipy` |
| Data frames + Parquet | `pandas`, `pyarrow` |
| Config | `pyyaml` |
| Env vars | `python-dotenv` |

---

## Failure Conditions

Agents MUST NOT:

- Push to remote without an explicit user request.
- Overwrite raw Parquet files — append only.
- Hard-code numeric values that belong in `config/settings.yaml`.
- Commit without running `pre-commit run --all-files` (or documenting why not).
- Use `print()` in library code.
- Introduce a dependency without pinning it immediately in `requirements.txt`.
- Commit `.env`, `.venv/`, `data/`, or any file containing secrets.

---

## Git Rules

- Conventional Commits: `<type>(<scope>): <subject>` (imperative, max 72 chars, no full stop)
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`
- `README.md`, `REPORT.md`, `config/settings.yaml`, `AGENTS.md`, `requirements.txt` always committed.
- `data/`, `.venv/`, `__pycache__/` always in `.gitignore`.
- **Never push automatically.** `git push` only on explicit user request.

---

## Input File Convention

User-facing parameters live in `input/<name>.yaml`, not in `config/settings.yaml`.
`config/settings.yaml` contains only technical / fee parameters that rarely change.

Required fields in an input file:
```yaml
ticker: "SGHC"
dividend_yield: 0.025
option_type: "call"
target_leverage: 4.0
investment_eur: 1000.0
holding_months: 6
expected_price: 17.00     # optional — or use expected_change_pct
```

Run: `python main.py --input input/sghc.yaml`

---

## Output Structure

The tool produces output in this order:
1. Candidate table ranked by expected P&L at `holding_months`
2. Theta decay table (flat spot) for top 3 candidates
3. Sensitivity grid (spot x time) for top 3 candidates
4. Live-verification checklist (what to look up in flatex / Yahoo Finance)
5. Product recommendation with full rationale

---

## End Goal

A self-contained CLI tool that:
1. Reads a plain-text input file (ticker, type, leverage, investment, holding, price target).
2. Fetches the CBOE option chain for the underlying via yfinance.
3. Filters candidates by target leverage (Omega).
4. Computes Black-Scholes value, Greeks, theta decay, and P&L sensitivity grid.
5. Deducts flatex.at transaction costs; computes affordable contracts from investment_eur.
6. Prints an actionable checklist of what to verify live in flatex / Yahoo Finance.
7. Recommends the best product with full investment rationale.
8. Exports a Parquet file with all results.
