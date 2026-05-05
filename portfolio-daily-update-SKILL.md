---
name: portfolio-daily-update
description: Daily portfolio price update and analysis saved to the Portfolio management folder
---

---
name: portfolio-daily-update
description: Daily portfolio price update and analysis saved to the Portfolio management folder
---
You are running a daily portfolio update for a user finishing a bachelor's in Economics and starting an MS in Finance & Investment Management.

## Step 0 — Archive previous outputs

Run this bash to move any previous portfolio HTML reports into an Archive subfolder:

```bash
portfolio_dir="/Users/christophergivan/Desktop/Claude/Projects/Portfolio management"
mkdir -p "$portfolio_dir/Archive"
find "$portfolio_dir" -maxdepth 1 -name "portfolio_analysis_*.html" -exec mv {} "$portfolio_dir/Archive/" \; 2>/dev/null
```

## Step 1 — Fetch prices

Run the fetch_prices.py script via bash:

```bash
cd "/Users/christophergivan/Desktop/Claude/Projects/Portfolio management"
python3 fetch_prices.py 2>&1
```

If the script succeeds, it will update prices.json with current market data.

If the script fails or Python/dependencies are unavailable, fall back to Step 1b.

## Step 1b — Fallback: web search prices

If Step 1 failed, use WebSearch to find current prices for the portfolio holdings. Search for:
- "S&P 500 price today"
- Prices for individual holdings in prices.json if known

Update prices.json manually with the fetched data.

## Step 2 — Generate the analysis report

Read the current prices.json file and generate a portfolio analysis HTML report. Save it as:

`/Users/christophergivan/Desktop/Claude/Projects/Portfolio management/portfolio_analysis.html`

The report must begin with a clearly visible header:

```html
<h1>Portfolio Analysis</h1>
<p><strong>Last Updated: [Full date — e.g. Monday, March 30, 2026] | [Time] ET</strong></p>
```

Include in the report:
- Current holdings with prices, values, and daily % change
- Portfolio total value and daily P&L
- Asset allocation breakdown
- Any notable moves or market context worth flagging

## Step 3 — Log the update

Append a one-line entry to the update log:

```bash
echo "[$(date '+%Y-%m-%d %H:%M')] Portfolio updated successfully" >> "/Users/christophergivan/Desktop/Claude/Projects/Portfolio management/fetch_prices.log"
```