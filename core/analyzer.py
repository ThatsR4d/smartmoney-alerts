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
        # High-conviction sectors (more catalyst potential)
        self.high_conviction_sectors = {
            'biotech', 'pharma', 'defense', 'semiconductor', 'ai', 'crypto', 'cannabis'
        }

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
        shares = trade.get('shares', 0)
        shares_owned_after = trade.get('shares_owned_after', 0)
        transaction_type = trade.get('transaction_type', 'P')
        is_purchase = transaction_type == 'P'
        is_sale = transaction_type == 'S'

        role_check = insider_role + ' ' + officer_title

        # ========================================
        # PURCHASE-SPECIFIC SIGNALS (Bullish)
        # ========================================
        if is_purchase:
            # === CEO/Founder Buy (strongest signal) ===
            if any(role in role_check for role in ['CEO', 'FOUNDER', 'CHIEF EXECUTIVE']):
                anomalies.append('ceo_founder_buy')
                anomaly_texts.append("CEO/Founder buying = maximum conviction signal")

            # === CFO Buy (knows the numbers) ===
            elif any(role in role_check for role in ['CFO', 'CHIEF FINANCIAL']):
                anomalies.append('cfo_buy')
                anomaly_texts.append("CFO buying = knows the financials inside out")

            # === Chairman Buy ===
            if 'CHAIRMAN' in role_check and 'VICE' not in role_check:
                anomalies.append('chairman_buy')
                anomaly_texts.append("Chairman buying shares")

            # === 10% Owner Buy ===
            if trade.get('is_ten_percent_owner'):
                anomalies.append('major_shareholder_buy')
                anomaly_texts.append("Major shareholder (10%+ owner) adding to position")

            # === Conviction Score: What % of position is this buy? ===
            if shares > 0 and shares_owned_after > 0:
                position_increase_pct = (shares / (shares_owned_after - shares)) * 100 if shares_owned_after > shares else 0
                if position_increase_pct >= 100:
                    anomalies.append('position_doubled')
                    anomaly_texts.append(f"Doubled their position or more (+{position_increase_pct:.0f}%)")
                elif position_increase_pct >= 50:
                    anomalies.append('major_position_increase')
                    anomaly_texts.append(f"Increased position by {position_increase_pct:.0f}%")
                elif position_increase_pct >= 25:
                    anomalies.append('significant_position_increase')
                    # No text for smaller increases

            # === First Purchase Ever ===
            if shares_owned_after > 0 and shares_owned_after == shares:
                anomalies.append('first_ever_purchase')
                anomaly_texts.append("First time owning shares in this company")

        # ========================================
        # SALE-SPECIFIC SIGNALS (Context matters)
        # ========================================
        if is_sale:
            # === C-Suite Selling (could be bearish or just diversification) ===
            if any(role in role_check for role in ['CEO', 'FOUNDER', 'CHIEF EXECUTIVE']):
                if total_value >= 10_000_000:
                    anomalies.append('ceo_large_sale')
                    anomaly_texts.append("CEO selling significant stake")
                else:
                    anomalies.append('ceo_sale')

            # === CFO Selling (they know the numbers - more concerning) ===
            elif any(role in role_check for role in ['CFO', 'CHIEF FINANCIAL']):
                anomalies.append('cfo_sale')
                anomaly_texts.append("CFO reducing position - watch closely")

            # === Major Shareholder Reducing Stake ===
            if trade.get('is_ten_percent_owner'):
                anomalies.append('major_shareholder_sale')
                anomaly_texts.append("10%+ owner reducing stake")

            # === Selling entire position ===
            if shares_owned_after == 0 and shares > 0:
                anomalies.append('complete_exit')
                anomaly_texts.append("Sold entire position - complete exit")
            elif shares_owned_after > 0 and shares > 0:
                sell_pct = (shares / (shares_owned_after + shares)) * 100
                if sell_pct >= 75:
                    anomalies.append('major_reduction')
                    anomaly_texts.append(f"Sold {sell_pct:.0f}% of holdings")
                elif sell_pct >= 50:
                    anomalies.append('significant_reduction')

        # ========================================
        # CLUSTER ACTIVITY (Multiple insiders)
        # ========================================
        if ticker:
            try:
                recent_trades = get_recent_trades_for_ticker(ticker, days=14)

                # Count unique buyers and sellers
                unique_buyers = set()
                unique_sellers = set()
                for t in recent_trades:
                    cik = t.get('insider_cik')
                    if t.get('transaction_type') == 'P':
                        unique_buyers.add(cik)
                    elif t.get('transaction_type') == 'S':
                        unique_sellers.add(cik)

                if is_purchase and len(unique_buyers) >= 3:
                    anomalies.append('cluster_buy')
                    anomaly_texts.append(f"{len(unique_buyers)} insiders buying in last 2 weeks")
                elif is_purchase and len(unique_buyers) >= 2:
                    anomalies.append('multiple_buyers')

                if is_sale and len(unique_sellers) >= 3:
                    anomalies.append('cluster_sell')
                    anomaly_texts.append(f"{len(unique_sellers)} insiders selling - potential red flag")

            except Exception:
                pass

        # ========================================
        # HISTORICAL ANALYSIS
        # ========================================
        if insider_cik and ticker:
            try:
                history = get_insider_history(insider_cik, ticker)
                purchases = [t for t in history if t.get('transaction_type') == 'P']
                sales = [t for t in history if t.get('transaction_type') == 'S']

                if is_purchase:
                    if len(purchases) <= 1:
                        anomalies.append('first_purchase')
                        anomaly_texts.append("First recorded purchase at this company")
                    elif len(purchases) >= 2:
                        last_date_str = purchases[1].get('filing_date')
                        if last_date_str:
                            try:
                                last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
                                days_since = (datetime.now() - last_date).days
                                if days_since > 730:  # 2+ years
                                    years = days_since // 365
                                    anomalies.append('first_buy_in_years')
                                    anomaly_texts.append(f"First buy in {years}+ years")
                                elif days_since > 365:
                                    anomalies.append('first_buy_in_year')
                                    anomaly_texts.append("First buy in over a year")
                            except ValueError:
                                pass

                    # Consecutive buying (high conviction)
                    if len(purchases) >= 3:
                        recent_purchases = purchases[:3]
                        dates = []
                        for p in recent_purchases:
                            try:
                                d = datetime.strptime(p.get('filing_date', ''), '%Y-%m-%d')
                                dates.append(d)
                            except ValueError:
                                pass
                        if len(dates) >= 3:
                            span = (dates[0] - dates[2]).days
                            if span <= 90:  # 3 buys in 90 days
                                anomalies.append('consecutive_buying')
                                anomaly_texts.append("3rd purchase in last 90 days - high conviction")

                # Was this person only selling before and now buying?
                if is_purchase and len(sales) > len(purchases):
                    anomalies.append('seller_turned_buyer')
                    anomaly_texts.append("Previously only sold, now buying")

            except Exception:
                pass

        # ========================================
        # SIZE-BASED SIGNALS
        # ========================================
        if is_purchase:
            if total_value >= 25_000_000:
                anomalies.append('massive_buy')
                anomaly_texts.append(f"${total_value/1_000_000:.0f}M+ purchase - huge conviction")
            elif total_value >= 10_000_000:
                anomalies.append('large_buy')
                anomaly_texts.append(f"${total_value/1_000_000:.1f}M purchase")
            elif total_value >= 5_000_000:
                anomalies.append('significant_buy')
                anomaly_texts.append(f"${total_value/1_000_000:.1f}M purchase")
            elif total_value >= 1_000_000:
                anomalies.append('million_plus_buy')
        elif is_sale:
            if total_value >= 50_000_000:
                anomalies.append('massive_sale')
                anomaly_texts.append(f"${total_value/1_000_000:.0f}M+ sale")
            elif total_value >= 10_000_000:
                anomalies.append('large_sale')

        # ========================================
        # RELATIVE SIZE (vs their history)
        # ========================================
        if insider_cik and total_value > 0:
            try:
                history = get_insider_history(insider_cik)
                if is_purchase:
                    past_values = [t.get('total_value', 0) for t in history
                                   if t.get('transaction_type') == 'P' and t.get('total_value')]
                else:
                    past_values = [t.get('total_value', 0) for t in history
                                   if t.get('transaction_type') == 'S' and t.get('total_value')]

                if len(past_values) > 1:
                    avg_value = sum(past_values[1:]) / len(past_values[1:])
                    if avg_value > 0:
                        multiple = total_value / avg_value
                        if multiple >= 5:
                            anomalies.append('unusually_large')
                            anomaly_texts.append(f"{multiple:.0f}x their average transaction")
                        elif multiple >= 3:
                            anomalies.append('larger_than_usual')
            except Exception:
                pass

        # ========================================
        # DIRECTOR-SPECIFIC
        # ========================================
        if trade.get('is_director') and is_purchase:
            if 'ceo_founder_buy' not in anomalies and 'cfo_buy' not in anomalies:
                anomalies.append('director_buy')

        # Add to trade dict
        trade['anomalies'] = json.dumps(anomalies)
        trade['anomaly_texts'] = anomaly_texts
        trade['is_bullish'] = is_purchase and len([a for a in anomalies if 'buy' in a or 'purchase' in a]) > 0
        trade['is_bearish'] = is_sale and len([a for a in anomalies if 'sale' in a or 'sell' in a or 'exit' in a or 'reduction' in a]) > 0

        return trade


