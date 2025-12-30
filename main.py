#!/usr/bin/env python3
"""
SmartMoneyAlerts - Main Entry Point

Runs the scraping, analysis, and posting pipeline.
"""

import argparse
import asyncio
import time
import sys
import os
from datetime import datetime
import logging

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import init_db, insert_insider_trade, get_unposted_trades, get_stats_summary
from scrapers.sec_form4 import SECForm4Scraper
from core.analyzer import analyze_trade
from core.scorer import score_and_tier, get_tier_description
from bots.twitter_bot import twitter_bot
from bots.discord_bot import discord_poster, post_to_discord_sync
from config.settings import SCRAPE_INTERVAL_MINUTES, DRY_RUN

# Try to import schedule
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Scrapers
form4_scraper = SECForm4Scraper()


def scrape_and_process() -> list:
    """Main scraping and processing job."""
    logger.info("=" * 50)
    logger.info(f"Starting scrape job at {datetime.now()}")

    # Scrape SEC Form 4
    trades = form4_scraper.scrape_recent_filings(max_filings=50)
    logger.info(f"Scraped {len(trades)} trades from SEC")

    new_trades = []
    for trade in trades:
        # Analyze for anomalies
        trade = analyze_trade(trade)

        # Calculate virality score
        trade = score_and_tier(trade)

        # Insert into database
        trade_id = insert_insider_trade(trade)

        if trade_id:
            trade['id'] = trade_id
            new_trades.append(trade)
            logger.info(
                f"New trade: ${trade.get('ticker', 'N/A')} - "
                f"{trade.get('insider_role', 'Unknown')} - "
                f"${trade.get('total_value', 0):,.0f} - "
                f"Score: {trade.get('virality_score', 0)}"
            )

    logger.info(f"Inserted {len(new_trades)} new trades")
    return new_trades


def post_alerts():
    """Post pending alerts to Twitter and Discord."""
    logger.info("Checking for trades to post...")

    # Get unposted trades, sorted by virality
    unposted = get_unposted_trades('twitter', limit=20)
    logger.info(f"Found {len(unposted)} unposted trades")

    posted_count = 0

    for trade in unposted:
        tier = trade.get('tier', 4)
        score = trade.get('virality_score', 0)

        # Only auto-post tier 1-2 trades
        if tier <= 2:
            logger.info(
                f"Posting tier {tier} trade: ${trade.get('ticker', 'N/A')} "
                f"(score: {score}) - {get_tier_description(tier)}"
            )

            # Post to Twitter
            tweet_id = twitter_bot.post_trade(trade)
            if tweet_id:
                posted_count += 1

            # Post to Discord (sync version)
            post_to_discord_sync(trade)

            # Rate limit: wait between posts
            time.sleep(30)

        elif tier == 3:
            # Tier 3: batch post less frequently
            logger.info(f"Tier 3 trade queued: ${trade.get('ticker', 'N/A')} (score: {score})")

    logger.info(f"Posted {posted_count} alerts")
    return posted_count


def run_full_pipeline():
    """Run complete pipeline: scrape → analyze → post."""
    logger.info("#" * 50)
    logger.info("Running full pipeline")
    logger.info("#" * 50)

    # Step 1: Scrape and process
    new_trades = scrape_and_process()

    # Step 2: Post alerts
    post_alerts()

    # Step 3: Show stats
    stats = get_stats_summary()
    logger.info("\nDatabase Stats:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("Pipeline complete")
    return new_trades


def run_scheduler():
    """Run scheduled jobs."""
    if not SCHEDULE_AVAILABLE:
        logger.error("'schedule' package not installed. Run: pip install schedule")
        logger.info("Falling back to simple loop...")
        run_simple_loop()
        return

    logger.info(f"Starting scheduler (interval: {SCRAPE_INTERVAL_MINUTES} minutes)")

    # Schedule scraping job
    schedule.every(SCRAPE_INTERVAL_MINUTES).minutes.do(run_full_pipeline)

    # Run immediately on start
    run_full_pipeline()

    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)


def run_simple_loop():
    """Simple loop without schedule package."""
    logger.info(f"Starting simple loop (interval: {SCRAPE_INTERVAL_MINUTES} minutes)")

    while True:
        run_full_pipeline()
        logger.info(f"Sleeping for {SCRAPE_INTERVAL_MINUTES} minutes...")
        time.sleep(SCRAPE_INTERVAL_MINUTES * 60)


def show_status():
    """Show current system status."""
    print("\n" + "=" * 60)
    print("SMARTMONEY ALERTS - SYSTEM STATUS")
    print("=" * 60)

    # Database stats
    print("\n📊 Database Statistics:")
    try:
        stats = get_stats_summary()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"  Error reading database: {e}")

    # Twitter status
    print("\n🐦 Twitter Bot:")
    twitter_status = twitter_bot.get_status()
    for key, value in twitter_status.items():
        print(f"  {key}: {value}")

    # Configuration
    print("\n⚙️ Configuration:")
    print(f"  Scrape interval: {SCRAPE_INTERVAL_MINUTES} minutes")
    print(f"  Dry run: {DRY_RUN}")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SmartMoneyAlerts Bot - Track and share insider trading activity"
    )
    parser.add_argument('--scrape', action='store_true', help='Run scraper only')
    parser.add_argument('--post', action='store_true', help='Post pending alerts only')
    parser.add_argument('--once', action='store_true', help='Run full pipeline once')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (scheduled)')
    parser.add_argument('--init-db', action='store_true', help='Initialize database only')
    parser.add_argument('--status', action='store_true', help='Show system status')

    args = parser.parse_args()

    # Initialize database (always ensure it exists)
    init_db()

    if args.status:
        show_status()
    elif args.init_db:
        print("Database initialized successfully.")
    elif args.scrape:
        scrape_and_process()
    elif args.post:
        post_alerts()
    elif args.once:
        run_full_pipeline()
    elif args.daemon:
        run_scheduler()
    else:
        # Default: show help
        parser.print_help()
        print("\nExamples:")
        print("  python main.py --once      # Run full pipeline once")
        print("  python main.py --daemon    # Run continuously")
        print("  python main.py --scrape    # Scrape only (no posting)")
        print("  python main.py --post      # Post pending alerts")
        print("  python main.py --status    # Show system status")


if __name__ == "__main__":
    main()
