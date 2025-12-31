"""
Virality scoring algorithm.
Determines how "viral" a trade is likely to be on social media.
Higher score = post immediately with full promotion.

SCORING PHILOSOPHY:
- Purchases (buys) are generally MORE interesting than sales
- CEO/Founder actions are the strongest signals
- Context matters: first purchase > routine purchase
- Cluster activity (multiple insiders) amplifies signal
- Sales need context: could be diversification or warning sign
"""

import json
import os
import sys
from typing import Dict

# Handle imports for both module and direct execution
try:
    from config.tickers import SP500, FAANG, MEME_STOCKS, MAGNIFICENT_7
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.tickers import SP500, FAANG, MEME_STOCKS, MAGNIFICENT_7


def calculate_virality_score(trade: Dict) -> int:
    """
    Calculate virality score (0-100) for a trade.

    Scoring breakdown:
    - Base transaction score: 0-30 (role + size)
    - Company recognition: 0-20
    - Anomaly signals: 0-40
    - Bonuses/penalties: -10 to +10
    """
    score = 0
    transaction_type = trade.get('transaction_type', 'P')
    is_purchase = transaction_type == 'P'
    is_sale = transaction_type == 'S'

    # === INSIDER ROLE (max 20 points) ===
    role = trade.get('insider_role', '').upper()
    officer_title = trade.get('officer_title', '').upper() if trade.get('officer_title') else ''
    role_check = role + ' ' + officer_title

    role_score = 0
    if 'CEO' in role_check or 'CHIEF EXECUTIVE' in role_check:
        role_score = 20
    elif 'FOUNDER' in role_check:
        role_score = 20
    elif 'CFO' in role_check or 'CHIEF FINANCIAL' in role_check:
        role_score = 18
    elif 'COO' in role_check or 'CHIEF OPERATING' in role_check:
        role_score = 16
    elif 'CHAIRMAN' in role_check and 'VICE' not in role_check:
        role_score = 16
    elif 'CTO' in role_check or 'CHIEF TECHNOLOGY' in role_check:
        role_score = 14
    elif 'PRESIDENT' in role_check:
        role_score = 14
    elif trade.get('is_ten_percent_owner'):
        role_score = 12
    elif 'VP' in role_check or 'VICE PRESIDENT' in role_check:
        role_score = 8
    elif 'GENERAL COUNSEL' in role_check:
        role_score = 8
    elif trade.get('is_director'):
        role_score = 6
    elif trade.get('is_officer'):
        role_score = 6
    else:
        role_score = 2

    # Sales by C-suite are less interesting unless very large
    if is_sale and role_score >= 14:
        role_score = int(role_score * 0.6)  # Reduce for sales

    score += role_score

    # === TRANSACTION SIZE (max 20 points) ===
    value = trade.get('total_value', 0)
    size_score = 0

    if is_purchase:
        # Purchases - reward conviction
        if value >= 50_000_000:
            size_score = 20
        elif value >= 25_000_000:
            size_score = 18
        elif value >= 10_000_000:
            size_score = 16
        elif value >= 5_000_000:
            size_score = 14
        elif value >= 2_000_000:
            size_score = 12
        elif value >= 1_000_000:
            size_score = 10
        elif value >= 500_000:
            size_score = 7
        elif value >= 250_000:
            size_score = 5
        elif value >= 100_000:
            size_score = 3
        else:
            size_score = 1
    else:
        # Sales - only very large ones are newsworthy
        if value >= 100_000_000:
            size_score = 18
        elif value >= 50_000_000:
            size_score = 15
        elif value >= 25_000_000:
            size_score = 12
        elif value >= 10_000_000:
            size_score = 8
        elif value >= 5_000_000:
            size_score = 5
        else:
            size_score = 2  # Small sales are routine

    score += size_score

    # === COMPANY RECOGNITION (max 20 points) ===
    ticker = trade.get('ticker', '').upper() if trade.get('ticker') else ''
    company_score = 0

    if ticker in MAGNIFICENT_7:
        company_score = 20
    elif ticker in MEME_STOCKS:
        company_score = 18  # High engagement potential
    elif ticker in FAANG:
        company_score = 16
    elif ticker in SP500:
        company_score = 10
    elif ticker:
        company_score = 4
    else:
        company_score = 0  # No ticker = not useful

    score += company_score

    # === ANOMALY SIGNALS (max 40 points) ===
    anomalies = trade.get('anomalies', '[]')
    if isinstance(anomalies, str):
        try:
            anomalies = json.loads(anomalies)
        except (json.JSONDecodeError, TypeError):
            anomalies = []

    # Purchase anomalies (bullish signals)
    buy_anomaly_scores = {
        # Highest conviction signals
        'ceo_founder_buy': 15,
        'cfo_buy': 12,
        'chairman_buy': 10,
        'position_doubled': 12,
        'first_ever_purchase': 10,
        'seller_turned_buyer': 10,
        'consecutive_buying': 10,

        # Strong signals
        'cluster_buy': 12,
        'first_buy_in_years': 10,
        'first_buy_in_year': 7,
        'major_shareholder_buy': 8,
        'first_purchase': 6,
        'multiple_buyers': 5,

        # Size signals
        'massive_buy': 10,
        'large_buy': 7,
        'significant_buy': 5,
        'million_plus_buy': 3,
        'unusually_large': 8,
        'larger_than_usual': 4,

        # Position change signals
        'major_position_increase': 6,
        'significant_position_increase': 3,

        # Basic signals
        'director_buy': 2,
    }

    # Sale anomalies (bearish/warning signals)
    sell_anomaly_scores = {
        # Strong warning signals
        'ceo_large_sale': 12,
        'cfo_sale': 10,
        'complete_exit': 12,
        'cluster_sell': 15,
        'major_shareholder_sale': 10,

        # Moderate signals
        'ceo_sale': 6,
        'major_reduction': 8,
        'significant_reduction': 4,
        'massive_sale': 8,
        'large_sale': 5,
    }

    # Calculate anomaly score
    anomaly_points = 0
    for a in anomalies:
        if is_purchase:
            anomaly_points += buy_anomaly_scores.get(a, 2)
        else:
            anomaly_points += sell_anomaly_scores.get(a, 2)

    score += min(anomaly_points, 40)  # Cap at 40

    # === BONUSES & PENALTIES ===

    # Bonus: Multiple strong buy signals together
    if is_purchase:
        strong_buy_signals = sum(1 for a in anomalies if a in [
            'ceo_founder_buy', 'cfo_buy', 'cluster_buy', 'position_doubled',
            'first_ever_purchase', 'consecutive_buying', 'massive_buy'
        ])
        if strong_buy_signals >= 3:
            score += 10
        elif strong_buy_signals >= 2:
            score += 5

    # Bonus: Multiple warning signals for sales
    if is_sale:
        warning_signals = sum(1 for a in anomalies if a in [
            'complete_exit', 'cluster_sell', 'cfo_sale', 'ceo_large_sale'
        ])
        if warning_signals >= 2:
            score += 8

    # Penalty: No ticker (can't post without ticker)
    if not ticker or ticker in ['N/A', 'NONE', 'None', '']:
        score = max(score - 30, 0)

    # Penalty: Suspiciously large values (likely data error)
    if value >= 1_000_000_000:  # $1B+
        score = max(score - 20, 0)

    # Bonus: Magnificent 7 + C-suite = always interesting
    if ticker in MAGNIFICENT_7 and role_score >= 14:
        score += 5

    return min(max(score, 0), 100)


