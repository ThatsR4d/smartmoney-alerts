# SmartMoneyAlerts Architecture

## Overview

SmartMoneyAlerts is a financial intelligence bot that scrapes SEC insider trading filings, congressional stock trades, and hedge fund 13F filings, analyzes them for viral potential, and automatically posts alerts to social media.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN SCHEDULER                           │
│                         (main.py)                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   scrape_    │  │   analyze_   │  │   post_      │          │
│  │   and_       │──▶│   trade()    │──▶│   alerts()   │          │
│  │   process()  │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    SCRAPERS     │  │      CORE       │  │      BOTS       │
│                 │  │                 │  │                 │
│  sec_form4.py   │  │  analyzer.py    │  │  twitter_bot.py │
│  congress.py    │  │  scorer.py      │  │  twitter_browser│
│  hedge_funds.py │  │  formatter.py   │  │  discord_bot.py │
└─────────────────┘  │  database.py    │  └─────────────────┘
         │           └─────────────────┘           │
         │                   │                     │
         ▼                   ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   SEC EDGAR     │  │     SQLite      │  │  Twitter/X      │
│   RSS Feed      │  │    Database     │  │  Discord        │
│   Capitol Trades│  │   (6 tables)    │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Data Flow

### 1. Scraping Phase
```
Data Sources → Parse XML/HTML/API → Extract Trade Data → Return Dict
```

**SEC Form 4 Scraper** (`scrapers/sec_form4.py`):
1. Fetches the SEC EDGAR RSS feed for recent Form 4 filings
2. Parses each filing's index page to find the XML document
3. Extracts structured data: issuer, owner, transaction details
4. Returns a list of trade dictionaries

**Congress Scraper** (`scrapers/congress.py`):
1. Fetches from Capitol Trades API (primary) or HTML scraping (fallback)
2. Extracts politician info, party, state, chamber
3. Parses transaction details and amount ranges
4. Returns congressional trade dictionaries

**Hedge Fund Scraper** (`scrapers/hedge_funds.py`):
1. Fetches SEC 13F-HR filings from EDGAR RSS feed
2. Parses holdings information table XML
3. Extracts top holdings and position data
4. Identifies famous funds (Buffett, Burry, etc.)

### 2. Analysis Phase
```
Trade Dict → Anomaly Detection → Virality Scoring → Enriched Dict
```

**Analyzer** detects patterns:
- CEO/Founder purchases
- Cluster buying (multiple insiders)
- First purchase in years
- Unusually large transactions
- Massive values ($10M+)

**Scorer** calculates 0-100 virality score based on:
- Insider role (25 pts max)
- Transaction size (25 pts max)
- Company recognition (20 pts max)
- Detected anomalies (25 pts max)

### 3. Storage Phase
```
Enriched Dict → SQLite Database → Unique Constraint Check
```

Trades are stored with:
- Filing metadata
- Company/insider info
- Transaction details
- Virality score & anomalies
- Posting status flags

### 4. Posting Phase
```
Unposted Trades → Format Message → Post to Platform → Update Status
```

**Tiered posting:**
- Tier 1 (70+): Immediate post with influencer tags
- Tier 2 (50-69): Post within cycle
- Tier 3 (30-49): Batch post
- Tier 4 (<30): Daily roundup only

## Module Responsibilities

### config/
| File | Purpose |
|------|---------|
| `settings.py` | Environment variables, API keys, thresholds, feature flags |
| `tickers.py` | Stock lists (S&P500, FAANG, meme stocks, Magnificent 7) |
| `influencers.py` | Twitter handles to tag by stock/topic |
| `templates.py` | Tweet templates for each tier and trade type |

### scrapers/
| File | Purpose |
|------|---------|
| `sec_form4.py` | SEC EDGAR Form 4 RSS scraper (insider trades) |
| `congress.py` | Capitol Trades congressional stock trades |
| `hedge_funds.py` | SEC 13F-HR filings (hedge fund holdings) |

### core/
| File | Purpose |
|------|---------|
| `database.py` | SQLite schema (6 tables), CRUD operations |
| `analyzer.py` | Anomaly detection logic |
| `scorer.py` | Virality scoring algorithm |
| `formatter.py` | Tweet/Discord message formatting |

### bots/
| File | Purpose |
|------|---------|
| `twitter_bot.py` | Twitter API v2 integration (Tweepy) |
| `twitter_browser.py` | Browser automation (Playwright) with stealth mode |
| `discord_bot.py` | Discord bot + webhook posting |

### utils/
| File | Purpose |
|------|---------|
| `helpers.py` | Formatting, parsing utilities |
| `rate_limiter.py` | Token bucket rate limiting |

## Database Schema

### insider_trades
Primary table for SEC Form 4 data.

```sql
CREATE TABLE insider_trades (
    id INTEGER PRIMARY KEY,
    accession_number TEXT UNIQUE,  -- SEC filing ID
    filing_date TEXT,
    filing_url TEXT,

    -- Company
    ticker TEXT,
    company_name TEXT,
    company_cik TEXT,

    -- Insider
    insider_name TEXT,
    insider_cik TEXT,
    insider_role TEXT,
    is_director INTEGER,
    is_officer INTEGER,
    is_ten_percent_owner INTEGER,
    officer_title TEXT,

    -- Transaction
    transaction_type TEXT,  -- P=Purchase, S=Sale, A=Award
    transaction_date TEXT,
    shares INTEGER,
    price_per_share REAL,
    total_value REAL,
    shares_owned_after INTEGER,

    -- Analysis
    virality_score INTEGER,
    anomalies TEXT,  -- JSON array

    -- Posting
    twitter_posted INTEGER,
    twitter_post_id TEXT,
    twitter_posted_at TEXT,
    discord_posted INTEGER,
    discord_posted_at TEXT,

    created_at TEXT,
    updated_at TEXT
);
```

