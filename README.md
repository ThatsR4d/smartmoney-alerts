# SmartMoneyAlerts

Viral financial intelligence bot that tracks insider trades from SEC filings and posts to Twitter/Discord.

## Features

- **SEC Form 4 Scraping**: Real-time scraping of insider trading disclosures
- **Anomaly Detection**: Identifies unusual patterns (cluster buys, first purchases, large trades)
- **Virality Scoring**: Scores trades 0-100 based on newsworthiness
- **Twitter Bot**: Auto-posts high-scoring trades with smart tagging
- **Discord Bot**: Sends alerts to free/premium channels
- **SQLite Database**: Tracks all trades and posting history

## Quick Start

### 1. Install Dependencies

```bash
cd smartmoney
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Get API Keys

**Twitter/X:**
1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a project with read/write permissions
3. Get API Key, API Secret, Access Token, Access Secret

**Discord:**
1. Go to [discord.com/developers](https://discord.com/developers)
2. Create a new application
3. Create a bot and get the token
4. Invite bot to your server

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
python main.py --help        # Show all options
python main.py --status      # Show system status
python main.py --scrape      # Scrape only (no posting)
python main.py --post        # Post pending alerts
python main.py --once        # Full pipeline once
python main.py --daemon      # Run continuously
python main.py --init-db     # Initialize database
```

## Project Structure

```
smartmoney/
├── config/
│   ├── settings.py       # API keys, thresholds
│   ├── tickers.py        # Stock lists (SP500, meme stocks)
│   ├── influencers.py    # Twitter accounts to tag
│   └── templates.py      # Tweet templates
├── scrapers/
│   └── sec_form4.py      # SEC EDGAR Form 4 scraper
├── core/
│   ├── database.py       # SQLite database
│   ├── analyzer.py       # Anomaly detection
│   ├── scorer.py         # Virality scoring
│   └── formatter.py      # Tweet/Discord formatting
├── bots/
│   ├── twitter_bot.py    # Twitter posting
│   └── discord_bot.py    # Discord posting
├── utils/
│   ├── helpers.py        # Utility functions
│   └── rate_limiter.py   # API rate limiting
├── main.py               # Entry point
├── requirements.txt
└── .env.example
```

## Virality Scoring

Trades are scored 0-100 based on:
- **Insider Role** (25 pts max): CEO/Founder > CFO > VP > Director
- **Transaction Size** (25 pts max): $50M+ > $10M > $1M > etc.
- **Company Recognition** (20 pts max): Magnificent 7 > Meme Stocks > SP500
- **Anomalies** (25 pts max): Cluster buying, first purchase, unusual size

**Posting Tiers:**
- **Tier 1 (70+)**: Post immediately with full promotion
- **Tier 2 (50-69)**: Post within 1 hour
- **Tier 3 (30-49)**: Batch post
- **Tier 4 (<30)**: Daily roundup only

## Testing Components

```bash
# Test SEC scraper
python scrapers/sec_form4.py

# Test database
python core/database.py

# Test scorer
python core/scorer.py

# Test formatter
python core/formatter.py

# Test Twitter bot
python bots/twitter_bot.py
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

### Render

1. Create new Background Worker
2. Connect GitHub repo
3. Set start command: `python main.py --daemon`
4. Add environment variables
5. Deploy

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py", "--daemon"]
```

## Phase 2: Congress Tracking (Coming Soon)

- House/Senate stock trade disclosures
- STOCK Act compliance monitoring
- Suspicious timing detection

## Phase 3: 13F Filings (Coming Soon)

- Hedge fund quarterly holdings
- Position change tracking
- Famous investor alerts (Buffett, Burry, etc.)

## License

MIT

## Disclaimer

This tool is for educational and informational purposes only. It is not financial advice. Always do your own research before making investment decisions.