# Singleton instance
analyzer = TradeAnalyzer()


def analyze_trade(trade: Dict) -> Dict:
    """Convenience function to analyze a trade."""
    return analyzer.analyze(trade)


if __name__ == "__main__":
    # Test with sample data
    test_trades = [
        {
            'ticker': 'AAPL',
            'insider_name': 'Tim Cook',
            'insider_role': 'CEO',
            'insider_cik': '12345',
            'total_value': 15_000_000,
            'shares': 50000,
            'shares_owned_after': 150000,
            'transaction_type': 'P',
            'is_officer': 1,
            'officer_title': 'Chief Executive Officer',
        },
        {
            'ticker': 'TSLA',
            'insider_name': 'CFO Person',
            'insider_role': 'CFO',
            'insider_cik': '67890',
            'total_value': 5_000_000,
            'shares': 10000,
            'shares_owned_after': 0,
            'transaction_type': 'S',
            'is_officer': 1,
            'officer_title': 'Chief Financial Officer',
        },
    ]

    print("Anomaly Detection Test Results")
    print("=" * 50)

    for trade in test_trades:
        result = analyze_trade(trade)
        tx_type = "BUY" if trade['transaction_type'] == 'P' else "SELL"
        print(f"\n{tx_type}: ${result.get('ticker')} - {result.get('insider_role')}")
        print(f"  Value: ${result.get('total_value', 0):,.0f}")
        print(f"  Anomalies: {result.get('anomalies')}")
        print(f"  Signals: {result.get('anomaly_texts')}")
        print(f"  Bullish: {result.get('is_bullish')} | Bearish: {result.get('is_bearish')}")
