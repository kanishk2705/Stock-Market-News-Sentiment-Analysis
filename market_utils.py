# market_utils.py
import yfinance as yf
import streamlit as st
import requests

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

def search_yahoo_finance(query):
    """
    Searches Yahoo Finance for tickers matching the query.
    Supports US, Indian (NSE/BSE), and global stocks.
    """
    if not query:
        return []
    
    # This is the "secret" API endpoint Yahoo uses for its search bar
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=10&newsCount=0"
    
    # We need a User-Agent to look like a real browser, otherwise Yahoo blocks us
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        results = []
        if 'quotes' in data:
            for item in data['quotes']:
                # Filter out useless things like "Option" or "Future" if you only want stocks
                # but for now, let's keep Equities and ETFs
                if 'symbol' in item and 'shortname' in item:
                    results.append({
                        'symbol': item['symbol'],     # e.g., "TATASTEEL.NS"
                        'name': item['shortname'],    # e.g., "Tata Steel Limited"
                        'exchange': item['exchange'], # e.g., "NSI" (NSE India) or "NYQ" (NYSE)
                        'type': item['quoteType']     # e.g., "EQUITY"
                    })
        return results
    except Exception as e:
        print(f"Search Error: {e}")
        return []