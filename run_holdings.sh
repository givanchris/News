#!/bin/bash
# run_holdings.sh — fetch prices + commit + push holdings.json
# Runs from cron every 30 min M-F 8am-5pm MT (= 14:00-23:00 UTC)

set -e
REPO="$HOME/News"
LOG="$HOME/logs/holdings-update.log"
mkdir -p "$HOME/logs"

echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') ===" >> "$LOG"

cd "$REPO"

# Pull any remote changes first
git pull --no-rebase origin main >> "$LOG" 2>&1 || true

# Fetch fresh prices
python3 "$REPO/update_holdings.py" >> "$LOG" 2>&1

# Commit + push if holdings.json changed
if ! git diff --quiet data/holdings.json; then
    git add data/holdings.json
    git commit -m "holdings: auto-update $(date -u '+%Y-%m-%dT%H:%MZ')" >> "$LOG" 2>&1
    git push origin main >> "$LOG" 2>&1
    echo "Pushed." >> "$LOG"
else
    echo "No change." >> "$LOG"
fi
