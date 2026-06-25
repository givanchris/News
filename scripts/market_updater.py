#!/usr/bin/env python3
"""market_updater.py — Refresh live quotes in data/markets.json and data/brief.json"""
import json, datetime, subprocess, os, sys
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print('  [markets] yfinance not installed, skipping')
    sys.exit(0)

REPO_DIR    = Path.home() / 'News'
MARKETS_OUT = REPO_DIR / 'data' / 'markets.json'
BRIEF_OUT   = REPO_DIR / 'data' / 'brief.json'

now_utc = datetime.datetime.now(datetime.timezone.utc)
now_mt  = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=-6)))
ts_mt   = now_mt.strftime('%Y-%m-%dT%H:%M:%S-06:00')

SYMBOLS = {
    'sp500':  '^GSPC',
    'nasdaq': '^NDX',
    'yield':  '^TNX',
    'wti':    'CL=F',
    'gold':   'GC=F',
    'dxy':    'DX-Y.NYB',
}

def fmt_price(key, p):
    if key == 'yield':           return f'{p:.2f}%'
    if key == 'dxy':             return f'{p:.2f}'
    if key in ('wti', 'gold'):   return f'${p:.0f}'
    return f'{p:.0f}'

def fmt_change(key, price, prev):
    if key == 'yield':
        bps = round((price - prev) * 100)
        return ('+' if bps >= 0 else '') + f'{bps} bps'
    pct = (price - prev) / prev * 100
    return ('+' if pct >= 0 else '') + f'{pct:.2f}%'

def direction(key, price, prev):
    if key == 'yield':
        # yield up = bond price down
        if abs(price - prev) < 0.005: return 'flat'
        return 'down' if price > prev else 'up'
    pct = (price - prev) / prev * 100
    if abs(pct) < 0.01: return 'flat'
    return 'up' if pct > 0 else 'down'

print(f'  [markets] {now_utc.strftime("%H:%M")} UTC')
quotes = {}
for key, sym in SYMBOLS.items():
    try:
        fi = yf.Ticker(sym).fast_info
        price, prev = fi.last_price, fi.previous_close
        if not (price and prev):
            raise ValueError('empty data')
        quotes[key] = {
            'price':  fmt_price(key, price),
            'change': fmt_change(key, price, prev),
            'dir':    direction(key, price, prev),
        }
        print(f'    {key}: {quotes[key]["price"]} {quotes[key]["change"]}')
    except Exception as e:
        print(f'    {key}: SKIP ({e})')

if not quotes:
    print('  [markets] No quotes fetched, skipping')
    sys.exit(0)

# Update markets.json
markets = {'lastUpdated': ts_mt, 'source': 'market-updater', 'quotes': quotes}
if MARKETS_OUT.exists():
    try:
        existing = json.loads(MARKETS_OUT.read_text())
        if 'watchlist' in existing:
            markets['watchlist'] = existing['watchlist']
    except Exception:
        pass
MARKETS_OUT.write_text(json.dumps(markets, indent=2))
print(f'  [markets] Wrote markets.json')

# Update brief.json (market + lastUpdated only, preserve all other fields)
if BRIEF_OUT.exists():
    try:
        brief = json.loads(BRIEF_OUT.read_text())
        brief['market'] = quotes
        brief['lastUpdated'] = ts_mt
        BRIEF_OUT.write_text(json.dumps(brief, indent=2))
        print(f'  [markets] Patched brief.json')
    except Exception as e:
        print(f'  [markets] brief.json patch failed: {e}')

# Commit and push
os.chdir(REPO_DIR)
subprocess.run(['git', 'add', 'data/markets.json', 'data/brief.json'], check=True)
r = subprocess.run(['git', 'commit', '-m', f'markets: {now_utc.strftime("%H:%M")}Z'],
                   capture_output=True, text=True)
if 'nothing to commit' in (r.stdout + r.stderr):
    print('  [markets] No changes')
else:
    subprocess.run(['git', 'push'], check=True)
    print('  [markets] Pushed')
