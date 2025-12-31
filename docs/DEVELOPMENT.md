# Development Notes

Reference for maintaining and extending SmartMoneyAlerts.

## Quick Reference

### Run Commands

```bash
# Development
python main.py --once          # Single run
python main.py --scrape        # Scrape only
python main.py --post          # Post pending only
python main.py --status        # Show stats
python main.py --setup-twitter # Login to Twitter (browser mode)

# Production
python main.py --daemon        # Continuous
```

### Test Individual Components

```bash
python scrapers/sec_form4.py   # Test SEC scraper
python scrapers/congress.py    # Test Congress scraper
python scrapers/hedge_funds.py # Test 13F scraper
python core/database.py        # Test/init DB
python core/scorer.py          # Test scoring
python core/formatter.py       # Test tweet formatting
python bots/twitter_bot.py     # Test Twitter auth
python bots/discord_bot.py     # Test Discord formatting
```

## Code Patterns

### Adding a New Scraper

1. Create `scrapers/new_source.py`
2. Implement class with `scrape_recent_filings()` method
3. Return list of dicts with standard fields
4. Add database table in `core/database.py`
5. Add insert function in `core/database.py`
6. Add to `main.py` pipeline

Standard trade dict fields:
```python
{
    'accession_number': str,  # Unique ID
    'filing_date': str,       # YYYY-MM-DD
    'filing_url': str,
    'ticker': str,
    'company_name': str,
    'insider_name': str,
    'insider_role': str,
    'transaction_type': str,  # P, S, A, M
    'shares': int,
    'price_per_share': float,
    'total_value': float,
}
```

### Adding New Anomaly Detection

Edit `core/analyzer.py`:

```python
def analyze(self, trade: Dict) -> Dict:
    # Add new check
    if condition:
        anomalies.append('new_anomaly_type')
        anomaly_texts.append("Human readable description")
```

Update `core/scorer.py`:
```python
anomaly_scores = {
    # ...
    'new_anomaly_type': 7,  # Points value
}
```

### Adding New Tweet Templates

Edit `config/templates.py`:

```python
NEW_TEMPLATE = """
Alert text here

{ticker}: {value_display}

{anomaly_text}

{tags}
"""
```

Placeholders available:
- `{ticker}` - Stock symbol
- `{ticker_clean}` - Symbol without dots
- `{insider_role}` - CEO, Director, etc.
- `{insider_name}` - Person's name
- `{shares}` - Number (use `{shares:,}` for commas)
- `{value_display}` - Formatted ($1.5M)
- `{time_ago}` - "yesterday", "2 days ago"
- `{anomaly_text}` - First anomaly description
- `{insight_text}` - Random insight quote
- `{tags}` - @mentions

### Database Migrations

SQLite doesn't have built-in migrations. Pattern:

```python
def migrate_v2():
    conn = get_connection()
    cursor = conn.cursor()

    # Check if migration needed
    cursor.execute("PRAGMA table_info(insider_trades)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'new_column' not in columns:
        cursor.execute("ALTER TABLE insider_trades ADD COLUMN new_column TEXT")
        conn.commit()

    conn.close()
```

## SEC EDGAR Notes

### RSS Feed URL
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=only&count=100&output=atom
```

Parameters:
- `type=4` - Form 4 only
- `owner=only` - Insider filings only
- `count=100` - Results per page
- `output=atom` - RSS format

### 13F RSS Feed URL
```
https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=13F-HR&company=&dateb=&owner=include&count=100&output=atom
```

### XML Namespaces

SEC XML uses namespaces. Handle with:
```python
# Standard find
element.find('.//tagName')

# With wildcard namespace
element.find('.//{*}tagName')
```

### Transaction Codes

| Code | Meaning |
|------|---------|
| P | Open market purchase |
| S | Open market sale |
| A | Grant/award |
| M | Exercise of derivative |
| G | Gift |
| D | Disposition to issuer |
| F | Tax withholding |

We track `P` (purchases) and `S` (sales) by default.

### Rate Limits

SEC requires:
- Identify yourself via User-Agent
- Max 10 requests/second
- Be respectful during market hours

## Capitol Trades API Notes

### Endpoint
```
https://www.capitoltrades.com/trades?page=1&pageSize=50
```

### Fallback
If API returns 503, falls back to HTML scraping.

### Politicians Tracked
40+ high-profile members including:
- Nancy Pelosi, Mitch McConnell, Chuck Schumer
- AOC, Elizabeth Warren, Ted Cruz
- Dan Crenshaw, Mark Kelly, Tommy Tuberville
- And more...

## Twitter Notes

### Browser Mode (Recommended)

Browser automation using Playwright:
- Persistent session in `bots/.twitter_session/`
- Post history in `bots/post_history.json`
- Screenshots for debugging in `bots/screenshots/`

Safety settings:
```python
MIN_DELAY_BETWEEN_POSTS = 150  # seconds
MAX_DELAY_BETWEEN_POSTS = 300  # seconds
MAX_POSTS_PER_HOUR = 8
TYPING_DELAY = (50, 150)  # ms per character
```

### API Mode

v2 Endpoints Used:
- `POST /2/tweets` - Create tweet
- `GET /2/users/me` - Verify auth

Rate Limits (Free Tier):
- 50 tweets/24 hours (very limited)
- 1500 tweets/month

Rate Limits (Basic $100/mo):
- 100 tweets/24 hours
- 3000 tweets/month

### Thread Posting

```python
response1 = client.create_tweet(text="First tweet")
tweet_id = response1.data['id']

