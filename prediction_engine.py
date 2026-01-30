import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta

def predict_next_day_price(ticker, df):
    """
    Trains a Linear Regression model on the stock's history to forecast the next price.
    Returns: Predicted Price (float), Signal (Buy/Sell/Hold)
    """
    # 1. SAFETY CHECK: We need history to predict the future.
    # If the robot has run for less than 5 days, we cannot predict yet.
    if len(df) < 5:
        return None, "Not Enough Data"

    # 2. PREPARE DATA
    # We create a copy to avoid messing up the original dashboard data
    df = df.sort_values(by='timestamp').copy()
    
    # Feature Engineering: Convert Date to "Day Number" (0, 1, 2, 3...)
    df['Days'] = (df['timestamp'] - df['timestamp'].min()).dt.days
    
    # Feature Engineering: Combine Sentiment Label & Confidence into one score
    # Positive (0.9) -> +0.9
    # Negative (0.9) -> -0.9
    # Neutral -> 0
    sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1}
    df['Sentiment_Score'] = df['sentiment'].map(sentiment_map) * df['confidence']
    
    # X (Inputs): Time and Sentiment
    X = df[['Days', 'Sentiment_Score']].values
    # y (Target): The Stock Price
    y = df['price'].values

    # 3. TRAIN MODEL (The "Learning" Step)
    model = LinearRegression()
    model.fit(X, y)

    # 4. PREDICT TOMORROW
    # "Tomorrow" is the last day + 1
    next_day_index = df['Days'].iloc[-1] + 1
    
    # We assume tomorrow's news sentiment is similar to today's (Naive assumption for V1)
    latest_sentiment = df['Sentiment_Score'].iloc[-1]
    
    # Ask the model: "Given it's Day X+1 and sentiment is Y, what is the price?"
    prediction = model.predict([[next_day_index, latest_sentiment]])[0]
    
    # 5. GENERATE SIGNAL
    current_price = df['price'].iloc[-1]
    threshold = 0.02 # 2% movement threshold
    
    if prediction > current_price * (1 + threshold):
        signal = "🟢 STRONG BUY"
    elif prediction < current_price * (1 - threshold):
        signal = "🔴 STRONG SELL"
    else:
        signal = "⚪ HOLD"

    return prediction, signal

if __name__ == "__main__":
    print("Run this via main.py or app.py")