"""
Congressional Stock Trading Scraper

Scrapes stock trades disclosed by members of Congress.
Sources:
- House Financial Disclosures
- Senate Financial Disclosures
- Capitol Trades API (aggregator)
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import sys

# Handle imports
try:
    from config.settings import SEC_USER_AGENT, MIN_TRANSACTION_VALUE
    from config.tickers import COMPANY_ALIASES, SP500, MEME_STOCKS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import SEC_USER_AGENT, MIN_TRANSACTION_VALUE
    from config.tickers import COMPANY_ALIASES, SP500, MEME_STOCKS


# Known politicians for higher virality
HIGH_PROFILE_POLITICIANS = {
    "pelosi": "Nancy Pelosi",
    "mcconnell": "Mitch McConnell",
    "schumer": "Chuck Schumer",
    "ocasio-cortez": "Alexandria Ocasio-Cortez",
    "aoc": "Alexandria Ocasio-Cortez",
    "warren": "Elizabeth Warren",
    "cruz": "Ted Cruz",
    "tuberville": "Tommy Tuberville",
    "kelly": "Mark Kelly",
    "ossoff": "Jon Ossoff",
}

# Amount ranges from disclosures
AMOUNT_RANGES = {
    "$1,001 - $15,000": (1001, 15000),
    "$15,001 - $50,000": (15001, 50000),
    "$50,001 - $100,000": (50001, 100000),
    "$100,001 - $250,000": (100001, 250000),
    "$250,001 - $500,000": (250001, 500000),
    "$500,001 - $1,000,000": (500001, 1000000),
    "$1,000,001 - $5,000,000": (1000001, 5000000),
    "$5,000,001 - $25,000,000": (5000001, 25000000),
    "$25,000,001 - $50,000,000": (25000001, 50000000),
    "Over $50,000,000": (50000001, 100000000),
}


class CongressScraper:
    """Scraper for Congressional stock trades."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': SEC_USER_AGENT,
            'Accept': 'application/json, text/html, */*',
        })

        # Capitol Trades API (free tier)
        self.capitol_trades_url = "https://bff.capitoltrades.com/trades"

        # House disclosures
        self.house_url = "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure"

    def scrape_recent_trades(self, max_trades: int = 100, days_back: int = 30) -> List[Dict]:
        """
        Scrape recent congressional trades.
        Tries multiple sources.
        """
        print(f"Scraping congressional trades (last {days_back} days)...")

        trades = []

        # Try Capitol Trades API first (most reliable)
        try:
            api_trades = self._scrape_capitol_trades(max_trades, days_back)
            trades.extend(api_trades)
        except Exception as e:
            print(f"Capitol Trades API error: {e}")

        # Deduplicate by creating unique key
        seen = set()
        unique_trades = []
        for trade in trades:
            key = f"{trade.get('politician_name')}_{trade.get('ticker')}_{trade.get('transaction_date')}"
            if key not in seen:
                seen.add(key)
                unique_trades.append(trade)

        print(f"Found {len(unique_trades)} unique congressional trades")
        return unique_trades

    def _scrape_capitol_trades(self, max_trades: int, days_back: int) -> List[Dict]:
        """Scrape from Capitol Trades API."""
        trades = []

        try:
            # API parameters
            params = {
                'page': 1,
                'pageSize': min(max_trades, 100),
                'sortBy': '-txDate',  # Most recent first
            }

            response = self.session.get(
                self.capitol_trades_url,
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                print(f"Capitol Trades API returned {response.status_code}")
                # Fall back to scraping their public page
                return self._scrape_capitol_trades_html()

            data = response.json()

            for item in data.get('data', []):
                trade = self._parse_capitol_trade(item)
                if trade:
                    trades.append(trade)

        except requests.exceptions.JSONDecodeError:
            # API might return HTML, try scraping
            return self._scrape_capitol_trades_html()
        except Exception as e:
            print(f"Error scraping Capitol Trades: {e}")

        return trades

    def _scrape_capitol_trades_html(self) -> List[Dict]:
        """Fallback: scrape Capitol Trades HTML page."""
        trades = []

        try:
            response = self.session.get(
                "https://www.capitoltrades.com/trades",
                timeout=30
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            # Find trade rows
            table = soup.find('table') or soup.find('div', class_='trades-table')
            if not table:
                print("Could not find trades table")
                return trades

            rows = table.find_all('tr')[1:]  # Skip header

            for row in rows[:50]:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue

                    trade = {
                        'source': 'capitol_trades',
                        'politician_name': cells[0].get_text(strip=True),
                        'ticker': cells[1].get_text(strip=True).upper(),
                        'transaction_type': 'purchase' if 'buy' in cells[2].get_text().lower() else 'sale',
                        'amount_range': cells[3].get_text(strip=True),
                        'transaction_date': cells[4].get_text(strip=True),
                    }

                    # Parse amount range
                    trade.update(self._parse_amount_range(trade['amount_range']))

                    # Add chamber/party if available
                    trade['politician_chamber'] = 'House' if 'rep.' in cells[0].get_text().lower() else 'Senate'

                    trades.append(trade)

                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error scraping Capitol Trades HTML: {e}")

        return trades

    def _parse_capitol_trade(self, item: Dict) -> Optional[Dict]:
        """Parse a trade from Capitol Trades API response."""
        try:
            politician = item.get('politician', {})
            asset = item.get('asset', {})

            # Get ticker
            ticker = asset.get('assetTicker', '')
            if not ticker:
                ticker = self._extract_ticker_from_name(asset.get('assetName', ''))

            # Parse transaction type
            tx_type = item.get('txType', '').lower()
            if 'purchase' in tx_type or 'buy' in tx_type:
                transaction_type = 'purchase'
            elif 'sale' in tx_type or 'sell' in tx_type:
                transaction_type = 'sale'
            else:
                transaction_type = tx_type

            # Parse dates
            tx_date = item.get('txDate', '')
            disclosure_date = item.get('filingDate', '')

            # Calculate days to disclose
            days_to_disclose = 0
            if tx_date and disclosure_date:
                try:
                    tx_dt = datetime.strptime(tx_date[:10], '%Y-%m-%d')
                    disc_dt = datetime.strptime(disclosure_date[:10], '%Y-%m-%d')
                    days_to_disclose = (disc_dt - tx_dt).days
                except:
                    pass

            # Parse amount
            amount_range = item.get('value', '$1,001 - $15,000')
            amount_low, amount_high = self._parse_amount_range(amount_range).values()

            trade = {
                'source': 'capitol_trades',
                'external_id': f"ct_{item.get('_txId', '')}",
                'politician_name': politician.get('name', 'Unknown'),
                'politician_party': politician.get('party', ''),
                'politician_state': politician.get('state', ''),
                'politician_chamber': politician.get('chamber', ''),
                'ticker': ticker.upper() if ticker else None,
                'company_name': asset.get('assetName', ''),
                'transaction_type': transaction_type,
                'transaction_date': tx_date[:10] if tx_date else None,
                'disclosure_date': disclosure_date[:10] if disclosure_date else None,
                'amount_range': amount_range,
                'amount_low': amount_low,
                'amount_high': amount_high,
                'asset_type': asset.get('assetType', 'Stock'),
                'days_to_disclose': days_to_disclose,
                'suspicious_timing': 1 if days_to_disclose > 45 else 0,
            }

            # Check if high-profile
            name_lower = trade['politician_name'].lower()
            for key in HIGH_PROFILE_POLITICIANS:
                if key in name_lower:
                    trade['is_high_profile'] = True
                    break

            return trade

        except Exception as e:
            print(f"Error parsing Capitol trade: {e}")
            return None

    def _parse_amount_range(self, amount_str: str) -> Dict:
        """Parse amount range string to low/high values."""
        for range_str, (low, high) in AMOUNT_RANGES.items():
            if range_str.lower() in amount_str.lower():
                return {'amount_low': low, 'amount_high': high}

        # Try to extract numbers
        numbers = re.findall(r'[\d,]+', amount_str.replace(',', ''))
        if len(numbers) >= 2:
            return {'amount_low': int(numbers[0]), 'amount_high': int(numbers[1])}
        elif len(numbers) == 1:
            val = int(numbers[0])
            return {'amount_low': val, 'amount_high': val}

        return {'amount_low': 1001, 'amount_high': 15000}  # Default minimum

    def _extract_ticker_from_name(self, name: str) -> Optional[str]:
        """Try to extract ticker from company name."""
        if not name:
            return None

        name_upper = name.upper()

        # Check aliases
        for alias, ticker in COMPANY_ALIASES.items():
            if alias in name_upper:
                return ticker

        # Look for ticker in parentheses: "Apple Inc (AAPL)"
        match = re.search(r'\(([A-Z]{1,5})\)', name)
        if match:
            return match.group(1)

        return None


class CongressAnalyzer:
    """Analyzer for congressional trades."""

    def analyze(self, trade: Dict) -> Dict:
        """Analyze a congressional trade for anomalies."""
        anomalies = []
        anomaly_texts = []

        # High-profile politician
        if trade.get('is_high_profile'):
            anomalies.append('high_profile_politician')
            anomaly_texts.append(f"{trade.get('politician_name')} is a high-profile member")

        # Large trade
        amount_high = trade.get('amount_high', 0)
        if amount_high >= 1000000:
            anomalies.append('million_plus_trade')
            anomaly_texts.append(f"${amount_high/1000000:.1f}M+ trade")
        elif amount_high >= 500000:
            anomalies.append('large_trade')
            anomaly_texts.append(f"$500K+ trade")

        # Late disclosure (> 45 days is a STOCK Act violation)
        days_to_disclose = trade.get('days_to_disclose', 0)
        if days_to_disclose > 45:
            anomalies.append('late_disclosure')
            anomaly_texts.append(f"Disclosed {days_to_disclose} days after trade (45-day limit)")
        elif days_to_disclose > 30:
            anomalies.append('slow_disclosure')
            anomaly_texts.append(f"Disclosed {days_to_disclose} days after trade")

        # Hot stock
        ticker = trade.get('ticker', '')
        if ticker in MEME_STOCKS:
            anomalies.append('meme_stock')
            anomaly_texts.append(f"Trading meme stock ${ticker}")

        # Purchase (more interesting than sales)
        if trade.get('transaction_type') == 'purchase':
            anomalies.append('purchase')

        trade['anomalies'] = json.dumps(anomalies)
        trade['anomaly_texts'] = anomaly_texts

        return trade


class CongressScorer:
    """Virality scorer for congressional trades."""

    def score(self, trade: Dict) -> int:
        """Calculate virality score (0-100)."""
        score = 0

        # Politician profile (max 25)
        if trade.get('is_high_profile'):
            score += 25
        else:
            score += 10

        # Chamber (Senators slightly more notable)
        if trade.get('politician_chamber', '').lower() == 'senate':
            score += 5

        # Transaction size (max 25)
        amount_high = trade.get('amount_high', 0)
        if amount_high >= 5000000:
            score += 25
        elif amount_high >= 1000000:
            score += 20
        elif amount_high >= 500000:
            score += 15
        elif amount_high >= 250000:
            score += 10
        elif amount_high >= 100000:
            score += 5

        # Stock recognition (max 20)
        ticker = trade.get('ticker', '')
        if ticker in MEME_STOCKS:
            score += 20
        elif ticker in SP500:
            score += 12
        elif ticker:
            score += 5

        # Anomalies (max 25)
        anomalies = trade.get('anomalies', '[]')
        if isinstance(anomalies, str):
            anomalies = json.loads(anomalies)

        if 'late_disclosure' in anomalies:
            score += 15
        if 'million_plus_trade' in anomalies:
            score += 10
        if 'purchase' in anomalies:
            score += 5

        # Transaction type bonus
        if trade.get('transaction_type') == 'purchase':
            score += 5

        return min(score, 100)


# Instances
congress_scraper = CongressScraper()
congress_analyzer = CongressAnalyzer()
congress_scorer = CongressScorer()


def scrape_congress_trades(max_trades: int = 100) -> List[Dict]:
    """Convenience function to scrape and analyze congressional trades."""
    trades = congress_scraper.scrape_recent_trades(max_trades)

    analyzed_trades = []
    for trade in trades:
        trade = congress_analyzer.analyze(trade)
        trade['virality_score'] = congress_scorer.score(trade)
        trade['tier'] = 1 if trade['virality_score'] >= 70 else 2 if trade['virality_score'] >= 50 else 3 if trade['virality_score'] >= 30 else 4
        analyzed_trades.append(trade)

    return analyzed_trades


if __name__ == "__main__":
    print("Testing Congress Scraper...")
    print("=" * 60)

    trades = scrape_congress_trades(max_trades=20)

    print(f"\nFound {len(trades)} trades")
    print("=" * 60)

    for trade in trades[:10]:
        print(f"\n{trade.get('politician_name')} ({trade.get('politician_party', '?')}-{trade.get('politician_state', '?')})")
        print(f"  ${trade.get('ticker', 'N/A')}: {trade.get('transaction_type')}")
        print(f"  Amount: {trade.get('amount_range')}")
        print(f"  Date: {trade.get('transaction_date')}")
        print(f"  Score: {trade.get('virality_score')}/100 (Tier {trade.get('tier')})")
        if trade.get('anomaly_texts'):
            print(f"  Anomalies: {', '.join(trade.get('anomaly_texts', []))}")
