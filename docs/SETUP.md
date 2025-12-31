# Setup Guide

## Prerequisites

- Python 3.9+
- pip
- Git

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/ThatsR4d/smartmoney-alerts.git
cd smartmoney-alerts
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright (For Browser Mode)

```bash
playwright install chromium
```

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration.

## Twitter Setup

### Option 1: Browser Mode (Recommended)

Browser automation is easier to set up and doesn't require API keys.

```bash
python main.py --setup-twitter
```

This will:
1. Open a Chromium browser window
2. Navigate to Twitter login
3. Wait for you to log in manually
4. Save your session for future posts

**Advantages:**
- No API costs
- No developer account needed
- More reliable posting
- Human-like behavior (avoids rate limits)

**Session Storage:** `bots/.twitter_session/`

### Option 2: Twitter API

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a new project and app
3. Enable **Read and Write** permissions
4. Generate keys:
   - API Key and Secret
   - Access Token and Secret
   - Bearer Token

Add to `.env`:
```
TWITTER_MODE=api
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret
TWITTER_BEARER_TOKEN=your_bearer_token
```

## Discord Setup

### Discord Bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Create New Application
3. Go to Bot → Add Bot
4. Copy the token
5. Enable these Intents:
   - Message Content Intent
   - Server Members Intent (if using role gating)

**Invite URL** (replace CLIENT_ID):
```
https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=2048&scope=bot
```

Add to `.env`:
```
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
DISCORD_FREE_CHANNEL_ID=channel_for_free_alerts
DISCORD_PREMIUM_CHANNEL_ID=channel_for_premium_alerts
```

### Discord Webhook (Alternative)

Simpler than full bot, good for one-way posting:

1. Server Settings → Integrations → Webhooks
2. Create Webhook
3. Copy URL

Add to `.env`:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## Configuration Options

### Feature Flags

```bash
# Enable/disable platforms
TWITTER_ENABLED=true
DISCORD_ENABLED=true

# Twitter mode: "browser" or "api"
TWITTER_MODE=browser

# Actually post (false = log only)
POST_TO_TWITTER=true

# Dry run mode (no posts, just simulation)
DRY_RUN=true
```

### Scraping Settings

```bash
# How often to check SEC (minutes)
SCRAPE_INTERVAL_MINUTES=5

# Minimum trade value to track
MIN_TRANSACTION_VALUE=10000

# Max items per scrape
MAX_FORM4_FILINGS=100
MAX_CONGRESS_TRADES=200
MAX_13F_FILINGS=100

# Transaction types to track
TRACK_PURCHASES=true
TRACK_SALES=true
TRACK_AWARDS=false
```

### Posting Settings

```bash
# Virality score thresholds
TIER1_SCORE=70
TIER2_SCORE=50
TIER3_SCORE=30

# Rate limiting (API mode)
MAX_POSTS_PER_HOUR=15
```

## Initialize Database

```bash
python main.py --init-db
```

This creates `data/smartmoney.db` with all required tables.

## Verify Setup

### Test Scrapers

```bash
# Test SEC Form 4 scraper
python scrapers/sec_form4.py

# Test Congress scraper
python scrapers/congress.py

# Test 13F scraper
python scrapers/hedge_funds.py
```

### Test Full Pipeline (Dry Run)

```bash
# Ensure DRY_RUN=true in .env
python main.py --once
```

### Check Status

```bash
python main.py --status
```

## Running the Bot

### One-Time Run

```bash
python main.py --once
```

### Continuous (Daemon)

```bash
python main.py --daemon
```

### Background with nohup

```bash
nohup python main.py --daemon > smartmoney.log 2>&1 &
```

### With systemd (Linux)

Create `/etc/systemd/system/smartmoney.service`:

```ini
[Unit]
Description=SmartMoney Alerts Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/smartmoney
ExecStart=/path/to/venv/bin/python main.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable smartmoney
sudo systemctl start smartmoney
sudo systemctl status smartmoney
```

## Troubleshooting

### "Twitter bot disabled or missing credentials"

**API Mode:**
- Check all 4 Twitter credentials are set in `.env`
- Ensure no quotes around values
- Verify API access level (need Elevated or higher)

**Browser Mode:**
- Run `python main.py --setup-twitter` to create session
- Check `.twitter_session/` directory exists
- Try deleting session and re-logging in

### "Discord bot token not configured"

- Check `DISCORD_BOT_TOKEN` is set
- Ensure bot is invited to server
- Check channel IDs are correct

### "No trades found"

- SEC RSS feed might be temporarily unavailable
- Check network connectivity
- Verify User-Agent is set (SEC blocks generic agents)

### Database Locked

- Only one process should access the database
- Kill any zombie processes: `pkill -f "python main.py"`

### Rate Limited

- Reduce posting frequency
- Increase delay between posts
- Check Twitter/SEC API usage dashboards

### Browser Mode Issues

- Delete `.twitter_session/` and re-login
- Check Playwright is installed: `playwright install chromium`
- Look at screenshots in `bots/screenshots/` for debugging
