# Deployment Guide

## Deployment Options

### Option 1: Railway (Recommended)

Railway offers easy deployment with free tier.

#### Setup

1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Add environment variables from `.env`
5. Set start command: `python main.py --daemon`

#### Environment Variables

Add in Railway dashboard:
```
TWITTER_MODE=browser
DISCORD_BOT_TOKEN=xxx
DISCORD_WEBHOOK_URL=xxx
DRY_RUN=false
POST_TO_TWITTER=true
```

Note: Browser mode requires setting up Twitter session locally first, then including the `.twitter_session/` directory in the deployment.

#### Costs

- Free tier: 500 hours/month
- Hobby: $5/month (enough for 24/7)

---

### Option 2: Render

#### Setup

1. Push to GitHub
2. Go to [render.com](https://render.com)
3. New → Background Worker
4. Connect GitHub repo
5. Configure:
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt && playwright install chromium --with-deps`
   - Start Command: `python main.py --daemon`
6. Add environment variables

#### Costs

- Free tier: Spins down after inactivity (not ideal)
- Starter: $7/month

---

### Option 3: Fly.io

#### Setup

1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Create app: `fly launch`
4. Deploy: `fly deploy`

#### fly.toml

```toml
app = "smartmoney-alerts"
primary_region = "ord"

[build]
  builder = "paketobuildpacks/builder:base"

[env]
  DRY_RUN = "false"
  POST_TO_TWITTER = "true"
  TWITTER_MODE = "browser"

[processes]
  app = "python main.py --daemon"
```

Set secrets:
```bash
fly secrets set DISCORD_BOT_TOKEN=xxx DISCORD_WEBHOOK_URL=xxx
```

---

### Option 4: VPS (DigitalOcean/Linode)

#### Setup

```bash
# SSH to server
ssh user@your-server

# Clone repo
git clone https://github.com/ThatsR4d/smartmoney-alerts.git
cd smartmoney-alerts

# Setup Python
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Create venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps

# Configure
cp .env.example .env
nano .env  # Add your keys

# Setup Twitter (browser mode)
python main.py --setup-twitter

# Test
python main.py --once

# Run with systemd (see below)
```

#### Systemd Service

Create `/etc/systemd/system/smartmoney.service`:

```ini
[Unit]
Description=SmartMoney Alerts Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/smartmoney-alerts
Environment=PATH=/home/ubuntu/smartmoney-alerts/venv/bin
ExecStart=/home/ubuntu/smartmoney-alerts/venv/bin/python main.py --daemon
Restart=always
RestartSec=10
StandardOutput=append:/var/log/smartmoney/output.log
StandardError=append:/var/log/smartmoney/error.log

[Install]
WantedBy=multi-user.target
```

Setup:
```bash
sudo mkdir -p /var/log/smartmoney
sudo chown ubuntu:ubuntu /var/log/smartmoney
sudo systemctl daemon-reload
sudo systemctl enable smartmoney
sudo systemctl start smartmoney
```

Commands:
```bash
sudo systemctl status smartmoney   # Check status
sudo systemctl restart smartmoney  # Restart
sudo journalctl -u smartmoney -f   # View logs
```

---

### Option 5: Docker

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data

# Run
CMD ["python", "main.py", "--daemon"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  smartmoney:
    build: .
    restart: always
    environment:
      - TWITTER_MODE=browser
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN}
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - DRY_RUN=false
      - POST_TO_TWITTER=true
    volumes:
      - ./data:/app/data
      - ./bots/.twitter_session:/app/bots/.twitter_session
      - ./bots/post_history.json:/app/bots/post_history.json
```

Commands:
```bash
docker-compose up -d           # Start
docker-compose logs -f         # View logs
docker-compose down            # Stop
docker-compose up -d --build   # Rebuild and start
```

---

## Production Checklist

### Before Deployment

- [ ] All tests pass locally
- [ ] `.env` has production values
- [ ] `DRY_RUN=false`
- [ ] `POST_TO_TWITTER=true`
- [ ] Database initialized
- [ ] Twitter session created (browser mode)
- [ ] API rate limits configured appropriately

### After Deployment

- [ ] Verify bot is posting (check Twitter/Discord)
- [ ] Monitor logs for errors
- [ ] Check API usage dashboards
- [ ] Set up alerting for failures

---

## Monitoring

### Health Check Script

```python
#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

db_path = "data/smartmoney.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check last scrape
cursor.execute("""
    SELECT MAX(created_at) FROM insider_trades
""")
last_scrape = cursor.fetchone()[0]

if last_scrape:
    last_time = datetime.fromisoformat(last_scrape)
    age = datetime.now() - last_time

    if age > timedelta(hours=1):
        print(f"WARNING: No scrapes in {age}")
        exit(1)
    else:
        print(f"OK: Last scrape {age} ago")
else:
    print("WARNING: No trades in database")
    exit(1)
```

### Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake

Create a health endpoint or monitor the process.

---

## Browser Mode Considerations

### Session Persistence

Browser mode requires a logged-in Twitter session. For cloud deployments:

1. **Local setup first**: Run `python main.py --setup-twitter` locally
2. **Copy session**: Include `.twitter_session/` directory in deployment
3. **Mount as volume**: In Docker, mount the session directory

### Session Expiry

Twitter sessions may expire. If posting fails:
1. Delete `.twitter_session/` directory
2. Run setup again
3. Redeploy with new session

### Headless Mode

Browser runs in headless mode in production. For debugging:
```python
# In twitter_browser.py, temporarily set:
headless=False
```

---

## Scaling Considerations

### Current Limits

- Single process
- SQLite (file-based)
- ~10 req/sec to SEC

### If Scaling Needed

1. **Multiple Scrapers**: Run congress/13F scrapers as separate processes
2. **PostgreSQL**: Replace SQLite for concurrent access
3. **Redis Queue**: For job distribution
4. **Multiple Twitter Accounts**: Rotate to avoid rate limits

For now, single process is sufficient for 24/7 operation.

---

## Backup Strategy

### Database Backup

```bash
# Manual backup
cp data/smartmoney.db data/smartmoney.db.backup

# Automated daily backup
0 0 * * * cp /path/to/data/smartmoney.db /path/to/backups/smartmoney.db.$(date +\%Y\%m\%d)
```

### Session Backup

```bash
# Backup Twitter session
tar -czf twitter_session_backup.tar.gz bots/.twitter_session/
```
