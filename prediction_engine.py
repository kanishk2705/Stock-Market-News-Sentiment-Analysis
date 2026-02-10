import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

def prepare_sliding_window(data, window_size=60):
    """
    Converts a list of prices into a supervised learning problem.
    Input: [100, 101, 102, 103...]
    X: [[100, 101, 102]], y: [103]
    """
    X, y = [], []
    for i in range(len(data) - window_size):
        X.append(data[i:i+window_size])
        y.append(data[i+window_size])
    return np.array(X), np.array(y)

def predict_next_day_price(ticker, df):
    """
    Uses Random Forest to predict the next price based on the last 60 days.
    """
    # 1. PREPARE DATA
    if df.empty or 'price' not in df.columns:
        return None, "Insufficient Data"

    # Sort by date to ensure time order
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # Extract just the prices
    prices = df['price'].values
    
    # 2. CREATE FEATURES (Sliding Window)
    WINDOW_SIZE = 60
    
    if len(prices) < WINDOW_SIZE + 10:
        return None, "Need > 70 Days Data"

    # X = Matrix of past 60 days, y = Target next day
    X, y = prepare_sliding_window(prices, WINDOW_SIZE)

    # 3. TRAIN RANDOM FOREST MODEL
    # n_estimators=100 means we create 100 decision trees and average them
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)

    # 4. PREDICT TOMORROW
    # Get the very last 60 days from the dataset
    last_window = prices[-WINDOW_SIZE:]
    last_window = last_window.reshape(1, -1) # Reshape to be 2D array [1, 60]
    
    predicted_price = model.predict(last_window)[0]

    # 5. GENERATE SIGNAL
    current_price = prices[-1]
    
    # Threshold: 1% change
    if predicted_price > current_price * 1.01:
        signal = "🟢 STRONG BUY"
    elif predicted_price < current_price * 0.99:
        signal = "🔴 STRONG SELL"
    else:
        signal = "⚪ HOLD"

    return float(predicted_price), signal