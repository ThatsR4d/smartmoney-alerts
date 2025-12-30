"""
Discord Bot for posting alerts to channels.
Supports free and premium tiers via role gating.
"""

import asyncio
import os
import sys
import logging
from typing import Optional, Dict, List

# Handle imports for both module and direct execution
try:
    from config.settings import (
        DISCORD_BOT_TOKEN,
        DISCORD_GUILD_ID,
        DISCORD_FREE_CHANNEL_ID,
        DISCORD_PREMIUM_CHANNEL_ID,
        DISCORD_ENABLED,
        DRY_RUN,
    )
    from core.formatter import discord_formatter
    from core.database import mark_trade_posted
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import (
        DISCORD_BOT_TOKEN,
        DISCORD_GUILD_ID,
        DISCORD_FREE_CHANNEL_ID,
        DISCORD_PREMIUM_CHANNEL_ID,
        DISCORD_ENABLED,
        DRY_RUN,
    )
    from core.formatter import discord_formatter
    from core.database import mark_trade_posted

# Try to import discord.py, handle if not installed
try:
    import discord
    from discord.ext import commands
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    discord = None
    commands = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartMoneyBot:
    """Discord bot for SmartMoney alerts (simplified version that doesn't require running an event loop)."""

    def __init__(self):
        self.enabled = DISCORD_ENABLED and DISCORD_AVAILABLE and bool(DISCORD_BOT_TOKEN)
        self.client = None
        self.free_channel = None
        self.premium_channel = None
        self._ready = False

        if not DISCORD_AVAILABLE:
            logger.warning("discord.py not installed. Run: pip install discord.py")
        elif not DISCORD_BOT_TOKEN:
            logger.warning("Discord bot token not configured")

    async def start(self):
        """Start the Discord bot."""
        if not self.enabled:
            logger.warning("Discord bot not enabled")
            return

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self.client.user}")
            self._ready = True

            # Get channel references
            if DISCORD_FREE_CHANNEL_ID:
                try:
                    self.free_channel = self.client.get_channel(int(DISCORD_FREE_CHANNEL_ID))
                    if self.free_channel:
                        logger.info(f"Free channel: #{self.free_channel.name}")
                except (ValueError, TypeError):
                    logger.warning("Invalid free channel ID")

            if DISCORD_PREMIUM_CHANNEL_ID:
                try:
                    self.premium_channel = self.client.get_channel(int(DISCORD_PREMIUM_CHANNEL_ID))
                    if self.premium_channel:
                        logger.info(f"Premium channel: #{self.premium_channel.name}")
                except (ValueError, TypeError):
                    logger.warning("Invalid premium channel ID")

        # Start the bot
        await self.client.start(DISCORD_BOT_TOKEN)

    async def post_alert(self, trade: Dict, tier: int = 2) -> bool:
        """
        Post an alert to appropriate channels.
        Tier 1-2: Both channels (premium first)
        Tier 3-4: Free channel only
        """
        if not self._ready or not self.client:
            logger.warning("Discord bot not ready")
            return False

        message = discord_formatter.format_insider_trade(trade)

        if DRY_RUN:
            logger.info(f"[DRY RUN] Would post to Discord:\n{message[:200]}...")
            return True

        posted = False

        # Post to premium channel first (no delay)
        if self.premium_channel and tier <= 2:
            try:
                await self.premium_channel.send(message)
                logger.info(f"Posted to premium channel #{self.premium_channel.name}")
                posted = True
            except Exception as e:
                logger.error(f"Error posting to premium channel: {e}")

        # Post to free channel
        if self.free_channel:
            try:
                await self.free_channel.send(message)
                logger.info(f"Posted to free channel #{self.free_channel.name}")
                posted = True
            except Exception as e:
                logger.error(f"Error posting to free channel: {e}")

        # Mark as posted in database
        if posted and trade.get('id'):
            mark_trade_posted(trade['id'], 'discord')

        return posted

    async def post_message(self, message: str, channel_type: str = 'free') -> bool:
        """Post a message to specified channel type."""
        if not self._ready or not self.client:
            logger.warning("Discord bot not ready")
            return False

        if DRY_RUN:
            logger.info(f"[DRY RUN] Would post to {channel_type} channel:\n{message[:200]}...")
            return True

        channel = self.premium_channel if channel_type == 'premium' else self.free_channel

        if not channel:
            logger.warning(f"Channel {channel_type} not available")
            return False

        try:
            await channel.send(message)
            logger.info(f"Posted to {channel_type} channel")
            return True
        except Exception as e:
            logger.error(f"Error posting to {channel_type} channel: {e}")
            return False

    def is_ready(self) -> bool:
        """Check if bot is ready."""
        return self._ready

    async def close(self):
        """Close the bot connection."""
        if self.client:
            await self.client.close()


# Simple synchronous wrapper for use without running full event loop
class DiscordPoster:
    """Simple Discord poster that can be used synchronously via webhooks."""

    def __init__(self):
        self.enabled = DISCORD_ENABLED
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

        if not self.enabled:
            logger.warning("Discord posting disabled")

    def post_via_webhook(self, message: str) -> bool:
        """Post message via Discord webhook (simpler than full bot)."""
        if not self.webhook_url:
            logger.warning("No Discord webhook URL configured")
            return False

        if DRY_RUN:
            logger.info(f"[DRY RUN] Would post via webhook:\n{message[:200]}...")
            return True

        try:
            import requests
            response = requests.post(
                self.webhook_url,
                json={"content": message},
                timeout=10
            )
            response.raise_for_status()
            logger.info("Posted via Discord webhook")
            return True
        except Exception as e:
            logger.error(f"Error posting via webhook: {e}")
            return False

    def post_trade(self, trade: Dict) -> bool:
        """Post a trade alert via webhook."""
        message = discord_formatter.format_insider_trade(trade)
        return self.post_via_webhook(message)


# Global instances
discord_bot = SmartMoneyBot()
discord_poster = DiscordPoster()


async def post_to_discord(trade: Dict, tier: int = 2):
    """Post to Discord - uses bot if available, falls back to webhook."""
    if discord_bot.is_ready():
        return await discord_bot.post_alert(trade, tier)
    else:
        # Use webhook as fallback
        return discord_poster.post_trade(trade)


def post_to_discord_sync(trade: Dict) -> bool:
    """Synchronous version using webhook."""
    return discord_poster.post_trade(trade)


if __name__ == "__main__":
    print("Discord Bot Status:")
    print("-" * 40)
    print(f"  Discord.py available: {DISCORD_AVAILABLE}")
    print(f"  Bot enabled: {discord_bot.enabled}")
    print(f"  Token configured: {bool(DISCORD_BOT_TOKEN)}")
    print(f"  Dry run: {DRY_RUN}")

    # Test with webhook poster
    print("\nTesting Discord Poster (webhook mode):")
    sample_trade = {
        'ticker': 'TEST',
        'company_name': 'Test Company',
        'insider_name': 'John Doe',
        'insider_role': 'CEO',
        'transaction_type': 'P',
        'shares': 10000,
        'price_per_share': 50.00,
        'total_value': 500000,
        'transaction_date': '2024-01-15',
        'filing_date': '2024-01-16',
        'tier': 2,
        'virality_score': 55,
        'anomaly_texts': ['Test anomaly'],
    }

    # Show formatted message
    message = discord_formatter.format_insider_trade(sample_trade)
    print("\nFormatted message:")
    print(message)
