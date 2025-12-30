"""
Twitter accounts to tag based on stock or topic.
Format: ticker/topic -> list of handles (without @)
"""

# Stock-specific influencers
STOCK_INFLUENCERS = {
    "TSLA": ["TESLAcharts", "WholeMarsBlog", "SawyerMerritt", "TroyTeslike", "elikitten"],
    "NVDA": ["borrowed_ideas", "Deepinsideleak", "FGoria"],
    "AAPL": ["markgurman", "mingchikuo"],
    "META": ["alexheath", "MikeIsaac"],
    "AMZN": ["JasonDelRey", "spaborner"],
    "GOOGL": ["lorenzofb", "alexheath"],
    "MSFT": ["maborik", "tomwarren"],
    "AMD": ["IanCutress", "chilobot"],
    "GME": ["TheRoaringKitty", "GMEdd"],
    "COIN": ["zaborowsky", "tier10k"],
    "PLTR": ["Palantir_Bull", "JoshShultz84"],
}

# General FinTwit personalities (use for high-profile trades)
FINTWIT_PERSONALITIES = [
    "chaabornn",
    "TrungTPhan",
    "litaborges",
    "BrianFeroldi",
    "QCompounding",
    "10kdiver",
    "borrowed_ideas",
    "ChrisBloomstran",
    "StockMKTNewz",
    "unusual_whales",
    "Fxhedgers",
    "DeItaone",
    "zerohedge",
]

# Finance journalists (use for newsworthy trades)
FINANCE_JOURNALISTS = [
    "DeItaone",
    "Fxhedgers",
    "carlquintanilla",
    "KellyCNBC",
    "jimcramer",
]

# Congress trading accounts (for Phase 2)
CONGRESS_TRACKERS = [
    "unusual_whales",
    "QuiverQuant",
    "PelosiTracker_",
    "CapitolTrades",
]

# Hedge fund / 13F accounts (for Phase 3)
HEDGE_FUND_TRACKERS = [
    "BurryTracker",
    "WhaleWisdom",
    "HedgeFollow",
]


def get_tags_for_stock(ticker: str, max_tags: int = 3) -> list:
    """Get relevant Twitter handles to tag for a given stock."""
    tags = []

    # Stock-specific tags first
    if ticker in STOCK_INFLUENCERS:
        tags.extend(STOCK_INFLUENCERS[ticker][:2])

    # Fill remaining with general FinTwit
    remaining = max_tags - len(tags)
    if remaining > 0:
        import random
        tags.extend(random.sample(FINTWIT_PERSONALITIES, min(remaining, len(FINTWIT_PERSONALITIES))))

    return tags[:max_tags]


def get_tags_for_congress(max_tags: int = 3) -> list:
    """Get Twitter handles for congressional trading alerts."""
    return CONGRESS_TRACKERS[:max_tags]


def get_tags_for_hedge_fund(fund_name: str, max_tags: int = 3) -> list:
    """Get Twitter handles for hedge fund alerts."""
    tags = HEDGE_FUND_TRACKERS[:2]
    # Add general FinTwit
    import random
    remaining = max_tags - len(tags)
    if remaining > 0:
        tags.extend(random.sample(FINTWIT_PERSONALITIES, min(remaining, len(FINTWIT_PERSONALITIES))))
    return tags[:max_tags]