def get_tier(score: int) -> int:
    """
    Determine posting tier based on score.

    Tier 1 (score >= 70): Post IMMEDIATELY with full tagging
    Tier 2 (score >= 50): Post within 1 hour
    Tier 3 (score >= 30): Batch post
    Tier 4 (score < 30): Daily roundup only
    """
    if score >= 70:
        return 1
    elif score >= 50:
        return 2
    elif score >= 30:
        return 3
    else:
        return 4


def get_tier_description(tier: int) -> str:
    """Get human-readable tier description."""
    descriptions = {
        1: "URGENT - Post immediately with full promotion",
        2: "HIGH - Post within 1 hour",
        3: "MEDIUM - Batch post",
        4: "LOW - Daily roundup only",
    }
    return descriptions.get(tier, "Unknown tier")


def score_and_tier(trade: Dict) -> Dict:
    """Add virality score and tier to trade dict."""
    score = calculate_virality_score(trade)
    tier = get_tier(score)

    trade['virality_score'] = score
    trade['tier'] = tier

    return trade


def explain_score(trade: Dict) -> Dict:
    """
    Calculate score with detailed breakdown explanation.
    Useful for debugging and understanding why a trade scored as it did.
    """
    explanation = {
        'role_score': 0,
        'size_score': 0,
        'company_score': 0,
        'anomaly_score': 0,
        'bonuses': 0,
        'penalties': 0,
        'final_score': 0,
        'details': []
    }

    transaction_type = trade.get('transaction_type', 'P')
    is_purchase = transaction_type == 'P'
    role = trade.get('insider_role', '').upper()
    officer_title = trade.get('officer_title', '').upper() if trade.get('officer_title') else ''
    role_check = role + ' ' + officer_title
    value = trade.get('total_value', 0)
    ticker = trade.get('ticker', '').upper() if trade.get('ticker') else ''

    # Role scoring
    if 'CEO' in role_check or 'FOUNDER' in role_check:
        explanation['role_score'] = 20
        explanation['details'].append(f"Role: CEO/Founder (+20)")
    elif 'CFO' in role_check:
        explanation['role_score'] = 18
        explanation['details'].append(f"Role: CFO (+18)")
    elif trade.get('is_director'):
        explanation['role_score'] = 6
        explanation['details'].append(f"Role: Director (+6)")

    # Size scoring
    if is_purchase and value >= 10_000_000:
        explanation['size_score'] = 16
        explanation['details'].append(f"Size: ${value/1e6:.1f}M purchase (+16)")
    elif is_purchase and value >= 1_000_000:
        explanation['size_score'] = 10
        explanation['details'].append(f"Size: ${value/1e6:.1f}M purchase (+10)")

    # Company scoring
    if ticker in MAGNIFICENT_7:
        explanation['company_score'] = 20
        explanation['details'].append(f"Company: {ticker} (Magnificent 7) (+20)")
    elif ticker in MEME_STOCKS:
        explanation['company_score'] = 18
        explanation['details'].append(f"Company: {ticker} (Meme Stock) (+18)")
    elif ticker in SP500:
        explanation['company_score'] = 10
        explanation['details'].append(f"Company: {ticker} (S&P 500) (+10)")

    # Anomaly scoring
    anomalies = trade.get('anomalies', '[]')
    if isinstance(anomalies, str):
        try:
            anomalies = json.loads(anomalies)
        except:
            anomalies = []

    for a in anomalies:
        explanation['details'].append(f"Anomaly: {a}")

    explanation['final_score'] = calculate_virality_score(trade)
    return explanation


