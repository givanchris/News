#!/usr/bin/env python3
"""
update_holdings.py — Fetch current prices for all portfolio holdings
and write data/holdings.json for brief.html.
Uses requests + Yahoo Finance cookie/crumb auth — works on Python 3.8+.
Only writes ticker/name/price/change/changePct/prevClose/closes5d (no shares/cost).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
HOLDINGS_SRC = os.path.join(SCRIPT_DIR, "..", "Portfolio management", "holdings.json")
OUT_FILE     = os.path.join(SCRIPT_DIR, "data", "holdings.json")

FALLBACK_TICKERS = [
    "MRVL", "AVGO", "GOOG", "ALAB", "AMAT", "CEG", "ASML", "COHR",
    "HUBB", "TCEHY", "LEU", "CRWV", "MOG-A", "SOLS", "VELO",
    "ZBRA", "NOW", "GRPN", "BTC-USD",
]

TICKER_DISPLAY = {"MOG-A": "MOG.A", "BTC-USD": "BTC"}

NAMES = {
    "MRVL":    "Marvell Technology",
    "AVGO":    "Broadcom",
    "GOOG":    "Alphabet",
    "ALAB":    "Astera Labs",
    "AMAT":    "Applied Materials",
    "CEG":     "Constellation Energy",
    "ASML":    "ASML Holding",
    "COHR":    "Coherent Corp",
    "HUBB":    "Hubbell",
    "TCEHY":   "Tencent Holdings",
    "LEU":     "Centrus Energy",
    "CRWV":    "CoreWeave",
    "MOG.A":   "Moog Inc",
    "MOG-A":   "Moog Inc",
    "SOLS":    "Solaris Energy",
    "VELO":    "Velodyne Lidar",
    "ZBRA":    "Zebra Technologies",
    "NOW":     "ServiceNow",
    "GRPN":    "Groupon",
    "BTC":     "Bitcoin",
    "BTC-USD": "Bitcoin",
}

YF_MAP = {"MOG.A": "MOG-A", "BTC": "BTC-USD"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com/",
    "Origin": "https://finance.yahoo.com",
}

try:
    import requests
except ImportError:
    print("requests not installed — run: pip3 install --user requests")
    sys.exit(1)


def build_session():
    """Create a requests Session with Yahoo Finance cookies + crumb."""
    s = requests.Session()
    s.headers.update(HEADERS)

    # Hit the main page to set consent/session cookies
    s.get("https://finance.yahoo.com/", timeout=10)
    time.sleep(0.5)

    # Fetch crumb
    r = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=10)
    crumb = r.text.strip()

    if not crumb or "<" in crumb or r.status_code != 200:
        raise RuntimeError(f"Crumb fetch failed (HTTP {r.status_code}): {crumb[:80]}")

    return s, crumb


def yf_chart(session, crumb, symbol, range_="10d", interval="1d"):
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval={interval}&range={range_}&crumb={crumb}"
    )
    r = session.get(url, timeout=10)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}"}
    return r.json()


def fetch_holding(session, crumb, portfolio_ticker):
    yf_sym         = YF_MAP.get(portfolio_ticker, portfolio_ticker)
    display_ticker = TICKER_DISPLAY.get(yf_sym, yf_sym)

    data = yf_chart(session, crumb, yf_sym)
    if "error" in data:
        print(f"  {display_ticker:<8s}  ERROR — {data['error']}")
        return None

    try:
        result = data["chart"]["result"][0]
        meta   = result["meta"]
        price  = meta.get("regularMarketPrice") or meta.get("previousClose")
        prev   = meta.get("previousClose") or price
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"  {display_ticker:<8s}  parse error — {exc}")
        return None

    if not price or not prev:
        print(f"  {display_ticker:<8s}  no price data")
        return None

    change     = price - prev
    change_pct = (price - prev) / prev * 100 if prev else 0
    closes5d   = [round(c, 2) for c in closes[-5:]] if len(closes) >= 2 else [round(prev, 2), round(price, 2)]

    name = NAMES.get(display_ticker, display_ticker)
    sign = "+" if change >= 0 else ""
    print(f"  {display_ticker:<8s}  ${price:.2f}  {sign}{change_pct:.2f}%")

    return {
        "ticker":    display_ticker,
        "name":      name,
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
        return [YF_MAP.get(h["ticker"], h["ticker"]) for h in data["holdings"]]
    return FALLBACK_TICKERS


def main():
    tickers = load_tickers()
    print(f"Fetching {len(tickers)} tickers…\n")

    print("Initializing Yahoo Finance session…")
    try:
        session, crumb = build_session()
        print(f"Crumb OK ({crumb[:8]}…)\n")
    except Exception as exc:
        print(f"ERROR: session init failed — {exc}")
        sys.exit(1)

    results = []
    for sym in tickers:
        row = fetch_holding(session, crumb, sym)
        if row:
            results.append(row)
        time.sleep(0.4)

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
