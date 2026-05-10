# Options Sentiment Pipeline

Local + GitHub-Actions Python pipeline for the **Options Sentiment Dashboard**
at `/options.html`. Lives inside the News repo so a single workflow can run it,
commit fresh JSON, and push to Pages.

## Status

- **Phase 1** ✓ Static UI + mock data (`options.html`)
- **Phase 2** ✓ Pipeline scaffold, yfinance provider, calculations
- **Phase 3** ✓ Daily history persistence, GitHub Actions cron, Fetch button
- **Phase 4** Historical charts (uses the history files Phase 3 writes)
- **Phase 5** Sector heatmap details + VIX term structure (UI already in place)

## How updates happen

| Trigger              | Mechanism                                                    |
|----------------------|--------------------------------------------------------------|
| Daily, weekdays      | GitHub Actions cron at 22:30 UTC (4:30 PM MDT / 3:30 MST)    |
| Manual, anyone       | Actions tab → "Options Snapshot" → "Run workflow"            |
| Local, you           | `python pipeline/run.py market` (writes the same JSON files) |
| Visitor's "Fetch"    | Re-loads `latest.json` from the server (does not re-run)     |

The Fetch button on the dashboard re-reads the latest committed snapshot —
it does **not** spawn a fresh fetch. True on-demand re-fetches need a
serverless backend (Cloudflare Worker or Netlify Function) and can be added
later as Phase 3.5.

## Local setup

```bash
cd News/pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# One ticker → JSON to stdout
python run.py snapshot AAPL

# Full market snapshot → writes data/options/latest.json + history files
python run.py market

# Same, but stdout-only (no writes)
python run.py market --dry-run

# Skip history files (faster, only refreshes latest.json)
python run.py market --no-history

# Custom watchlist
python run.py market --tickers SPY QQQ NVDA
```

## Output files

All paths are relative to the News repo root.

```
data/options/
├── latest.json                 most recent market snapshot (overwritten)
├── tickers/<SYMBOL>.json       per-ticker chronological history
├── sectors.json                sector heatmap history
└── vix.json                    VIX & term-structure history
```

History files use one record per market day. Re-running on the same date
upserts (replaces the same-date record).

## Architecture

```
pipeline/
├── run.py                         CLI entrypoint
├── requirements.txt
├── .env.example
└── src/
    ├── config.py                  universe, output path, sentiment thresholds
    ├── data_providers/
    │   ├── base.py                Provider ABC + Quote/OptionsChain
    │   └── yfinance_provider.py
    ├── calculations/
    │   ├── ratios.py              put_call_volume_ratio, aggregate_pc_volume
    │   ├── volatility.py          atm_iv, calculate_skew, iv_rank, iv_percentile
    │   └── sentiment.py           classify_sentiment, sector_sentiment_score, classify_regime
    ├── storage/
    │   └── snapshots.py           write_latest, append_*_history
    └── utils/dates.py
```

To swap providers (Polygon, Alpha Vantage), drop a new file under
`data_providers/` implementing the `Provider` ABC and import it from `run.py`.

## Sentiment thresholds (edit in `src/config.py`)

| Threshold        | Default | Meaning                                |
|------------------|---------|----------------------------------------|
| PUT_CALL_BEARISH | 1.20    | P/C above → bearish                    |
| PUT_CALL_BULLISH | 0.80    | P/C below → bullish                    |
| IV_RANK_HIGH     | 70      | IV in top 30% of 52w → fear elevated   |
| IV_RANK_LOW      | 30      | IV in bottom 30% → complacency         |
| UNUSUAL_VOL_MULT | 2.0     | Strike vol > 2× OI → flagged           |
| VIX_LOW / HIGH   | 15 / 25 | Regime classifier bands                |

## Limits

- **yfinance is ~15-min delayed** (free feed). Fine for daily snapshots.
- **IV rank / IV percentile** stay `null` until ~21 daily snapshots accumulate.
- **Skew** is a 25-delta proxy using ±5% OTM strikes from the front-month chain.
- **Unusual flow** flags any strike with `vol > 2× OI` and ≥100 contracts.
- A full `market` run hits ~25 tickers and takes 1–2 minutes locally;
  GitHub Actions runs it in ~2–3 minutes including Python setup.