if __name__ == "__main__":
    # Test with sample trades
    test_trades = [
        {
            'ticker': 'TSLA',
            'insider_role': 'CEO',
            'officer_title': 'Chief Executive Officer',
            'total_value': 25_000_000,
            'transaction_type': 'P',
            'is_officer': 1,
            'anomalies': '["ceo_founder_buy", "massive_buy", "first_purchase"]',
        },
        {
            'ticker': 'AAPL',
            'insider_role': 'Director',
            'total_value': 500_000,
            'transaction_type': 'P',
            'is_director': 1,
            'anomalies': '["director_buy", "first_purchase"]',
        },
        {
            'ticker': 'META',
            'insider_role': 'CFO',
            'officer_title': 'Chief Financial Officer',
            'total_value': 10_000_000,
            'transaction_type': 'S',
            'is_officer': 1,
            'anomalies': '["cfo_sale", "large_sale"]',
        },
        {
            'ticker': 'XYZ',
            'insider_role': 'Officer',
            'total_value': 75_000,
            'transaction_type': 'P',
            'is_officer': 1,
            'anomalies': '[]',
        },
        {
            'ticker': 'GME',
            'insider_role': 'Director',
            'total_value': 200_000,
            'transaction_type': 'P',
            'is_director': 1,
            'anomalies': '["cluster_buy", "director_buy"]',
        },
    ]

    print("=" * 60)
    print("VIRALITY SCORING TEST RESULTS")
    print("=" * 60)

    for trade in test_trades:
        result = score_and_tier(trade)
        tx_type = "BUY" if trade['transaction_type'] == 'P' else "SELL"
        tier = result.get('tier')
        score = result.get('virality_score')

        print(f"\n{tx_type}: ${result.get('ticker')} - {result.get('insider_role')}")
        print(f"  Value: ${result.get('total_value', 0):,.0f}")
        print(f"  Anomalies: {result.get('anomalies')}")
        print(f"  Score: {score}/100 → Tier {tier} ({get_tier_description(tier)})")
