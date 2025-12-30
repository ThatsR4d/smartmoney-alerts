"""
Formats trades into tweets and Discord messages.
Handles template selection, tag insertion, and character limits.
"""

import random
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

# Handle imports for both module and direct execution
try:
    from config.templates import (
        INSIDER_TIER1_TEMPLATES,
        INSIDER_TIER2_TEMPLATES,
        INSIDER_TIER3_TEMPLATES,
        DAILY_ROUNDUP_TEMPLATE,
        CLUSTER_BUY_TEMPLATE,
        get_random_insight,
    )
    from config.influencers import get_tags_for_stock
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.templates import (
        INSIDER_TIER1_TEMPLATES,
        INSIDER_TIER2_TEMPLATES,
        INSIDER_TIER3_TEMPLATES,
        DAILY_ROUNDUP_TEMPLATE,
        CLUSTER_BUY_TEMPLATE,
        get_random_insight,
    )
    from config.influencers import get_tags_for_stock


class TweetFormatter:
    """Formats trades into Twitter-ready text."""

    MAX_TWEET_LENGTH = 280

    def format_insider_trade(self, trade: Dict) -> Dict:
        """
        Format an insider trade for Twitter.
        Returns dict with 'text', 'tags', 'tier'.
        """
        tier = trade.get('tier', 4)
        ticker = trade.get('ticker') or 'N/A'

        # Select template based on tier
        if tier == 1:
            template = random.choice(INSIDER_TIER1_TEMPLATES)
        elif tier == 2:
            template = random.choice(INSIDER_TIER2_TEMPLATES)
        else:
            template = random.choice(INSIDER_TIER3_TEMPLATES)

        # Prepare values
        value = trade.get('total_value', 0)
        value_display = self._format_value(value)

        shares = trade.get('shares', 0)

        # Time ago
        filing_date = trade.get('filing_date')
        time_ago = self._time_ago(filing_date) if filing_date else 'recently'

        # Anomaly text
        anomaly_texts = trade.get('anomaly_texts', [])
        anomaly_text = anomaly_texts[0] if anomaly_texts else ''

        # Additional anomaly text for multi-anomaly trades
        if len(anomaly_texts) > 1:
            anomaly_text += f"\n{anomaly_texts[1]}"

        # Insight text
        insight_text = get_random_insight() if tier <= 2 else ''

        # Tags
        tags = []
        if tier <= 2:
            tag_handles = get_tags_for_stock(ticker, max_tags=3 if tier == 1 else 2)
            tags = ['@' + h for h in tag_handles]
        tags_text = ' '.join(tags)

        # Clean ticker for hashtag (remove special chars)
        ticker_clean = ticker.replace('.', '').replace('-', '') if ticker else ''

        # Shorten insider name if too long
        insider_name = trade.get('insider_name', 'Unknown')
        if len(insider_name) > 25:
            parts = insider_name.split()
            if len(parts) >= 2:
                insider_name = f"{parts[0]} {parts[-1]}"

        # Format the template
        try:
            text = template.format(
                ticker=ticker,
                ticker_clean=ticker_clean,
                insider_role=trade.get('insider_role', 'Insider'),
                insider_name=insider_name,
                shares=shares,
                value_display=value_display,
                time_ago=time_ago,
                anomaly_text=anomaly_text,
                insight_text=insight_text,
                tags=tags_text,
            )
        except KeyError as e:
            # Fallback if template has missing keys
            text = f"🔔 ${ticker}: {trade.get('insider_role', 'Insider')} bought ${value_display}"

        # Clean up extra whitespace
        text = self._clean_whitespace(text)

        # Trim if too long
        text = self._trim_to_length(text)

        return {
            'text': text,
            'tags': tags,
            'tier': tier,
            'ticker': ticker,
        }

    def format_daily_roundup(self, trades: List[Dict]) -> Optional[str]:
        """Format a daily roundup tweet."""
        if not trades:
            return None

        # Sort by value descending
        sorted_trades = sorted(trades, key=lambda x: x.get('total_value', 0), reverse=True)[:10]

        # Build ranked list
        lines = []
        total_value = 0
        for i, trade in enumerate(sorted_trades, 1):
            ticker = trade.get('ticker', 'N/A')
            role = trade.get('insider_role', 'Insider')
            value = trade.get('total_value', 0)
            value_display = self._format_value(value)
            total_value += value

            lines.append(f"{i}. ${ticker} — {role} — ${value_display}")

        ranked_list = '\n'.join(lines)
        total_display = self._format_value(total_value)

        text = DAILY_ROUNDUP_TEMPLATE.format(
            ranked_list=ranked_list,
            total_value=total_display,
            link='discord.gg/smartmoney'  # Replace with actual link
        )

        return self._trim_to_length(text)

    def format_cluster_alert(self, ticker: str, trades: List[Dict]) -> Optional[str]:
        """Format a cluster buying alert."""
        if len(trades) < 3:
            return None

        # Build insider list
        insider_lines = []
        total_value = 0
        for trade in trades[:5]:  # Max 5 insiders listed
            role = trade.get('insider_role', 'Insider')
            value = trade.get('total_value', 0)
            value_display = self._format_value(value)
            total_value += value
            insider_lines.append(f"• {role}: ${value_display}")

        text = CLUSTER_BUY_TEMPLATE.format(
            ticker=ticker,
            count=len(trades),
            days=7,
            insider_list='\n'.join(insider_lines),
            total_value=self._format_value(total_value),
            tags=''  # Add tags as needed
        )

        return self._trim_to_length(text)

    def _format_value(self, value: float) -> str:
        """Format dollar value for display."""
        if value >= 1_000_000_000:
            return f"{value/1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value/1_000:.0f}K"
        else:
            return f"{value:,.0f}"

    def _time_ago(self, date_str: str) -> str:
        """Convert date string to 'X hours/days ago'."""
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            delta = datetime.now() - date

            if delta.days == 0:
                return "today"
            elif delta.days == 1:
                return "yesterday"
            elif delta.days < 7:
                return f"{delta.days} days ago"
            elif delta.days < 30:
                weeks = delta.days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            else:
                return date_str
        except ValueError:
            return "recently"

    def _clean_whitespace(self, text: str) -> str:
        """Clean up extra whitespace and empty lines."""
        # Remove multiple consecutive newlines
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove trailing whitespace on lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        # Remove leading/trailing whitespace
        return text.strip()

    def _trim_to_length(self, text: str, max_length: int = 280) -> str:
        """Trim text to max length, preserving whole words."""
        if len(text) <= max_length:
            return text

        # Find last space before limit
        trimmed = text[:max_length - 3]
        last_space = trimmed.rfind(' ')
        last_newline = trimmed.rfind('\n')

        # Cut at whichever is later (space or newline)
        cut_point = max(last_space, last_newline)

        if cut_point > max_length // 2:
            trimmed = trimmed[:cut_point]

        return trimmed + '...'


