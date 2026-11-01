import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

WINDOW_SIZE = 60        # days of past prices the model sees
SIGNAL_THRESHOLD = 0.01 # predicted move needed for a BUY / SELL signal (1%)

PRICE_FEATURES = ["ret_1", "ret_2", "ret_3", "ret_4", "ret_5", "mom_5", "mom_20",
                  "vol_20", "rsi_14", "dist_sma50", "dist_sma200"]
SENTIMENT_FEATURES = ["sentiment_score", "sentiment_3d"]


def build_features(df):
    """
    One feature row per day, computed only from that day and earlier.
    Target 'next_return' is the following day's log return (NaN on the last row).
    """
    price = df["price"].astype(float).reset_index(drop=True)
    r = np.log(price).diff()
    f = pd.DataFrame(index=price.index)
    for lag in range(1, 6):
        f[f"ret_{lag}"] = r.shift(lag - 1)            # ret_1 = today's return
    f["mom_5"] = r.rolling(5).sum()
    f["mom_20"] = r.rolling(20).sum()
    f["vol_20"] = r.rolling(20).std()
    delta = price.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    f["rsi_14"] = (100 - 100 / (1 + gain / loss)) / 100
    f["dist_sma50"] = price / price.rolling(50).mean() - 1
    f["dist_sma200"] = price / price.rolling(200, min_periods=100).mean() - 1

    # FinBERT signal: +confidence for positive news, -confidence for negative, 0 otherwise
    if "sentiment" in df.columns:
        label = df["sentiment"].reset_index(drop=True).fillna("neutral")
        conf = df.get("confidence", pd.Series(0.0, index=df.index)).reset_index(drop=True).fillna(0.0).astype(float)
        score = np.where(label == "positive", conf, np.where(label == "negative", -conf, 0.0))
        f["sentiment_score"] = score
        f["sentiment_3d"] = pd.Series(score).rolling(3, min_periods=1).mean()
    else:
        f["sentiment_score"] = 0.0
        f["sentiment_3d"] = 0.0

    f["next_return"] = r.shift(-1)
    return f


class ReturnsModel:
    """
    Predicts tomorrow's log return from engineered features, then converts it to a price:
        predicted_price = today's price * exp(predicted return)
    Because it learns returns (not price levels), it is not limited to prices seen in training.
    """
    def __init__(self, kind="ridge", use_sentiment=False):
        self.kind, self.use_sentiment = kind, use_sentiment
        self.features = PRICE_FEATURES + (SENTIMENT_FEATURES if use_sentiment else [])
        label = {"ridge": "Ridge regression", "gbm": "Gradient boosting"}[kind]
        self.name = f"{label} on returns" + (" + sentiment" if use_sentiment else "")

    def _estimator(self):
        if self.kind == "ridge":
            return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
        return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=200,
                                             l2_regularization=1.0, min_samples_leaf=40, random_state=42)

    def fit(self, history):
        f = build_features(history).dropna(subset=["ret_5", "mom_20", "vol_20", "dist_sma50", "next_return"])
        self.model = self._estimator()
        X = f[self.features].fillna(0.0) if self.kind == "ridge" else f[self.features]
        self.model.fit(X, f["next_return"])

    def predict_return(self, history):
        last = build_features(history)[self.features].iloc[[-1]]
        X = last.fillna(0.0) if self.kind == "ridge" else last
        return float(self.model.predict(X)[0])

    def predict(self, history):
        return float(history["price"].iloc[-1]) * float(np.exp(self.predict_return(history)))


def prepare_sliding_window(data, window_size=WINDOW_SIZE):
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


def fit_model(prices, window_size=WINDOW_SIZE):
    """Trains the Random Forest on every sliding window in `prices`."""
    X, y = prepare_sliding_window(np.asarray(prices, dtype=float), window_size)
    # n_estimators=100 means we create 100 decision trees and average them
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X, y)
    return model


def predict_next(model, prices, window_size=WINDOW_SIZE):
    """Predicts the price that follows the last `window_size` prices."""
    last_window = np.asarray(prices, dtype=float)[-window_size:].reshape(1, -1)
    return float(model.predict(last_window)[0])


def price_signal(predicted_price, current_price, threshold=SIGNAL_THRESHOLD):
    if predicted_price > current_price * (1 + threshold):
        return "🟢 STRONG BUY"
    if predicted_price < current_price * (1 - threshold):
        return "🔴 STRONG SELL"
    return "⚪ HOLD"


# Chosen by the walk-forward comparison (results/model_comparison.md): lowest error and
# best risk-adjusted return of the candidates. No candidate beat the naive forecast.
def make_production_model():
    return ReturnsModel("ridge")


PRODUCTION_MODEL_NAME = make_production_model().name


def predict_next_day_price(ticker, df):
    """
    Predicts tomorrow's price with the production model (Ridge regression on returns).
    """
    # 1. PREPARE DATA
    if df.empty or 'price' not in df.columns:
        return None, "Insufficient Data"

    # Sort by date to ensure time order (work on a copy, never mutate the caller's frame)
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').dropna(subset=['price']).reset_index(drop=True)

    if len(df) < WINDOW_SIZE + 10:
        return None, "Need > 70 Days Data"

    # 2. TRAIN + 3. PREDICT TOMORROW
    model = make_production_model()
    model.fit(df)
    predicted_price = model.predict(df)

    # 4. GENERATE SIGNAL
    return predicted_price, price_signal(predicted_price, float(df['price'].iloc[-1]))