response2 = client.create_tweet(
    text="Reply",
    in_reply_to_tweet_id=tweet_id
)
```

## Discord Notes

### Bot vs Webhook

**Bot** (discord.py):
- Two-way interaction
- Role-based access
- Commands
- More complex

**Webhook**:
- One-way posting
- Simple HTTP POST
- No setup required
- Recommended for alerts

### Webhook Posting

```python
import requests

requests.post(
    webhook_url,
    json={"content": "Message here"}
)
```

### Embed Formatting

Discord supports rich embeds but we use plain markdown for simplicity.

## Common Issues & Fixes

### "XML Parse Error: mismatched tag"

SEC changed their XML format. The `xslF345X05` files are XSL-transformed and not valid XML.

**Fix**: Skip files with `xsl` in the path, look for actual XML files.

### Duplicate Trades

Same trade appears multiple times in RSS.

**Fix**: `INSERT OR IGNORE` with UNIQUE constraint on `accession_number`.

### Empty Ticker

Some filings don't include ticker symbol.

**Fix**: `_match_ticker()` function tries to match company name to known tickers.

### Large Values (Billions)

Some trades show unrealistic values.

**Analysis needed**: Could be stock awards valued at market cap, or data parsing issues.

### 13F Holdings XML Parse Errors

SEC 13F information tables sometimes have malformed XML.

**Current behavior**: Log error, continue with basic filing info without holdings detail.

### Capitol Trades 503 Errors

API occasionally unavailable.

**Fix**: Falls back to HTML scraping automatically.

## Performance Tuning

### Reduce API Calls

- Cache RSS feed (short TTL)
- Skip already-processed accession numbers early
- Batch database writes

### Reduce Memory

- Process trades one at a time
- Don't load full history for analysis

### Faster Startup

- Lazy-load Twitter/Discord clients
- Initialize DB once, reuse connection

## Monitoring

### Log Output

```bash
tail -f smartmoney.log
```

### Database Stats

```bash
python main.py --status
```

### Manual Database Query

```bash
sqlite3 data/smartmoney.db "SELECT * FROM insider_trades ORDER BY id DESC LIMIT 5;"
sqlite3 data/smartmoney.db "SELECT * FROM congress_trades ORDER BY id DESC LIMIT 5;"
sqlite3 data/smartmoney.db "SELECT * FROM hedge_fund_filings ORDER BY id DESC LIMIT 5;"
```

### Check Posting History

```bash
cat bots/post_history.json | python -m json.tool
```

## Deployment Checklist

- [ ] Set `DRY_RUN=false`
- [ ] Set `POST_TO_TWITTER=true`
- [ ] Verify all API keys (if using API mode)
- [ ] Run `--setup-twitter` (if using browser mode)
- [ ] Test with `--once` first
- [ ] Check rate limit settings
- [ ] Set up logging
- [ ] Configure restart on failure
- [ ] Monitor first 24 hours

## Database Tables Summary

| Table | Purpose | Unique Key |
|-------|---------|------------|
| `insider_trades` | SEC Form 4 filings | `accession_number` |
| `congress_trades` | House/Senate stock trades | `external_id` |
| `hedge_fund_filings` | 13F quarterly holdings | `accession_number` |
| `posting_queue` | Scheduled posts | `id` |
| `daily_stats` | Daily aggregates | `date` |

## Famous Hedge Funds Tracked

| Fund | Manager | CIK |
|------|---------|-----|
| Berkshire Hathaway | Warren Buffett | 1067983 |
| Scion Asset Management | Michael Burry | 1649339 |
| Pershing Square | Bill Ackman | 1336528 |
| Bridgewater Associates | Ray Dalio | 1350694 |
| Renaissance Technologies | Jim Simons | 1037389 |
| Citadel Advisors | Ken Griffin | 1423053 |
| Tiger Global | Chase Coleman | 1167483 |
| Third Point | Dan Loeb | 1040273 |
| Greenlight Capital | David Einhorn | 1079114 |
| Baupost Group | Seth Klarman | 1061768 |
| And more... | | |
