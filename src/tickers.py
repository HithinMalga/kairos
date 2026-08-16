"""
Kairos - Tracked Tickers
A curated list of ~25 well-known, liquid stocks across sectors.
Keeping this list small and diverse makes the dashboard fast and easy to demo.
"""

TICKERS_BY_SECTOR = {
    "Tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX"],
    "Finance": ["JPM", "BAC", "GS", "V", "MA"],
    "Healthcare": ["JNJ", "PFE", "UNH"],
    "Consumer": ["WMT", "COST", "MCD", "NKE", "SBUX"],
    "Energy/Industrial": ["XOM", "CVX", "CAT", "BA"],
}

# Flat list for scripts that just need every ticker
TICKERS = [t for sector_tickers in TICKERS_BY_SECTOR.values() for t in sector_tickers]

# Reverse lookup: ticker -> sector
SECTOR_OF = {t: sector for sector, tickers in TICKERS_BY_SECTOR.items() for t in tickers}
