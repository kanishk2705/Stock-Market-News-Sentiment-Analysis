import pandas as pd
import numpy as np

def calculate_technical_indicators(df):
    """
    Adds SMA-50, SMA-200, and RSI-14 to the dataframe using pure Pandas.
    (No heavy dependencies like pandas_ta required)
    """
    if df.empty:
        return df

    # Ensure we are working with a copy to avoid SettingWithCopy warnings
    df = df.copy()
    
    # 1. Simple Moving Averages (SMA)
    # The 'rolling' function handles the math natively
    df['SMA_50'] = df['price'].rolling(window=50).mean()
    df['SMA_200'] = df['price'].rolling(window=200).mean()
    
    # 2. RSI (Relative Strength Index) - Manual Calculation
    # Formula: RSI = 100 - (100 / (1 + RS))
    delta = df['price'].diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate the Exponential Moving Average (EMA) for smoother RSI
    # Standard RSI uses a 14-period smoothing (com=13 means alpha=1/14)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Fill NaN values (start of data) with backward fill so charts don't break
    df = df.bfill()
    
    return df

def get_market_signal(latest_row):
    """
    Returns a text signal based on Technicals.
    """
    signals = []
    
    # RSI Logic
    # We use .get() safely in case the column is missing
    rsi = latest_row.get('RSI', 50)
    if pd.isna(rsi): rsi = 50 
    
    if rsi > 70:
        signals.append("⚠️ Overbought (RSI > 70)")
    elif rsi < 30:
        signals.append("✅ Oversold (RSI < 30)")
        
    # SMA Logic (Price vs Trends)
    price = latest_row.get('price', 0)
    sma_50 = latest_row.get('SMA_50', 0)
    sma_200 = latest_row.get('SMA_200', 0)
    
    # Check if we actually have SMA values (not 0) before judging
    if sma_50 > 0 and sma_200 > 0:
        if price > sma_50 and price > sma_200:
            signals.append("📈 Bullish Trend")
        elif price < sma_50 and price < sma_200:
            signals.append("📉 Bearish Trend")
        elif price > sma_50:
            signals.append("🔄 Recovery (Above SMA50)")
        
    if not signals:
        return "⚖️ Market Neutral"
        
    return " | ".join(signals)