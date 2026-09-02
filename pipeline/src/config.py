"""Central configuration: universe, output path, sentiment thresholds.

Edit thresholds here — they're imported by sentiment classifiers and
pipeline runners.
"""
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Output ────────────────────────────────────────────────────────────────
# Pipeline now lives at News/pipeline/src/config.py — parents[2] is News/.
# Snapshots write to News/data/options/ so the static site can serve them.
_THIS = Path(__file__).resolve()
_NEWS_ROOT = _THIS.parents[2]
_DEFAULT_OUT = _NEWS_ROOT / "data" / "options"
OUTPUT_DIR = Path(os.getenv("OPTIONS_OUTPUT_DIR") or _DEFAULT_OUT)
CHARTS_DIR = Path(os.getenv("OPTIONS_CHARTS_DIR") or (_NEWS_ROOT / "charts"))

# ── Universe ──────────────────────────────────────────────────────────────
WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "META", "GOOGL", "AMZN", "AMD", "JPM", "GS"]

INDICES = [
    {"ticker": "SPY", "name": "S&P 500"},
    {"ticker": "QQQ", "name": "Nasdaq 100"},
    {"ticker": "IWM", "name": "Russell 2000"},
]

SECTORS = [
    {"ticker": "XLK",  "name": "Technology"},
    {"ticker": "XLF",  "name": "Financials"},
    {"ticker": "XLE",  "name": "Energy"},
    {"ticker": "XLV",  "name": "Health Care"},
    {"ticker": "XLY",  "name": "Consumer Disc."},
    {"ticker": "XLP",  "name": "Consumer Staples"},
    {"ticker": "XLI",  "name": "Industrials"},
    {"ticker": "XLU",  "name": "Utilities"},
    {"ticker": "XLB",  "name": "Materials"},
    {"ticker": "XLRE", "name": "Real Estate"},
]

VIX_TERM = [
    ("^VIX9D", "VIX9D"),
    ("^VIX",   "VIX"),
    ("^VIX3M", "VIX3M"),
    ("^VIX6M", "VIX6M"),
]

# ── Sentiment thresholds (edit freely) ────────────────────────────────────
PUT_CALL_BEARISH  = 1.20   # P/C > 1.20  → bearish
PUT_CALL_BULLISH  = 0.80   # P/C < 0.80  → bullish
IV_RANK_HIGH      = 70     # IV rank > 70 → fear elevated
IV_RANK_LOW       = 30     # IV rank < 30 → complacency
UNUSUAL_VOL_MULT  = 2.0    # daily option volume > 2× OI at strike
UNUSUAL_MIN_VOL   = 100    # ignore unusual flag below this volume
SKEW_BEARISH      = 4.0    # OTM put IV − OTM call IV > 4 pp → meaningful

# Regime thresholds
VIX_LOW           = 15.0
VIX_HIGH          = 25.0
