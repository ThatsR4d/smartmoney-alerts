# SmartMoneyAlerts Architecture

## Overview

SmartMoneyAlerts is a financial intelligence bot that scrapes SEC insider trading filings, analyzes them for viral potential, and automatically posts alerts to social media.

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
│  (congress.py)  │  │  scorer.py      │  │  discord_bot.py │
│  (hedge_funds)  │  │  formatter.py   │  │                 │
└─────────────────┘  │  database.py    │  └─────────────────┘
         │           └─────────────────┘           │
         │                   │                     │
         ▼                   ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   SEC EDGAR     │  │     SQLite      │  │  Twitter API    │
│   RSS Feed      │  │    Database     │  │  Discord API    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Data Flow

### 1. Scraping Phase
```
SEC RSS Feed → Parse XML → Extract Trade Data → Return Dict
```

The SEC Form 4 scraper:
1. Fetches the SEC EDGAR RSS feed for recent Form 4 filings
2. Parses each filing's index page to find the XML document
3. Extracts structured data: issuer, owner, transaction details
4. Returns a list of trade dictionaries

### 2. Analysis Phase
```
Trade Dict → Anomaly Detection → Virality Scoring → Enriched Dict
```

**Analyzer** detects patterns:
- CEO/Founder purchases
- Cluster buying (multiple insiders)
- First purchase in years
- Unusually large transactions

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
| `settings.py` | Environment variables, API keys, thresholds |
| `tickers.py` | Stock lists (SP500, FAANG, meme stocks) |
| `influencers.py` | Twitter handles to tag by stock/topic |
| `templates.py` | Tweet templates for each tier |

### scrapers/
| File | Purpose |
|------|---------|
| `sec_form4.py` | SEC EDGAR Form 4 RSS scraper |
| `congress.py` | House/Senate trades (Phase 2) |
| `hedge_funds.py` | 13F filings (Phase 3) |

### core/
| File | Purpose |
|------|---------|
| `database.py` | SQLite schema, CRUD operations |
| `analyzer.py` | Anomaly detection logic |
| `scorer.py` | Virality scoring algorithm |
| `formatter.py` | Tweet/Discord message formatting |

### bots/
| File | Purpose |
|------|---------|
| `twitter_bot.py` | Twitter API v2 integration |
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
    transaction_type TEXT,  -- P=Purchase, S=Sale
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
    discord_posted INTEGER,

    created_at TEXT
);
```

### Indexes
```sql
CREATE INDEX idx_insider_ticker ON insider_trades(ticker);
CREATE INDEX idx_insider_date ON insider_trades(filing_date);
CREATE INDEX idx_insider_posted ON insider_trades(twitter_posted);
CREATE INDEX idx_insider_virality ON insider_trades(virality_score);
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

### Twitter API
- ~50 tweets per 15 minutes
- Tracked via posts_this_hour counter

### Discord
- 30 messages per minute
- Managed by discord.py library

## Error Handling

1. **Network Errors**: Retry with exponential backoff
2. **Parse Errors**: Log and skip, continue with next filing
3. **API Errors**: Log, mark as failed, retry later
4. **Duplicate Detection**: SQLite UNIQUE constraint on accession_number

## Future Phases

### Phase 2: Congressional Trading
- Data source: House/Senate financial disclosures
- Additional scoring: days to disclosure, committee membership
- New templates for politician trades

### Phase 3: Hedge Fund 13F
- Data source: SEC 13F filings
- Track: Buffett, Burry, Ackman, etc.
- Position changes quarter-over-quarter
