"""
Tweet templates organized by tier and type.
Use {placeholders} for dynamic content.
"""

# === INSIDER TRADING TEMPLATES ===

INSIDER_TIER1_TEMPLATES = [
    """🚨 BREAKING: ${ticker} {insider_role} {insider_name} just made a MASSIVE buy

💰 Bought: {shares:,} shares
💵 Value: ${value_display}
📅 Filed: {time_ago}

{anomaly_text}

{insight_text}

{tags}""",

    """🔥 INSIDER ALERT: ${ticker}

{insider_role} just bought ${value_display} worth of stock

This is {anomaly_text}

{insight_text}

What does {insider_name} know? 👀

{tags}""",

    """🚨 ${ticker} {insider_role} BUYING

{insider_name} just filed:
→ {shares:,} shares purchased
→ ${value_display} total value
→ {time_ago}

{anomaly_text}

{insight_text}

{tags}""",
]

INSIDER_TIER2_TEMPLATES = [
    """🔔 INSIDER BUY: ${ticker}

{insider_role} {insider_name} purchased {shares:,} shares (${value_display})

{anomaly_text}

Filed {time_ago}

#InsiderTrading #{ticker_clean}""",

    """📊 ${ticker} — Insider Activity

{insider_role} bought ${value_display}

{anomaly_text}

{insight_text}

#SmartMoney #{ticker_clean}""",
]

INSIDER_TIER3_TEMPLATES = [
    """📈 ${ticker}: {insider_role} bought {shares:,} shares (${value_display})

{anomaly_text}

#InsiderBuying""",
]

DAILY_ROUNDUP_TEMPLATE = """📋 Today's Top Insider Buys:

{ranked_list}

Total insider buying today: ${total_value}

Which one are you watching? 👇

Full alerts: {link}

#InsiderTrading #SmartMoney"""

# === CLUSTER BUY TEMPLATE ===

CLUSTER_BUY_TEMPLATE = """👀 CLUSTER BUYING DETECTED: ${ticker}

{count} insiders have bought in the past {days} days:

{insider_list}

Total value: ${total_value}

When multiple insiders buy together, pay attention 📈

{tags}"""

# === CONGRESS TRADING TEMPLATES (Phase 2) ===

CONGRESS_TIER1_TEMPLATES = [
    """🏛️ CONGRESS TRADE ALERT

{politician_name} ({party}-{state}) just {action} ${ticker}

💰 Amount: {value_range}
📅 Trade: {trade_date}
📅 Disclosed: {disclosure_date}

{anomaly_text}

Do they know something? 🤔

{tags}""",

    """🚨 POLITICIAN STOCK TRADE

{politician_name} {action} ${ticker}

Amount: {value_range}
Chamber: {chamber}

{anomaly_text}

#CongressTrading #STOCKAct

{tags}""",
]

CONGRESS_TIER2_TEMPLATES = [
    """🏛️ {politician_name} ({party}) {action} ${ticker}

Amount: {value_range}
Date: {trade_date}

{anomaly_text}

#CongressTrading""",

    """📊 Congress Trade: ${ticker}

{politician_name} ({party}-{state})
{action}: {value_range}

{anomaly_text}

#STOCKAct""",
]

CONGRESS_TIER3_TEMPLATES = [
    """🏛️ ${ticker}: {politician_name} ({party}) {action} {value_range}

#CongressTrading""",
]

CONGRESS_AGGREGATE_TEMPLATE = """📊 What is Congress buying this month?

TOP STOCKS BY CONGRESSIONAL PURCHASES:

{ranked_list}

They're loading up on {top_sector}. Are you?

Full data: {link}

#CongressTrading #STOCKAct"""

# === HEDGE FUND 13F TEMPLATES (Phase 3) ===

HEDGE_FUND_TIER1_TEMPLATES = [
    """🚨 {manager_name} 13F FILING

{fund_name} just disclosed Q{quarter} holdings:

💼 Portfolio: ${total_value}
📊 Positions: {position_count}

Top Holdings:
{top_holdings_text}

What's {manager_name} seeing? 🧐

{tags}""",

    """📈 HEDGE FUND ALERT: {manager_name}

{fund_name} Q{quarter} 13F just dropped

${total_value} portfolio across {position_count} positions

{anomaly_text}

{tags}""",
]

HEDGE_FUND_TIER2_TEMPLATES = [
    """📊 13F Filing: {fund_name}

Manager: {manager_name}
Portfolio: ${total_value}
Positions: {position_count}

{anomaly_text}

#13F #HedgeFund""",
]

HEDGE_FUND_TIER3_TEMPLATES = [
    """📈 {fund_name} filed 13F: ${total_value} across {position_count} positions

#13F""",
]

# === ANOMALY TEXT SNIPPETS ===

ANOMALY_TEXTS = {
    "first_buy_in_years": "This is the FIRST insider buy at {company} since {last_buy_year}",
    "largest_purchase": "This is the LARGEST insider purchase at {company} in {timeframe}",
    "cluster_buy": "{count} insiders have bought this week",
    "buy_during_crash": "Stock is DOWN {pct_down}% this month — insider buying the dip",
    "pre_earnings": "Earnings in {days_to_earnings} days 👀",
    "ceo_founder": "CEO/Founder buying = maximum conviction signal",
    "first_purchase_ever": "This is {insider_name}'s FIRST EVER purchase",
    "10x_normal": "This purchase is {multiple}x their average buy size",
}

INSIGHT_TEXTS = [
    "Insiders are usually right. They know more than we do.",
    "Follow the smart money.",
    "When CEOs buy with their own money, pay attention.",
    "Insider buying often precedes positive news.",
    "This level of conviction is rare.",
]


def get_random_insight():
    import random
    return random.choice(INSIGHT_TEXTS)
