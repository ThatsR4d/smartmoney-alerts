"""
Utility helpers for SmartMoneyAlerts.
"""

import re
from datetime import datetime, timedelta
from typing import Optional


def format_currency(value: float) -> str:
    """Format a dollar value for display."""
    if value >= 1_000_000_000:
        return f"${value/1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value/1_000:.0f}K"
    else:
        return f"${value:,.0f}"


def format_shares(shares: int) -> str:
    """Format share count for display."""
    if shares >= 1_000_000:
        return f"{shares/1_000_000:.1f}M"
    elif shares >= 1_000:
        return f"{shares/1_000:.1f}K"
    else:
        return f"{shares:,}"


def time_ago(date_str: str, format: str = '%Y-%m-%d') -> str:
    """Convert date string to relative time (e.g., '2 days ago')."""
    try:
        date = datetime.strptime(date_str, format)
        delta = datetime.now() - date

        if delta.days == 0:
            if delta.seconds < 3600:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
    except ValueError:
        return date_str


def clean_company_name(name: str) -> str:
    """Clean up company name for display."""
    if not name:
        return "Unknown"

    # Remove common suffixes
    suffixes = [
        ', INC.', ', INC', ' INC.', ' INC',
        ', CORP.', ', CORP', ' CORP.', ' CORP',
        ' CORPORATION', ', LLC', ' LLC',
        ', LTD.', ', LTD', ' LTD.',
        ' CO.', ', CO.', '/DE', '/DE/',
        ' COMMON STOCK', ' COM', ' CLASS A', ' CLASS B',
    ]

    name_upper = name.upper()
    for suffix in suffixes:
        if name_upper.endswith(suffix.upper()):
            name = name[:-len(suffix)]
            name_upper = name.upper()

    return name.strip()


def clean_insider_name(name: str) -> str:
    """Clean up insider name for display."""
    if not name:
        return "Unknown"

    # Remove extra whitespace
    name = ' '.join(name.split())

    # Handle "LASTNAME FIRSTNAME" format
    parts = name.split()
    if len(parts) >= 2:
        # Check if first part is all caps (likely last name first)
        if parts[0].isupper() and not parts[1].isupper():
            # Rearrange to "Firstname Lastname"
            name = ' '.join(parts[1:] + [parts[0].title()])

    # Title case
    name = name.title()

    return name


def extract_ticker_from_url(url: str) -> Optional[str]:
    """Try to extract ticker symbol from SEC URL."""
    if not url:
        return None

    # Look for patterns like "CIK=0001318605" and map to ticker
    # This would need a CIK->ticker mapping database
    return None


def is_valid_ticker(ticker: str) -> bool:
    """Check if a string looks like a valid ticker symbol."""
    if not ticker:
        return False

    # Basic validation: 1-5 uppercase letters, possibly with a period
    return bool(re.match(r'^[A-Z]{1,5}\.?[A-Z]{0,2}$', ticker.upper()))


def sanitize_for_tweet(text: str) -> str:
    """Sanitize text for Twitter posting."""
    if not text:
        return ""

    # Remove or replace problematic characters
    text = text.replace('\r', '')
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines

    # Ensure no line is too long (Twitter handles this, but for display)
    lines = text.split('\n')
    sanitized_lines = []
    for line in lines:
        if len(line) > 100:
            # Break long lines at spaces
            words = line.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > 100:
                    sanitized_lines.append(current_line.strip())
                    current_line = word
                else:
                    current_line += " " + word
            if current_line:
                sanitized_lines.append(current_line.strip())
        else:
            sanitized_lines.append(line)

    return '\n'.join(sanitized_lines).strip()


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats."""
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%m/%d/%Y',
        '%d-%m-%Y',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def get_market_hours_status() -> dict:
    """Check if US markets are currently open."""
    now = datetime.now()

    # Simple check (doesn't account for holidays)
    is_weekday = now.weekday() < 5
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    is_market_hours = is_weekday and market_open <= now <= market_close

    return {
        'is_open': is_market_hours,
        'is_weekday': is_weekday,
        'current_time': now.strftime('%H:%M:%S'),
        'market_open': '09:30',
        'market_close': '16:00',
    }


if __name__ == "__main__":
    # Test helpers
    print("Testing helpers...")

    print(f"\nformat_currency(1234567): {format_currency(1234567)}")
    print(f"format_currency(500000): {format_currency(500000)}")
    print(f"format_shares(1500000): {format_shares(1500000)}")

    print(f"\ntime_ago('2024-01-15'): {time_ago('2024-01-15')}")

    print(f"\nclean_company_name('APPLE INC.'): {clean_company_name('APPLE INC.')}")
    print(f"clean_insider_name('COOK TIMOTHY D'): {clean_insider_name('COOK TIMOTHY D')}")

    print(f"\nis_valid_ticker('AAPL'): {is_valid_ticker('AAPL')}")
    print(f"is_valid_ticker('BRK.B'): {is_valid_ticker('BRK.B')}")

    print(f"\nmarket_status: {get_market_hours_status()}")
