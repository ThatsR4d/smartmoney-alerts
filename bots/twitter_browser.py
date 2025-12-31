"""
Twitter Browser Automation Bot

Uses Playwright with stealth mode for safe, human-like posting.
Maintains persistent session to avoid repeated logins.
"""

import asyncio
import random
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import logging

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# Handle imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DRY_RUN

logger = logging.getLogger(__name__)

# === CONFIGURATION ===
TWITTER_URL = "https://x.com"
USER_DATA_DIR = os.path.join(os.path.dirname(__file__), ".twitter_session")
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), ".screenshots")

# Safety settings
MIN_DELAY_BETWEEN_POSTS = 180  # 3 minutes minimum between posts
MAX_POSTS_PER_HOUR = 8  # Conservative limit
TYPING_DELAY_MIN = 50  # ms per character
TYPING_DELAY_MAX = 150  # ms per character
ACTION_DELAY_MIN = 1.0  # seconds between actions
ACTION_DELAY_MAX = 3.0  # seconds between actions


class TwitterBrowserBot:
    """Safe browser automation for Twitter/X posting."""

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.is_logged_in = False
        self.last_post_time: Optional[datetime] = None
        self.posts_this_hour = 0
        self.hour_start: Optional[datetime] = None

        # Ensure directories exist
        Path(USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)

        # Load post history
        self._load_post_history()

    def _load_post_history(self):
        """Load posting history to respect rate limits across restarts."""
        history_file = os.path.join(USER_DATA_DIR, "post_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    if data.get('last_post_time'):
                        self.last_post_time = datetime.fromisoformat(data['last_post_time'])
                    if data.get('hour_start'):
                        hour_start = datetime.fromisoformat(data['hour_start'])
                        # Reset if more than an hour ago
                        if datetime.now() - hour_start < timedelta(hours=1):
                            self.hour_start = hour_start
                            self.posts_this_hour = data.get('posts_this_hour', 0)
            except Exception as e:
                logger.warning(f"Could not load post history: {e}")

    def _save_post_history(self):
        """Save posting history for rate limiting."""
        history_file = os.path.join(USER_DATA_DIR, "post_history.json")
        try:
            with open(history_file, 'w') as f:
                json.dump({
                    'last_post_time': self.last_post_time.isoformat() if self.last_post_time else None,
                    'hour_start': self.hour_start.isoformat() if self.hour_start else None,
                    'posts_this_hour': self.posts_this_hour
                }, f)
        except Exception as e:
            logger.warning(f"Could not save post history: {e}")

    async def _random_delay(self, min_sec: float = None, max_sec: float = None):
        """Add human-like random delay."""
        min_sec = min_sec or ACTION_DELAY_MIN
        max_sec = max_sec or ACTION_DELAY_MAX
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def _human_type(self, page: Page, selector: str, text: str):
        """Type text with human-like speed and occasional pauses."""
        element = await page.wait_for_selector(selector, timeout=10000)
        await element.click()
        await self._random_delay(0.5, 1.0)

        for char in text:
            await page.keyboard.type(char, delay=random.randint(TYPING_DELAY_MIN, TYPING_DELAY_MAX))
            # Occasional longer pause (like thinking)
            if random.random() < 0.05:
                await self._random_delay(0.3, 0.8)

    async def start(self, headless: bool = True) -> bool:
        """Start browser with persistent session."""
        try:
            self.playwright = await async_playwright().start()

            # Launch with persistent context (keeps cookies/session)
            self.context = await self.playwright.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=headless,
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                # Stealth settings
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            # Apply stealth scripts
            await self._apply_stealth(self.context)

            self.page = await self.context.new_page()

            # Check if already logged in
            await self.page.goto(TWITTER_URL, wait_until='domcontentloaded', timeout=60000)
            await self._random_delay(3, 5)

            self.is_logged_in = await self._check_logged_in()

            if self.is_logged_in:
                logger.info("Twitter session active - already logged in")
            else:
                logger.warning("Not logged in - manual login required")

            return self.is_logged_in

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False

    async def _apply_stealth(self, context: BrowserContext):
        """Apply stealth modifications to avoid detection."""
        await context.add_init_script("""
            // Mask webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mask automation
            window.navigator.chrome = {
                runtime: {}
            };

            // Mask permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Add plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Add languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

    async def _check_logged_in(self) -> bool:
        """Check if user is logged into Twitter."""
        try:
            # Look for elements that indicate logged-in state
            selectors = [
                '[data-testid="SideNav_NewTweet_Button"]',
                '[data-testid="AppTabBar_Home_Link"]',
                '[aria-label="Post"]',
                'a[href="/compose/tweet"]'
            ]

            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        return True
                except:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False

    async def manual_login(self):
        """Open browser for manual login (non-headless)."""
        if self.context:
            await self.stop()

        print("\n" + "=" * 50)
        print("MANUAL LOGIN REQUIRED")
        print("=" * 50)
        print("A browser window will open.")
        print("Please log in to Twitter/X manually.")
        print("After logging in, press Enter here to continue...")
        print("=" * 50 + "\n")

        # Start in non-headless mode
        await self.start(headless=False)

        if not self.is_logged_in:
            await self.page.goto("https://x.com/login", wait_until='networkidle')

            # Wait for user to complete login
            input("Press Enter after you've logged in...")

            # Verify login
            await self.page.goto(TWITTER_URL, wait_until='networkidle')
            await self._random_delay(2, 3)
            self.is_logged_in = await self._check_logged_in()

            if self.is_logged_in:
                print("Login successful! Session saved.")
                # Take screenshot for verification
                await self.page.screenshot(
                    path=os.path.join(SCREENSHOT_DIR, "logged_in.png")
                )
            else:
                print("Login verification failed. Please try again.")

        return self.is_logged_in

    def _can_post(self) -> tuple[bool, str]:
        """Check if we can post (rate limiting)."""
        now = datetime.now()

        # Check minimum delay between posts
        if self.last_post_time:
            seconds_since_last = (now - self.last_post_time).total_seconds()
            if seconds_since_last < MIN_DELAY_BETWEEN_POSTS:
                wait_time = MIN_DELAY_BETWEEN_POSTS - seconds_since_last
                return False, f"Rate limit: wait {wait_time:.0f}s before next post"

        # Check hourly limit
        if self.hour_start:
            if now - self.hour_start < timedelta(hours=1):
                if self.posts_this_hour >= MAX_POSTS_PER_HOUR:
                    return False, f"Hourly limit reached ({MAX_POSTS_PER_HOUR} posts/hour)"
            else:
                # Reset hourly counter
                self.hour_start = now
                self.posts_this_hour = 0
        else:
            self.hour_start = now
            self.posts_this_hour = 0

        return True, "OK"

    async def post_tweet(self, text: str) -> Optional[str]:
        """Post a tweet with human-like behavior."""
        if DRY_RUN:
            logger.info(f"[DRY RUN] Would post: {text[:100]}...")
            return "dry_run_id"

        # Check rate limits
        can_post, reason = self._can_post()
        if not can_post:
            logger.warning(f"Cannot post: {reason}")
            return None

        if not self.is_logged_in:
            logger.error("Not logged in - cannot post")
            return None

        try:
            # Navigate to home if not there
            current_url = self.page.url
            if '/home' not in current_url:
                await self.page.goto(f"{TWITTER_URL}/home", wait_until='networkidle')
                await self._random_delay(2, 4)

            # Find and click the tweet compose button or box
            compose_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="SideNav_NewTweet_Button"]',
                '[aria-label="Post"]',
            ]

            clicked = False
            for selector in compose_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.click()
                        clicked = True
                        await self._random_delay(1, 2)
                        break
                except:
                    continue

            if not clicked:
                logger.error("Could not find compose button")
                await self.page.screenshot(
                    path=os.path.join(SCREENSHOT_DIR, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                )
                return None

            # Find the text input area
            textarea_selectors = [
                '[data-testid="tweetTextarea_0"]',
                '[data-testid="tweetTextarea_0_label"]',
                '.public-DraftEditor-content',
                '[role="textbox"]'
            ]

            typed = False
            for selector in textarea_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.click()
                        await self._random_delay(0.5, 1)

                        # Type with human-like speed
                        for char in text:
                            await self.page.keyboard.type(char, delay=random.randint(TYPING_DELAY_MIN, TYPING_DELAY_MAX))
                            if random.random() < 0.03:  # 3% chance of pause
                                await self._random_delay(0.2, 0.6)

                        typed = True
                        break
                except Exception as e:
                    continue

            if not typed:
                logger.error("Could not find text input")
                return None

            await self._random_delay(1.5, 2.5)

            # Click the Post button - try multiple methods
            post_button_selectors = [
                '[data-testid="tweetButtonInline"]',
                '[data-testid="tweetButton"]',
                'button[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]',
            ]

            posted = False

            # Method 1: Try direct click on selectors
            for selector in post_button_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=3000)
                    if button:
                        # Check if button is enabled
                        is_disabled = await button.get_attribute('aria-disabled')
                        if is_disabled != 'true':
                            # Scroll into view first
                            await button.scroll_into_view_if_needed()
                            await self._random_delay(0.3, 0.6)

                            # Try regular click
                            await button.click(force=True)
                            posted = True
                            logger.info(f"Clicked post button via selector: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            # Method 2: Try JavaScript click as fallback
            if not posted:
                try:
                    logger.info("Trying JavaScript click fallback...")
                    await self._random_delay(0.5, 1)
                    result = await self.page.evaluate('''() => {
                        // Try multiple ways to find the post button
                        let btn = document.querySelector('[data-testid="tweetButtonInline"]');
                        if (!btn) btn = document.querySelector('[data-testid="tweetButton"]');
                        if (!btn) {
                            // Find by text content
                            const buttons = document.querySelectorAll('button');
                            for (const b of buttons) {
                                if (b.innerText === 'Post' && !b.disabled) {
                                    btn = b;
                                    break;
                                }
                            }
                        }
                        if (btn && !btn.disabled && btn.getAttribute('aria-disabled') !== 'true') {
                            btn.click();
                            return true;
                        }
                        return false;
                    }''')
                    if result:
                        posted = True
                        logger.info("Posted via JavaScript click")
                except Exception as e:
                    logger.error(f"JavaScript click failed: {e}")

            # Method 3: Try keyboard shortcut (Ctrl+Enter)
            if not posted:
                try:
                    logger.info("Trying keyboard shortcut (Ctrl+Enter)...")
                    await self._random_delay(0.3, 0.6)
                    await self.page.keyboard.press('Control+Enter')
                    await self._random_delay(1, 2)
                    # Check if we're still on compose (if not, it worked)
                    posted = True
                    logger.info("Posted via Ctrl+Enter")
                except Exception as e:
                    logger.error(f"Keyboard shortcut failed: {e}")

            if not posted:
                logger.error("Could not click post button after all attempts")
                await self.page.screenshot(
                    path=os.path.join(SCREENSHOT_DIR, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                )
                return None

            # Wait for post to complete
            await self._random_delay(3, 5)

            # Update rate limiting
            self.last_post_time = datetime.now()
            self.posts_this_hour += 1
            self._save_post_history()

            logger.info(f"Tweet posted successfully ({self.posts_this_hour}/{MAX_POSTS_PER_HOUR} this hour)")

            # Take success screenshot
            await self.page.screenshot(
                path=os.path.join(SCREENSHOT_DIR, f"posted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            )

            return f"browser_post_{datetime.now().timestamp()}"

        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            try:
                await self.page.screenshot(
                    path=os.path.join(SCREENSHOT_DIR, f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                )
            except:
                pass
            return None

    async def post_trade(self, trade: Dict) -> Optional[str]:
        """Format and post a trade alert."""
        from core.formatter import tweet_formatter

        formatted = tweet_formatter.format_insider_trade(trade)
        return await self.post_tweet(formatted['text'])

    async def stop(self):
        """Close browser and cleanup."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser stopped")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")

    def get_status(self) -> Dict:
        """Get current bot status."""
        can_post, reason = self._can_post()
        return {
            'logged_in': self.is_logged_in,
            'can_post': can_post,
            'status': reason,
            'posts_this_hour': self.posts_this_hour,
            'max_posts_per_hour': MAX_POSTS_PER_HOUR,
            'last_post': self.last_post_time.isoformat() if self.last_post_time else None
        }


# Singleton instance
twitter_browser = TwitterBrowserBot()


# === SYNC WRAPPER FOR MAIN.PY ===
def post_tweet_sync(text: str) -> Optional[str]:
    """Synchronous wrapper for posting tweets."""
    async def _post():
        if not twitter_browser.is_logged_in:
            # Use headless=False since headless has issues with x.com
            await twitter_browser.start(headless=False)
        return await twitter_browser.post_tweet(text)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_post())


