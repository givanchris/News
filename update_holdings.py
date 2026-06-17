#!/usr/bin/env python3
"""
update_holdings.py — Fetch current prices for all portfolio holdings
and write data/holdings.json for brief.html.
Uses Yahoo Finance API with cookie+crumb auth — no yfinance needed.
Only writes ticker/name/price/change/changePct/prevClose/closes5d (no shares/cost).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
from urllib.error import URLError

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

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def build_session():
    """Return (opener, crumb) with Yahoo Finance cookies + crumb set."""
    jar    = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", UA), ("Accept", "*/*")]

    # Step 1: hit finance.yahoo.com to receive session cookies
    req = Request("https://finance.yahoo.com/", headers={"User-Agent": UA})
    opener.open(req, timeout=10)

    # Step 2: fetch crumb
    crumb_url = "https://query1.finance.yahoo.com/v1/test/getcrumb"
    resp  = opener.open(Request(crumb_url, headers={"User-Agent": UA}), timeout=10)
    crumb = resp.read().decode().strip()

    if not crumb or "<" in crumb:
        raise RuntimeError(f"Failed to get crumb: {crumb[:80]}")

    return opener, crumb


def yf_chart(opener, crumb, symbol, range_="10d", interval="1d"):
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?interval={interval}&range={range_}&crumb={crumb}"
    )
    try:
        resp = opener.open(Request(url, headers={"User-Agent": UA}), timeout=10)
        return json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc)}


def fetch_holding(opener, crumb, portfolio_ticker):
    yf_sym         = YF_MAP.get(portfolio_ticker, portfolio_ticker)
    display_ticker = TICKER_DISPLAY.get(yf_sym, yf_sym)

    data = yf_chart(opener, crumb, yf_sym)
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

    print("Getting Yahoo Finance session…")
    try:
        opener, crumb = build_session()
        print(f"Crumb: {crumb[:8]}…\n")
    except Exception as exc:
        print(f"ERROR: could not init session — {exc}")
        sys.exit(1)

    results = []
    for sym in tickers:
        row = fetch_holding(opener, crumb, sym)
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
