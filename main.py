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
from scrapers.congress import scrape_congress_trades
from scrapers.hedge_funds import scrape_hedge_fund_filings
from core.analyzer import analyze_trade
from core.scorer import score_and_tier, get_tier_description
from core.formatter import tweet_formatter
from bots.twitter_bot import twitter_bot
from bots.discord_bot import discord_poster, post_to_discord_sync
from config.settings import (
    SCRAPE_INTERVAL_MINUTES, DRY_RUN,
    MAX_FORM4_FILINGS, MAX_CONGRESS_TRADES, MAX_13F_FILINGS,
    TWITTER_MODE
)

# Browser automation for Twitter (when API not available)
if TWITTER_MODE == "browser":
    try:
        from bots.twitter_browser import post_tweet_sync, post_trade_sync
        BROWSER_BOT_AVAILABLE = True
    except ImportError:
        BROWSER_BOT_AVAILABLE = False
else:
    BROWSER_BOT_AVAILABLE = False


def post_to_twitter(text: str = None, trade: dict = None) -> str:
    """Post to Twitter using configured method (API or browser)."""
    if TWITTER_MODE == "browser" and BROWSER_BOT_AVAILABLE:
        if trade:
            return post_trade_sync(trade)
        elif text:
            return post_tweet_sync(text)
    else:
        # Fall back to API
        if trade:
            return twitter_bot.post_trade(trade)
        elif text:
            return twitter_bot.post_text(text)
    return None

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

# Feature flags for different trade types
SCRAPE_INSIDER_TRADES = True
SCRAPE_CONGRESS_TRADES = True
SCRAPE_HEDGE_FUNDS = True


def scrape_and_process() -> dict:
    """Main scraping and processing job."""
    logger.info("=" * 50)
    logger.info(f"Starting scrape job at {datetime.now()}")

    results = {
        'insider_trades': [],
        'congress_trades': [],
        'hedge_fund_filings': [],
    }

    # === SCRAPE SEC FORM 4 (Insider Trades) ===
    if SCRAPE_INSIDER_TRADES:
        logger.info("\n--- Scraping SEC Form 4 (Insider Trades) ---")
        trades = form4_scraper.scrape_recent_filings(max_filings=MAX_FORM4_FILINGS)
        logger.info(f"Scraped {len(trades)} insider trades from SEC")

        for trade in trades:
            trade = analyze_trade(trade)
            trade = score_and_tier(trade)
            trade_id = insert_insider_trade(trade)

            if trade_id:
                trade['id'] = trade_id
                trade['trade_type'] = 'insider'
                results['insider_trades'].append(trade)
                logger.info(
                    f"  Insider: ${trade.get('ticker', 'N/A')} - "
                    f"{trade.get('insider_role', 'Unknown')} - "
                    f"${trade.get('total_value', 0):,.0f} - "
                    f"Score: {trade.get('virality_score', 0)}"
                )

        logger.info(f"Inserted {len(results['insider_trades'])} new insider trades")

    # === SCRAPE CONGRESS TRADES ===
    if SCRAPE_CONGRESS_TRADES:
        logger.info("\n--- Scraping Congressional Trades ---")
        try:
            congress_trades = scrape_congress_trades(max_trades=MAX_CONGRESS_TRADES)
            logger.info(f"Scraped {len(congress_trades)} congressional trades")

            for trade in congress_trades:
                trade['trade_type'] = 'congress'
                results['congress_trades'].append(trade)

                if trade.get('virality_score', 0) >= 50:
                    logger.info(
                        f"  Congress: {trade.get('politician_name', 'Unknown')} - "
                        f"${trade.get('ticker', 'N/A')} - "
                        f"{trade.get('amount_range', '')} - "
                        f"Score: {trade.get('virality_score', 0)}"
                    )

            logger.info(f"Found {len(results['congress_trades'])} congressional trades")
        except Exception as e:
            logger.error(f"Error scraping congress trades: {e}")

    # === SCRAPE HEDGE FUND 13F FILINGS ===
    if SCRAPE_HEDGE_FUNDS:
        logger.info("\n--- Scraping Hedge Fund 13F Filings ---")
        try:
            filings = scrape_hedge_fund_filings(max_filings=MAX_13F_FILINGS)
            logger.info(f"Scraped {len(filings)} 13F filings")

            for filing in filings:
                filing['trade_type'] = '13f'
                results['hedge_fund_filings'].append(filing)

                if filing.get('is_famous') or filing.get('virality_score', 0) >= 50:
                    logger.info(
                        f"  13F: {filing.get('fund_name', 'Unknown')[:30]} - "
                        f"${filing.get('total_value', 0)/1e9:.1f}B - "
                        f"Score: {filing.get('virality_score', 0)}"
                    )

            logger.info(f"Found {len(results['hedge_fund_filings'])} 13F filings")
        except Exception as e:
            logger.error(f"Error scraping 13F filings: {e}")

    # Summary
    total = (len(results['insider_trades']) +
             len(results['congress_trades']) +
             len(results['hedge_fund_filings']))
    logger.info(f"\nTotal new items: {total}")

    return results