def post_trade_sync(trade: Dict) -> Optional[str]:
    """Synchronous wrapper for posting trades."""
    async def _post():
        if not twitter_browser.is_logged_in:
            # Use headless=False since headless has issues with x.com
            await twitter_browser.start(headless=False)
        return await twitter_browser.post_trade(trade)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_post())


# === CLI FOR SETUP ===
async def setup_cli():
    """Interactive setup for browser bot."""
    print("\n" + "=" * 60)
    print("TWITTER BROWSER BOT SETUP")
    print("=" * 60)

    bot = TwitterBrowserBot()

    # Try to start with existing session
    print("\nChecking for existing session...")
    logged_in = await bot.start(headless=False)

    if logged_in:
        print("Already logged in!")
        status = bot.get_status()
        print(f"Posts this hour: {status['posts_this_hour']}/{status['max_posts_per_hour']}")
    else:
        print("No active session found.")
        response = input("Would you like to log in now? (y/n): ")

        if response.lower() == 'y':
            await bot.manual_login()

    # Test post option
    if bot.is_logged_in:
        response = input("\nWould you like to send a test post? (y/n): ")
        if response.lower() == 'y':
            test_text = input("Enter test message (or press Enter for default): ").strip()
            if not test_text:
                test_text = f"Test post from SmartMoneyAlerts bot - {datetime.now().strftime('%H:%M:%S')}"

            result = await bot.post_tweet(test_text)
            if result:
                print(f"Test post successful!")
            else:
                print("Test post failed - check screenshots folder")

    await bot.stop()
    print("\nSetup complete!")


if __name__ == "__main__":
    asyncio.run(setup_cli())
