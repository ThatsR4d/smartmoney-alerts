import os
from dotenv import load_dotenv

load_dotenv()

# === TWITTER API ===
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# === DISCORD ===
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DISCORD_FREE_CHANNEL_ID = os.getenv("DISCORD_FREE_CHANNEL_ID")
DISCORD_PREMIUM_CHANNEL_ID = os.getenv("DISCORD_PREMIUM_CHANNEL_ID")
DISCORD_PREMIUM_ROLE_ID = os.getenv("DISCORD_PREMIUM_ROLE_ID")

# === DATABASE ===
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/smartmoney.db")

# === FEATURE FLAGS ===
TWITTER_ENABLED = os.getenv("TWITTER_ENABLED", "true").lower() == "true"
DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "true").lower() == "true"
POST_TO_TWITTER = os.getenv("POST_TO_TWITTER", "true").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# === TWITTER MODE ===
# "api" = use Twitter API (requires API keys)
# "browser" = use browser automation (requires login setup)
TWITTER_MODE = os.getenv("TWITTER_MODE", "browser")

# === SEC EDGAR ===
SEC_FORM4_RSS = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&company=&dateb=&owner=only&count=100&output=atom"
SEC_BASE_URL = "https://www.sec.gov"
SEC_USER_AGENT = "SmartMoneyAlerts contact@smartmoneyalerts.com"  # SEC requires identification

# === SCRAPING SETTINGS ===
# Different intervals for different data sources (in minutes)
SCRAPE_INTERVAL_FORM4 = 10  # SEC Form 4 - most time-sensitive
SCRAPE_INTERVAL_CONGRESS = 60  # Congress trades - updated less frequently
SCRAPE_INTERVAL_13F = 240  # 13F filings - quarterly, check every 4 hours

# Legacy setting (used as fallback)
SCRAPE_INTERVAL_MINUTES = 10

MIN_TRANSACTION_VALUE = 10000  # Minimum $ to track (lowered for more coverage)
MAX_POSTS_PER_HOUR = 15  # Increased for more activity

# === SCRAPING LIMITS ===
MAX_FORM4_FILINGS = 100  # SEC RSS returns max 100
MAX_CONGRESS_TRADES = 200  # Get more congressional trades
MAX_13F_FILINGS = 100  # SEC RSS returns max 100

# === TRANSACTION FILTERS ===
TRACK_PURCHASES = True  # Track insider buys
TRACK_SALES = True  # Track insider sales (can indicate problems)
TRACK_AWARDS = False  # Stock awards (less meaningful)

# Maximum single transaction value to post (filter out institutional-level filings)
MAX_TRANSACTION_VALUE = 500_000_000  # $500M max - above this is likely institutional

# === VIRALITY THRESHOLDS ===
TIER1_SCORE = 70  # Post immediately with full promotion
TIER2_SCORE = 50  # Post within 1 hour
TIER3_SCORE = 30  # Batch post
# Below 30 = daily roundup only