def post_all_alerts(results: dict):
    """Post alerts for all trade types."""
    posted_count = 0

    # Post insider trade alerts
    for trade in results.get('insider_trades', []):
        tier = trade.get('tier', 4)
        if tier <= 2:
            tweet_id = post_to_twitter(trade=trade)
            if tweet_id:
                posted_count += 1
            post_to_discord_sync(trade)
            time.sleep(30)

    # Post congress trade alerts
    for trade in results.get('congress_trades', []):
        tier = trade.get('tier', 4)
        if tier <= 2:
            formatted = tweet_formatter.format_congress_trade(trade)
            tweet_id = post_to_twitter(text=formatted['text'])
            if tweet_id:
                posted_count += 1
            time.sleep(30)

    # Post 13F filing alerts (famous funds only or high score)
    for filing in results.get('hedge_fund_filings', []):
        if filing.get('is_famous') or filing.get('virality_score', 0) >= 60:
            formatted = tweet_formatter.format_hedge_fund_filing(filing)
            tweet_id = post_to_twitter(text=formatted['text'])
            if tweet_id:
                posted_count += 1
            time.sleep(30)

    return posted_count


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

            # Post to Twitter (uses browser or API based on config)
            tweet_id = post_to_twitter(trade=trade)
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

    # Step 1: Scrape and process all sources
    results = scrape_and_process()

    # Step 2: Post alerts for new items
    posted = post_all_alerts(results)
    logger.info(f"Posted {posted} new alerts")

    # Step 3: Post any pending insider trade alerts from DB
    post_alerts()

    # Step 4: Show stats
    stats = get_stats_summary()
    logger.info("\nDatabase Stats:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    logger.info("Pipeline complete")
    return results


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
    print(f"  Mode: {TWITTER_MODE}")
    if TWITTER_MODE == "browser":
        if BROWSER_BOT_AVAILABLE:
            from bots.twitter_browser import twitter_browser
            browser_status = twitter_browser.get_status()
            for key, value in browser_status.items():
                print(f"  {key}: {value}")
        else:
            print("  Browser bot not available - run: python main.py --setup-twitter")
    else:
        twitter_status = twitter_bot.get_status()
        for key, value in twitter_status.items():
            print(f"  {key}: {value}")

    # Configuration
    print("\n⚙️ Configuration:")
    print(f"  Scrape interval: {SCRAPE_INTERVAL_MINUTES} minutes")
    print(f"  Twitter mode: {TWITTER_MODE}")
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
    parser.add_argument('--setup-twitter', action='store_true', help='Setup Twitter browser login')

    args = parser.parse_args()

    # Initialize database (always ensure it exists)
    init_db()

    if args.setup_twitter:
        # Run browser setup for Twitter
        import asyncio
        from bots.twitter_browser import setup_cli
        asyncio.run(setup_cli())
        return
    elif args.status:
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
        print("  python main.py --setup-twitter  # Login to Twitter (first time)")
        print("  python main.py --once           # Run full pipeline once")
        print("  python main.py --daemon         # Run continuously")
        print("  python main.py --scrape         # Scrape only (no posting)")
        print("  python main.py --post           # Post pending alerts")
        print("  python main.py --status         # Show system status")


if __name__ == "__main__":
    main()
