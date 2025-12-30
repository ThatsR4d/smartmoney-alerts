"""
Twitter/X Bot for posting alerts.
Handles authentication, posting, and rate limiting.
"""

import time
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

# Handle imports for both module and direct execution
try:
    from config.settings import (
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
        TWITTER_ENABLED,
        POST_TO_TWITTER,
        DRY_RUN,
        MAX_POSTS_PER_HOUR,
    )
    from core.formatter import tweet_formatter
    from core.database import mark_trade_posted
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import (
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET,
        TWITTER_ENABLED,
        POST_TO_TWITTER,
        DRY_RUN,
        MAX_POSTS_PER_HOUR,
    )
    from core.formatter import tweet_formatter
    from core.database import mark_trade_posted

# Try to import tweepy, handle if not installed
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    tweepy = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TwitterBot:
    """Bot for posting to Twitter/X."""

    def __init__(self):
        self.enabled = TWITTER_ENABLED and TWEEPY_AVAILABLE and all([
            TWITTER_API_KEY,
            TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN,
            TWITTER_ACCESS_SECRET,
        ])

        self.client = None
        self.posts_this_hour = 0
        self.hour_started = datetime.now()
        self.post_history: List[str] = []  # Track recent post IDs

        if not TWEEPY_AVAILABLE:
            logger.warning("Tweepy not installed. Run: pip install tweepy")
        elif self.enabled:
            self._authenticate()
        else:
            logger.warning("Twitter bot disabled or missing credentials")

    def _authenticate(self):
        """Authenticate with Twitter API v2."""
        try:
            self.client = tweepy.Client(
                consumer_key=TWITTER_API_KEY,
                consumer_secret=TWITTER_API_SECRET,
                access_token=TWITTER_ACCESS_TOKEN,
                access_token_secret=TWITTER_ACCESS_SECRET,
            )
            # Test the connection
            me = self.client.get_me()
            if me.data:
                logger.info(f"Twitter authentication successful. Logged in as @{me.data.username}")
            else:
                logger.info("Twitter authentication successful")
        except Exception as e:
            logger.error(f"Twitter authentication failed: {e}")
            self.enabled = False

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()

        # Reset counter every hour
        if (now - self.hour_started).total_seconds() >= 3600:
            self.posts_this_hour = 0
            self.hour_started = now

        return self.posts_this_hour < MAX_POSTS_PER_HOUR

    def post_trade(self, trade: Dict) -> Optional[str]:
        """
        Post a trade alert to Twitter.
        Returns tweet ID if successful, None otherwise.
        """
        if not self.enabled:
            logger.warning("Twitter bot not enabled")
            return None

        if not self._check_rate_limit():
            logger.warning("Rate limit reached, skipping post")
            return None

        # Format the tweet
        formatted = tweet_formatter.format_insider_trade(trade)
        text = formatted['text']

        if DRY_RUN:
            logger.info(f"[DRY RUN] Would post:\n{text}\n")
            return "dry_run_id"

        if not POST_TO_TWITTER:
            logger.info(f"[POSTING DISABLED] Formatted tweet:\n{text[:100]}...")
            return None

        try:
            response = self.client.create_tweet(text=text)
            tweet_id = str(response.data['id'])

            self.posts_this_hour += 1
            self.post_history.append(tweet_id)

            logger.info(f"Posted tweet {tweet_id}: {text[:50]}...")

            # Mark as posted in database
            if trade.get('id'):
                mark_trade_posted(trade['id'], 'twitter', tweet_id)

            return tweet_id

        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return None

    def post_text(self, text: str) -> Optional[str]:
        """Post arbitrary text to Twitter."""
        if not self.enabled:
            logger.warning("Twitter bot not enabled")
            return None

        if not self._check_rate_limit():
            logger.warning("Rate limit reached")
            return None

        if DRY_RUN:
            logger.info(f"[DRY RUN] Would post:\n{text}\n")
            return "dry_run_id"

        if not POST_TO_TWITTER:
            logger.info(f"[POSTING DISABLED] Would post: {text[:100]}...")
            return None

        try:
            response = self.client.create_tweet(text=text)
            tweet_id = str(response.data['id'])
            self.posts_this_hour += 1
            self.post_history.append(tweet_id)
            logger.info(f"Posted tweet {tweet_id}")
            return tweet_id
        except Exception as e:
            logger.error(f"Error posting: {e}")
            return None

    def post_thread(self, tweets: List[str]) -> List[str]:
        """Post a thread of tweets."""
        tweet_ids = []
        reply_to = None

        for i, text in enumerate(tweets):
            if DRY_RUN:
                logger.info(f"[DRY RUN] Thread tweet {i+1}/{len(tweets)}:\n{text}\n")
                tweet_ids.append(f"dry_run_id_{i}")
                continue

            if not POST_TO_TWITTER:
                logger.info(f"[POSTING DISABLED] Thread tweet {i+1}: {text[:50]}...")
                continue

            try:
                if reply_to:
                    response = self.client.create_tweet(
                        text=text,
                        in_reply_to_tweet_id=reply_to
                    )
                else:
                    response = self.client.create_tweet(text=text)

                tweet_id = str(response.data['id'])
                tweet_ids.append(tweet_id)
                reply_to = tweet_id
                self.posts_this_hour += 1

                # Small delay between thread tweets
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error posting thread tweet {i+1}: {e}")
                break

        return tweet_ids

    def get_status(self) -> Dict:
        """Get current bot status."""
        return {
            'enabled': self.enabled,
            'authenticated': self.client is not None,
            'posts_this_hour': self.posts_this_hour,
            'max_posts_per_hour': MAX_POSTS_PER_HOUR,
            'dry_run': DRY_RUN,
            'posting_enabled': POST_TO_TWITTER,
        }


# Singleton instance
twitter_bot = TwitterBot()


if __name__ == "__main__":
    print("Twitter Bot Status:")
    print("-" * 40)
    status = twitter_bot.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    if twitter_bot.enabled:
        # Test with a sample trade
        sample_trade = {
            'ticker': 'TEST',
            'company_name': 'Test Company',
            'insider_name': 'John Doe',
            'insider_role': 'CEO',
            'transaction_type': 'P',
            'shares': 10000,
            'total_value': 500000,
            'tier': 2,
            'virality_score': 55,
            'anomaly_texts': ['Test anomaly'],
        }

        print("\nTest posting (DRY_RUN mode)...")
        result = twitter_bot.post_trade(sample_trade)
        print(f"Result: {result}")