class DiscordFormatter:
    """Formats trades for Discord messages."""

    def format_insider_trade(self, trade: Dict, include_embed: bool = True) -> str:
        """Format an insider trade for Discord (can be longer than Twitter)."""
        ticker = trade.get('ticker') or 'N/A'
        value = trade.get('total_value', 0)
        transaction_type = trade.get('transaction_type', 'P')

        # Action text
        action = 'BUY' if transaction_type == 'P' else 'SELL' if transaction_type == 'S' else transaction_type

        # Format value
        if value >= 1_000_000:
            value_str = f"${value/1_000_000:.2f}M"
        else:
            value_str = f"${value:,.2f}"

        # Build message
        embed_text = f"""**🔔 INSIDER TRADE ALERT**

**Ticker:** ${ticker}
**Company:** {trade.get('company_name') or 'Unknown'}
**Insider:** {trade.get('insider_name') or 'Unknown'} ({trade.get('insider_role') or 'Insider'})
**Action:** {action}
**Shares:** {trade.get('shares', 0):,}
**Price:** ${trade.get('price_per_share', 0):,.2f}
**Total Value:** {value_str}
**Trade Date:** {trade.get('transaction_date') or 'N/A'}
**Filed:** {trade.get('filing_date') or 'N/A'}
"""

        # Add anomalies
        anomaly_texts = trade.get('anomaly_texts', [])
        if anomaly_texts:
            embed_text += "\n**Notable:**\n"
            for anomaly in anomaly_texts:
                embed_text += f"• {anomaly}\n"

        # Add score
        score = trade.get('virality_score', 0)
        tier = trade.get('tier', 4)
        embed_text += f"\n**Virality Score:** {score}/100 (Tier {tier})"

        # Add filing URL if available
        if trade.get('filing_url'):
            embed_text += f"\n\n📄 [View SEC Filing]({trade.get('filing_url')})"

        return embed_text.strip()

    def format_daily_summary(self, trades: List[Dict]) -> str:
        """Format a daily summary for Discord."""
        if not trades:
            return "No significant insider trades today."

        # Sort by value
        sorted_trades = sorted(trades, key=lambda x: x.get('total_value', 0), reverse=True)

        total_value = sum(t.get('total_value', 0) for t in sorted_trades)
        total_value_str = f"${total_value/1_000_000:.1f}M" if total_value >= 1_000_000 else f"${total_value:,.0f}"

        message = f"""**📊 Daily Insider Trading Summary**

**Total Insider Buying Today:** {total_value_str}
**Number of Trades:** {len(sorted_trades)}

**Top 10 Purchases:**
"""

        for i, trade in enumerate(sorted_trades[:10], 1):
            ticker = trade.get('ticker', 'N/A')
            role = trade.get('insider_role', 'Insider')
            value = trade.get('total_value', 0)
            if value >= 1_000_000:
                value_str = f"${value/1_000_000:.1f}M"
            else:
                value_str = f"${value/1_000:.0f}K"

            message += f"{i}. **${ticker}** — {role} — {value_str}\n"

        return message.strip()


# Singleton instances
tweet_formatter = TweetFormatter()
discord_formatter = DiscordFormatter()


if __name__ == "__main__":
    # Test the formatters
    sample_trade = {
        'ticker': 'TSLA',
        'company_name': 'Tesla, Inc.',
        'insider_name': 'Elon Musk',
        'insider_role': 'CEO',
        'transaction_type': 'P',
        'shares': 100000,
        'price_per_share': 250.00,
        'total_value': 25_000_000,
        'transaction_date': '2024-01-15',
        'filing_date': '2024-01-16',
        'filing_url': 'https://www.sec.gov/example',
        'tier': 1,
        'virality_score': 85,
        'anomaly_texts': ['CEO/Founder buying = maximum conviction signal', '$25M+ purchase'],
    }

    print("=" * 60)
    print("TWEET FORMAT (Tier 1)")
    print("=" * 60)
    result = tweet_formatter.format_insider_trade(sample_trade)
    print(result['text'])
    print(f"\nLength: {len(result['text'])} characters")
    print(f"Tags: {result['tags']}")

    print("\n" + "=" * 60)
    print("DISCORD FORMAT")
    print("=" * 60)
    discord_msg = discord_formatter.format_insider_trade(sample_trade)
    print(discord_msg)
