# SmartMoneyAlerts

Viral financial intelligence bot that tracks insider trades, congressional stock trades, and hedge fund positions from SEC filings and posts to Twitter/Discord.

## Features

- **SEC Form 4 Scraping**: Real-time scraping of insider trading disclosures
- **Congressional Trade Tracking**: House and Senate stock trades from Capitol Trades
- **Hedge Fund 13F Monitoring**: Track positions of famous investors (Buffett, Burry, Ackman, etc.)
- **Anomaly Detection**: Identifies unusual patterns (cluster buys, first purchases, large trades)
- **Virality Scoring**: Scores trades 0-100 based on newsworthiness
- **Twitter Bot**: Auto-posts via API or browser automation (Playwright)
- **Discord Bot**: Sends alerts to free/premium channels with role gating
- **SQLite Database**: Tracks all trades and posting history

## Quick Start

### 1. Install Dependencies

```bash
cd smartmoney
pip install -r requirements.txt
playwright install chromium  # For browser automation
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Setup Twitter (Browser Mode - Recommended)

Browser automation is more reliable and doesn't require expensive API access:

```bash
python main.py --setup-twitter
```

This opens a browser window for you to log in to Twitter. Your session is saved for future posts.

### 4. Initialize Database

```bash
python main.py --init-db
```

### 5. Test Run (Dry Run)

```bash
# Ensure DRY_RUN=true in .env
python main.py --once
```

### 6. Run for Real

```bash
# Set DRY_RUN=false in .env
python main.py --daemon
```

## Commands

```bash
python main.py --help           # Show all options
python main.py --status         # Show system status
python main.py --setup-twitter  # Login to Twitter (browser mode)
python main.py --scrape         # Scrape only (no posting)
python main.py --post           # Post pending alerts
python main.py --once           # Full pipeline once
python main.py --daemon         # Run continuously
python main.py --init-db        # Initialize database
```

## Project Structure

```
smartmoney/
├── config/
│   ├── settings.py       # API keys, thresholds, feature flags
│   ├── tickers.py        # Stock lists (S&P500, meme stocks, Magnificent 7)
│   ├── influencers.py    # Twitter accounts to tag by stock/topic
│   └── templates.py      # Tweet templates for each tier
├── scrapers/
│   ├── sec_form4.py      # SEC EDGAR Form 4 scraper
│   ├── congress.py       # Capitol Trades congressional scraper
│   └── hedge_funds.py    # SEC 13F hedge fund scraper
├── core/
│   ├── database.py       # SQLite database (6 tables)
│   ├── analyzer.py       # Anomaly detection
│   ├── scorer.py         # Virality scoring algorithm
│   └── formatter.py      # Tweet/Discord formatting
├── bots/
│   ├── twitter_bot.py    # Twitter API posting (Tweepy)
│   ├── twitter_browser.py # Browser automation (Playwright)
│   └── discord_bot.py    # Discord posting
├── utils/
│   ├── helpers.py        # Formatting utilities
│   └── rate_limiter.py   # Token bucket rate limiting
├── data/
│   └── smartmoney.db     # SQLite database
├── main.py               # Entry point
├── requirements.txt
└── .env.example
```

## Data Sources

### SEC Form 4 (Insider Trades)
- Real-time scraping of insider trading disclosures
- Required filings within 2 business days of trade
- Tracks purchases, sales, and awards
- Company officers, directors, and 10% owners

### Congressional Trades
- House and Senate member stock trades
- Data from Capitol Trades API
- Tracks 40+ high-profile politicians (Pelosi, McConnell, AOC, etc.)
- Disclosure timing analysis

### Hedge Fund 13F Filings
- Quarterly institutional holdings disclosures
- 18 famous funds tracked:
  - Berkshire Hathaway (Buffett)
  - Scion Asset Management (Burry)
  - Pershing Square (Ackman)
  - Bridgewater Associates (Dalio)
  - Renaissance Technologies (Simons)
  - And more...

## Virality Scoring

Trades are scored 0-100 based on:
- **Insider Role** (25 pts max): CEO/Founder > CFO > VP > Director
- **Transaction Size** (25 pts max): $50M+ > $10M > $1M > etc.
- **Company Recognition** (20 pts max): Magnificent 7 > Meme Stocks > S&P500
- **Anomalies** (25 pts max): Cluster buying, first purchase, unusual size

**Posting Tiers:**
- **Tier 1 (70+)**: Post immediately with full promotion
- **Tier 2 (50-69)**: Post within 1 hour
- **Tier 3 (30-49)**: Batch post
- **Tier 4 (<30)**: Daily roundup only

## Twitter Modes

### Browser Mode (Recommended)
- Uses Playwright for browser automation
- Human-like typing delays and randomized timing
- No API costs
- Persistent session storage
- Set `TWITTER_MODE=browser` in .env

### API Mode
- Uses Twitter API v2 via Tweepy
- Requires developer account and API keys
- Rate limited (50-100 tweets/day depending on tier)
- Set `TWITTER_MODE=api` in .env

## Testing Components

```bash
# Test SEC scraper
python scrapers/sec_form4.py

# Test Congress scraper
python scrapers/congress.py

# Test 13F scraper
python scrapers/hedge_funds.py

# Test database
python core/database.py

# Test scorer
python core/scorer.py

# Test formatter
python core/formatter.py
```

## Documentation

Detailed documentation is available in the `docs/` folder:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design, data flow, database schema
- **[SETUP.md](docs/SETUP.md)** - Detailed installation and configuration guide
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Deploy to Railway, Render, Docker, VPS
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Development notes, extending the system

## Deployment

### Railway

1. Push to GitHub
2. Connect Railway to your repo
3. Add environment variables
4. Deploy

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && playwright install chromium --with-deps
COPY . .
CMD ["python", "main.py", "--daemon"]
```

## Rate Limiting

- **SEC EDGAR**: Max 10 requests/second (0.15s delay between requests)
- **Twitter Browser**: 8 posts/hour max, 150-300s random delay between posts
- **Twitter API**: 50-100 tweets/day depending on tier
- **Discord**: 30 messages/minute

## License

MIT

## Disclaimer

This tool is for educational and informational purposes only. It is not financial advice. Always do your own research before making investment decisions.
