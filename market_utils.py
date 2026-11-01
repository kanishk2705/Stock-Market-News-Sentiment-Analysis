# market_utils.py
import yfinance as yf
import streamlit as st
import requests

# Yahoo ticker suffix -> currency symbol (US tickers have no suffix)
CURRENCY_BY_SUFFIX = {
    ".NS": "₹", ".BO": "₹",   # India (NSE / BSE)
    ".L": "£",                # London
    ".T": "¥",                # Tokyo
    ".HK": "HK$",             # Hong Kong
    ".TO": "C$", ".V": "C$",  # Canada
    ".AX": "A$",              # Australia
    ".DE": "€", ".PA": "€", ".AS": "€", ".MI": "€", ".MC": "€",  # Euro area
}


def get_currency_symbol(ticker):
    """Returns the display currency for a Yahoo ticker, e.g. 'INFY.NS' -> '₹'."""
    ticker = (ticker or "").upper()
    if ticker in ("^NSEI", "^BSESN"):
        return "₹"
    for suffix, symbol in CURRENCY_BY_SUFFIX.items():
        if ticker.endswith(suffix):
            return symbol
    return "$"


@st.cache_data(ttl=300) # Cache data for 5 minutes to prevent loading delays
def get_market_indices():
    """
    Fetches live data for global indices (Nifty, Sensex, US Markets).
    Returns a list of dictionaries.
    """
    indices = {
        "NIFTY 50": "^NSEI",
        "SENSEX": "^BSESN",
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC"
    }

    data = []
    tickers = list(indices.values())

    try:
        # Download last 5 days of data to ensure we get a valid 'Close' even on weekends
        market_data = yf.download(tickers, period="5d", interval="1d", progress=False)['Close']

        for name, ticker in indices.items():
            if ticker in market_data.columns:
                # Drop NaN values (holidays/weekends) and get the last 2 valid days
                series = market_data[ticker].dropna()

                if len(series) >= 2:
                    current_price = series.iloc[-1]
                    prev_close = series.iloc[-2]

                    # Calculate % Change
                    change = ((current_price - prev_close) / prev_close) * 100

                    data.append({
                        "Index": name,
                        "Price": current_price,
                        "Change": change
                    })
    except Exception as e:
        print(f"⚠️ Market Data Error: {e}")
        # Return empty list so the app doesn't crash
        return []

    return data


@st.cache_data(ttl=3600)
def search_yahoo_finance(query):
    """
    Searches Yahoo Finance for tickers matching the query.
    Supports US, Indian (NSE/BSE), and global stocks.
    """
    if not query or not query.strip():
        return []

    # This is the public endpoint Yahoo uses for its own search bar
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query.strip(), "quotesCount": 10, "newsCount": 0}

    # We need a User-Agent to look like a real browser, otherwise Yahoo blocks us
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()

        results = []
        for item in data.get('quotes', []):
            # Keep tradable instruments that have a display name
            if 'symbol' in item and (item.get('shortname') or item.get('longname')):
                results.append({
                    'symbol': item['symbol'],                               # e.g., "TATASTEEL.NS"
                    'name': item.get('longname') or item.get('shortname'),  # e.g., "Tata Steel Limited"
                    'exchange': item.get('exchDisp', item.get('exchange', '')),  # e.g., "NSE"
                    'type': item.get('quoteType', '')                       # e.g., "EQUITY"
                })
        return results
    except Exception as e:
        print(f"Search Error: {e}")
        return []
