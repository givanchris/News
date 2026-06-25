#!/bin/bash
echo "--- $(date) ---"
/Users/christophergivan/News/pipeline/.venv/bin/python3 /Users/christophergivan/scripts/headlines.py
/Users/christophergivan/News/pipeline/.venv/bin/python3 /Users/christophergivan/scripts/market_updater.py
