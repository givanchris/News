# News / pipeline — Options Sentiment Pipeline Skill File

Parent: `../skills.md`. Global: `~/.claude/skills/python.md`.

## Purpose

The data pipeline behind `options.html` (the Options Sentiment Dashboard). Pulls options chains,
computes put/call ratios, volatility, and a sentiment read, and writes `latest.json` that the
dashboard renders.

## Entry point

`run.py` — CLI:

```bash
python run.py snapshot AAPL              # one ticker → JSON to stdout
python run.py market                     # full snapshot → latest.json
python run.py market --dry-run           # full snapshot → stdout (no write)
python run.py market --tickers AAPL TSLA NVDA
```

## Structure (`src/`)

- `config.py` — config (tickers, paths, thresholds).
- `data_providers/base.py` — `Provider` / `OptionsChain` interface.
- `data_providers/yfinance_provider.py` — concrete yfinance implementation.
- `calculations/ratios.py` — put/call and related ratios.
- `calculations/volatility.py` — IV / volatility measures.
- `calculations/sentiment.py` — combines signals into a sentiment read.
- `storage/snapshots.py` — writes/reads timestamped snapshots (→ `latest.json`).
- `utils/dates.py` — market-date helpers.

## Rules

- New data sources go behind `data_providers/base.py`; don't call yfinance directly from calc code.
- Keep `calculations/` pure (chain in → numbers out) so they're unit-testable without the network.
- Guard for empty/None option chains and yfinance rate-limits before computing — missing data is
  common and must not crash or produce garbage sentiment.
- `latest.json` is the contract with `options.html`. Don't change its shape without updating the page.
- Respect `requirements.txt` / `requirements.lock` pins.

## Deployment — Mac Mini (primary runner)

Pipeline runs on Mac Mini (10.0.0.144) via cron — NOT GitHub Actions.

- **Cron:** `30 16 * * 1-5` (4:30 PM MDT weekdays)
- **Script:** `~/scripts/run_options.sh`
- **Log:** `~/logs/options.log`
- **Repo:** cloned at `~/News/` on the Mini; script commits + pushes after each run
- **PAT:** embedded in Mini's git remote URL (`~/.git/config`) — repo scope, `daily-brief-automation` token

GitHub Actions workflow (`options-snapshot.yml`) schedule is **disabled** — only `workflow_dispatch` remains for manual emergency runs.

To deploy pipeline code changes: push from MacBook → Mini pulls on next cron run (or `ssh ... "cd ~/News && git pull"`).

## Validation

```bash
python run.py market --dry-run     # verify output shape without writing
# (add pytest tests for calculations/ as they grow)
```

## Debugging

1. Reproduce with a single ticker: `python run.py snapshot AAPL`.
2. Empty/odd numbers → check the provider returned a real chain (not rate-limited/empty).
3. Dashboard wrong → diff `latest.json` shape against what `options.html` expects.

## Self-Improvement Rule

yfinance options quirk, a sentiment-calc edge case, or a `latest.json` schema decision → record here.
