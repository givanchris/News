#!/usr/bin/env python3
"""headlines.py — Rolling news scraper for givanchris.github.io/News
Cron: 0,30 7-15 * * 1-5  and  0 16 * * 1-5  (7am–4pm MDT, Mon–Fri)
"""
import json, subprocess, os, sys, datetime, re
from pathlib import Path

now_utc  = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
utc_mins = now_utc.hour * 60 + now_utc.minute
if utc_mins < 13 * 60 or utc_mins >= 22 * 60 + 30:
    print(f'[{now_utc.strftime("%H:%M")} UTC] Outside scrape window.')
    sys.exit(0)

REPO_DIR      = Path.home() / 'News'
HEADLINES_OUT = REPO_DIR / 'data' / 'headlines.json'
MAX_HEADLINES = 40

import certifi, requests
import xml.etree.ElementTree as ET

SESSION = requests.Session()
SESSION.verify = certifi.where()
SESSION.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'

FEEDS = [
    ('CNBC', 'MARKETS', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
    ('YF',   'MARKETS', 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US'),
    ('WSJ',  'MARKETS', 'https://feeds.a.dj.com/rss/RSSMarketsMain.xml'),
    ('MW',   'MARKETS', 'https://feeds.marketwatch.com/marketwatch/topstories/'),
    ('FT',   'WORLD',   'https://www.ft.com/rss/home'),
    ('ARS',  'TECH',    'https://feeds.arstechnica.com/arstechnica/technology-lab'),
]

# Drop headlines that match these noise patterns
BLOCKLIST = re.compile(
    r'director (sells|buys|acquires)|insider (trading|transaction)|form 8-k|'
    r'files sec|quarterly dividend|declares dividend|stock split|'
    r'renounce (citizenship|us)|real estate|mortgage rate|'
    r'bulker|tanker|shipping|fleet|vessel',
    re.I
)

def ts_from_pubdate(s):
    if not s: return now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    import email.utils
    try:
        dt = email.utils.parsedate_to_datetime(s)
        return dt.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except Exception:
        return now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

def fetch_rss(source, category, url):
    items = []
    try:
        r = SESSION.get(url, timeout=12)
        if r.status_code != 200:
            print(f'  {source}: HTTP {r.status_code}')
            return items
        root = ET.fromstring(r.text)
        for item in root.findall('.//item')[:20]:
            title   = (item.findtext('title') or '').strip()
            link    = (item.findtext('link')  or '').strip()
            pubdate = (item.findtext('pubDate') or '').strip()
            if len(title) < 15: continue
            if BLOCKLIST.search(title): continue
            items.append({'source': source, 'category': category,
                          'title': title, 'url': link,
                          'ts': ts_from_pubdate(pubdate)})
    except Exception as e:
        print(f'  {source}: ERROR {e}')
    return items

def title_key(t):
    words = re.sub(r'[^a-z0-9 ]', '', t.lower()).split()
    return ' '.join(words[:7])

def dedup(items):
    seen, out = set(), []
    for item in items:
        k = title_key(item['title'])
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out

ts_now = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
print(f'[{now_utc.strftime("%H:%M")} UTC] Scraping...')

all_items = []
for source, cat, url in FEEDS:
    batch = fetch_rss(source, cat, url)
    print(f'  {source}: {len(batch)}')
    all_items.extend(batch)

all_items = dedup(all_items)
all_items.sort(key=lambda x: x['ts'], reverse=True)
all_items = all_items[:MAX_HEADLINES]

HEADLINES_OUT.write_text(json.dumps({
    'lastUpdated': ts_now, 'count': len(all_items), 'headlines': all_items
}, indent=2))
print(f'  Wrote {len(all_items)} headlines')

os.chdir(REPO_DIR)
subprocess.run(['git', 'add', 'data/headlines.json'], check=True)
r2 = subprocess.run(['git', 'commit', '-m', f'headlines: {ts_now[:16]}'],
                    capture_output=True, text=True)
if 'nothing to commit' in (r2.stdout + r2.stderr):
    print('  No changes')
else:
    subprocess.run(['git', 'push'], check=True)
    print('  Pushed')
print('  Done')
