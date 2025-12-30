# High-profile tickers that get extra attention
FAANG = {"META", "AAPL", "AMZN", "NFLX", "GOOGL", "GOOG"}

MEME_STOCKS = {
    "TSLA", "GME", "AMC", "BBBY", "PLTR", "NIO", "RIVN", "LCID",
    "SOFI", "HOOD", "COIN", "MARA", "RIOT", "NVDA", "AMD"
}

MAGNIFICENT_7 = {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA"}

# SP500 tickers (abbreviated - expand this)
SP500 = {
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "GOOG", "META", "TSLA", "BRK.B",
    "UNH", "JNJ", "JPM", "V", "PG", "XOM", "MA", "HD", "CVX", "MRK", "ABBV",
    "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "ACN", "TMO",
    "ABT", "DHR", "NEE", "VZ", "ADBE", "NKE", "PM", "TXN", "WFC", "CRM",
    "BMY", "UPS", "MS", "RTX", "HON", "QCOM", "UNP", "LOW", "ORCL", "IBM",
    "INTC", "SPGI", "CAT", "GE", "AMGN", "INTU", "BA", "DE", "AXP", "ISRG",
    "MDLZ", "SYK", "ADI", "REGN", "BKNG", "BLK", "GILD", "VRTX", "C", "SBUX",
    "MMC", "ADP", "TJX", "PLD", "CI", "CB", "SCHW", "LMT", "SO", "MO",
    "DUK", "EOG", "ZTS", "TMUS", "BDX", "CL", "NOC", "CSX", "ICE", "SHW",
    "CME", "ITW", "WM", "PNC", "USB", "TGT", "EQIX", "FDX", "EL", "GD",
    "ATVI", "EMR", "MU", "LRCX", "AMAT", "KLAC", "SNPS", "CDNS", "MRVL",
    "PANW", "CRWD", "DDOG", "ZS", "SNOW", "NET", "ABNB", "UBER", "LYFT",
}

# Company name variations for parsing
COMPANY_ALIASES = {
    "APPLE INC": "AAPL",
    "MICROSOFT CORP": "MSFT",
    "MICROSOFT CORPORATION": "MSFT",
    "AMAZON COM INC": "AMZN",
    "AMAZON.COM INC": "AMZN",
    "AMAZON.COM, INC.": "AMZN",
    "TESLA INC": "TSLA",
    "TESLA, INC.": "TSLA",
    "NVIDIA CORP": "NVDA",
    "NVIDIA CORPORATION": "NVDA",
    "META PLATFORMS": "META",
    "META PLATFORMS, INC.": "META",
    "ALPHABET INC": "GOOGL",
    "ALPHABET INC.": "GOOGL",
    "NETFLIX INC": "NFLX",
    "NETFLIX, INC.": "NFLX",
    "INTEL CORP": "INTC",
    "INTEL CORPORATION": "INTC",
    "AMD": "AMD",
    "ADVANCED MICRO DEVICES": "AMD",
    "PALANTIR TECHNOLOGIES": "PLTR",
    "COINBASE GLOBAL": "COIN",
    "GAMESTOP CORP": "GME",
    "AMC ENTERTAINMENT": "AMC",
    "RIVIAN AUTOMOTIVE": "RIVN",
    "LUCID GROUP": "LCID",
    "SNOWFLAKE INC": "SNOW",
    "CROWDSTRIKE HOLDINGS": "CRWD",
    "DATADOG INC": "DDOG",
    "UBER TECHNOLOGIES": "UBER",
    "AIRBNB INC": "ABNB",
    "SALESFORCE INC": "CRM",
    "SALESFORCE, INC.": "CRM",
    "JPMORGAN CHASE": "JPM",
    "BANK OF AMERICA": "BAC",
    "WELLS FARGO": "WFC",
    "GOLDMAN SACHS": "GS",
    "MORGAN STANLEY": "MS",
}
