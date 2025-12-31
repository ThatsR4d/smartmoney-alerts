"""
Tweet templates organized by tier and type.
Use {placeholders} for dynamic content.
"""

# === INSIDER TRADING TEMPLATES ===

INSIDER_TIER1_TEMPLATES = [
    """🚨 INSIDER {action}: ${ticker} ({company_name})

{insider_role} {insider_name} just {action_past} {shares:,} shares

💰 Value: ${value_display}
💵 Price: ${price_display}/share
📅 Filed: {time_ago}

{anomaly_text}

{insight_text}

#InsiderTrading #{ticker_clean} {tags}""",

    """🔥 MAJOR INSIDER {action}: ${ticker}

{company_name}

{insider_role} {action_past} ${value_display} worth of stock

{anomaly_text}

{insight_text}

What does {insider_name} know? 👀

#{ticker_clean} #SmartMoney {tags}""",

    """🚨 ${ticker} — {company_name}

{insider_role} {insider_name} just filed:
→ {action}: {shares:,} shares
→ Value: ${value_display}
→ Price: ${price_display}/share

{anomaly_text}

{insight_text}

#InsiderTrading #{ticker_clean} {tags}""",
]

INSIDER_TIER2_TEMPLATES = [
    """🔔 INSIDER {action}: ${ticker}

{company_name}

{insider_role} {insider_name} {action_past} {shares:,} shares (${value_display})

{anomaly_text}

Filed {time_ago}

#InsiderTrading #{ticker_clean}""",

    """📊 ${ticker} — {company_name}

Insider {action}:
• {insider_role}: {insider_name}
• Shares: {shares:,}
• Value: ${value_display}

{anomaly_text}

#SmartMoney #{ticker_clean}""",
]

INSIDER_TIER3_TEMPLATES = [
    """📈 ${ticker} ({company_name}): {insider_role} {action_past} {shares:,} shares (${value_display})

{anomaly_text}

#InsiderTrading""",
]

# === SELL TEMPLATES ===

INSIDER_SELL_TIER1_TEMPLATES = [
    """⚠️ INSIDER SALE: ${ticker} ({company_name})

{insider_role} {insider_name} just SOLD {shares:,} shares

💰 Value: ${value_display}
💵 Price: ${price_display}/share
📅 Filed: {time_ago}

{anomaly_text}

Why is {insider_name} selling? 🤔

#InsiderSelling #{ticker_clean} {tags}""",
]

INSIDER_SELL_TIER2_TEMPLATES = [
    """🔔 INSIDER SALE: ${ticker}

{company_name}

{insider_role} {insider_name} sold {shares:,} shares (${value_display})

{anomaly_text}

Filed {time_ago}

#InsiderSelling #{ticker_clean}""",
]

DAILY_ROUNDUP_TEMPLATE = """📋 Today's Top Insider Trades:

{ranked_list}

Total insider activity: ${total_value}

Which one are you watching? 👇

{link}

#InsiderTrading #SmartMoney"""

# === CLUSTER BUY TEMPLATE ===

CLUSTER_BUY_TEMPLATE = """👀 CLUSTER BUYING: ${ticker} ({company_name})

{count} insiders have bought in the past {days} days:

{insider_list}

Total value: ${total_value}

When multiple insiders buy together, pay attention 📈

#ClusterBuying #{ticker_clean} {tags}"""

# === CONGRESS TRADING TEMPLATES ===

CONGRESS_TIER1_TEMPLATES = [
    """🏛️ CONGRESS TRADE: ${ticker}

{company_name}

{politician_name} ({party}-{state}) {action}

💰 Amount: {value_range}
📅 Trade Date: {trade_date}
📅 Disclosed: {disclosure_date}

{anomaly_text}

What do they know? 🤔

#CongressTrading #STOCKAct {tags}""",

    """🚨 POLITICIAN TRADE: ${ticker}

{company_name}

{politician_name} ({party}) {action}

Amount: {value_range}
Chamber: {chamber}

{anomaly_text}

#CongressTrading #{ticker_clean} {tags}""",
]

CONGRESS_TIER2_TEMPLATES = [
    """🏛️ {politician_name} ({party}-{state}) {action} ${ticker}

{company_name}

Amount: {value_range}
Date: {trade_date}

{anomaly_text}

#CongressTrading #{ticker_clean}""",

    """📊 Congress Trade: ${ticker}

{company_name}

{politician_name} ({party}-{state})
{action}: {value_range}

{anomaly_text}

#STOCKAct""",
]

CONGRESS_TIER3_TEMPLATES = [
    """🏛️ ${ticker} ({company_name}): {politician_name} ({party}) {action} {value_range}

#CongressTrading""",
]

CONGRESS_AGGREGATE_TEMPLATE = """📊 What is Congress buying this month?

TOP STOCKS BY CONGRESSIONAL PURCHASES:

{ranked_list}

They're loading up on {top_sector}. Are you?

{link}

#CongressTrading #STOCKAct"""

# === HEDGE FUND 13F TEMPLATES ===

HEDGE_FUND_TIER1_TEMPLATES = [
    """🚨 13F FILING: {manager_name}

{fund_name} disclosed Q{quarter} holdings:

💼 Portfolio: ${total_value}
📊 Positions: {position_count}

Top Holdings:
{top_holdings_text}

What's {manager_name} seeing? 🧐

#13F #HedgeFund {tags}""",

    """📈 HEDGE FUND ALERT: {fund_name}

Manager: {manager_name}
Q{quarter} 13F filed

${total_value} across {position_count} positions

{anomaly_text}

#13F #HedgeFund {tags}""",
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
    "first_buy_in_years": "⚡ FIRST insider buy at {company} since {last_buy_year}",
    "largest_purchase": "⚡ LARGEST insider purchase at {company} in {timeframe}",
    "cluster_buy": "⚡ {count} insiders have bought this week",
    "buy_during_crash": "⚡ Stock DOWN {pct_down}% this month — insider buying the dip",
    "pre_earnings": "⚡ Earnings in {days_to_earnings} days 👀",
    "ceo_founder": "⚡ CEO/Founder buying = maximum conviction",
    "first_purchase_ever": "⚡ {insider_name}'s FIRST EVER purchase",
    "10x_normal": "⚡ {multiple}x their average buy size",
    "large_sale": "⚡ Significant insider selling activity",
}

INSIGHT_TEXTS = [
    "Insiders know more than we do.",
    "Follow the smart money.",
    "When executives buy with their own money, pay attention.",
    "Insider buying often precedes positive news.",
    "This level of conviction is rare.",
    "Insiders are rarely wrong.",
]


def get_random_insight():
    import random
    return random.choice(INSIGHT_TEXTS)