### congress_trades
Congressional stock trade disclosures.

```sql
CREATE TABLE congress_trades (
    id INTEGER PRIMARY KEY,
    source TEXT,           -- 'capitol_trades', 'house', 'senate'
    external_id TEXT UNIQUE,

    -- Politician
    politician_name TEXT,
    politician_party TEXT,
    politician_state TEXT,
    politician_chamber TEXT,

    -- Trade
    ticker TEXT,
    company_name TEXT,
    transaction_type TEXT,  -- purchase, sale, exchange
    transaction_date TEXT,
    disclosure_date TEXT,
    amount_range TEXT,      -- "$1,001 - $15,000"
    amount_low INTEGER,
    amount_high INTEGER,
    asset_type TEXT,

    -- Analysis
    virality_score INTEGER,
    days_to_disclose INTEGER,
    suspicious_timing INTEGER,

    -- Posting
    twitter_posted INTEGER,
    twitter_post_id TEXT,
    discord_posted INTEGER,

    created_at TEXT
);
```

### hedge_fund_filings
13F quarterly holdings disclosures.

```sql
CREATE TABLE hedge_fund_filings (
    id INTEGER PRIMARY KEY,
    accession_number TEXT UNIQUE,
    filing_date TEXT,
    report_date TEXT,      -- Quarter end date

    -- Fund
    fund_name TEXT,
    fund_cik TEXT,
    manager_name TEXT,

    -- Positions (JSON)
    new_positions TEXT,
    increased_positions TEXT,
    decreased_positions TEXT,
    exited_positions TEXT,

    -- Summary
    total_value REAL,
    position_count INTEGER,
    virality_score INTEGER,

    -- Posting
    twitter_posted INTEGER,
    discord_posted INTEGER,

    created_at TEXT
);
```

### posting_queue
Queue for scheduled posts.

```sql
CREATE TABLE posting_queue (
    id INTEGER PRIMARY KEY,
    source_type TEXT,      -- 'insider', 'congress', 'hedge_fund'
    source_id INTEGER,
    platform TEXT,         -- 'twitter', 'discord'
    tier INTEGER,
    message_text TEXT,
    tags TEXT,             -- JSON array
    scheduled_for TEXT,
    posted_at TEXT,
    post_id TEXT,
    status TEXT,           -- 'pending', 'posted', 'failed'
    error_message TEXT,
    created_at TEXT
);
```

### daily_stats
Daily aggregate statistics.

```sql
CREATE TABLE daily_stats (
    id INTEGER PRIMARY KEY,
    date TEXT UNIQUE,
    insider_trades_scraped INTEGER,
    insider_trades_posted INTEGER,
    congress_trades_scraped INTEGER,
    congress_trades_posted INTEGER,
    hedge_fund_filings_scraped INTEGER,
    hedge_fund_filings_posted INTEGER,
    twitter_posts INTEGER,
    twitter_impressions INTEGER,
    twitter_engagements INTEGER,
    discord_messages INTEGER,
    new_discord_members INTEGER,
    created_at TEXT
);
```

### Indexes
```sql
CREATE INDEX idx_insider_ticker ON insider_trades(ticker);
CREATE INDEX idx_insider_date ON insider_trades(filing_date);
CREATE INDEX idx_insider_posted ON insider_trades(twitter_posted);
CREATE INDEX idx_insider_virality ON insider_trades(virality_score);
CREATE INDEX idx_queue_status ON posting_queue(status);
CREATE INDEX idx_congress_ticker ON congress_trades(ticker);
CREATE INDEX idx_congress_date ON congress_trades(transaction_date);
```

## Virality Scoring Algorithm

```python
def calculate_virality_score(trade):
    score = 0

    # Insider Role (0-25)
    if CEO/Founder: score += 25
    elif CFO: score += 22
    elif President: score += 18
    elif 10% Owner: score += 15
    elif Director: score += 8

    # Transaction Size (0-25)
    if value >= $50M: score += 25
    elif value >= $10M: score += 20
    elif value >= $1M: score += 11
    elif value >= $100K: score += 3

    # Company Recognition (0-20)
    if Magnificent 7: score += 20
    elif Meme Stock: score += 18
    elif SP500: score += 12

    # Anomalies (0-25)
    if ceo_founder_buy: score += 10
    if cluster_buy: score += 8
    if first_buy_in_years: score += 8
    if unusually_large: score += 7

    return min(score, 100)
```

## Rate Limiting

### SEC EDGAR
- Max 10 requests/second
- Implemented via sleep(0.15) between requests
- User-Agent header required

### Twitter Browser Mode
- 8 posts/hour max (conservative)
- 150-300 seconds random delay between posts
- Human-like typing delays (50-150ms per character)
- Post history tracking to prevent duplicates

### Twitter API Mode
- ~50 tweets per 24 hours (free tier)
- Tracked via posts_this_hour counter

### Discord
- 30 messages per minute
- Managed by discord.py library

## Error Handling

1. **Network Errors**: Retry with exponential backoff
2. **Parse Errors**: Log and skip, continue with next filing
3. **API Errors**: Log, mark as failed, retry later
4. **Duplicate Detection**: SQLite UNIQUE constraint on accession_number/external_id
5. **Rate Limits**: Token bucket algorithm, graceful degradation

## Twitter Posting Modes

### Browser Mode (Recommended)
- Uses Playwright with persistent Chromium session
- Stealth mode for human-like behavior
- No API costs or developer account needed
- Session stored in `.twitter_session/` directory
- Post history in `post_history.json`

### API Mode
- Uses Tweepy library with Twitter API v2
- Requires developer account and API keys
- Subject to API rate limits and costs
- Better for high-volume, verified accounts
