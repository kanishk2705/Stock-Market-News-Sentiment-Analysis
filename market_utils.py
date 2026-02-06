# market_utils.py
import yfinance as yf
import streamlit as st

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