"""
Virality scoring algorithm.
Determines how "viral" a trade is likely to be on social media.
Higher score = post immediately with full promotion.
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

    Scoring factors:
    - Insider role (CEO > Director)
    - Transaction size
    - Company recognition
    - Anomalies detected
    """
    score = 0

    # === INSIDER ROLE (max 25 points) ===
    role = trade.get('insider_role', '').upper()
    officer_title = trade.get('officer_title', '').upper() if trade.get('officer_title') else ''
    role_check = role + ' ' + officer_title

    if 'CEO' in role_check or 'CHIEF EXECUTIVE' in role_check:
        score += 25
    elif 'FOUNDER' in role_check:
        score += 25
    elif 'CFO' in role_check or 'CHIEF FINANCIAL' in role_check:
        score += 22
    elif 'COO' in role_check or 'CHIEF OPERATING' in role_check:
        score += 20
    elif 'CTO' in role_check or 'CHIEF TECHNOLOGY' in role_check:
        score += 18
    elif 'PRESIDENT' in role_check:
        score += 18
    elif trade.get('is_ten_percent_owner'):
        score += 15
    elif 'VP' in role_check or 'VICE PRESIDENT' in role_check:
        score += 10
    elif 'GENERAL COUNSEL' in role_check:
        score += 10
    elif trade.get('is_director'):
        score += 8
    elif trade.get('is_officer'):
        score += 8
    else:
        score += 3

    # === TRANSACTION SIZE (max 25 points) ===
    value = trade.get('total_value', 0)

    if value >= 50_000_000:
        score += 25
    elif value >= 20_000_000:
        score += 23
    elif value >= 10_000_000:
        score += 20
    elif value >= 5_000_000:
        score += 17
    elif value >= 2_000_000:
        score += 14
    elif value >= 1_000_000:
        score += 11
    elif value >= 500_000:
        score += 8
    elif value >= 250_000:
        score += 5
    elif value >= 100_000:
        score += 3
    else:
        score += 1

    # === COMPANY RECOGNITION (max 20 points) ===
    ticker = trade.get('ticker', '').upper() if trade.get('ticker') else ''

    if ticker in MAGNIFICENT_7:
        score += 20
    elif ticker in MEME_STOCKS:
        score += 18  # Meme stocks get high engagement
    elif ticker in FAANG:
        score += 17
    elif ticker in SP500:
        score += 12
    elif ticker:  # Has a ticker at least
        score += 5

    # === ANOMALIES DETECTED (max 25 points) ===
    anomalies = trade.get('anomalies', '[]')
    if isinstance(anomalies, str):
        try:
            anomalies = json.loads(anomalies)
        except (json.JSONDecodeError, TypeError):
            anomalies = []

    anomaly_scores = {
        'ceo_founder_buy': 10,
        'cluster_buy': 8,
        'first_buy_in_years': 8,
        'first_purchase': 5,
        'unusually_large': 7,
        'massive_value': 6,
        'large_value': 4,
        'million_plus': 3,
        'buy_during_crash': 7,
        'pre_earnings': 6,
        'major_shareholder_buy': 5,
        'director_buy': 2,
    }

    anomaly_points = sum(anomaly_scores.get(a, 2) for a in anomalies)
    score += min(anomaly_points, 25)  # Cap at 25

    # === BONUS: Multiple strong signals ===
    strong_signals = sum(
        1 for a in anomalies
        if a in ['ceo_founder_buy', 'cluster_buy', 'first_buy_in_years', 'massive_value', 'major_shareholder_buy']
    )
    if strong_signals >= 2:
        score += 5

    return min(score, 100)


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


if __name__ == "__main__":
    # Test with sample trades
    test_trades = [
        {
            'ticker': 'TSLA',
            'insider_role': 'CEO',
            'officer_title': 'Chief Executive Officer',
            'total_value': 10_000_000,
            'is_officer': 1,
            'anomalies': '["ceo_founder_buy", "massive_value"]',
        },
        {
            'ticker': 'AAPL',
            'insider_role': 'Director',
            'total_value': 500_000,
            'is_director': 1,
            'anomalies': '["first_purchase"]',
        },
        {
            'ticker': 'XYZ',
            'insider_role': 'Officer',
            'total_value': 75_000,
            'is_officer': 1,
            'anomalies': '[]',
        },
    ]

    print("Virality Scoring Test Results")
    print("=" * 50)

    for trade in test_trades:
        result = score_and_tier(trade)
        print(f"\nTicker: ${result.get('ticker')}")
        print(f"  Role: {result.get('insider_role')}")
        print(f"  Value: ${result.get('total_value', 0):,.0f}")
        print(f"  Score: {result.get('virality_score')}/100")
        print(f"  Tier: {result.get('tier')} - {get_tier_description(result.get('tier'))}")
