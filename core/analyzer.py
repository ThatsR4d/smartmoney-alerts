"""
Anomaly detection for insider trades.
Identifies unusual patterns that indicate newsworthy activity.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Handle imports for both module and direct execution
try:
    from core.database import get_recent_trades_for_ticker, get_insider_history
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.database import get_recent_trades_for_ticker, get_insider_history


class TradeAnalyzer:
    """Analyzes trades for anomalies and patterns."""

    def __init__(self):
        pass

    def analyze(self, trade: Dict) -> Dict:
        """
        Analyze a trade and return enriched data with anomalies.
        Returns the trade dict with added 'anomalies' list and 'anomaly_texts' list.
        """
        anomalies = []
        anomaly_texts = []

        ticker = trade.get('ticker')
        insider_cik = trade.get('insider_cik')
        insider_name = trade.get('insider_name', 'Unknown')
        insider_role = trade.get('insider_role', '').upper()
        officer_title = (trade.get('officer_title') or '').upper()
        total_value = trade.get('total_value', 0)

        # === CHECK: CEO/Founder Buy ===
        role_check = insider_role + ' ' + officer_title
        if any(role in role_check for role in ['CEO', 'FOUNDER', 'CHIEF EXECUTIVE']):
            anomalies.append('ceo_founder_buy')
            anomaly_texts.append("CEO/Founder buying = maximum conviction signal")

        # === CHECK: Cluster Buying ===
        if ticker:
            try:
                recent_trades = get_recent_trades_for_ticker(ticker, days=7)
                # Count unique insiders buying in last 7 days
                unique_buyers = set()
                for t in recent_trades:
                    if t.get('transaction_type') == 'P':
                        unique_buyers.add(t.get('insider_cik'))

                if len(unique_buyers) >= 3:
                    anomalies.append('cluster_buy')
                    anomaly_texts.append(f"{len(unique_buyers)} insiders have bought this week")
            except Exception:
                pass  # Database might not be initialized yet

        # === CHECK: First Buy / Historical Analysis ===
        if insider_cik and ticker:
            try:
                history = get_insider_history(insider_cik, ticker)
                purchases = [t for t in history if t.get('transaction_type') == 'P']

                if len(purchases) <= 1:
                    # This might be their first purchase at this company
                    anomalies.append('first_purchase')
                    anomaly_texts.append(f"First recorded purchase by this insider")
                elif len(purchases) >= 2:
                    # Check time since last purchase
                    last_purchase_date = purchases[1].get('filing_date')  # Index 0 is current
                    if last_purchase_date:
                        try:
                            last_date = datetime.strptime(last_purchase_date, '%Y-%m-%d')
                            days_since = (datetime.now() - last_date).days
                            if days_since > 365:
                                years = days_since // 365
                                anomalies.append('first_buy_in_years')
                                anomaly_texts.append(f"First buy in {years}+ year{'s' if years > 1 else ''}")
                        except ValueError:
                            pass
            except Exception:
                pass  # Database might not be initialized yet

        # === CHECK: Large Purchase (relative to history) ===
        if insider_cik and total_value > 0:
            try:
                history = get_insider_history(insider_cik)
                purchase_values = [
                    t.get('total_value', 0)
                    for t in history
                    if t.get('transaction_type') == 'P' and t.get('total_value')
                ]

                if len(purchase_values) > 1:
                    # Exclude current trade from average calculation
                    avg_value = sum(purchase_values[1:]) / len(purchase_values[1:])
                    if avg_value > 0 and total_value >= avg_value * 3:
                        multiple = int(total_value / avg_value)
                        anomalies.append('unusually_large')
                        anomaly_texts.append(f"This is {multiple}x their average purchase size")
            except Exception:
                pass

        # === CHECK: Massive Absolute Value ===
        if total_value >= 10_000_000:
            anomalies.append('massive_value')
            anomaly_texts.append(f"${total_value/1_000_000:.1f}M+ purchase")
        elif total_value >= 5_000_000:
            anomalies.append('large_value')
            anomaly_texts.append(f"${total_value/1_000_000:.1f}M purchase")
        elif total_value >= 1_000_000:
            anomalies.append('million_plus')
            anomaly_texts.append(f"$1M+ purchase")

        # === CHECK: Director Buy (still notable) ===
        if trade.get('is_director') and 'Director' in insider_role:
            if not any(a in anomalies for a in ['ceo_founder_buy']):
                anomalies.append('director_buy')
                # Don't add text for this, it's implicit in the role

        # === CHECK: 10% Owner Buy ===
        if trade.get('is_ten_percent_owner'):
            anomalies.append('major_shareholder_buy')
            anomaly_texts.append("Major shareholder (10%+ owner) buying more")

        # Add to trade dict
        trade['anomalies'] = json.dumps(anomalies)
        trade['anomaly_texts'] = anomaly_texts

        return trade


# Singleton instance
analyzer = TradeAnalyzer()


def analyze_trade(trade: Dict) -> Dict:
    """Convenience function to analyze a trade."""
    return analyzer.analyze(trade)


if __name__ == "__main__":
    # Test with sample data
    sample_trade = {
        'ticker': 'AAPL',
        'insider_name': 'Tim Cook',
        'insider_role': 'CEO',
        'insider_cik': '12345',
        'total_value': 5_000_000,
        'transaction_type': 'P',
        'is_officer': 1,
        'officer_title': 'Chief Executive Officer',
    }

    result = analyze_trade(sample_trade)
    print("Analyzed trade:")
    print(f"  Anomalies: {result.get('anomalies')}")
    print(f"  Anomaly texts: {result.get('anomaly_texts')}")
