#!/usr/local/bin/python3.14
"""
update_holdings.py — Fetch current prices for all portfolio holdings
and write data/holdings.json for brief.html.
Uses yfinance with fast_info for accurate prev close.
Only writes ticker/name/price/change/changePct/prevClose/closes5d (no shares/cost).
"""

import json
import os
import sys
import time
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
HOLDINGS_SRC = os.path.join(SCRIPT_DIR, "..", "Portfolio management", "holdings.json")
OUT_FILE     = os.path.join(SCRIPT_DIR, "data", "holdings.json")

FALLBACK_TICKERS = [
    "MRVL", "AVGO", "GOOG", "ALAB", "AMAT", "CEG", "ASML", "COHR",
    "HUBB", "TCEHY", "LEU", "CRWV", "MOG.A", "SOLS", "VELO",
    "ZBRA", "NOW", "GRPN", "BTC",
]

NAMES = {
    "MRVL":  "Marvell Technology",
    "AVGO":  "Broadcom",
    "GOOG":  "Alphabet",
    "ALAB":  "Astera Labs",
    "AMAT":  "Applied Materials",
    "CEG":   "Constellation Energy",
    "ASML":  "ASML Holding",
    "COHR":  "Coherent Corp",
    "HUBB":  "Hubbell",
    "TCEHY": "Tencent Holdings",
    "LEU":   "Centrus Energy",
    "CRWV":  "CoreWeave",
    "MOG.A": "Moog Inc",
    "SOLS":  "Solaris Energy",
    "VELO":  "Velodyne Lidar",
    "ZBRA":  "Zebra Technologies",
    "NOW":   "ServiceNow",
    "GRPN":  "Groupon",
    "BTC":   "Bitcoin",
}

YF_MAP = {"MOG.A": "MOG-A", "BTC": "BTC-USD"}

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance not installed. Run: /usr/local/bin/python3.14 -m pip install yfinance --break-system-packages")
    sys.exit(1)


def fetch_holding(ticker):
    yf_sym = YF_MAP.get(ticker, ticker)
    t      = yf.Ticker(yf_sym)

    fi    = t.fast_info
    price = fi.last_price
    prev  = fi.previous_close
    if not price or not prev:
        print(f"  {ticker:<8s}  no data")
        return None

    change     = price - prev
    change_pct = (price - prev) / prev * 100

    hist = t.history(period="10d", auto_adjust=True)
    if not hist.empty:
        closes5d = [round(float(c), 2) for c in hist["Close"].tolist()[-5:]]
    else:
        closes5d = [round(prev, 2), round(price, 2)]

    sign = "+" if change >= 0 else ""
    print(f"  {ticker:<8s}  ${price:.2f}  {sign}{change_pct:.2f}%")

    return {
        "ticker":    ticker,
        "name":      NAMES.get(ticker, ticker),
        "price":     round(price, 2),
        "change":    round(change, 2),
        "changePct": round(change_pct, 2),
        "prevClose": round(prev, 2),
        "closes5d":  closes5d,
    }


def load_tickers():
    if os.path.exists(HOLDINGS_SRC):
        with open(HOLDINGS_SRC) as f:
            data = json.load(f)
        return [h["ticker"] for h in data["holdings"]]
    return FALLBACK_TICKERS


def main():
    tickers = load_tickers()
    print(f"Fetching {len(tickers)} tickers…\n")

    results = []
    for tk in tickers:
        row = fetch_holding(tk)
        if row:
            results.append(row)
        time.sleep(0.3)

    if not results:
        print("ERROR: no data fetched — holdings.json not updated")
        sys.exit(1)

    out = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "holdings": results,
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n{len(results)}/{len(tickers)} holdings written → {OUT_FILE}")


if __name__ == "__main__":
    main()
